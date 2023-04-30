# This file is part of django-ca (https://github.com/mathiasertl/django-ca).
#
# django-ca is free software: you can redistribute it and/or modify it under the terms of the GNU General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# django-ca is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along with django-ca. If not, see
# <http://www.gnu.org/licenses/>.

"""Management command to sign a new certificate.

.. seealso:: https://docs.djangoproject.com/en/dev/howto/custom-management-commands/
"""

import sys
from datetime import timedelta
from typing import Any, List, Optional

from cryptography import x509
from cryptography.x509.oid import ExtensionOID, NameOID

from django.core.management.base import CommandError, CommandParser
from django.utils import timezone

from django_ca import ca_settings
from django_ca.constants import EXTENSION_KEYS
from django_ca.management.base import BaseSignCertCommand
from django_ca.models import Certificate, CertificateAuthority, Watcher
from django_ca.profiles import profiles
from django_ca.typehints import AllowedHashTypes


class Command(BaseSignCertCommand):  # pylint: disable=missing-class-docstring
    help = f"""Sign a CSR and output signed certificate. The defaults depend on the configured
default profile, currently {ca_settings.CA_DEFAULT_PROFILE}."""

    add_extensions_help = """Values for more complex x509 extensions. This is for advanced usage only, the
profiles already set the correct values for the most common use cases. See
https://django-ca.readthedocs.io/en/latest/extensions.html for more information."""
    subject_help = """The certificate subject of the CSR is not used. The default subject is configured
            with the CA_DEFAULT_SUBJECT setting and may be overwritten by a profile named with
            --profile. The --subject option allows you to name a CommonName (which is not usually
            in the defaults) and override any default values."""

    def add_cn_in_san(self, parser: CommandParser) -> None:
        """Add argument group for the CommonName-in-SubjectAlternativeName options."""
        if ca_settings.CA_PROFILES[ca_settings.CA_DEFAULT_PROFILE]["cn_in_san"]:
            cn_in_san_default = " (default)"
            cn_not_in_san_default = ""
        else:
            cn_in_san_default = ""
            cn_not_in_san_default = " (default)"

        group = parser.add_argument_group(
            "CommonName in subjectAltName",
            """Whether or not to automatically include the CommonName (given in --subject) in the
            list of subjectAltNames (given by --alt).""",
        )
        group = group.add_mutually_exclusive_group()

        group.add_argument(
            "--cn-not-in-san",
            default=None,
            action="store_false",
            dest="cn_in_san",
            help=f"Do not add the CommonName as subjectAlternativeName{cn_not_in_san_default}.",
        )
        group.add_argument(
            "--cn-in-san",
            default=None,
            action="store_true",
            dest="cn_in_san",
            help=f"Add the CommonName as subjectAlternativeName{cn_in_san_default}.",
        )

    def add_arguments(self, parser: CommandParser) -> None:
        general_group = self.add_base_args(parser)
        self.add_cn_in_san(parser)

        general_group.add_argument(
            "--csr",
            dest="csr_path",
            default="-",
            metavar="FILE",
            help="The path to the certificate to sign, if omitted, you will be be prompted.",
        )
        general_group.add_argument(
            "-b", "--bundle", default=False, action="store_true", help="Output the whole certificate bundle."
        )

        self.add_profile(
            parser,
            """Sign certificate based on the given profile. A profile only sets the the
                         default values, options like --key-usage still override the profile.""",
        )

    def handle(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        ca: CertificateAuthority,
        subject: Optional[x509.Name],
        expires: Optional[timedelta],
        watch: List[str],
        password: Optional[bytes],
        cn_in_san: bool,
        csr_path: str,
        bundle: bool,
        profile: Optional[str],
        out: Optional[str],
        algorithm: Optional[AllowedHashTypes],
        extended_key_usage: Optional[x509.ExtendedKeyUsage],
        extended_key_usage_critical: bool,
        key_usage: Optional[x509.KeyUsage],
        key_usage_critical: bool,
        ocsp_no_check: bool,
        ocsp_no_check_critical: bool,
        **options: Any,
    ) -> None:
        # Validate parameters early so that we can return better feedback to the user.
        if ca.expires < timezone.now():
            raise CommandError("Certificate Authority has expired.")
        if ca.revoked:
            raise CommandError("Certificate Authority is revoked.")

        # Get/validate signature hash algorithm
        algorithm = self.get_hash_algorithm(ca.key_type, algorithm, ca.algorithm)

        profile_obj = profiles[profile]
        self.test_options(ca=ca, expires=expires, password=password, profile=profile_obj, **options)

        # get list of watchers
        watchers = [Watcher.from_addr(addr) for addr in watch]

        # get extensions based on profiles
        extensions: List[x509.Extension[x509.ExtensionType]] = []

        for ext_type in self.sign_extensions:
            ext_key = EXTENSION_KEYS[ext_type.oid]
            if options[ext_key]:
                extensions.append(options[ext_key])

        if extended_key_usage is not None:
            extensions.append(
                x509.Extension(
                    oid=ExtensionOID.EXTENDED_KEY_USAGE,
                    critical=extended_key_usage_critical,
                    value=extended_key_usage,
                )
            )
        if key_usage is not None:
            extensions.append(
                x509.Extension(oid=ExtensionOID.KEY_USAGE, critical=key_usage_critical, value=key_usage)
            )
        if ocsp_no_check is True:
            extensions.append(
                x509.Extension(
                    oid=ExtensionOID.OCSP_NO_CHECK, critical=ocsp_no_check_critical, value=x509.OCSPNoCheck()
                )
            )

        cname = None
        if subject is not None:
            cname = subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if not cname and not options["subject_alternative_name"]:
            raise CommandError("Must give at least a CN in --subject or one or more --alt arguments.")

        # Read the CSR
        if csr_path == "-":
            self.stdout.write("Please paste the CSR:")
            csr_bytes = b""
            while True:
                csr_bytes += sys.stdin.buffer.read(1)
                # COVERAGE NOTE: mock function always returns the full string, so we always break right away
                if csr_bytes.strip().endswith(b"-----END CERTIFICATE REQUEST-----"):  # pragma: no branch
                    break
        else:
            with open(csr_path, "rb") as csr_stream:
                csr_bytes = csr_stream.read()

        if csr_bytes.startswith(b"-----BEGIN CERTIFICATE REQUEST-----"):
            csr = x509.load_pem_x509_csr(csr_bytes)
        else:
            csr = x509.load_der_x509_csr(csr_bytes)

        try:
            cert = Certificate.objects.create_cert(
                ca,
                csr,
                profile=profile_obj,
                cn_in_san=cn_in_san,
                expires=expires,
                extensions=extensions,
                password=password,
                subject=subject,
                algorithm=algorithm,
            )
        except Exception as ex:
            raise CommandError(ex) from ex

        cert.watchers.add(*watchers)

        if bundle is True:
            output = cert.bundle_as_pem
        else:
            output = cert.pub.pem

        if out:
            with open(out, "w", encoding="ascii") as stream:
                stream.write(output)
        else:
            self.stdout.write(output)
