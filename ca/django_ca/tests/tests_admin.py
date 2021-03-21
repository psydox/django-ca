# This file is part of django-ca (https://github.com/mathiasertl/django-ca).
#
# django-ca is free software: you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# django-ca is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with django-ca.  If not,
# see <http://www.gnu.org/licenses/>

"""Base test cases for admin views and CertificateAdmin tests."""

import json
from http import HTTPStatus
from unittest import mock

from cryptography.hazmat.primitives.serialization import Encoding

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_str

from freezegun import freeze_time

from .. import ca_settings
from .. import extensions
from .. import models
from ..models import Certificate
from ..models import Watcher
from ..subject import Subject
from ..utils import SUBJECT_FIELDS
from .base import DjangoCATestCase
from .base import DjangoCAWithGeneratedCertsTestCase
from .base import certs
from .base import override_tmpcadir
from .base import timestamps
from .base_mixins import AdminTestCaseMixin
from .base_mixins import StandardAdminViewTestCaseMixin

User = get_user_model()


class CertificateAdminTestCaseMixin:  # pylint: disable=too-few-public-methods
    """Specialized variant of :py:class:`~django_ca.tests.tests_admin.AdminTestCaseMixin` for certificates."""

    model = Certificate
    media_css = (
        "django_ca/admin/css/base.css",
        "django_ca/admin/css/certificateadmin.css",
    )


