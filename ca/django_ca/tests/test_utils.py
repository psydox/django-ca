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

"""Test utility functions."""

import ipaddress
import itertools
import os
import typing
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone as tz
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID

from django.test import TestCase, override_settings

import pytest
from freezegun import freeze_time

from django_ca import utils
from django_ca.conf import model_settings
from django_ca.tests.base.doctest import doctest_module
from django_ca.tests.base.utils import cn, country, dns
from django_ca.utils import (
    bytes_to_hex,
    format_general_name,
    generate_private_key,
    get_cert_builder,
    merge_x509_names,
    parse_encoding,
    read_file,
    validate_private_key_parameters,
    validate_public_key_parameters,
)

SuperclassTypeVar = typing.TypeVar("SuperclassTypeVar", bound=type[object])


def test_doctests() -> None:
    """Load doctests."""
    failures, *_tests = doctest_module("django_ca.utils")
    assert failures == 0, f"{failures} doctests failed, see above for output."


def test_read_file(tmpcadir: Path) -> None:
    """Test :py:func:`django_ca.utils.read_file`."""
    name = "test-data"
    path = os.path.join(tmpcadir, name)
    data = b"test data"
    with open(path, "wb") as stream:
        stream.write(data)

    assert read_file(name) == data
    assert read_file(path) == data


class GeneratePrivateKeyTestCase(TestCase):
    """Test :py:func:`django_ca.utils.generate_private_key`."""

    def test_key_types(self) -> None:
        """Test generating various private key types."""
        ec_key = generate_private_key(None, "EC", ec.BrainpoolP256R1())
        assert isinstance(ec_key, ec.EllipticCurvePrivateKey)
        assert isinstance(ec_key.curve, ec.BrainpoolP256R1)

        ed448_key = generate_private_key(None, "Ed448", None)
        assert isinstance(ed448_key, ed448.Ed448PrivateKey)

    def test_dsa_default_key_size(self) -> None:
        """Test the default DSA key size."""
        key = generate_private_key(None, "DSA", None)
        assert isinstance(key, dsa.DSAPrivateKey)
        assert key.key_size == model_settings.CA_DEFAULT_KEY_SIZE

    def test_invalid_type(self) -> None:
        """Test passing an invalid key type."""
        with pytest.raises(ValueError, match=r"^FOO: Unknown key type\.$"):
            generate_private_key(16, "FOO", None)  # type: ignore[call-overload]


@pytest.mark.parametrize(
    ("general_name", "expected"),
    (
        (dns("example.com"), "DNS:example.com"),
        (x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")), "IP:127.0.0.1"),
        (
            x509.DirectoryName(x509.Name([country("AT"), cn("example.com")])),
            "dirname:C=AT,CN=example.com",
        ),
        (x509.OtherName(NameOID.COMMON_NAME, b"\x01\x01\xff"), "otherName:2.5.4.3;BOOLEAN:TRUE"),
    ),
)
def test_format_general_name(general_name: x509.GeneralName, expected: str) -> None:
    """Test :py:func:`django_ca.utils.format_general_name`."""
    assert format_general_name(general_name) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    (("PEM", Encoding.PEM), ("DER", Encoding.DER), ("ASN1", Encoding.DER), ("OpenSSH", Encoding.OpenSSH)),
)
def test_parse_encoding(value: Any, expected: Encoding) -> None:
    """Test :py:func:`django_ca.utils.parse_encoding`."""
    assert parse_encoding(value) == expected


def test_parse_encoding_with_invalid_value() -> None:
    """Test some error cases."""
    with pytest.raises(ValueError, match="^Unknown encoding: foo$"):
        parse_encoding("foo")


