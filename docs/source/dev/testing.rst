#######
Testing
#######

**django-ca** uses `pytest <https://docs.pytest.org/>`_ for running the test suite:

.. code-block:: console

   $ pytest -v

This will generate a code coverage report in ``docs/build/html/``.

*************
Test coverage
*************

The test suite must ensure 100% test coverage. Completely excluding code from test coverage is only allowed
when absolutely necessary.

Conditional pragmas
===================

In addition to the standard ``# pragma: no cover`` and ``# pragma: no branch``, the test suite adds pragmas to
exclude code based on the Python version or library versions. For example::

   if sys.version_info >= (3, 8):  # pragma: only py>=3.8
      from typing import Literal
   else:  # pragma: only py<3.8
      from typing_extensions import Literal

If you have branches that are only relevant for some versions, there's also pragmas for that::

   if sys.version_info >= (3, 8):  # pragma: py>=3.8 branch
      print("Do something that's only useful in Python 3.8 or newer.")
   if django.VERSION[:2] >= (3, 2):  # pragma: django>=3.2 branch
      print("Do something that's only useful in Django 3.2 or newer.")

You can use all operators (``<``, ``<=``, ``==``, ``!=``, ``>``, ``>=``), and we add pragma for the versions
of Python, Django, cryptography.

Please check :file:`ca/django_ca/tests/base/pragmas.py` for a tested file that includes all supported pragmas.
Correctly using the pragmas is mandatory, as they are also used for finding outdated code when older versions
are deprecated.