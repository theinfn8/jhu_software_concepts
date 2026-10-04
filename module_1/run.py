from flask import Flask, render_template
from app.core import bp as core_bp

# Construct app
app = Flask(__name__,static_folder='static')

# Register single blueprint
app.register_blueprint(core_bp)

# Run program
if __name__=='__main__':
    app.run(host='0.0.0.0', port=8080)