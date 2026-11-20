from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '<div>Hello World</div>'

if __name__ == '__main__':
    app.run(debug=True)