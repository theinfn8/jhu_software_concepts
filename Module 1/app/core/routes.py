from flask import render_template, send_from_directory
from app.core import bp
import os

@bp.route('/')
@bp.route('/about')
def home():
    #return "Test good"
    return render_template('home.html')

@bp.route('/contact')
def contact():
    return render_template('contact.html')

@bp.route('/projects')
def projects():
    return "Project info here"

#@bp.route('/favicon.ico')
#def favicon():
#    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')