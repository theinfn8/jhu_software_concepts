from flask import Blueprint

# Setup blueprint config, and make available to root app
bp = Blueprint('core', __name__, template_folder="templates", static_folder="static", static_url_path='/core/static')

# Ensure reference to routes is auto included
from app.core import routes

