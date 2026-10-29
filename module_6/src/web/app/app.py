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
* :mod:`werkzeug` -- third-party (installed with Flask), supplies
  :class:`~werkzeug.middleware.proxy_fix.ProxyFix`.
* :mod:`src.routes` -- local package, supplies ``bp``, the
  :class:`~flask.Blueprint` registered on the created app.

**Module-level imports:**

``bp``
    The application's primary :class:`flask.Blueprint`, imported from
    :mod:`src.routes` and registered on every app instance produced by
    :func:`create_app`. All routes defined on ``bp`` become part of the
    returned application.

"""

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from .routes import bp

def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Initializes a Flask app instance with static and template folders,
    registers the main blueprint, and loads configuration from ``config.py``.
    The WSGI app is wrapped in :class:`~werkzeug.middleware.proxy_fix.ProxyFix`
    so the app can be served under a reverse proxy path such as
    ``/deployanywhere``.

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

    # Trust one reverse proxy's X-Forwarded-* headers so url_for honours the
    # proxy's path prefix and scheme; without the headers nothing changes
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    return app