class AddColonsTestCase(TestCase):
    """Test :py:func:`django_ca.utils.add_colons`."""

    def test_basic(self) -> None:
        """Some basic tests."""
        assert utils.add_colons("") == ""
        assert utils.add_colons("a") == "0a"
        assert utils.add_colons("ab") == "ab"
        assert utils.add_colons("abc") == "0a:bc"
        assert utils.add_colons("abcd") == "ab:cd"
        assert utils.add_colons("abcde") == "0a:bc:de"
        assert utils.add_colons("abcdef") == "ab:cd:ef"
        assert utils.add_colons("abcdefg") == "0a:bc:de:fg"

    def test_pad(self) -> None:
        """Test padding."""
        assert utils.add_colons("a", pad="z") == "za"
        assert utils.add_colons("ab", pad="z") == "ab"
        assert utils.add_colons("abc", pad="z") == "za:bc"

    def test_no_pad(self) -> None:
        """Test disabling padding."""
        assert utils.add_colons("a", pad="") == "a"
        assert utils.add_colons("ab", pad="") == "ab"
        assert utils.add_colons("abc", pad="") == "ab:c"

    def test_zero_padding(self) -> None:
        """Test when there is no padding."""
        assert (
            utils.add_colons("F570A555BC5000FA301E8C75FFB31684FCF64436")
            == "F5:70:A5:55:BC:50:00:FA:30:1E:8C:75:FF:B3:16:84:FC:F6:44:36"
        )
        assert (
            utils.add_colons("85BDA79A857379A4C9E910DAEA21C896D16394")
            == "85:BD:A7:9A:85:73:79:A4:C9:E9:10:DA:EA:21:C8:96:D1:63:94"
        )


class IntToHexTestCase(TestCase):
    """Test :py:func:`django_ca.utils.int_to_hex`."""

    def test_basic(self) -> None:
        """Test the first view numbers."""
        assert utils.int_to_hex(0) == "0"
        assert utils.int_to_hex(1) == "1"
        assert utils.int_to_hex(2) == "2"
        assert utils.int_to_hex(3) == "3"
        assert utils.int_to_hex(4) == "4"
        assert utils.int_to_hex(5) == "5"
        assert utils.int_to_hex(6) == "6"
        assert utils.int_to_hex(7) == "7"
        assert utils.int_to_hex(8) == "8"
        assert utils.int_to_hex(9) == "9"
        assert utils.int_to_hex(10) == "A"
        assert utils.int_to_hex(11) == "B"
        assert utils.int_to_hex(12) == "C"
        assert utils.int_to_hex(13) == "D"
        assert utils.int_to_hex(14) == "E"
        assert utils.int_to_hex(15) == "F"
        assert utils.int_to_hex(16) == "10"
        assert utils.int_to_hex(17) == "11"
        assert utils.int_to_hex(18) == "12"
        assert utils.int_to_hex(19) == "13"
        assert utils.int_to_hex(20) == "14"
        assert utils.int_to_hex(21) == "15"
        assert utils.int_to_hex(22) == "16"
        assert utils.int_to_hex(23) == "17"
        assert utils.int_to_hex(24) == "18"
        assert utils.int_to_hex(25) == "19"
        assert utils.int_to_hex(26) == "1A"
        assert utils.int_to_hex(27) == "1B"
        assert utils.int_to_hex(28) == "1C"
        assert utils.int_to_hex(29) == "1D"
        assert utils.int_to_hex(30) == "1E"
        assert utils.int_to_hex(31) == "1F"
        assert utils.int_to_hex(32) == "20"
        assert utils.int_to_hex(33) == "21"
        assert utils.int_to_hex(34) == "22"
        assert utils.int_to_hex(35) == "23"
        assert utils.int_to_hex(36) == "24"
        assert utils.int_to_hex(37) == "25"
        assert utils.int_to_hex(38) == "26"
        assert utils.int_to_hex(39) == "27"
        assert utils.int_to_hex(40) == "28"
        assert utils.int_to_hex(41) == "29"
        assert utils.int_to_hex(42) == "2A"
        assert utils.int_to_hex(43) == "2B"
        assert utils.int_to_hex(44) == "2C"
        assert utils.int_to_hex(45) == "2D"
        assert utils.int_to_hex(46) == "2E"
        assert utils.int_to_hex(47) == "2F"
        assert utils.int_to_hex(48) == "30"
        assert utils.int_to_hex(49) == "31"

    def test_high(self) -> None:
        """Test some high numbers."""
        assert utils.int_to_hex(1513282098) == "5A32DA32"
        assert utils.int_to_hex(1513282099) == "5A32DA33"
        assert utils.int_to_hex(1513282100) == "5A32DA34"
        assert utils.int_to_hex(1513282101) == "5A32DA35"
        assert utils.int_to_hex(1513282102) == "5A32DA36"
        assert utils.int_to_hex(1513282103) == "5A32DA37"
        assert utils.int_to_hex(1513282104) == "5A32DA38"
        assert utils.int_to_hex(1513282105) == "5A32DA39"
        assert utils.int_to_hex(1513282106) == "5A32DA3A"
        assert utils.int_to_hex(1513282107) == "5A32DA3B"
        assert utils.int_to_hex(1513282108) == "5A32DA3C"
        assert utils.int_to_hex(1513282109) == "5A32DA3D"
        assert utils.int_to_hex(1513282110) == "5A32DA3E"
        assert utils.int_to_hex(1513282111) == "5A32DA3F"
        assert utils.int_to_hex(1513282112) == "5A32DA40"
        assert utils.int_to_hex(1513282113) == "5A32DA41"


