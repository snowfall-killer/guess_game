# use pip install -U to ensure the compatible versions for these three modules
# pip install -U flask flask-socketio eventlet
import random
from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
from contextlib import contextmanager

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

MAX_GUESSES = 10

# 啟用 Eventlet
import eventlet
eventlet.import_patched('socket')

game_data = {
    'players': {},
    'guesses': [],
    'correct_answer': random.randint(1, 100)
}

@contextmanager
def app_context():
    with app.app_context():
        yield

@app.route('/')
def index():
    return render_template('guess_game.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    root_dir = os.path.dirname(os.getcwd())
    return send_from_directory(os.path.join(root_dir, 'static'), filename)

@socketio.on('join')
def on_join(data):
    player_name = data['name']
    player_id = request.sid
    game_data['players'][player_id] = {'name': player_name, 'score': 0, 'guesses': 0}
    emit('player_joined', {'players': game_data['players'], 'guesses': game_data['guesses']}, broadcast=True)
    print(f"Player joined: {player_name}")

@socketio.on('guess')
def on_guess(data):
    player_id = request.sid
    guess = data['guess']
    player = game_data['players'][player_id]
    # 加入限制至多只能猜 10 次
    if player['guesses'] >= MAX_GUESSES:
        emit('game_lost', {'player_id': player_id})
        return

    player['guesses'] += 1
    hint = generate_hint(guess)

    new_guess = {'player': player['name'], 'guess': guess, 'hint': hint}
    game_data['guesses'].insert(0, new_guess)

    emit('new_guess', new_guess, broadcast=True)
    print(f"Guess received: {player['name']} guessed {guess}, hint: {hint}")

    if guess == game_data['correct_answer']:
        player['score'] += 1
        emit('correct_answer', {'player_name': player['name'], 'correct_answer': guess}, broadcast=True)
        start_new_round()
    else:
        emit('game_update', {'players': game_data['players'], 'guesses': game_data['guesses']}, broadcast=True)

def generate_hint(guess):
    if guess < game_data['correct_answer']:
        return 'Too low'
    elif guess > game_data['correct_answer']:
        return 'Too high'
    return 'Correct!'

def start_new_round():
    game_data['guesses'] = []
    game_data['correct_answer'] = random.randint(1, 100)
    emit('new_round_update', {'players': game_data['players'], 'guesses': game_data['guesses']}, broadcast=True)
    for player in game_data['players'].values():
        player['guesses'] = 0

    print("New round started")

if __name__ == '__main__':
    socketio.run(app, host='::1', port=5000, debug=True)