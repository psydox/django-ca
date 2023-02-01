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
# see <http://www.gnu.org/licenses/>

"""Test the view_ca management command."""

import typing

from django.test import TestCase

from django_ca.tests.base import override_settings, override_tmpcadir
from django_ca.tests.base.mixins import TestCaseMixin

expected = {
    "ecc": """{name} (enabled):
* Serial: {serial_colons}
* Path to private key:
  {key_path}
* Is a root CA.
* Has no children.
* Distinguished Name: {subject_str}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): {crl_url}
* Issuer URL: {issuer_url}
* OCSP URL: {ocsp_url}
* Issuer Alternative Name: None

{pub[pem]}""",
    "ed25519": """{name} (enabled):
* Serial: {serial_colons}
* Path to private key:
  {key_path}
* Is a root CA.
* Has no children.
* Distinguished Name: {subject_str}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): {crl_url}
* Issuer URL: {issuer_url}
* OCSP URL: {ocsp_url}
* Issuer Alternative Name: None

{pub[pem]}""",
    "ed448": """{name} (enabled):
* Serial: {serial_colons}
* Path to private key:
  {key_path}
* Is a root CA.
* Has no children.
* Distinguished Name: {subject_str}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): {crl_url}
* Issuer URL: {issuer_url}
* OCSP URL: {ocsp_url}
* Issuer Alternative Name: None

{pub[pem]}""",
    "child": """{name} (enabled):
* Serial: {serial_colons}
* Path to private key:
  {key_path}
* Parent: {parent_name} ({parent_serial})
* Has no children.
* Distinguished Name: {subject_str}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): {crl_url}
* Issuer URL: {issuer_url}
* OCSP URL: {ocsp_url}
* Issuer Alternative Name: None

{pub[pem]}""",
    "root": """{name} (enabled):
* Serial: {serial_colons}
* Path to private key:
  {key_path}
* Is a root CA.
* Children:
  * {children[0][0]} ({children[0][1]})
* Distinguished Name: {subject_str}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): {crl_url}
* Issuer URL: {issuer_url}
* OCSP URL: {ocsp_url}
* Issuer Alternative Name: None

{pub[pem]}""",
    "root-properties": """{name} (enabled):
* Serial: {serial_colons}
* Path to private key:
  {key_path}
* Is a root CA.
* Children:
  * {children[0][0]} ({children[0][1]})
* Distinguished Name: {subject_str}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}
* Website: {ca.website}
* Terms of service: {ca.terms_of_service}
* CAA identity: {ca.caa_identity}

ACMEv2 support:
* Enabled: {ca.acme_enabled}
* Requires contact: {ca.acme_requires_contact}

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): {crl_url}
* Issuer URL: {issuer_url}
* OCSP URL: {ocsp_url}
* Issuer Alternative Name: None

{pub[pem]}""",
    "root-acme-disabled": """{name} (enabled):
* Serial: {serial_colons}
* Path to private key:
  {key_path}
* Is a root CA.
* Children:
  * {children[0][0]} ({children[0][1]})
* Distinguished Name: {subject_str}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): {crl_url}
* Issuer URL: {issuer_url}
* OCSP URL: {ocsp_url}
* Issuer Alternative Name: None

{pub[pem]}""",
    "globalsign": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "digicert_ev_root": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "comodo": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "identrust_root_1": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "globalsign_r2_root": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "comodo_dv": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Extended Key Usage{extended_key_usage_critical}:
{extended_key_usage_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "rapidssl_g3": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "geotrust": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "comodo_ev": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "digicert_ha_intermediate": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Extended Key Usage{extended_key_usage_critical}:
{extended_key_usage_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "dst_root_x3": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "globalsign_dv": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "godaddy_g2_intermediate": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "godaddy_g2_root": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "google_g3": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Extended Key Usage{extended_key_usage_critical}:
{extended_key_usage_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "letsencrypt_x1": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Name Constraints{name_constraints_critical}:
{name_constraints_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "letsencrypt_x3": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "startssl_root": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}
Unknown extension (2.16.840.1.113730.1.1):
    03:02:00:07
Unknown extension (2.16.840.1.113730.1.13):
    16:29:53:74:61:72:74:43:6F:6D:20:46:72:65:65:20:53:53:4C:20:43:65:72:74:69:66:69:63:61:74:69:6F:6E:20:41:75:74:68:6F:72:69:74:79

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "startssl_class2": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "startssl_class3": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Extended Key Usage{extended_key_usage_critical}:
{extended_key_usage_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "trustid_server_a52": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Extended Key Usage{extended_key_usage_critical}:
{extended_key_usage_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "digicert_global_root": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
    "digicert_sha2": """{name} (enabled):
* Serial: {serial_colons}
* Private key not available locally.
* Is a root CA.
* Has no children.
* Distinguished Name: {subject}
* Maximum levels of sub-CAs (pathlen): {pathlen_text}
* HPKP pin: {hpkp}

ACMEv2 support:
* Enabled: False

X509 v3 certificate extensions for CA:
Authority Information Access{authority_information_access_critical}:
{authority_information_access_text}
Authority Key Identifier{authority_key_identifier_critical}:
{authority_key_identifier_text}
Basic Constraints{basic_constraints_critical}:
{basic_constraints_text}
CRL Distribution Points{crl_distribution_points_critical}:
{crl_distribution_points_text}
Certificate Policies{certificate_policies_critical}:
{certificate_policies_text}
Key Usage{key_usage_critical}:
{key_usage_text}
Subject Key Identifier{subject_key_identifier_critical}:
{subject_key_identifier_text}

X509 v3 certificate extensions for signed certificates:
* Certificate Revokation List (CRL): None
* Issuer URL: None
* OCSP URL: None
* Issuer Alternative Name: None

{pub[pem]}""",
}

# Root CAs with no children can always use the same template (since they all use the same extensions)
expected["dsa"] = expected["ecc"]
expected["pwd"] = expected["ecc"]


class ViewCATestCase(TestCaseMixin, TestCase):
    """Main test class for this command."""

    load_cas = "__all__"

    @override_tmpcadir()
    def test_all_cas(self) -> None:
        """Test viewing all CAs."""
        for name, ca in sorted(self.cas.items(), key=lambda t: t[0]):
            stdout, stderr = self.cmd("view_ca", ca.serial)
            data = self.get_cert_context(name)
            self.assertMultiLineEqual(stdout, expected[name].format(**data), name)
            self.assertEqual(stderr, "")

    @override_tmpcadir()
    def test_properties(self) -> None:
        """Test viewing of various optional properties."""
        ca = self.cas["root"]
        hostname = "ca.example.com"
        ca.website = f"https://website.{hostname}"
        ca.terms_of_service = f"{ca.website}/tos/"
        ca.caa_identity = hostname
        ca.acme_enabled = True
        ca.acme_requires_contact = False
        ca.save()

        stdout, stderr = self.cmd("view_ca", ca.serial)
        self.assertEqual(stderr, "")
        data = self.get_cert_context("root")
        self.assertMultiLineEqual(stdout, expected["root-properties"].format(ca=ca, **data))

    @override_tmpcadir(CA_ENABLE_ACME=False)
    def test_acme_disabled(self) -> None:
        """Test viewing when ACME is disabled."""
        stdout, stderr = self.cmd("view_ca", self.cas["root"].serial)
        self.assertEqual(stderr, "")
        data = self.get_cert_context("root")
        self.assertMultiLineEqual(stdout, expected["root-acme-disabled"].format(**data))

    @override_tmpcadir()
    def test_no_no_private_key(self) -> None:
        """Test viewing when we have no private key."""

        def side_effect(cls: typing.Any) -> None:
            raise NotImplementedError

        ca_storage = "django_ca.management.commands.view_ca.ca_storage.%s"
        with self.patch(ca_storage % "path", side_effect=side_effect) as path_mock, self.patch(
            ca_storage % "exists", return_value=True
        ) as exists_mock:
            stdout, stderr = self.cmd("view_ca", self.cas["root"].serial)

        path_mock.assert_called_once_with(self.cas["root"].private_key_path)
        exists_mock.assert_called_once_with(self.cas["root"].private_key_path)
        data = self.get_cert_context("root")
        data["key_path"] = self.cas["root"].private_key_path
        self.assertMultiLineEqual(stdout, expected["root"].format(**data))
        self.assertEqual(stderr, "")


@override_settings(USE_TZ=True)
class ViewCAWithTZTestCase(ViewCATestCase):
    """Main tests but with TZ support."""