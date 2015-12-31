# -*- coding: utf-8 -*-
#
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

from datetime import datetime
from datetime import timedelta

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .fields import BasicConstraintsField
from .models import Certificate


def _initial_expires():
    return datetime.today() + timedelta(days=settings.CA_DEFAULT_EXPIRES)


class CreateCertificateForm(forms.ModelForm):
    expires = forms.DateField(initial=_initial_expires)
    subjectAltName = forms.CharField(label='subjectAltName', required=False)
    keyUsage = forms.MultipleChoiceField(label='keyUsage', required=False, choices=(
        ('cRLSign', 'cRLSign'),
        ('dataEncipherment', 'dataEncipherment'),
        ('decipherOnly', 'decipherOnly'),
        ('digitalSignature', 'digitalSignature'),
        ('encipherOnly', 'encipherOnly'),
        ('keyAgreement', 'keyAgreement'),
        ('keyCertSign', 'keyCertSign'),
        ('keyEncipherment', 'keyEncipherment'),
        ('nonRepudiation', 'nonRepudiation'),
    ))
    extendedKeyUsage = forms.MultipleChoiceField(label='extendedKeyUsage', required=False, choices=(
        ('serverAuth', 'SSL/TLS Web Server Authentication'),
        ('clientAuth', 'SSL/TLS Web Client Authentication'),
        ('codeSigning', 'Code signing'),
        ('emailProtection', 'E-mail Protection (S/MIME)'),
        ('timeStamping', 'Trusted Timestamping'),
        ('msCodeInd', 'Microsoft Individual Code Signing (authenticode)'),
        ('msCodeCom', 'Microsoft Commercial Code Signing (authenticode)'),
        ('msCTLSign', 'Microsoft Trust List Signing'),
        ('msEFS', 'Microsoft Encrypted File System'),
    ))
    basicConstraints = BasicConstraintsField(label='basicConstraints')

    class Meta:
        model = Certificate
        fields = ['cn', 'csr', 'watchers', ]


class RevokeCertificateForm(forms.ModelForm):
    reason = forms.ChoiceField(required=False, choices=(
        ('', _('No reason')),
        ('unspecified', _('Unspecified')),
        ('keyCompromise', _('Key compromised')),
        ('CACompromise', _('CA compromised')),
        ('affiliationChanged', _('Affiliation changed')),
        ('superseded', _('Superseded')),
        ('cessationOfOperation', _('Cessation of operation')),
        ('certificateHold', _('On Hold')),
        # Not currently useful according to "man ca":
        #('removeFromCRL', _('Remove from CRL')),
    ))

    class Meta:
        model = Certificate
        fields = []
