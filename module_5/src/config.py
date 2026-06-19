"""
Environment configuration loader.

This module loads key/value configuration pairs from a local ``.env``
file at import time, using :func:`dotenv.dotenv_values`, and exposes
the result as a module-level dictionary for use elsewhere in the
application.

Unlike :func:`dotenv.load_dotenv`, this approach does **not** mutate
:data:`os.environ`; values are only available via the :data:`config`
dictionary exported by this module.

**Module contents:**

+---------------------------+------------------------------------------+
| Name                      | Description                               |
+===========================+============================================+
| ``FILE_LOCATION``         | Path to the ``.env`` file to load          |
+---------------------------+------------------------------------------+
| ``config``                | Parsed key/value pairs from the ``.env``  |
|                            | file, as an ordered mapping               |
+---------------------------+------------------------------------------+

**Dependencies:**

* :mod:`dotenv` (``python-dotenv``) -- third-party, supplies
  :func:`dotenv.dotenv_values` for parsing ``.env`` files without
  touching process environment variables.

**Module-level constants:**

``FILE_LOCATION``
    ``"./src/.env"`` -- relative path to the ``.env`` file to be
    parsed. Resolved relative to the current working directory at
    import time, *not* relative to this module's own file location;
    callers running the application from a different working
    directory may fail to locate the file.

``config``
    The :class:`dict`-like object (an :class:`~collections.OrderedDict`
    on older ``python-dotenv`` versions, plain :class:`dict` on newer
    ones) returned by :func:`dotenv.dotenv_values`, mapping each
    variable name found in the ``.env`` file to its string value. If
    the file at ``FILE_LOCATION`` does not exist, :func:`dotenv_values`
    returns an empty mapping rather than raising an exception.

.. warning::
    ``config`` is computed once, at import time. Subsequent edits to
    the ``.env`` file on disk will not be reflected without reloading
    or re-importing this module.

.. warning::
    All values in ``config`` are strings (or ``None`` for keys present
    without an assigned value). Callers requiring other types (e.g.
    :class:`int`, :class:`bool`) must perform their own conversion;
    no validation or type coercion is performed by this module.

.. note::
    If ``FILE_LOCATION`` does not exist or is unreadable,
    :func:`dotenv.dotenv_values` silently returns an empty
    :class:`dict` rather than raising :exc:`FileNotFoundError`.
    Callers depending on specific configuration keys being present
    should validate ``config`` explicitly rather than assuming load
    success.

**Typical usage:**

.. code-block:: python

    from src import settings  # this module

    api_key = settings.config.get("API_KEY")
    if api_key is None:
        raise RuntimeError("API_KEY missing from .env configuration")

.. seealso::
    `python-dotenv documentation
    <https://saurabh-kumar.com/python-dotenv/>`_ for details on
    ``.env`` file syntax and the differences between
    :func:`dotenv.dotenv_values` and :func:`dotenv.load_dotenv`.
"""
import os

def get_config():
    config = {
        "host" : os.environ.get("DB_HOST"),
        "port" : os.environ.get("DB_PORT"),
        "dbname" : os.environ.get("DB_NAME"),
        "user" : os.environ.get("DB_USER"),
        "password" : os.environ.get("DB_PASSWORD")
    }
    return config