class BytesToHexTestCase(TestCase):
    """Test :py:func:`~django_ca.utils.byutes_to_hex`."""

    def test_basic(self) -> None:
        """Some basic test cases."""
        assert bytes_to_hex(b"test") == "74:65:73:74"
        assert bytes_to_hex(b"foo") == "66:6F:6F"
        assert bytes_to_hex(b"bar") == "62:61:72"
        assert bytes_to_hex(b"") == ""
        assert bytes_to_hex(b"a") == "61"


class SanitizeSerialTestCase(TestCase):
    """Test :py:func:`~django_ca.utils.sanitize_serial`."""

    def test_already_sanitized(self) -> None:
        """Test some already sanitized input."""
        assert utils.sanitize_serial("A") == "A"
        assert utils.sanitize_serial("5A32DA3B") == "5A32DA3B"
        assert utils.sanitize_serial("1234567890ABCDEF") == "1234567890ABCDEF"

    def test_sanitized(self) -> None:
        """Test some input that can be correctly sanitized."""
        assert utils.sanitize_serial("5A:32:DA:3B") == "5A32DA3B"
        assert utils.sanitize_serial("0A:32:DA:3B") == "A32DA3B"
        assert utils.sanitize_serial("0a:32:da:3b") == "A32DA3B"

    def test_zero(self) -> None:
        """An imported CA might have a serial of just a ``0``, so it must not be stripped."""
        assert utils.sanitize_serial("0") == "0"

    def test_invalid_input(self) -> None:
        """Test some input that raises an exception."""
        with pytest.raises(ValueError, match=r"^ABCXY: Serial has invalid characters$"):
            utils.sanitize_serial("ABCXY")


class MergeX509NamesTestCase(TestCase):
    """Test ``django_ca.utils.merge_x509_name``."""

    cc1 = x509.NameAttribute(NameOID.COUNTRY_NAME, "AT")
    cc2 = x509.NameAttribute(NameOID.COUNTRY_NAME, "US")
    org1 = x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Example Org")
    org2 = x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Other Org")
    ou1 = x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Example Org Unit")
    ou2 = x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Other Org Unit")
    ou3 = x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Example Org Unit2")
    ou4 = x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Other Org Unit2")
    common_name1 = x509.NameAttribute(NameOID.COMMON_NAME, "example.com")
    common_name2 = x509.NameAttribute(NameOID.COMMON_NAME, "example.net")
    email1 = x509.NameAttribute(NameOID.EMAIL_ADDRESS, "user@xample.com")
    email2 = x509.NameAttribute(NameOID.EMAIL_ADDRESS, "user@xample.net")

    def assertMerged(  # pylint: disable=invalid-name  # unittest standard
        self,
        base: Iterable["x509.NameAttribute[str | bytes]"],
        update: Iterable["x509.NameAttribute[str | bytes]"],
        merged: Iterable["x509.NameAttribute[str | bytes]"],
    ) -> None:
        """Assert that the given base and update are merged to the expected value."""
        base_name = x509.Name(base)
        update_name = x509.Name(update)
        merged_name = x509.Name(merged)
        assert merge_x509_names(base_name, update_name) == merged_name

    def test_full_merge(self) -> None:
        """Test a basic merge."""
        # Order here matches the order from model_settings.CA_DEFAULT_NAME_ORDER
        expected = [self.cc1, self.org1, self.ou1, self.common_name1, self.email1]

        self.assertMerged([self.cc1, self.org1, self.ou1], [self.common_name1, self.email1], expected)
        self.assertMerged([self.cc1, self.org1], [self.ou1, self.common_name1, self.email1], expected)
        self.assertMerged([self.cc1], [self.org1, self.ou1, self.common_name1, self.email1], expected)

    def test_order(self) -> None:
        """Test passing subjects in different order."""
        expected = [self.cc1, self.org1, self.ou1, self.common_name1, self.email1]

        # For-loop for splitting expected between every element
        for i in range(1, len(expected)):
            base = expected[:i]
            update = expected[i:]

            # loop through every possible permutation
            for base_perm in itertools.permutations(base):
                for update_perm in itertools.permutations(update):
                    self.assertMerged(base_perm, update_perm, expected)

    def test_merging_multiple_org_units(self) -> None:
        """Test merging names with multiple org units."""
        expected = [self.cc1, self.org1, self.ou1, self.ou2, self.common_name1]
        self.assertMerged([self.cc1, self.org1, self.ou1, self.ou2], [self.common_name1], expected)
        self.assertMerged([self.cc1, self.org1], [self.common_name1, self.ou1, self.ou2], expected)

    def test_overwriting_attributes(self) -> None:
        """Test overwriting attributes when merging."""
        expected = [self.cc2, self.org2, self.ou3, self.ou4, self.common_name2, self.email2]
        self.assertMerged([self.cc1], expected, expected)
        self.assertMerged([self.cc1, self.ou1], expected, expected)
        self.assertMerged([self.cc1, self.ou1, self.ou2, self.email2, self.common_name1], expected, expected)

    def test_unsortable_values(self) -> None:
        """Test merging unsortable values."""
        sortable = x509.Name([self.cc1, self.common_name1])
        unsortable = x509.Name([self.cc1, x509.NameAttribute(NameOID.INN, "unsortable")])
        with pytest.raises(ValueError, match=r"Unsortable name"):
            merge_x509_names(unsortable, sortable)
        with pytest.raises(ValueError, match=r"Unsortable name"):
            merge_x509_names(sortable, unsortable)


