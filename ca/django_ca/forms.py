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

"""Specialized Django forms for the admin interface."""

import typing
from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID

from django import forms
from django.contrib.admin.widgets import AdminDateWidget, AdminSplitDateTime
from django.forms.models import ModelFormOptions
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ca import ca_settings, constants, fields
from django_ca.models import Certificate, CertificateAuthority, X509CertMixin
from django_ca.querysets import CertificateAuthorityQuerySet
from django_ca.utils import parse_general_name
from django_ca.widgets import ProfileWidget

if typing.TYPE_CHECKING:
    CertificateModelForm = forms.ModelForm[Certificate]
    X509CertMixinModelForm = forms.ModelForm[X509CertMixin]
else:
    CertificateModelForm = X509CertMixinModelForm = forms.ModelForm

HASH_ALGORITHM_CHOICES = tuple(
    [("", "None")] + sorted([(name, name) for name in constants.HASH_ALGORITHM_TYPES], key=lambda t: t[1])
)


def _initial_expires() -> datetime:
    return datetime.today() + ca_settings.CA_DEFAULT_EXPIRES


def _profile_choices() -> Iterable[Tuple[str, str]]:
    return sorted([(p, p) for p in ca_settings.CA_PROFILES], key=lambda e: e[0])


class X509CertMixinAdminForm(X509CertMixinModelForm):
    """Admin form to add a dynamic help text to the ``pub`` field.

    The help_text is set by adding a value to the help_texts dictionary of the models Meta class. We use this
    unusual way because it should contain links referencing the currently displayed object and the normal
    methods do not work this way:

    * You cannot use the normal way of setting ``help_texts`` in the forms ``Meta`` class, because we cannot
      reference the object instance here.
    * We cannot access self.fields['pub'] in the constructor, because it is a readonly field and thus not
      present in the form.
    """

    _meta: "ModelFormOptions[X509CertMixin]"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        meta = self._meta
        if meta.help_texts is None:  # pragma: no cover
            # help_texts is always set since we have a Meta class, but keeping this here as a precaution.
            meta.help_texts = {}

        info = f"{self.instance._meta.app_label}_{self.instance._meta.model_name}"
        url = reverse(f"admin:{info}_download", kwargs={"pk": self.instance.pk})
        bundle_url = reverse(f"admin:{info}_download_bundle", kwargs={"pk": self.instance.pk})
        meta.help_texts["pub_pem"] = _(
            'Download: <a href="%s?format=PEM">as PEM</a> | <a href="%s?format=DER">as DER</a><br />'
            'Certificate bundle: <a href="%s?format=PEM">as PEM</a>'
        ) % (url, url, bundle_url)

    class Meta:
        help_texts = {
            "hpkp_pin": _(
                """SHA-256 HPKP pin of this certificate. See also
<a href="https://en.wikipedia.org/wiki/HTTP_Public_Key_Pinning">HTTP Public Key Pinning</a>
on Wikipedia."""
            ),
        }


class CertificateAuthorityForm(X509CertMixinAdminForm):
    """Admin form for :py:class:`django_ca.models.CertificateAuthority`."""

    acme_profile = forms.ChoiceField(
        label=_("Profile"),
        required=True,
        widget=ProfileWidget,
        help_text=_("Profile used when issuing certificates via ACMEv2."),
        initial=ca_settings.CA_DEFAULT_PROFILE,
        choices=_profile_choices,
    )


