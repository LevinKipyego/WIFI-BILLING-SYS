from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def main():
    return '<p> Hello world , this is kenya</>'

    if __name__ == '__main__':
        app.run(debug=True)