class GetCertBuilderTestCase(TestCase):
    """Test :py:func:`django_ca.utils.get_cert_builder`."""

    def parse_date(self, date: str) -> datetime:
        """Helper to parse a date."""
        return datetime.strptime(date, "%Y%m%d%H%M%SZ")

    @freeze_time("2018-11-03 11:21:33")
    @override_settings(CA_DEFAULT_EXPIRES=100)
    def test_basic(self) -> None:
        """Basic tests."""
        # pylint: disable=protected-access; only way to test builder attributes
        after = datetime(2020, 10, 23, 11, 21, tzinfo=tz.utc)
        builder = get_cert_builder(after)
        assert builder._not_valid_before == datetime(2018, 11, 3, 11, 21)
        assert builder._not_valid_after == datetime(2020, 10, 23, 11, 21)
        assert isinstance(builder._serial_number, int)

    @freeze_time("2021-01-23 14:42:11.1234")
    def test_datetime(self) -> None:
        """Basic tests."""
        expires = datetime.now(tz.utc) + timedelta(days=10)
        assert expires.second != 0
        assert expires.microsecond != 0
        expires_expected = datetime(2021, 2, 2, 14, 42)
        builder = get_cert_builder(expires)
        assert builder._not_valid_after == expires_expected  # pylint: disable=protected-access
        assert isinstance(builder._serial_number, int)  # pylint: disable=protected-access

    @freeze_time("2021-01-23 14:42:11.1234")
    def test_serial(self) -> None:
        """Test manually setting a serial."""
        after = datetime(2022, 10, 23, 11, 21, tzinfo=tz.utc)
        builder = get_cert_builder(after, serial=123)
        assert builder._serial_number == 123  # pylint: disable=protected-access
        assert builder._not_valid_after == datetime(2022, 10, 23, 11, 21)  # pylint: disable=protected-access

    @freeze_time("2021-01-23 14:42:11")
    def test_negative_datetime(self) -> None:
        """Test passing a datetime in the past."""
        with pytest.raises(ValueError, match=r"^not_after must be in the future$"):
            get_cert_builder(datetime.now(tz.utc) - timedelta(seconds=60))

    def test_invalid_type(self) -> None:
        """Test passing an invalid type."""
        with pytest.raises(AttributeError):
            get_cert_builder("a string")  # type: ignore[arg-type]

    def test_naive_datetime(self) -> None:
        """Test passing a naive datetime."""
        with pytest.raises(ValueError, match=r"^not_after must not be a naive datetime$"):
            get_cert_builder(datetime.now())


