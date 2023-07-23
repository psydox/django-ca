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

"""Test the list-view for certificates."""
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse_lazy
from django.utils import timezone

from freezegun import freeze_time

from django_ca import ca_settings
from django_ca.models import Certificate
from django_ca.tests.api.mixins import APITestCaseMixin
from django_ca.tests.base import certs, timestamps
from django_ca.utils import x509_name


class ListCertificateTestCase(APITestCaseMixin, TestCase):
    """Test the list-view for certificates."""

    path = reverse_lazy("django_ca:api:list_certificates", kwargs={"serial": certs["ec"]["serial"]})
    required_permission = (Certificate, "view_certificate")
    default_ca = "ec"
    default_cert = "ec-cert"
    load_cas = "__all__"  # type: ignore[assignment]
    load_certs = "__all__"

    def setUp(self) -> None:
        super().setUp()
        cert = certs["ec-cert"]
        self.cert.profile = ca_settings.CA_DEFAULT_PROFILE
        self.cert.save()
        self.expected_response = [
            {
                "autogenerated": False,
                "created": self.iso_format(self.cert.created),
                "not_after": self.iso_format(self.cert.expires),
                "not_before": self.iso_format(self.cert.valid_from),
                "pem": cert["pub"]["pem"],
                "profile": self.cert.profile,
                "revoked": False,
                "serial": cert["serial"],
                "subject": x509_name(cert["subject"]).rfc4514_string(),
                "updated": self.iso_format(self.cert.updated),
            }
        ]

    def test_empty_list_view(self) -> None:
        """Test the request with no certificates (empty list view)."""
        Certificate.objects.all().delete()
        response = self.default_request()
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), [])

    @freeze_time(timestamps["everything_valid"])
    def test_list_view(self) -> None:
        """Test an ordinary list view."""
        response = self.default_request()
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), self.expected_response, response.json())

    @freeze_time(timestamps["everything_expired"])
    def test_expired_certificates_are_excluded(self) -> None:
        """Test that expired certificates are excluded by default."""
        response = self.default_request()
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), [])

    @freeze_time(timestamps["everything_valid"])
    def test_autogenerated_are_excluded(self) -> None:
        """Test that auto-generated certificates are excluded by default."""
        Certificate.objects.filter(ca=self.ca).update(autogenerated=True)

        response = self.default_request()
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), [], response.json())

    @freeze_time(timestamps["everything_valid"])
    def test_revoked_are_excluded(self) -> None:
        """Test that revoked certificates are excluded by default."""
        self.cert.revoke()

        response = self.default_request()
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), [], response.json())

    @freeze_time(timestamps["everything_valid"])
    def test_autogenerated_filter(self) -> None:
        """Test the `autogenerated` filter."""
        # Mark certificates as auto-generated
        Certificate.objects.filter(ca=self.ca).update(autogenerated=True)
        self.expected_response[0]["autogenerated"] = True

        response = self.default_request({"autogenerated": "1"})
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), self.expected_response, response.json())

    @freeze_time(timestamps["everything_valid"])
    def test_profile_filter(self) -> None:
        """Test the `profile` filter."""

        # Explicitly giving the profile of the cert will return it
        response = self.default_request({"profile": self.cert.profile})
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), self.expected_response, response.json())

        # Giving a different profile will exclude it
        response = self.default_request({"profile": "other-profile"})
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), [], response.json())

    @freeze_time(timestamps["everything_expired"])
    def test_expired_filter(self) -> None:
        """Test the `expired` filter."""
        response = self.default_request({"expired": "1"})
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), self.expected_response, response.json())

    @freeze_time(timestamps["everything_valid"])
    def test_revoked_filter(self) -> None:
        """Test the `revoked` filter."""
        self.cert.revoke()
        self.expected_response[0]["updated"] = self.iso_format(timezone.now())
        self.expected_response[0]["revoked"] = True
        response = self.default_request({"revoked": "1"})
        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(response.json(), self.expected_response, response.json())

    @freeze_time(timestamps["everything_valid"])
    def test_disabled_ca(self) -> None:
        """Test that certificates for a disabled can *not* be viewed."""
        self.ca.enabled = False
        self.ca.save()

        response = self.default_request()
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())
        self.assertEqual(response.json(), {"detail": "Not Found"}, response.json())
