###########
2.1.0 (TBR)
###########

****************************
Certificate Revocation Lists
****************************

* Certificate Revocation Lists (CRLs) are now stored in the database via the
  :class:`~django_ca.models.CertificateRevocationList` model. This makes CRL functionality more robust, as
  clearing the cache will no longer cause an error.

**********************
Command-line utilities
**********************

* Add the ``--only-some-reasons`` parameter to :command:`manage.py dump_crl`.
* The ``--scope`` parameter to :command:`manage.py dump_crl` is deprecated and will be removed in django-ca
  2.3.0. Use ``--only-contains-ca-certs``, ``--only-contains-user-certs`` or
  ``--only-contains-attribute-certs`` instead.
* **BACKWARDS INCOMPATIBLE:** The ``--algorithm`` parameter no longer has any effect and will be removed in
  django-ca 2.3.0.

********
Settings
********

* The `encodings` parameter to :ref:`settings-ca-crl-profiles` was removed. Both encodings are now always
  available.
* The `scope` parameter to :ref:`settings-ca-crl-profiles` is now deprecated in favor of the
  `only_contains_ca_certs`, `only_contains_user_certs` and `only_some_reasons` parameters. The old parameter
  currently still takes precedence, but will be removed in django-ca 2.3.0.

************
Dependencies
************

* **BACKWARDS INCOMPATIBLE:** Dropped support for ``pydantic~=2.7.0``, ``pydantic~=2.8.0``,
  ``cryptography~=42.0`` and ``acme~=2.10.0``.

**********
Python API
**********

* Functions that create a certificate now take a ``not_after`` parameter, replacing ``expires``. The
  ``expires`` parameter  is deprecated and will be removed in django-ca 2.3.0. The following functions are
  affected:

  * :func:`django_ca.models.CertificateAuthority.sign`
  * :func:`django_ca.models.CertificateAuthority.generate_ocsp_key`
  * :func:`django_ca.managers.CertificateAuthorityManager.init`
  * :func:`django_ca.managers.CertificateManager.create_cert`
  * :func:`django_ca.profiles.Profile.create_cert`

* :func:`~django_ca.utils.get_crl_cache_key` added the `only_contains_ca_certs`, `only_contains_user_certs`,
  `only_contains_attribute_certs` and `only_some_reasons` arguments.
* **BACKWARDS INCOMPATIBLE:** The `scope` argument for :func:`~django_ca.utils.get_crl_cache_key` was removed.
  Use the parameters described above instead.

***************
Database models
***************

* Rename the ``valid_from`` to ``not_before`` and ``expires`` to ``not_after`` to align with the terminology
  used in `RFC 5280`_. The previous read-only property was removed.
* Add the :class:`~django_ca.models.CertificateRevocationList` model to store generated CRLs.
* :func:`django_ca.models.CertificateAuthority.get_crl_certs` and
  :func:`django_ca.models.CertificateAuthority.get_crl` are deprecated and will be removed in django-ca 2.3.0.
* **BACKWARDS INCOMPATIBLE:** The `algorithm`, `counter`, `full_name`, `relative_name` and
  `include_issuing_distribution_point` parameters for :func:`django_ca.models.CertificateAuthority.get_crl`
  no longer have any effect.

*****
Views
*****

* The :class:`~django_ca.views.CertificateRevocationListView` has numerous updates:

  * The `expires` parameter now has a default of ``86400`` (from ``600``) to align with defaults elsewhere.
  * The `scope` parameter is deprecated and will be removed in django-ca 2.3.0. Use `only_contains_ca_certs`
    and `only_contains_user_certs` instead.
  * The `include_issuing_distribution_point` no longer has any effect and will be removed in django-ca 2.3.0.