@freeze_time(timestamps["everything_valid"])
class CertificateAdminViewTestCase(
    CertificateAdminTestCaseMixin, StandardAdminViewTestCaseMixin, DjangoCAWithGeneratedCertsTestCase
):
    """Tests for the Certificate ModelAdmin class."""

    def get_changelists(self):
        # yield various different result sets for different filters and times
        with self.freeze_time("everything_valid"):
            yield (self.model.objects.all(), {})
            yield (self.model.objects.all(), {"status": "valid"})
            yield (self.model.objects.all(), {"status": "all"})
            yield ([], {"status": "expired"})
            yield ([], {"status": "revoked"})

            yield ([], {"auto": "auto"})
            yield (self.model.objects.all(), {"auto": "all"})

        with self.freeze_time("ca_certs_expired"):
            yield (self.model.objects.all(), {"status": "all"})
            yield [
                self.certs["profile-client"],
                self.certs["profile-server"],
                self.certs["profile-webserver"],
                self.certs["profile-enduser"],
                self.certs["profile-ocsp"],
                self.certs["no-extensions"],
                self.certs["all-extensions"],
                self.certs["alt-extensions"],
            ], {}
            yield [
                self.certs["root-cert"],
                self.certs["pwd-cert"],
                self.certs["ecc-cert"],
                self.certs["dsa-cert"],
                self.certs["child-cert"],
            ], {"status": "expired"}
            yield [], {"status": "revoked"}

        with self.freeze_time("everything_expired"):
            yield ([], {})  # default view shows nothing - everything is expired
            yield (self.model.objects.all(), {"status": "all"})
            yield (self.model.objects.all(), {"status": "expired"})

        # load all certs (including 3rd party certs) and view with status_all
        with self.freeze_time("everything_valid"):
            self.load_all_certs()
            yield (self.model.objects.all(), {"status": "all"})

            # now revoke all certs, to test that filter
            self.model.objects.update(revoked=True)
            yield (self.model.objects.all(), {"status": "all"})
            yield (self.model.objects.all(), {"status": "revoked"})
            yield ([], {})  # default shows nothing - everything expired

            # unrevoke all certs, but set one of them as auto-generated
            self.model.objects.update(revoked=False)
            self.certs["profile-ocsp"].autogenerated = True
            self.certs["profile-ocsp"].save()

            yield ([self.certs["profile-ocsp"]], {"auto": "auto"})
            yield (self.model.objects.all(), {"auto": "all", "status": "all"})

    def test_change_view(self):
        self.load_all_certs()
        super().test_change_view()

    def test_revoked(self):
        """View a revoked certificate (fieldset should be collapsed)."""
        self.certs["root-cert"].revoke()

        response = self.client.get(self.change_url())
        self.assertChangeResponse(response)

        self.assertContains(
            response,
            text="""<div class="fieldBox field-revoked"><label>Revoked:</label>
                     <div class="readonly"><img src="/static/admin/img/icon-yes.svg" alt="True"></div>
                </div>""",
            html=True,
        )

    def test_no_san(self):
        """Test viewing a certificate with no extensions."""
        cert = self.certs["no-extensions"]
        response = self.client.get(cert.admin_change_url)
        self.assertChangeResponse(response)
        self.assertContains(
            response,
            text="""
<div class="form-row field-subject_alternative_name">
    <div>
        <label>SubjectAlternativeName:</label>
        <div class="readonly">
            <span class="django-ca-extension">
                <div class="django-ca-extension-value">
                    &lt;Not present&gt;
                </div>
            </span>
        </div>
    </div>
</div>
""",
            html=True,
        )

    def test_unsupported_extensions(self):
        """Test viewing a certificate with unsupported extensions."""
        cert = self.certs["all-extensions"]
        # Act as if no extensions is recognized, to see what happens if we'd encounter an unknown extension.
        with mock.patch.object(models, "OID_TO_EXTENSION", {}), mock.patch.object(
            extensions, "OID_TO_EXTENSION", {}
        ), self.assertLogs() as logs:
            response = self.client.get(cert.admin_change_url)
            self.assertChangeResponse(response)

        log_msg = "WARNING:django_ca.models:Unknown extension encountered: %s"
        expected = [
            log_msg % "AuthorityInfoAccess (1.3.6.1.5.5.7.1.1)",
            log_msg % "AuthorityKeyIdentifier (2.5.29.35)",
            log_msg % "BasicConstraints (2.5.29.19)",
            log_msg % "CRLDistributionPoints (2.5.29.31)",
            log_msg % "CtPoison (1.3.6.1.4.1.11129.2.4.3)",
            log_msg % "ExtendedKeyUsage (2.5.29.37)",
            log_msg % "FreshestCRL (2.5.29.46)",
            log_msg % "InhibitAnyPolicy (2.5.29.54)",
            log_msg % "IssuerAltName (2.5.29.18)",
            log_msg % "KeyUsage (2.5.29.15)",
            log_msg % "NameConstraints (2.5.29.30)",
            log_msg % "OCSPNoCheck (1.3.6.1.5.5.7.48.1.5)",
            log_msg % "PolicyConstraints (2.5.29.36)",
            log_msg % "SubjectAltName (2.5.29.17)",
            log_msg % "SubjectKeyIdentifier (2.5.29.14)",
            log_msg % "TLSFeature (1.3.6.1.5.5.7.1.24)",
        ]

        self.assertEqual(logs.output, sorted(expected))

    def test_change_watchers(self):
        """Test changing watchers.

        NOTE: This only tests standard Django functionality, BUT save_model() has special handling when
        creating a new object (=sign a new cert). So we have to test saving a cert that already exists for
        code coverage.
        """
        cert = self.certs["root-cert"]
        cert = Certificate.objects.get(serial=cert.serial)
        watcher = Watcher.objects.create(name="User", mail="user@example.com")

        response = self.client.post(
            self.change_url(),
            data={
                "watchers": [watcher.pk],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.changelist_url)
        self.assertEqual(list(cert.watchers.all()), [watcher])


class CSRDetailTestCase(CertificateAdminTestCaseMixin, AdminTestCaseMixin, DjangoCATestCase):
    """Test the CSR detail view."""

    url = reverse("admin:django_ca_certificate_csr_details")
    csr_pem = certs["root-cert"]["csr"]["pem"]

    def test_basic(self):
        """Test a basic CSR info retrieval."""
        for cert_data in [v for v in certs.values() if v["type"] == "cert" and v["cat"] == "generated"]:
            response = self.client.post(self.url, data={"csr": cert_data["csr"]["pem"]})
            self.assertEqual(response.status_code, 200)
            self.assertJSONEqual(response.content, {"subject": cert_data["csr_subject"]})

    def test_fields(self):
        """Test fetching a CSR with all subject fields."""
        subject = [(f, "AT" if f == "C" else "test-%s" % f) for f in SUBJECT_FIELDS]
        csr = self.create_csr(subject)[1]
        csr_pem = csr.public_bytes(Encoding.PEM).decode("utf-8")

        response = self.client.post(self.url, data={"csr": csr_pem})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")),
            {
                "subject": {
                    "C": "AT",
                    "CN": "test-CN",
                    "L": "test-L",
                    "O": "test-O",
                    "OU": "test-OU",
                    "ST": "test-ST",
                    "emailAddress": "test-emailAddress",
                }
            },
        )

    def test_bad_request(self):
        """Test posting bogus data."""
        response = self.client.post(self.url, data={"csr": "foobar"})
        self.assertEqual(response.status_code, 400)

    def test_anonymous(self):
        """Try downloading as anonymous user."""
        client = Client()
        self.assertRequiresLogin(client.post(self.url, data={"csr": self.csr_pem}))

    def test_plain_user(self):
        """Try downloading as non-superuser."""
        self.user.is_superuser = self.user.is_staff = False
        self.user.save()
        self.assertRequiresLogin(self.client.post(self.url, data={"csr": self.csr_pem}))

    def test_no_perms(self):
        """Try downloading as staff user with missing permissions."""
        self.user.is_superuser = False
        self.user.save()
        response = self.client.post(self.url, data={"csr": self.csr_pem})
        self.assertEqual(response.status_code, 403)

    def test_no_staff(self):
        """Try downloading as user that has permissions but is not staff."""
        self.user.is_superuser = self.user.is_staff = False
        self.user.save()
        self.user.user_permissions.add(Permission.objects.get(codename="change_certificate"))
        self.assertRequiresLogin(self.client.post(self.url, data={"csr": self.csr_pem}))


