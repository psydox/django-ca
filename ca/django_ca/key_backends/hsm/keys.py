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

"""Private key implementations that use an HSM in the background."""

import hashlib
from typing import ClassVar, Generic, NoReturn, TypeVar, cast

import pkcs11
from pkcs11 import MGF, Mechanism, Session
from pkcs11.constants import Attribute
from pkcs11.util.ec import encode_ec_public_key, encode_ecdsa_signature
from pkcs11.util.rsa import encode_rsa_public_key

from asn1crypto.core import OctetString
from asn1crypto.keys import PublicKeyInfo
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa, utils as asym_utils
from cryptography.hazmat.primitives.asymmetric.padding import (
    PSS,
    AsymmetricPadding,
    PKCS1v15,
    calculate_max_pss_salt_length,
)
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives.serialization import load_der_public_key

from django_ca.typehints import Self

EdwardsPublicKeyTypeVar = TypeVar("EdwardsPublicKeyTypeVar", ed448.Ed448PublicKey, ed25519.Ed25519PublicKey)


class PKCS11PrivateKeyMixin:
    """Mixin providing common functionality to PKCS11 key implementations."""

    # pylint: disable=missing-function-docstring  # implements standard functions of the base class.

    key_type: pkcs11.KeyType

    def __init__(
        self,
        session: Session,
        key_id: str,
        key_label: str,
        pkcs11_private_key: pkcs11.PrivateKey | None = None,
        pkcs11_public_key: pkcs11.PublicKey | None = None,
    ) -> None:
        self._session = session
        self._key_id = key_id.encode()
        self._key_label = key_label
        self._pkcs11_private_key = pkcs11_private_key
        self._pkcs11_public_key = pkcs11_public_key

        super().__init__()

    def __copy__(self) -> Self:  # pragma: no cover
        return type(self)(
            self._session,
            self._key_id.decode(),
            self._key_label,
            self._pkcs11_private_key,
            self._pkcs11_public_key,
        )

    def decrypt(self, ciphertext: bytes, padding: AsymmetricPadding) -> bytes:
        raise NotImplementedError(
            "Decryption is not implemented for keys stored in a hardware security module (HSM)."
        )

    def private_bytes(
        self,
        encoding: serialization.Encoding,
        format: serialization.PrivateFormat,  # pylint: disable=redefined-builtin  # given by cryptography
        encryption_algorithm: serialization.KeySerializationEncryption,
    ) -> bytes:
        raise NotImplementedError(
            "Private bytes cannot be retrieved for keys stored in a hardware security module (HSM)."
        )

    def private_numbers(self) -> NoReturn:
        raise NotImplementedError(
            "Private numbers cannot be retrieved for keys stored in a hardware security module (HSM)."
        )

    @property
    def pkcs11_private_key(self) -> pkcs11.PrivateKey:
        if self._pkcs11_private_key is None:
            self._pkcs11_private_key = self._session.get_key(
                key_type=self.key_type,
                object_class=pkcs11.ObjectClass.PRIVATE_KEY,
                id=self._key_id,
                label=self._key_label,
            )
        return self._pkcs11_private_key

    @property
    def pkcs11_public_key(self) -> pkcs11.PublicKey:
        if self._pkcs11_public_key is None:
            self._pkcs11_public_key = self._session.get_key(
                key_type=self.key_type,
                object_class=pkcs11.ObjectClass.PUBLIC_KEY,
                id=self._key_id,
                label=self._key_label,
            )
        return self._pkcs11_public_key


class PKCS11EdwardsPrivateKeyMixin(PKCS11PrivateKeyMixin, Generic[EdwardsPublicKeyTypeVar]):
    """Specialized mixin for Ed448 and Ed5519 keys (which handle identical)."""

    # pylint: disable=missing-function-docstring  # implements standard functions of the base class.

    public_key_algorithm: ClassVar[str]
    key_type = pkcs11.KeyType.EC_EDWARDS
    cryptograph_key_type: EdwardsPublicKeyTypeVar

    def private_bytes_raw(self) -> bytes:
        raise NotImplementedError(
            "Private bytes cannot be retrieved for keys stored in a hardware security module (HSM)."
        )

    def public_key(self) -> EdwardsPublicKeyTypeVar:
        ec_point = bytes(OctetString.load(self.pkcs11_public_key[Attribute.EC_POINT]))
        value = {"algorithm": {"algorithm": self.public_key_algorithm}, "public_key": ec_point}
        public_key: bytes = PublicKeyInfo(value).dump()

        return cast(EdwardsPublicKeyTypeVar, load_der_public_key(public_key))

    def sign(self, data: bytes) -> bytes:
        return self.pkcs11_private_key.sign(data, mechanism=pkcs11.Mechanism.EDDSA)  # type: ignore[no-any-return]


