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

"""Asynchronous Celery tasks for django-ca.

.. seealso:: https://docs.celeryproject.org/en/stable/index.html
"""

import logging
import typing
from datetime import timedelta
from http import HTTPStatus
from typing import Any, Iterable, List, Optional, Tuple

import requests

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtensionOID

from django.db import transaction
from django.utils import timezone

from django_ca import ca_settings, constants
from django_ca.acme.validation import validate_dns_01
from django_ca.constants import EXTENSION_DEFAULT_CRITICAL
from django_ca.models import (
    AcmeAuthorization,
    AcmeCertificate,
    AcmeChallenge,
    AcmeOrder,
    Certificate,
    CertificateAuthority,
)
from django_ca.profiles import profiles
from django_ca.typehints import AllowedHashTypes
from django_ca.utils import parse_general_name

log = logging.getLogger(__name__)

FuncTypeVar = typing.TypeVar("FuncTypeVar", bound=typing.Callable[..., Any])

try:
    from celery import shared_task
    from celery.local import Proxy
except ImportError:

    def shared_task(func: FuncTypeVar) -> "Proxy[FuncTypeVar]":
        """Dummy decorator so that we can use the decorator whether celery is installed or not."""

        # We do not yet need this, but might come in handy in the future:
        # func.delay = lambda *a, **kw: func(*a, **kw)
        # func.apply_async = lambda *a, **kw: func(*a, **kw)
        func.delay = func  # type: ignore[attr-defined]
        return typing.cast("Proxy[FuncTypeVar]", func)


def run_task(task: "Proxy[FuncTypeVar]", *args: Any, **kwargs: Any) -> Any:
    """Function that passes `task` to celery or invokes it directly, depending on if Celery is installed."""
    eager = kwargs.pop("eager", False)

    if ca_settings.CA_USE_CELERY is True and eager is False:
        return task.delay(*args, **kwargs)

    return task(*args, **kwargs)


@shared_task
def cache_crl(serial: str, **kwargs: Any) -> None:
    """Task to cache the CRL for a given CA."""
    ca = CertificateAuthority.objects.get(serial=serial)
    ca.cache_crls(**kwargs)


@shared_task
def cache_crls(serials: Optional[Iterable[str]] = None) -> None:
    """Task to cache the CRLs for all CAs."""
    if serials is None:  # pragma: no cover; just to make mypy happy
        serials = []

    if not serials:
        serials = typing.cast(
            Iterable[str], CertificateAuthority.objects.usable().values_list("serial", flat=True)
        )

    for serial in serials:
        run_task(cache_crl, serial)


@shared_task
def generate_ocsp_key(
    serial: str,
    expires: Optional[int] = None,
    algorithm: Optional[str] = None,
    elliptic_curve: Optional[str] = None,
    **kwargs: Any,
) -> Tuple[str, str, int]:
    """Task to generate an OCSP key for the CA named by `serial`."""

    ca: CertificateAuthority = CertificateAuthority.objects.get(serial=serial)

    parsed_expires: Optional[timedelta] = None
    parsed_algorithm: Optional[AllowedHashTypes] = None
    parsed_curve: Optional[ec.EllipticCurve] = None
    if expires is not None:
        parsed_expires = timedelta(seconds=expires)
    if algorithm is not None:
        parsed_algorithm = constants.HASH_ALGORITHM_TYPES[algorithm]()
    if elliptic_curve is not None:
        parsed_curve = constants.ELLIPTIC_CURVE_TYPES[elliptic_curve]()

    private_path, cert_path, cert = ca.generate_ocsp_key(
        expires=parsed_expires, algorithm=parsed_algorithm, elliptic_curve=parsed_curve, **kwargs
    )
    return private_path, cert_path, cert.pk


@shared_task
def generate_ocsp_keys(**kwargs: Any) -> List[Tuple[str, str, int]]:
    """Task to generate an OCSP keys for all usable CAs."""
    keys = []
    for serial in CertificateAuthority.objects.usable().values_list("serial", flat=True):
        keys.append(generate_ocsp_key(serial, **kwargs))
    return keys


