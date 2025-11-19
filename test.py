from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('login.html')  # or register.html — any page you have

if __name__ == '__main__':
    app.run(debug=True)