from flask import Flask, jsonify
from engine import Game

app = Flask(__name__, static_folder='static', static_url_path='')

game = None

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/start')
def start():
    global game
    game = Game()
    ev = game.next_event()
    return jsonify(ev)

@app.route('/next')
def next_event():
    if not game:
        return jsonify(None)
    ev = game.next_event()
    return jsonify(ev)

if __name__ == '__main__':
    app.run()