# pylint: disable-next=abstract-method  # private key functions are deliberately not implemented in base.
class PKCS11RSAPrivateKey(PKCS11PrivateKeyMixin, rsa.RSAPrivateKey):
    """Private key implementation for RSA keys stored in a HSM."""

    key_type = pkcs11.KeyType.RSA

    def public_key(self) -> RSAPublicKey:
        der_public_key = encode_rsa_public_key(self.pkcs11_public_key)
        return cast(RSAPublicKey, load_der_public_key(der_public_key))

    @property
    def key_size(self) -> int:
        return self.public_key().key_size

    def _get_pss_signing_parameters(
        self, padding: PSS, algorithm: hashes.HashAlgorithm | Prehashed
    ) -> tuple[Mechanism, MGF, int]:
        # PYLINT NOTE: No public access available.
        mgf_algorithm: hashes.HashAlgorithm = padding.mgf._algorithm  # pylint: disable=protected-access
        if isinstance(mgf_algorithm, hashes.SHA224):
            pkcs11_mgf_algorithm = MGF.SHA224
        elif isinstance(mgf_algorithm, hashes.SHA256):
            pkcs11_mgf_algorithm = MGF.SHA256
        elif isinstance(mgf_algorithm, hashes.SHA384):
            pkcs11_mgf_algorithm = MGF.SHA384
        elif isinstance(mgf_algorithm, hashes.SHA512):
            pkcs11_mgf_algorithm = MGF.SHA512
        else:
            raise ValueError(f"{mgf_algorithm.name}: Hash algorithm not supported.")

        if isinstance(algorithm, Prehashed):
            algorithm = algorithm._algorithm  # pylint: disable=protected-access  # only way to access

        if isinstance(algorithm, hashes.SHA224):
            pkcs11_algorithm = Mechanism.SHA224
        elif isinstance(algorithm, hashes.SHA256):
            pkcs11_algorithm = Mechanism.SHA256
        elif isinstance(algorithm, hashes.SHA384):
            pkcs11_algorithm = Mechanism.SHA384
        elif isinstance(algorithm, hashes.SHA512):
            pkcs11_algorithm = Mechanism.SHA512
        else:
            raise ValueError(f"{algorithm.name}: Hash algorithm not supported.")

        # PYLINT NOTE: No public access available.
        salt_length = padding._salt_length  # pylint: disable=protected-access
        if salt_length == PSS.MAX_LENGTH:
            pkcs11_salt_length = calculate_max_pss_salt_length(self, algorithm)
        elif salt_length == PSS.DIGEST_LENGTH:
            raise ValueError("DIGEST_LENGTH is not supported when signing.")
        elif salt_length == PSS.AUTO:
            raise ValueError("AUTO is not supported when signing.")
        else:
            pkcs11_salt_length = cast(int, salt_length)  # it's already an int

        return (pkcs11_algorithm, pkcs11_mgf_algorithm, pkcs11_salt_length)

    def sign(
        self,
        data: bytes,
        padding: AsymmetricPadding,
        algorithm: asym_utils.Prehashed | hashes.HashAlgorithm,
    ) -> bytes:
        mechanism_param = None
        if isinstance(padding, PSS):
            mechanism_param = self._get_pss_signing_parameters(padding, algorithm)

        if isinstance(algorithm, hashes.SHA224) and isinstance(padding, PSS):
            # NOTE: using Mechanism.RSA_PKCS_PSS as suggested in the docs does not work at all.
            mechanism: hashes.HashAlgorithm = pkcs11.Mechanism.SHA224_RSA_PKCS_PSS
        elif isinstance(algorithm, hashes.SHA224) and isinstance(padding, PKCS1v15):
            mechanism = pkcs11.Mechanism.SHA224_RSA_PKCS
        elif isinstance(algorithm, hashes.SHA256) and isinstance(padding, PSS):
            mechanism = pkcs11.Mechanism.SHA256_RSA_PKCS_PSS
        elif isinstance(algorithm, hashes.SHA256) and isinstance(padding, PKCS1v15):
            mechanism = pkcs11.Mechanism.SHA256_RSA_PKCS
        elif isinstance(algorithm, hashes.SHA384) and isinstance(padding, PSS):
            mechanism = pkcs11.Mechanism.SHA384_RSA_PKCS_PSS
        elif isinstance(algorithm, hashes.SHA384) and isinstance(padding, PKCS1v15):
            mechanism = pkcs11.Mechanism.SHA384_RSA_PKCS
        elif isinstance(algorithm, hashes.SHA512) and isinstance(padding, PSS):
            mechanism = pkcs11.Mechanism.SHA512_RSA_PKCS_PSS
        elif isinstance(algorithm, hashes.SHA512) and isinstance(padding, PKCS1v15):
            mechanism = pkcs11.Mechanism.SHA512_RSA_PKCS
        elif isinstance(algorithm, Prehashed) and isinstance(padding, PKCS1v15):
            # NOTE: pkcs11.Mechanism.RSA_PKCS does not work.
            raise ValueError("Prehashed data with PKCS1v15 is not supported.")
        elif isinstance(algorithm, Prehashed) and isinstance(padding, PSS):
            mechanism = pkcs11.Mechanism.RSA_PKCS_PSS
        elif isinstance(algorithm, hashes.SHA3_224 | hashes.SHA3_384 | hashes.SHA3_256 | hashes.SHA3_512):
            raise ValueError("SHA3 is not support by the HSM backend.")
        else:
            assert isinstance(algorithm, hashes.HashAlgorithm)  # Cannot be pre-hashed at this point
            raise ValueError(
                f"{algorithm.name} with {padding.name} padding: Unknown signing algorithm and/or padding."
            )

        # TYPEHINT NOTE: library is not type-hinted.
        return self.pkcs11_private_key.sign(data, mechanism=mechanism, mechanism_param=mechanism_param)  # type: ignore[no-any-return]


