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

"""pytest configuration."""

# pylint: disable=redefined-outer-name  # requested pytest fixtures show up this way.

import importlib.metadata
import os
import sys
from typing import Any

import coverage

from django.conf import settings
from django.test import Client

import pytest
from _pytest.config import Config as PytestConfig
from _pytest.config.argparsing import Parser
from pytest_cov.plugin import CovPlugin

from ca import settings_utils  # noqa: F401  # to get rid of pytest warnings for untested modules
from django_ca.tests.base.conftest_helpers import (
    contrib_ca_names,
    contrib_cert_names,
    generate_ca_fixture,
    generate_cert_fixture,
    generate_pub_fixture,
    generate_usable_ca_fixture,
    setup_pragmas,
    usable_ca_names,
    usable_cert_names,
)
from django_ca.tests.base.constants import GECKODRIVER_PATH, RUN_SELENIUM_TESTS
from django_ca.tests.base.typehints import User

# NOTE: Assertion rewrites are in __init__.py

# Load fixtures from local "plugin":
pytest_plugins = ["django_ca.tests.base.fixtures"]


def pytest_addoption(parser: Parser) -> None:
    """Add some pytest options."""
    parser.addoption("--no-selenium", action="store_true", default=False, help="Do not run selenium tests.")
    parser.addoption(
        "--no-virtual-display",
        action="store_true",
        default=False,
        help="Do not run tests in virtual display.",
    )
    parser.addoption("--no-hsm", action="store_true", default=False, help="Disable HSM tests.")


def pytest_configure(config: "PytestConfig") -> None:
    """Output libraries, configure coverage pragmas."""
    cov_plugin: CovPlugin = config.pluginmanager.get_plugin("_cov")
    if cov_plugin.cov_controller is not None:  # pragma: no branch
        cov: coverage.Coverage = cov_plugin.cov_controller.combining_cov
        setup_pragmas(cov)

    config.addinivalue_line("markers", "selenium: mark tests that use selenium")
    config.addinivalue_line("markers", "hsm: mark tests that use HSM")

    skip_selenium = config.getoption("--no-selenium") or not RUN_SELENIUM_TESTS
    skip_hsm = config.getoption("--no-hsm")

    if skip_hsm and cov_plugin.cov_controller is not None:  # pragma: no cover
        omit = cov.config.get_option("run:omit")
        omit.append("*/hsm/*")  # type: ignore[union-attr]  # we know it's a list
        cov.config.set_option("run:omit", omit)
        cov.config.set_option("report:omit", omit)
        cov.exclude("pragma: hsm")

    if config.getoption("--no-virtual-display"):  # pragma: no cover
        os.environ["VIRTUAL_DISPLAY"] = "n"

    # Add a header to log important software versions
    print("Testing with:")
    print("* Python: ", sys.version.replace("\n", ""))
    installed_versions = {p.name: p.version for p in importlib.metadata.distributions()}
    for pkg in sorted(["Django", "acme", "cryptography", "celery", "idna", "josepy", "pydantic"]):
        print(f"* {pkg}: {installed_versions[pkg]}")
    print(f"* Django DB engine: {settings.DATABASES['default']['ENGINE']}")
    print(f"* Selenium tests: {not skip_selenium}")
    if not skip_selenium:  # pragma: no cover
        print(f"    geckodriver at {GECKODRIVER_PATH}")

        if not os.path.exists(GECKODRIVER_PATH):  # pragma: no cover
            raise pytest.UsageError(
                f"{GECKODRIVER_PATH}: Please download geckodriver to {GECKODRIVER_PATH}: "
                "https://selenium-python.readthedocs.io/installation.html#drivers"
            )


def pytest_collection_modifyitems(config: "PytestConfig", items: list[Any]) -> None:  # pragma: no cover
    """Mark Selenium tests as skipped if appropriate."""
    if config.getoption("--no-selenium") or not RUN_SELENIUM_TESTS:
        if config.getoption("--no-selenium"):
            reason = "--no-selenium was passed"
        else:
            reason = "Not using the newest Python/cryptography/acme."

        skip_selenium = pytest.mark.skip(reason=reason)
        for item in items:
            if "selenium" in item.keywords:
                item.add_marker(skip_selenium)

    if config.getoption("--no-hsm"):
        skip_hsm = pytest.mark.skip(reason="HSM tests disabled via the command-line.")
        for item in items:
            if "hsm" in item.keywords:
                item.add_marker(skip_hsm)


@pytest.fixture
def user(
    # PYLINT NOTE: usefixtures() does not (yet?) work with fixtures as of pytest==7.4.3
    #   https://docs.pytest.org/en/7.4.x/how-to/fixtures.html
    #   https://github.com/pytest-dev/pytest/issues/3664
    db: None,  # pylint: disable=unused-argument
    django_user_model: type["User"],
) -> "User":
    """Fixture for a basic Django user with no extra permissions."""
    username = "user"

    try:
        user = django_user_model.objects.get_by_natural_key(username)
    except django_user_model.DoesNotExist:
        user = django_user_model.objects.create_user(username=username, password="password")
    return user


@pytest.fixture
def user_client(user: "User", client: Client) -> Client:
    """A Django test client logged in as a normal user."""
    client.force_login(user)  # type: ignore[arg-type]  # django-stubs 5.1.0 thinks user is AbstractUser
    return client


# Dynamically inject repetitive fixtures:
#   https://github.com/pytest-dev/pytest/issues/2424
for _ca_name in usable_ca_names:
    globals()[_ca_name] = generate_ca_fixture(_ca_name)
    globals()[f"usable_{_ca_name}"] = generate_usable_ca_fixture(_ca_name)
for _ca_name in contrib_ca_names:
    globals()[f"contrib_{_ca_name}"] = generate_ca_fixture(_ca_name)
for _ca_name in usable_ca_names + usable_cert_names:
    globals()[f"{_ca_name.replace('-', '_')}_pub"] = generate_pub_fixture(_ca_name)
for _ca_name in contrib_ca_names + contrib_cert_names:
    globals()[f"contrib_{_ca_name.replace('-', '_')}_pub"] = generate_pub_fixture(_ca_name)
for cert_name in usable_cert_names:
    globals()[cert_name.replace("-", "_")] = generate_cert_fixture(cert_name)
for cert_name in contrib_cert_names:
    # raise Exception(contrib_cert_names, cert_name.replace("-", "_"))
    globals()[f"contrib_{cert_name.replace('-', '_')}"] = generate_cert_fixture(cert_name)
