"""
Entry point for the Flask web application.

This module serves as the top-level entry point for running the Grad School
Cafe Data Analysis web application. It imports the application factory
function :func:`app.app.create_app`, constructs the Flask application
instance, and starts the development server when executed directly.

.. note::
    This module is intended to be run directly (``python main.py``) for
    development purposes only. For production deployments, use a WSGI
    server such as Gunicorn or uWSGI instead.

.. usage::
    To start the development server::

        $ python main.py

:module: main
:synopsis: Flask application entry point.
"""
from app import app

if __name__=='__main__':
    flask_app = app.create_app()
    flask_app.run(host='0.0.0.0', port=8080)
