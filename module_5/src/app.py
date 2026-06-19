"""
Flask application factory.

This module implements the application factory pattern for the Flask
app: it constructs a configured :class:`flask.Flask` instance,
registers the application's main blueprint, and loads configuration
from ``config.py``. The factory is intended to be the single entry
point used by WSGI servers, the Flask CLI (``flask run``), and test
suites to obtain an app instance.

**Module contents:**

+---------------------------+------------------------------------------+
| Name                      | Description                               |
+===========================+============================================+
| :func:`create_app`        | Build and configure the Flask application |
+---------------------------+------------------------------------------+

**Dependencies:**

* :mod:`flask` -- third-party, supplies the :class:`~flask.Flask`
  application class.
* :mod:`src.routes` -- local package, supplies ``bp``, the
  :class:`~flask.Blueprint` registered on the created app.

**Module-level imports:**

``bp``
    The application's primary :class:`flask.Blueprint`, imported from
    :mod:`src.routes` and registered on every app instance produced by
    :func:`create_app`. All routes defined on ``bp`` become part of the
    returned application.

.. warning::
    :func:`create_app` only assigns ``app`` inside the
    ``if test_config is None:`` branch. When ``test_config`` is *not*
    ``None``, ``app`` is never created, and the subsequent
    ``app.register_blueprint(bp)`` call will raise
    :exc:`UnboundLocalError`. As written, the ``test_config`` parameter
    has no effect on app creation and the override path is non-
    functional; passing any value other than ``None`` will currently
    cause the factory to fail. Fixing this requires constructing
    ``app`` unconditionally and applying ``test_config`` (e.g. via
    ``app.config.from_mapping(test_config)``) when provided.

.. warning::
    ``app.config.from_pyfile('config.py', silent=True)`` resolves
    ``config.py`` relative to the application's root path (typically
    the directory containing this module), not the current working
    directory. With ``silent=True``, a missing or unreadable
    ``config.py`` is silently ignored, so the app may run with empty
    configuration without any visible error.

**Typical usage:**

.. code-block:: python

    from src.app import create_app

    app = create_app()
    app.run()

.. code-block:: python

    # WSGI entry point, e.g. for gunicorn: `gunicorn "src.app:create_app()"`
    from src.app import create_app

    application = create_app()

.. seealso::
    :mod:`src.routes` for the blueprint and view functions registered
    on the application.

    `Flask Application Factories
    <https://flask.palletsprojects.com/en/latest/patterns/appfactories/>`_
    for background on this pattern.
"""

from flask import Flask
from src.routes import bp

def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Initializes a Flask app instance with static and template folders,
    registers the main blueprint, and loads configuration from ``config.py``.

    :param test_config: Optional configuration mapping to override the default
                        configuration. If ``None``, the app loads from
                        ``config.py``. Defaults to ``None``.
    :type test_config: dict or None
    :returns: A configured Flask application instance.
    :rtype: Flask
    """

    app = Flask(__name__, static_folder="static", template_folder="templates")

    app.register_blueprint(bp)

    app.config.from_pyfile('config.py', silent=True)

    return app