class CreateCertificateBaseForm(CertificateModelForm):
    """Base class for forms that create a certificate.

    This is used by forms for creating a new certificate and resigning an existing one."""

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text=_("Password for the private key. If not given, the private key must be unencrypted."),
    )
    expires = forms.DateField(initial=_initial_expires, widget=AdminDateWidget())
    subject = fields.SubjectField(label="Subject", required=True)
    subject_alternative_name = fields.SubjectAlternativeNameField(
        required=False,
        help_text=_("""Coma-separated list of alternative names for the certificate."""),
    )
    profile = forms.ChoiceField(
        required=False,
        widget=ProfileWidget,
        help_text=_("Select a suitable profile or manually select X509 extensions below."),
        initial=ca_settings.CA_DEFAULT_PROFILE,
        choices=_profile_choices,
    )
    algorithm = forms.ChoiceField(
        required=False,
        label=_("Signature hash algorithm"),
        initial=constants.HASH_ALGORITHM_NAMES[type(ca_settings.CA_DEFAULT_SIGNATURE_HASH_ALGORITHM)],
        choices=HASH_ALGORITHM_CHOICES,
        help_text=_(
            "SHA-512 is fine for RSA/EC-based certificate authorities, choose None for Ed448/Ed25519-based "
            "certificate authorities and SHA-256 for DSA-based certificate authorities."
        ),
    )
    autogenerated = forms.BooleanField(
        required=False, help_text=_("If this certificate was automatically generated.")
    )

    authority_information_access = fields.AuthorityInformationAccessField(
        help_text=_("Indicates how to access information and services of the issuer.")
    )
    crl_distribution_points = fields.CRLDistributionPointField(
        help_text=_("Where to retrieve Certificate Revocation Lists."),
    )
    freshest_crl = fields.FreshestCRLField(
        help_text=_("Where to retrieve Delta CRLs (rarely used, not supported by django-ca).")
    )
    issuer_alternative_name = fields.IssuerAlternativeNameField(
        help_text=_("Additional information about the issuer (rarely used).")
    )
    key_usage = fields.KeyUsageField(help_text=_("Defines the purpose of the certificate."))
    extended_key_usage = fields.ExtendedKeyUsageField(
        help_text=_("Defines additional purposes of the certificate.")
    )
    ocsp_no_check = fields.OCSPNoCheckField(
        help_text=_(
            "Indicates that an OCSP client can trust the certificate. Used in OCSP responder certificates."
        )
    )
    tls_feature = fields.TLSFeatureField(
        help_text=_("Allows enforcing TLS protocol features. Only OCSPMustStaple is commonly used.")
    )

    # Prevent auto-completing the password field. Browsers will otherwise prefill this field with the *users*
    # password, which is usually the wrong password. Especially annoying for CAs without a password, as the
    # browser will prevent form submission without entering a different non-empty password.
    password.widget.attrs.update({"autocomplete": "new-password"})

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Set choices, so we can filter out CAs where the private key does not exist locally
        field = typing.cast(forms.ModelChoiceField, self.fields["ca"])
        qs = typing.cast(CertificateAuthorityQuerySet, field.queryset)
        field.choices = [
            (field.prepare_value(ca), field.label_from_instance(ca))
            for ca in qs.filter(enabled=True)
            if ca.key_exists
        ]

    def clean_algorithm(self) -> Optional[hashes.HashAlgorithm]:  # pylint: disable=missing-function-docstring
        if algorithm_name := self.cleaned_data["algorithm"]:
            return constants.HASH_ALGORITHM_TYPES[algorithm_name]()
        return None  # required by mypy

    def clean_expires(self) -> datetime:  # pylint: disable=missing-function-docstring
        expires: datetime = self.cleaned_data["expires"]
        if expires < date.today():
            raise forms.ValidationError(_("Certificate cannot expire in the past."))
        return expires

    def clean_password(self) -> Optional[bytes]:  # pylint: disable=missing-function-docstring
        password: str = self.cleaned_data["password"]
        if not password:
            return None
        return password.encode("utf-8")

    def clean(self) -> Optional[Dict[str, Any]]:
        data = super().clean()

        # COVERAGE Unclear if/when this happens, but django-stubs==1.15.0 reports data as Optional.
        if data is None:  # pragma: no cover
            return data

        expires = data.get("expires")
        ca: CertificateAuthority = data["ca"]
        password = data.get("password")
        subject = data.get("subject")
        algorithm = data.get("algorithm")
        subject_alternative_name, cn_in_san = data.get("subject_alternative_name", (None, False))

        # Load the CA to test the password
        try:
            ca.key(password)
        except Exception as e:  # pylint: disable=broad-except; for simplicity
            self.add_error("password", str(e))

        if ca.key_type in ("Ed448", "Ed25519") and algorithm is not None:
            self.add_error(
                "algorithm",
                _("%(key_type)s-based certificate authorities do not use a signature hash algorithm.")
                % {"key_type": ca.key_type},
            )
        elif ca.key_type == "DSA" and not isinstance(algorithm, hashes.SHA256):
            self.add_error(
                "algorithm",
                _("DSA-based certificate authorities require a SHA-256 signature hash algorithm."),
            )
        elif ca.key_type not in ("Ed448", "Ed25519") and algorithm is None:
            self.add_error(
                "algorithm",
                _("%(key_type)s-based certificate authorities require a signature hash algorithm.")
                % {"key_type": ca.key_type},
            )

        if cn_in_san and subject:  # subject is None if user does not enter *anything*
            # NOTE: subject MUST have a common name at this point: If the user did not enter one, it would
            # have been rejected by SubjectField already.
            cname = next(attr for attr in subject if attr.oid == NameOID.COMMON_NAME)  # pragma: no branch

            try:
                parse_general_name(cname.value)
            except ValueError:
                self.add_error(
                    "subject_alternative_name",
                    _(
                        "The CommonName cannot be parsed as general name. Either change the "
                        "CommonName or do not include it."
                    ),
                )

        if ca and expires and ca.expires.date() < expires:
            stamp = ca.expires.strftime("%Y-%m-%d")
            self.add_error("expires", _("CA expires on %s, certificate must not expire after that.") % stamp)
        return data

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "django_ca/admin/js/extensions.js",
            "django_ca/admin/js/ca-details.js",
        )

    class Meta:
        model = Certificate
        fields = [
            "watchers",
            "ca",
        ]


class CreateCertificateForm(CreateCertificateBaseForm):
    """Admin form for creating a completely new certificate."""

    class Meta:
        model = Certificate
        fields = [
            "csr",
            "watchers",
            "ca",
        ]


class ResignCertificateForm(CreateCertificateBaseForm):
    """Admin form for resigning an existing certificate."""


class RevokeCertificateForm(CertificateModelForm):
    """Admin form for revoking a certificate."""

    class Media:
        js = (
            # jquery/core.js for the datetime widgets:
            "admin/js/vendor/jquery/jquery.js",
            "admin/js/jquery.init.js",
            "admin/js/core.js",
        )

    class Meta:
        model = Certificate
        fields = ["revoked_reason", "compromised"]
        field_classes = {
            "compromised": forms.SplitDateTimeField,
        }
        widgets = {
            "compromised": AdminSplitDateTime,
        }
