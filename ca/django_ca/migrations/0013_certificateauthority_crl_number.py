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

# Generated by Django 2.2 on 2019-04-27 16:26

from django.db import migrations, models

import django_ca.models


class Migration(migrations.Migration):
    dependencies = [
        ("django_ca", "0012_auto_20190405_2345"),
    ]

    operations = [
        migrations.AddField(
            model_name="certificateauthority",
            name="crl_number",
            field=models.TextField(
                blank=True,
                default='{"scope": {}}',
                help_text="Data structure to store the CRL number (see RFC 5280, 5.2.3) depending on the scope.",
                validators=[],
                verbose_name="CRL Number",
            ),
        ),
    ]
