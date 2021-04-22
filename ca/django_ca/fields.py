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

import typing

from django import forms

from .extensions import Extension
from .profiles import profile
from .subject import Subject
from .utils import SUBJECT_FIELDS
from .widgets import MultiValueExtensionWidget
from .widgets import SubjectAltNameWidget
from .widgets import SubjectWidget


class SubjectField(forms.MultiValueField):
    """A MultiValue field for a :py:class:`~django_ca.subject.Subject`."""

    def __init__(self, **kwargs: typing.Any) -> None:
        fields = (
            forms.CharField(required=False),  # C
            forms.CharField(required=False),  # ST
            forms.CharField(required=False),  # L
            forms.CharField(required=False),  # O
            forms.CharField(required=False),  # OU
            forms.CharField(),  # CN
            forms.CharField(required=False),  # E
        )

        # NOTE: do not pass initial here as this is done on webserver invocation
        #       This screws up tests.
        kwargs.setdefault("widget", SubjectWidget)
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list: typing.List[typing.Tuple[str, str]]) -> Subject:
        # list comprehension is to filter empty fields
        return Subject([(k, v) for k, v in zip(SUBJECT_FIELDS, data_list) if v])


class SubjectAltNameField(forms.MultiValueField):
    """A MultiValueField for a Subject Alternative Name extension."""

    def __init__(self, **kwargs: typing.Any) -> None:
        fields = (
            forms.CharField(required=False),
            forms.BooleanField(required=False),
        )
        kwargs.setdefault("widget", SubjectAltNameWidget)
        kwargs.setdefault("initial", ["", profile.cn_in_san])
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list: typing.Tuple[str, bool]) -> typing.Tuple[str, bool]:
        return data_list


class MultiValueExtensionField(forms.MultiValueField):
    """A MultiValueField for multiple-choice extensions (e.g. :py:class:`~django_ca.extensions.KeyUsage`."""

    def __init__(
        self,
        extension: typing.Type[Extension[typing.Any, typing.Any, typing.Any]],
        **kwargs: typing.Any
    ) -> None:
        self.extension = extension
        kwargs.setdefault("label", extension.name)
        ext = profile.extensions.get(self.extension.key)
        if ext:
            ext = ext.serialize()
            kwargs.setdefault("initial", [ext["value"], ext["critical"]])

        # NOTE: only use extensions that define CHOICES
        choices: typing.Tuple[typing.Tuple[str, str], ...] = extension.CHOICES  # type: ignore[attr-defined]
        fields = (
            forms.MultipleChoiceField(required=False, choices=choices),
            forms.BooleanField(required=False),
        )

        widget = MultiValueExtensionWidget(choices=choices)
        super().__init__(fields=fields, require_all_fields=False, widget=widget, **kwargs)

    def compress(
        self, data_list: typing.Tuple[typing.List[str], bool]
    ) -> Extension[typing.Any, typing.Any, typing.Any]:
        return self.extension(
            {
                "critical": data_list[1],
                "value": data_list[0],
            }
        )
