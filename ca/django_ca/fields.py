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
# see <http://www.gnu.org/licenses/>.

"""Django form fields related to django-ca."""

import abc
import typing

from cryptography import x509
from cryptography.x509 import NameOID

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from . import widgets
from .extensions import get_extension_name
from .extensions.utils import (
    EXTENDED_KEY_USAGE_HUMAN_READABLE_NAMES,
    EXTENDED_KEY_USAGE_NAMES,
    KEY_USAGE_NAMES,
)
from .profiles import profile
from .typehints import ExtensionTypeTypeVar
from .utils import ADMIN_SUBJECT_OIDS, parse_general_name

if typing.TYPE_CHECKING:
    from .modelfields import LazyCertificateSigningRequest

_EXTENDED_KEY_USAGE_CHOICES = sorted(
    [(EXTENDED_KEY_USAGE_NAMES[oid], name) for oid, name in EXTENDED_KEY_USAGE_HUMAN_READABLE_NAMES.items()],
    key=lambda t: t[1],
)
_EXTENDED_KEY_USAGE_MAPPING = {serialized: oid for oid, serialized in EXTENDED_KEY_USAGE_NAMES.items()}
_KEY_USAGE_MAPPING = {v: k for k, v in KEY_USAGE_NAMES.items()}


class CertificateSigningRequestField(forms.CharField):
    """A form field for `~cg:cryptography.x509.CertificateSigningRequest` encoded as PEM."""

    start = "-----BEGIN CERTIFICATE REQUEST-----"
    end = "-----END CERTIFICATE REQUEST-----"
    simple_validation_error = _(
        "Could not parse PEM-encoded CSR. They usually look like this: <pre>%(start)s\n...\n%(end)s</pre>"
    ) % {"start": start, "end": end}

    def __init__(self, **kwargs: typing.Any) -> None:
        # COVERAGE NOTE: Below condition is never false, as we never pass a custom help text.
        if not kwargs.get("help_text"):  # pragma: no branch
            kwargs["help_text"] = _(
                """The Certificate Signing Request (CSR) in PEM format. To create a new one:
<span class="shell">openssl genrsa -out hostname.key 4096
openssl req -new -key hostname.key -out hostname.csr -utf8 -batch \\
                     -subj '/CN=hostname/emailAddress=root@hostname'
</span>"""
            )
        if not kwargs.get("widget"):  # pragma: no branch # we never pass a custom widget
            kwargs["widget"] = forms.Textarea
        super().__init__(**kwargs)
        self.widget.attrs.update({"cols": "64"})

    def prepare_value(
        self, value: typing.Optional[typing.Union[str, "LazyCertificateSigningRequest"]]
    ) -> str:
        """Prepare a value to a form that can be shown in HTML.

        Unfortunately this function is not documented by Django at all but is called when a form is rendered.

        This function receives ``None`` when viewing an initial form for a new instance. If form validation
        fails, it receives the string as posted by the user (which might be an invalid string). When viewing
        an existing certificate, it will receive the LazyField instance of the object.
        """
        if value is None:  # for new objects
            return ""
        if isinstance(value, str):  # when form validation fails
            return value

        # COVERAGE NOTE: This would happen if the field is editable, but is always read-only.
        return value.pem  # pragma: no cover

    # TYPE NOTE: django-stubs typehints this as Optional[Any], but we only ever observed receiving ``str``.
    def to_python(self, value: str) -> x509.CertificateSigningRequest:  # type: ignore[override]
        """Coerce given str to correct data type, raises ValidationError if not possible.

        This function is called during form validation.
        """
        if not value.startswith(self.start) or not value.strip().endswith(self.end):
            raise forms.ValidationError(mark_safe(self.simple_validation_error))
        try:
            return x509.load_pem_x509_csr(value.encode("utf-8"))
        except ValueError as ex:
            raise forms.ValidationError(str(ex)) from ex


class SubjectField(forms.MultiValueField):
    """A MultiValue field for a :py:class:`~django_ca.subject.Subject`."""

    required_oids = (NameOID.COMMON_NAME,)

    def __init__(self, **kwargs: typing.Any) -> None:
        fields = tuple(forms.CharField(required=v in self.required_oids) for v in ADMIN_SUBJECT_OIDS)

        # NOTE: do not pass initial here as this is done on webserver invocation
        #       This screws up tests.
        kwargs.setdefault("widget", widgets.SubjectWidget)
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list: typing.List[str]) -> x509.Name:
        # list comprehension is to filter empty fields
        return x509.Name(
            [x509.NameAttribute(oid, value) for oid, value in zip(ADMIN_SUBJECT_OIDS, data_list) if value]
        )


class SubjectAltNameField(forms.MultiValueField):
    """A MultiValueField for a Subject Alternative Name extension."""

    def __init__(self, **kwargs: typing.Any) -> None:
        fields = (
            forms.CharField(required=False),
            forms.BooleanField(required=False),
        )
        kwargs.setdefault("widget", widgets.SubjectAltNameWidget)
        kwargs.setdefault("initial", ["", profile.cn_in_san])
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list: typing.Tuple[str, bool]) -> typing.Tuple[str, bool]:
        return data_list


class GeneralNamesField(forms.CharField):
    widget = forms.Textarea
    default_error_messages = {
        "invalid": _("Unparsable General Name: %(error)s"),
    }

    def to_python(self, value: str) -> typing.List[x509.GeneralName]:
        values = []
        for line in value.splitlines():
            try:
                values.append(parse_general_name(line))
            except ValueError as ex:
                raise forms.ValidationError(
                    self.error_messages["invalid"], params={"error": ex}, code="invalid"
                )
        return values


