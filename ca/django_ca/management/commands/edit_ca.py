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

"""Management command to edit a certificate authority.

.. seealso:: https://docs.djangoproject.com/en/dev/howto/custom-management-commands/
"""

from typing import Any, List, Optional

from cryptography import x509
from cryptography.x509.oid import ExtensionOID

from django.core.management.base import CommandError, CommandParser

from django_ca import ca_settings
from django_ca.management.base import BaseCommand
from django_ca.management.mixins import CertificateAuthorityDetailMixin
from django_ca.models import CertificateAuthority
from django_ca.utils import format_general_name


class Command(CertificateAuthorityDetailMixin, BaseCommand):
    """Implement :command:`manage.py edit_ca`."""

    help = "Edit a certificate authority."

    def add_arguments(self, parser: CommandParser) -> None:
        self.add_general_args(parser, default=None)
        self.add_ca(parser, "ca", allow_disabled=True)
        self.add_acme_group(parser)
        self.add_ocsp_group(parser)
        self.add_ca_args(parser)

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--enable",
            action="store_true",
            dest="enabled",
            default=None,
            help="Enable the certificate authority.",
        )
        group.add_argument(
            "--disable", action="store_false", dest="enabled", help="Disable the certificate authority."
        )

    def handle(  # pylint: disable=too-many-arguments
        self,
        ca: CertificateAuthority,
        sign_ca_issuer: str,
        sign_crl_full_name: List[str],
        sign_issuer_alternative_name: Optional[x509.Extension[x509.IssuerAlternativeName]],
        sign_ocsp_responder: str,
        enabled: Optional[bool],
        # Certificate Policies extension
        sign_certificate_policies: Optional[x509.CertificatePolicies],
        sign_certificate_policies_critical: bool,
        # OCSP responder configuration
        ocsp_responder_key_validity: Optional[int],
        ocsp_response_validity: Optional[int],
        **options: Any,
    ) -> None:
        if sign_ca_issuer:
            ca.issuer_url = sign_ca_issuer
        if sign_issuer_alternative_name:
            ca.issuer_alt_name = ",".join(
                [format_general_name(name) for name in sign_issuer_alternative_name.value]
            )
        if sign_ocsp_responder:
            ca.ocsp_url = sign_ocsp_responder
        if sign_crl_full_name:
            ca.crl_url = "\n".join(sign_crl_full_name)
        if sign_certificate_policies is not None:
            ca.sign_certificate_policies = x509.Extension(
                oid=ExtensionOID.CERTIFICATE_POLICIES,
                critical=sign_certificate_policies_critical,
                value=sign_certificate_policies,
            )

        if enabled is not None:
            ca.enabled = enabled

        if options["caa"] is not None:
            ca.caa_identity = options["caa"]
        if options["website"] is not None:
            ca.website = options["website"]
        if options["tos"] is not None:
            ca.terms_of_service = options["tos"]

        # Set ACME options
        if ca_settings.CA_ENABLE_ACME:  # pragma: no branch; never False because parser throws error already
            for param in ["acme_enabled", "acme_registration", "acme_requires_contact"]:
                if options[param] is not None:
                    setattr(ca, param, options[param])

            if acme_profile := options["acme_profile"]:
                if acme_profile not in ca_settings.CA_PROFILES:
                    raise CommandError(f"{acme_profile}: Profile is not defined.")
                ca.acme_profile = acme_profile

        # Set OCSP responder options
        if ocsp_responder_key_validity is not None:
            ca.ocsp_responder_key_validity = ocsp_responder_key_validity
        if ocsp_response_validity is not None:
            ca.ocsp_response_validity = ocsp_response_validity

        ca.save()