class ProfilesViewTestCase(CertificateAdminTestCaseMixin, AdminTestCaseMixin, DjangoCATestCase):
    """Test fetching profile information."""

    url = reverse("admin:django_ca_certificate_profiles")

    def test_basic(self):
        """Test fetching basic profile information."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        enduser_desc = "A certificate for an enduser, allows client authentication, code and email signing."
        self.assertEqual(
            json.loads(response.content.decode("utf-8")),
            {
                "client": {
                    "cn_in_san": True,
                    "description": "A certificate for a client.",
                    "extensions": {
                        "basic_constraints": {
                            "critical": True,
                            "value": {"ca": False},
                        },
                        "key_usage": {
                            "critical": True,
                            "value": ["digitalSignature"],
                        },
                        "extended_key_usage": {
                            "critical": False,
                            "value": ["clientAuth"],
                        },
                    },
                    "subject": dict(Subject(ca_settings.CA_DEFAULT_SUBJECT)),
                },
                "enduser": {
                    "cn_in_san": False,
                    "description": enduser_desc,
                    "extensions": {
                        "basic_constraints": {
                            "critical": True,
                            "value": {"ca": False},
                        },
                        "key_usage": {
                            "critical": True,
                            "value": [
                                "dataEncipherment",
                                "digitalSignature",
                                "keyEncipherment",
                            ],
                        },
                        "extended_key_usage": {
                            "critical": False,
                            "value": ["clientAuth", "codeSigning", "emailProtection"],
                        },
                    },
                    "subject": dict(Subject(ca_settings.CA_DEFAULT_SUBJECT)),
                },
                "ocsp": {
                    "cn_in_san": False,
                    "description": "A certificate for an OCSP responder.",
                    "extensions": {
                        "basic_constraints": {
                            "critical": True,
                            "value": {"ca": False},
                        },
                        "key_usage": {
                            "critical": True,
                            "value": ["digitalSignature", "keyEncipherment", "nonRepudiation"],
                        },
                        "extended_key_usage": {
                            "critical": False,
                            "value": ["OCSPSigning"],
                        },
                    },
                    "subject": dict(Subject(ca_settings.CA_DEFAULT_SUBJECT)),
                },
                "server": {
                    "cn_in_san": True,
                    "description": "A certificate for a server, allows client and server authentication.",
                    "extensions": {
                        "basic_constraints": {
                            "critical": True,
                            "value": {"ca": False},
                        },
                        "key_usage": {
                            "critical": True,
                            "value": [
                                "digitalSignature",
                                "keyAgreement",
                                "keyEncipherment",
                            ],
                        },
                        "extended_key_usage": {
                            "critical": False,
                            "value": ["clientAuth", "serverAuth"],
                        },
                    },
                    "subject": dict(Subject(ca_settings.CA_DEFAULT_SUBJECT)),
                },
                "webserver": {
                    "cn_in_san": True,
                    "description": "A certificate for a webserver.",
                    "extensions": {
                        "basic_constraints": {
                            "critical": True,
                            "value": {"ca": False},
                        },
                        "key_usage": {
                            "critical": True,
                            "value": [
                                "digitalSignature",
                                "keyAgreement",
                                "keyEncipherment",
                            ],
                        },
                        "extended_key_usage": {
                            "critical": False,
                            "value": ["serverAuth"],
                        },
                    },
                    "subject": dict(Subject(ca_settings.CA_DEFAULT_SUBJECT)),
                },
            },
        )

    def test_permission_denied(self):
        """Try fetching profiles without permissions."""
        self.user.is_superuser = False
        self.user.save()
        self.assertEqual(self.client.get(self.url).status_code, HTTPStatus.FORBIDDEN)

    # removes all profiles, adds one pretty boring one
    @override_tmpcadir(
        CA_PROFILES={
            "webserver": None,
            "server": None,
            "ocsp": None,
            "enduser": None,
            "client": None,
            "test": {
                "cn_in_san": True,
            },
        }
    )
    def test_empty_profile(self):
        """Try fetching a simple profile."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")),
            {
                "test": {
                    "cn_in_san": True,
                    "description": "",
                    "extensions": {
                        "basic_constraints": {
                            "critical": True,
                            "value": {"ca": False},
                        },
                    },
                    "subject": dict(Subject(ca_settings.CA_DEFAULT_SUBJECT)),
                },
            },
        )