@shared_task
@transaction.atomic
def acme_validate_challenge(challenge_pk: int) -> None:
    """Validate an ACME challenge."""
    if not ca_settings.CA_ENABLE_ACME:
        log.error("ACME is not enabled.")
        return

    try:
        challenge = AcmeChallenge.objects.url().get(pk=challenge_pk)
    except AcmeChallenge.DoesNotExist:
        log.error("Challenge with id=%s not found", challenge_pk)
        return

    # Whoever is invoking this task is responsible for setting the status to "processing" first.
    if challenge.status != AcmeChallenge.STATUS_PROCESSING:
        log.error(
            "%s: %s: Invalid state (must be %s)", challenge, challenge.status, AcmeChallenge.STATUS_PROCESSING
        )
        return

    # If the auth cannot be used for validation, neither can this challenge. We check auth.usable instead of
    # challenge.usable b/c a challenge in the "processing" state is not "usable" (= it is already being used).
    if challenge.auth.usable is False:
        log.error("%s: Authentication is not usable", challenge)
        return

    # General data for challenge validation
    value = challenge.auth.value

    # Challenge is marked as invalid by default
    challenge_valid = False

    # Validate HTTP challenge (only thing supported so far)
    if challenge.type == AcmeChallenge.TYPE_HTTP_01:
        decoded_token = challenge.encoded_token.decode("utf-8")
        expected = challenge.expected

        if requests is None:  # pragma: no cover
            log.error("requests is not installed, cannot do http-01 challenge validation.")
            return

        url = f"http://{value}/.well-known/acme-challenge/{decoded_token}"

        try:
            with requests.get(url, timeout=1, stream=True) as response:
                # Only fetch the response body if the status code is HTTP 200 (OK)
                if response.status_code == HTTPStatus.OK:
                    # Only fetch the expected number of bytes to prevent a large file ending up in memory
                    # But fetch one extra byte (if available) to make sure that response has no extra bytes
                    received = response.raw.read(len(expected) + 1, decode_content=True)
                    challenge_valid = received == expected
        except Exception as ex:  # pylint: disable=broad-except
            log.exception(ex)
    elif challenge.type == AcmeChallenge.TYPE_DNS_01:
        challenge_valid = validate_dns_01(challenge)

    # TODO: support ALPN_01 challenges
    # elif challenge.type == AcmeChallenge.TYPE_TLS_ALPN_01:
    #     host = socket.gethostbyname(value)
    #     sni_cert = crypto_util.probe_sni(
    #         host=host, port=443, name=value, alpn_protocols=[TlsAlpnProtocol.V1]
    #     )
    else:
        log.error("%s: Challenge type is not supported.", challenge)

    # Transition state of the challenge depending on if the challenge is valid or not. RFC8555, Section 7.1.6:
    #
    #   "If validation is successful, the challenge moves to the "valid" state; if there is an error, the
    #   challenge moves to the "invalid" state."
    #
    # We also transition the matching authorization object:
    #
    #   "If one of the challenges listed in the authorization transitions to the "valid" state, then the
    #   authorization also changes to the "valid" state.  If the client attempts to fulfill a challenge and
    #   fails, or if there is an error while the authorization is still pending, then the authorization
    #   transitions to the "invalid" state.
    #
    # We also transition the matching order object (section 7.4):
    #
    #   "* ready: The server agrees that the requirements have been fulfilled, and is awaiting finalization.
    #   Submit a finalization request."
    if challenge_valid:
        challenge.status = AcmeChallenge.STATUS_VALID
        challenge.validated = timezone.now()
        challenge.auth.status = AcmeAuthorization.STATUS_VALID

        # Set the order status to READY if all challenges are valid
        auths = AcmeAuthorization.objects.filter(order=challenge.auth.order)
        auths = auths.exclude(status=AcmeAuthorization.STATUS_VALID)
        if not auths.exclude(pk=challenge.auth.pk).exists():
            log.info("Order is now valid")
            challenge.auth.order.status = AcmeOrder.STATUS_READY
    else:
        challenge.status = AcmeChallenge.STATUS_INVALID

        # RFC 8555, section 7.1.6:
        #
        # If the client attempts to fulfill a challenge and fails, or if there is an error while the
        # authorization is still pending, then the authorization transitions to the "invalid" state.
        challenge.auth.status = AcmeAuthorization.STATUS_INVALID

        # RFC 8555, section 7.1.6:
        #
        #   If an error occurs at any of these stages, the order moves to the "invalid" state.
        challenge.auth.order.status = AcmeOrder.STATUS_INVALID

    log.info("%s is %s", challenge, challenge.status)
    challenge.save()
    challenge.auth.save()
    challenge.auth.order.save()


@shared_task
@transaction.atomic
def acme_issue_certificate(acme_certificate_pk: int) -> None:
    """Actually issue an ACME certificate."""
    if not ca_settings.CA_ENABLE_ACME:
        log.error("ACME is not enabled.")
        return

    try:
        acme_cert = AcmeCertificate.objects.select_related("order__account__ca").get(pk=acme_certificate_pk)
    except AcmeCertificate.DoesNotExist:
        log.error("Certificate with id=%s not found", acme_certificate_pk)
        return

    if acme_cert.usable is False:
        log.error("%s: Cannot issue certificate for this order", acme_cert.order)
        return

    names = [a.subject_alternative_name for a in acme_cert.order.authorizations.all()]
    log.info("%s: Issuing certificate for %s", acme_cert.order, ",".join(names))
    subject_alternative_names = x509.SubjectAlternativeName([parse_general_name(name) for name in names])

    extensions = [
        x509.Extension(
            oid=ExtensionOID.SUBJECT_ALTERNATIVE_NAME,
            critical=EXTENSION_DEFAULT_CRITICAL[ExtensionOID.SUBJECT_ALTERNATIVE_NAME],
            value=subject_alternative_names,
        )
    ]

    ca = acme_cert.order.account.ca
    profile = profiles[ca.acme_profile]

    # Honor not_after from the order if set
    if acme_cert.order.not_after:
        expires = acme_cert.order.not_after
    else:
        expires = timezone.now() + ca_settings.ACME_DEFAULT_CERT_VALIDITY

    csr = acme_cert.parse_csr()

    # Finally, actually create a certificate
    cert = Certificate.objects.create_cert(
        ca, csr=csr, profile=profile, expires=expires, extensions=extensions
    )

    acme_cert.cert = cert
    acme_cert.order.status = AcmeOrder.STATUS_VALID
    acme_cert.order.save()
    acme_cert.save()


@shared_task
@transaction.atomic
def acme_cleanup() -> None:
    """Cleanup expired ACME orders."""

    if not ca_settings.CA_ENABLE_ACME:
        # NOTE: Since this task does only cleanup, log message is only info.
        log.info("ACME is not enabled, not doing anything.")
        return

    # Delete orders that expired more than a day ago.
    threshold = timezone.now() - timedelta(days=1)
    AcmeOrder.objects.filter(expires__lt=threshold).delete()
