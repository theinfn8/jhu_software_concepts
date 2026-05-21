from flask import Flask, render_template

# Construct app
app = Flask(__name__)

# Bind route for root
@app.route("/")
def home():
    return render_template('home.html')

if __name__=='__run__':
    app.run(host='0.0.0.0', port=8080)