class ValidatePrivateKeyParametersTest(TestCase):
    """Test :py:func:`django_ca.utils.validate_private_key_parameters`."""

    def test_default_parameters(self) -> None:
        """Test that default values are returned."""
        assert validate_private_key_parameters("RSA", None, None) == (
            model_settings.CA_DEFAULT_KEY_SIZE,
            None,
        )

        assert validate_private_key_parameters("DSA", None, None) == (
            model_settings.CA_DEFAULT_KEY_SIZE,
            None,
        )

        key_size, elliptic_curve = validate_private_key_parameters("EC", None, None)
        assert key_size is None
        assert isinstance(elliptic_curve, type(model_settings.CA_DEFAULT_ELLIPTIC_CURVE))

        assert validate_private_key_parameters("Ed25519", None, None) == (None, None)
        assert validate_private_key_parameters("Ed448", None, None) == (None, None)

    def test_valid_parameters(self) -> None:
        """Test valid parameters."""
        assert validate_private_key_parameters("RSA", 8192, None) == (8192, None)
        assert validate_private_key_parameters("DSA", 8192, None) == (8192, None)

        key_size, elliptic_curve = validate_private_key_parameters("EC", None, ec.BrainpoolP384R1())
        assert key_size is None
        assert isinstance(elliptic_curve, ec.BrainpoolP384R1)

    def test_wrong_values(self) -> None:
        """Test validating various bogus values."""
        key_size = model_settings.CA_DEFAULT_KEY_SIZE
        elliptic_curve = model_settings.CA_DEFAULT_ELLIPTIC_CURVE
        with pytest.raises(ValueError, match="^FOOBAR: Unknown key type$"):
            validate_private_key_parameters("FOOBAR", 4096, None)  # type: ignore[call-overload]

        with pytest.raises(ValueError, match=r"^foo: Key size must be an int\.$"):
            validate_private_key_parameters("RSA", "foo", None)  # type: ignore[call-overload]

        with pytest.raises(ValueError, match="^4000: Key size must be a power of two$"):
            validate_private_key_parameters("RSA", 4000, None)

        with pytest.raises(ValueError, match="^16: Key size must be least 1024 bits$"):
            validate_private_key_parameters("RSA", 16, None)

        with pytest.raises(ValueError, match=r"^Key size is not supported for EC keys\.$"):
            validate_private_key_parameters("EC", key_size, elliptic_curve)

        with pytest.raises(ValueError, match=r"^secp192r1: Must be a subclass of ec\.EllipticCurve$"):
            validate_private_key_parameters("EC", None, "secp192r1")  # type: ignore

        for key_type in ("Ed448", "Ed25519"):
            with pytest.raises(ValueError, match=rf"^Key size is not supported for {key_type} keys\.$"):
                validate_private_key_parameters(key_type, key_size, None)
            with pytest.raises(
                ValueError, match=rf"^Elliptic curves are not supported for {key_type} keys\.$"
            ):
                validate_private_key_parameters(key_type, None, elliptic_curve)


class ValidatePublicKeyParametersTest(TestCase):
    """Test :py:func:`django_ca.utils.validate_public_key_parameters`."""

    def test_valid_parameters(self) -> None:
        """Test valid parameters."""
        for key_type in ("RSA", "DSA", "EC"):
            for algorithm in (hashes.SHA256(), hashes.SHA512()):
                validate_public_key_parameters(key_type, algorithm)
        for key_type in ("Ed448", "Ed25519"):
            validate_public_key_parameters(key_type, None)  # type: ignore[arg-type]

    def test_invalid_parameters(self) -> None:
        """Test invalid parameters."""
        with pytest.raises(ValueError, match="^FOOBAR: Unknown key type$"):
            validate_public_key_parameters("FOOBAR", None)  # type: ignore[arg-type]
        for key_type in ("RSA", "DSA", "EC"):
            msg = rf"^{key_type}: algorithm must be an instance of hashes.HashAlgorithm\.$"
            with pytest.raises(ValueError, match=msg):
                validate_public_key_parameters(key_type, True)  # type: ignore[arg-type]

        for key_type in ("Ed448", "Ed25519"):
            msg = rf"^{key_type} keys do not allow an algorithm for signing\.$"
            with pytest.raises(ValueError, match=msg):
                validate_public_key_parameters(key_type, hashes.SHA256())  # type: ignore[arg-type]
