from flask import Flask, jsonify, request
from engine import Game
import uuid

app = Flask(__name__, static_folder='static', static_url_path='')

game = None
current_run_id = None

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/start')
def start():
    global game, current_run_id
    game = Game()
    current_run_id = str(uuid.uuid4())
    ev = game.next_event()
    ev['runId'] = current_run_id
    return jsonify(ev)

@app.route('/next')
def next_event():
    if not game:
        return jsonify(None)
    if request.args.get('runId') != current_run_id:
        return jsonify(None)
    ev = game.next_event()
    if ev:
        ev['runId'] = current_run_id
    return jsonify(ev)

if __name__ == '__main__':
    app.run()
