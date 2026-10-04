from flask import Flask, render_template
from src.routes import bp

def create_app(test_config=None) -> Flask:
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