class CertDownloadTestCase(
    CertificateAdminTestCaseMixin, AdminTestCaseMixin, DjangoCAWithGeneratedCertsTestCase
):
    """Test fetching certificate bundles."""

    def get_url(self, cert):
        """Get url for the given object."""
        return reverse("admin:django_ca_certificate_download", kwargs={"pk": cert.pk})

    @property
    def url(self):
        """Get URL for the default object."""
        return self.get_url(cert=self.obj)

    def test_basic(self):
        """Basic bundle download."""
        filename = "root-cert_example_com.pem"
        response = self.client.get(self.url, {"format": "PEM"})
        self.assertBundle(response, filename, self.obj.pub)

    def test_der(self):
        """Download a certificate in DER format."""
        filename = "root-cert_example_com.der"
        response = self.client.get(self.url, {"format": "DER"})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "application/pkix-cert")
        self.assertEqual(response["Content-Disposition"], "attachment; filename=%s" % filename)
        self.assertEqual(response.content, self.obj.dump_certificate(Encoding.DER))

    def test_not_found(self):
        """Try downloading a certificate that does not exist."""
        url = reverse("admin:django_ca_certificate_download", kwargs={"pk": "123"})
        response = self.client.get("%s?format=DER" % url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_bad_format(self):
        """Try downloading an unknown format."""
        response = self.client.get("%s?format=bad" % self.url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.content, b"")

    def test_anonymous(self):
        """Try an anonymous download."""
        self.assertRequiresLogin(Client().get(self.url))

    def test_plain_user(self):
        """Try downloading as plain user."""
        self.user.is_superuser = self.user.is_staff = False
        self.user.save()
        self.assertRequiresLogin(self.client.get(self.url))

    def test_no_perms(self):
        """Try downloading as staff user with no permissions."""
        self.user.is_superuser = False
        self.user.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_no_staff(self):
        """Try downloading with right permissions but not as staff user."""
        self.user.is_staff = False
        self.user.save()
        self.user.user_permissions.add(Permission.objects.get(codename="change_certificate"))
        self.assertRequiresLogin(self.client.get(self.url))


class CertDownloadBundleTestCase(
    CertificateAdminTestCaseMixin, AdminTestCaseMixin, DjangoCAWithGeneratedCertsTestCase
):
    """Test downloading certificate bundles."""

    def get_url(self, cert):
        """Get URL for given certificate for this test."""
        return reverse("admin:django_ca_certificate_download_bundle", kwargs={"pk": cert.pk})

    @property
    def url(self):
        """Generic URL for this test."""
        return self.get_url(cert=self.obj)

    def test_cert(self):
        """TRy downloading a certificate bundle."""
        filename = "root-cert_example_com_bundle.pem"
        response = self.client.get("%s?format=PEM" % self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "application/pkix-cert")
        self.assertEqual(response["Content-Disposition"], "attachment; filename=%s" % filename)
        self.assertEqual(
            force_str(response.content), "%s\n%s" % (self.obj.pub.strip(), self.obj.ca.pub.strip())
        )
        self.assertEqual(self.cas["root"], self.obj.ca)  # just to be sure we test the right thing

    def test_invalid_format(self):
        """Try downloading an invalid format."""
        response = self.client.get("%s?format=INVALID" % self.url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.content, b"")

        # DER is not supported for bundles
        response = self.client.get("%s?format=DER" % self.url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.content, b"DER/ASN.1 certificates cannot be downloaded as a bundle.")
