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

# pylint: disable=redefined-outer-name  # requested pytest fixtures show up this way.

"""Test the list-view for certificates."""

from http import HTTPStatus
from typing import Any

from django.db.models import Model
from django.test.client import Client
from django.urls import reverse_lazy
from django.utils import timezone

import pytest

from django_ca.models import Certificate
from django_ca.tests.api.conftest import APIPermissionTestBase, ListResponse
from django_ca.tests.base.constants import CERT_DATA, TIMESTAMPS
from django_ca.tests.base.utils import iso_format

path = reverse_lazy("django_ca:api:list_certificates", kwargs={"serial": CERT_DATA["root"]["serial"]})


@pytest.fixture(scope="module")
def api_permission() -> tuple[type[Model], str]:
    """Fixture for the permission required by this view."""
    return Certificate, "view_certificate"


@pytest.fixture
def expected_response(root_cert_response: dict[str, Any]) -> ListResponse:
    """Fixture for the regular response expected from this API view."""
    return [root_cert_response]


@pytest.mark.usefixtures("root")
def test_empty_list_view(api_client: Client) -> None:
    """Test the request with no certificates (empty list view)."""
    Certificate.objects.all().delete()
    response = api_client.get(path)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == [], response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_valid"])
def test_list_view(api_client: Client, expected_response: ListResponse) -> None:
    """Test an ordinary list view."""
    response = api_client.get(path)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == expected_response, response.json()


@pytest.mark.usefixtures("root_cert")
@pytest.mark.freeze_time(TIMESTAMPS["everything_expired"])
def test_expired_certificates_are_excluded(api_client: Client) -> None:
    """Test that expired certificates are excluded by default."""
    response = api_client.get(path)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == [], response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_valid"])
def test_autogenerated_are_excluded(api_client: Client, root_cert: Certificate) -> None:
    """Test that auto-generated certificates are excluded by default."""
    root_cert.autogenerated = True
    root_cert.save()

    response = api_client.get(path)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == [], response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_valid"])
def test_revoked_are_excluded(api_client: Client, root_cert: Certificate) -> None:
    """Test that revoked certificates are excluded by default."""
    root_cert.revoke()

    response = api_client.get(path)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == [], response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_valid"])
def test_autogenerated_filter(
    api_client: Client, root_cert: Certificate, expected_response: ListResponse
) -> None:
    """Test the `autogenerated` filter."""
    # Mark certificates as auto-generated
    root_cert.autogenerated = True
    root_cert.save()
    expected_response[0]["autogenerated"] = True

    response = api_client.get(path, {"autogenerated": "1"})
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == expected_response, response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_valid"])
def test_profile_filter(api_client: Client, root_cert: Certificate, expected_response: ListResponse) -> None:
    """Test the `profile` filter."""
    root_cert.profile = "webserver"
    root_cert.save()
    expected_response[0]["profile"] = root_cert.profile

    # Explicitly giving the profile of the cert will return it
    response = api_client.get(path, {"profile": root_cert.profile})
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == expected_response, response.json()

    # Giving a different profile will exclude it
    response = api_client.get(path, {"profile": "other-profile"})
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == [], response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_expired"])
def test_expired_filter(api_client: Client, expected_response: ListResponse) -> None:
    """Test the `expired` filter."""
    response = api_client.get(path, {"expired": "1"})
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == expected_response, response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_valid"])
def test_revoked_filter(api_client: Client, root_cert: Certificate, expected_response: ListResponse) -> None:
    """Test the `revoked` filter."""
    root_cert.revoke()
    expected_response[0]["updated"] = iso_format(timezone.now())
    expected_response[0]["revoked"] = True

    response = api_client.get(path, {"revoked": "1"})
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == expected_response, response.json()


@pytest.mark.freeze_time(TIMESTAMPS["everything_valid"])
def test_disabled_ca(api_client: Client, root_cert: Certificate) -> None:
    """Test that certificates for a disabled can *not* be viewed."""
    root_cert.ca.enabled = False
    root_cert.ca.save()

    response = api_client.get(path)
    assert response.status_code == HTTPStatus.NOT_FOUND, response.content
    assert response.json() == {"detail": "Not Found"}, response.json()


class TestPermissions(APIPermissionTestBase):
    """Test permissions for this view."""

    path = path