class ExtensionField(forms.MultiValueField, typing.Generic[ExtensionTypeTypeVar], metaclass=abc.ABCMeta):
    """Base class for form fields that serialize to a :py:class:`~cg:cryptography.Extension`."""

    extension_type: typing.Type[ExtensionTypeTypeVar]
    fields: typing.Optional[typing.Tuple[forms.Field, ...]] = None

    def __init__(self, **kwargs: typing.Any) -> None:
        fields = self.get_fields() + (forms.BooleanField(required=False),)
        kwargs.setdefault("label", get_extension_name(self.extension_type.oid))
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(
        self, data_list: typing.List[typing.Any]
    ) -> typing.Optional[x509.Extension[ExtensionTypeTypeVar]]:
        if not data_list:
            return None

        *value, critical = data_list
        ext_value = self.get_value(*value)
        if ext_value is None:
            return None
        return x509.Extension(critical=critical, oid=self.extension_type.oid, value=ext_value)

    def get_fields(self) -> typing.Tuple[forms.Field, ...]:
        """Get the form fields used for this extension.

        Note that the `critical` input field is automatically appended.
        """
        if self.fields is not None:  # pragma: no branch
            return self.fields
        raise ValueError(  # pragma: no cover
            "ExtensionField must either set fields or implement get_fields()."
        )

    @abc.abstractmethod
    def get_value(self, value: typing.Any) -> typing.Optional[ExtensionTypeTypeVar]:
        """Get the extension value from the "compressed" form representation.

        Return `None` if no value was set and the extension should **not** be added.
        """


class MultipleChoiceExtensionField(ExtensionField[ExtensionTypeTypeVar]):
    """Base class for extensions that are basically a multiple choice field (plus critical)."""

    choices = typing.Tuple[typing.Tuple[str, str], ...]
    widget: typing.Type[widgets.MultipleChoiceExtensionWidget]

    def __init__(self, **kwargs: typing.Any) -> None:
        kwargs["widget"] = self.widget(choices=self.choices)
        super().__init__(**kwargs)

    def get_fields(self) -> typing.Tuple[forms.MultipleChoiceField]:
        return (forms.MultipleChoiceField(choices=self.choices, required=False),)

    def get_value(self, value: typing.List[str]) -> typing.Optional[ExtensionTypeTypeVar]:
        if not value:
            return None
        return self.get_values(value)

    @abc.abstractmethod
    def get_values(self, value: typing.List[str]) -> typing.Optional[ExtensionTypeTypeVar]:
        """Get the ExtensionType instance from the selected values."""


class ExtendedKeyUsageField(MultipleChoiceExtensionField[x509.ExtendedKeyUsage]):
    """Form field for a :py:class:`~cg:cryptography.x509.ExtendedKeyUsage` extension."""

    extension_type = x509.ExtendedKeyUsage
    choices = _EXTENDED_KEY_USAGE_CHOICES
    widget = widgets.ExtendedKeyUsageWidget

    def get_values(self, value: typing.List[str]) -> typing.Optional[x509.ExtendedKeyUsage]:
        return x509.ExtendedKeyUsage(usages=[_EXTENDED_KEY_USAGE_MAPPING[name] for name in value])


class IssuerAlternativeNameField(ExtensionField[x509.IssuerAlternativeName]):
    extension_type = x509.IssuerAlternativeName
    fields = (GeneralNamesField(required=False),)
    widget = widgets.IssuerAlternativeNameWidget

    def get_value(self, value: str) -> typing.Optional[x509.IssuerAlternativeName]:
        if not value:
            return None
        return x509.IssuerAlternativeName(general_names=value)


class KeyUsageField(MultipleChoiceExtensionField[x509.KeyUsage]):
    """Form field for a :py:class:`~cg:cryptography.x509.KeyUsage` extension."""

    # TYPEHINT NOTE: mypy typehints the tuple to the lambda function wrong and then mypy thinks the return
    #   value thought to be not comparable
    choices = sorted([(v, v) for v in KEY_USAGE_NAMES.values()], key=lambda t: t[1])  # type: ignore

    extension_type = x509.KeyUsage
    widget = widgets.KeyUsageWidget

    def get_values(self, value: typing.List[str]) -> typing.Optional[x509.KeyUsage]:
        values = {kwarg: choice in value for choice, kwarg in _KEY_USAGE_MAPPING.items()}
        return x509.KeyUsage(**values)


class OCSPNoCheckField(ExtensionField[x509.OCSPNoCheck]):
    """Form field for a :py:class:`~cg:cryptography.x509.OCSPNoCheck` extension."""

    extension_type = x509.OCSPNoCheck
    fields = (forms.BooleanField(required=False),)
    widget = widgets.OCSPNoCheckWidget

    def get_value(self, value: bool) -> typing.Optional[x509.OCSPNoCheck]:
        if value is True:
            return self.extension_type()
        return None


class TLSFeatureField(MultipleChoiceExtensionField[x509.TLSFeature]):
    """Form field for a :py:class:`~cg:cryptography.x509.TLSFeature` extension."""

    extension_type = x509.TLSFeature
    choices = (
        (x509.TLSFeatureType.status_request.name, "OCSPMustStaple"),
        (x509.TLSFeatureType.status_request_v2.name, "MultipleCertStatusRequest"),
    )  # TODO: choices can also be a function - better for testing for completeness
    widget = widgets.TLSFeatureWidget

    def get_values(self, value: typing.List[str]) -> typing.Optional[x509.TLSFeature]:
        # Note: sort value to get predictable output in test cases
        features = [getattr(x509.TLSFeatureType, elem) for elem in sorted(value)]
        return self.extension_type(features=features)