class PKCS11EllipticCurvePrivateKey(PKCS11PrivateKeyMixin, ec.EllipticCurvePrivateKey):
    """Private key implementation for EC keys stored in a HSM."""

    key_type = pkcs11.KeyType.EC

    @property
    def curve(self) -> ec.EllipticCurve:
        return self.public_key().curve

    def exchange(self, algorithm: ec.ECDH, peer_public_key: ec.EllipticCurvePublicKey) -> bytes:
        raise NotImplementedError(
            "exchange is not implemented for keys stored in a hardware security module (HSM)."
        )

    @property
    def key_size(self) -> int:
        return self.public_key().key_size

    def public_key(self) -> ec.EllipticCurvePublicKey:
        public_key = encode_ec_public_key(self.pkcs11_public_key)
        return cast(ec.EllipticCurvePublicKey, load_der_public_key(public_key))

    def sign(
        self,
        data: bytes | bytearray | memoryview,
        signature_algorithm: ec.EllipticCurveSignatureAlgorithm,
    ) -> bytes:
        if isinstance(signature_algorithm.algorithm, hashes.SHA224):
            hasher = hashlib.sha224()
        elif isinstance(signature_algorithm.algorithm, hashes.SHA256):
            hasher = hashlib.sha256()
        elif isinstance(signature_algorithm.algorithm, hashes.SHA384):
            hasher = hashlib.sha384()
        elif isinstance(signature_algorithm.algorithm, hashes.SHA512):
            hasher = hashlib.sha512()
        elif isinstance(
            signature_algorithm.algorithm,
            hashes.SHA3_224 | hashes.SHA3_384 | hashes.SHA3_256 | hashes.SHA3_512,
        ):
            raise ValueError("SHA3 is not support by the HSM backend.")
        elif isinstance(signature_algorithm.algorithm, asym_utils.Prehashed):
            raise ValueError("Signing of prehashed data is not supported.")
        else:
            raise ValueError(f"{signature_algorithm.algorithm.name}: Signature algorithm is not supported.")

        hasher.update(data)
        data = hasher.digest()

        signature = self.pkcs11_private_key.sign(data, mechanism=pkcs11.Mechanism.ECDSA)
        return encode_ecdsa_signature(signature)  # type: ignore[no-any-return]


# pylint: disable-next=abstract-method  # private key functions are deliberately not implemented in base.
class PKCS11Ed25519PrivateKey(  # type: ignore[misc]  # mypy complains about sign() not matching.
    PKCS11EdwardsPrivateKeyMixin[ed25519.Ed25519PublicKey], ed25519.Ed25519PrivateKey
):
    """Private key implementation for Ed25519 keys stored in a HSM."""

    public_key_algorithm = "ed25519"


# pylint: disable-next=abstract-method  # private key functions are deliberately not implemented in base.
class PKCS11Ed448PrivateKey(  # type: ignore[misc]  # mypy complains about sign() not matching.
    PKCS11EdwardsPrivateKeyMixin[ed448.Ed448PublicKey], ed448.Ed448PrivateKey
):
    """Private key implementation for Ed448 keys stored in a HSM."""

    public_key_algorithm = "ed448"


PKCS11PrivateKeyTypes = (
    PKCS11RSAPrivateKey | PKCS11Ed25519PrivateKey | PKCS11Ed448PrivateKey | PKCS11EllipticCurvePrivateKey
)
