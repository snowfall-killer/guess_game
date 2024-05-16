from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

players = {}

@app.route('/')
def index():
    return render_template('tetris_game.html')

@socketio.on('join')
def on_join(data):
    name = data['name']
    player_id = len(players) + 1
    players[player_id] = {'name': name, 'score': 0}
    join_room(player_id)
    emit('player_joined', {'id': player_id}, room=player_id)
    if len(players) == 2:
        start_game()

def start_game():
    game_state = {'state1': {}, 'state2': {}}  # Initialize the game state for both players
    for player_id in players:
        emit('game_start', {}, room=player_id)
        emit('game_update', game_state, broadcast=True)

@socketio.on('move')
def handle_move(data):
    player_id = data['id']
    move = data['move']
    # Update the game state based on the move
    if player_id == 1:
        # Update state for player 1
        pass
    elif player_id == 2:
        # Update state for player 2
        pass
    game_update = {'state1': {}, 'state2': {}}  # Replace with actual game states
    emit('game_update', game_update, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
