# use pip install -U to ensure the compatible versions for these three modules
# pip install -U flask flask-socketio eventlet
import random  # 導入 random 模組，用於生成隨機數
from flask import Flask, render_template, request, send_from_directory  # 導入 Flask 相關模組，用於建立網頁應用程式
from flask_socketio import SocketIO, emit  # 導入 SocketIO 相關模組，用於建立即時通訊
import os  # 導入 os 模組，用於處理檔案和目錄
from contextlib import contextmanager  # 導入 contextmanager，用於建立上下文管理器
import time  # 導入 time 模組，用於處理時間

app = Flask(__name__)  # 建立 Flask 應用程式
socketio = SocketIO(app, async_mode='eventlet')  # 建立 SocketIO 物件，使用 eventlet 作為非同步模式

# 為了配合電腦隨機猜測, 將最高猜測次數調為 20
MAX_GUESSES = 20  # 設定每個玩家最多可以猜測的次數

# 啟用 Eventlet
import eventlet  # 導入 eventlet 模組
eventlet.import_patched('socket')  # 使用 eventlet 修補 socket 模組

game_data = {  # 建立 game_data 字典，用於儲存遊戲資料
    'players': {},  # 儲存所有玩家的資料，以玩家 ID 為鍵，玩家資料為值
    'guesses': [],  # 儲存所有玩家的猜測，以時間順序排列
    'correct_answer': random.randint(1, 100)  # 儲存正確答案，是一個 1 到 100 之間的隨機整數
}

last_guess_time = None  # 記錄上次傳送猜測提示的時間，初始值為 None

# 電腦玩家的猜測範圍，初始值為 1 到 100
min_value = 1
max_value = 100

@contextmanager  # 使用 contextmanager 裝飾器，將 app_context 函數變成一個上下文管理器
def app_context():
    with app.app_context():  # 進入 Flask 應用程式的上下文
        yield  # 產生上下文，讓其他程式碼可以使用 Flask 應用程式的資源

@app.route('/')  # 設定路由，當使用者訪問根目錄時，執行 index 函數
def index():
    return render_template('guess_game.html')  # 渲染 guess_game.html 模板，並回傳給使用者

@app.route('/static/<path:filename>')  # 設定路由，當使用者訪問 /static/<filename> 時，執行 serve_static 函數
def serve_static(filename):
    root_dir = os.path.dirname(os.getcwd())  # 取得專案根目錄
    return send_from_directory(os.path.join(root_dir, 'static'), filename)  # 從 static 目錄中回傳指定檔案給使用者

@socketio.on('join')  # 使用 socketio.on 裝飾器，當收到 'join' 事件時，執行 on_join 函數
def on_join(data):
    player_name = data['name']  # 取得玩家名稱
    player_id = request.sid  # 取得玩家 ID

    # 檢查用户名是否已存在
    if any(player['name'] == player_name for player in game_data['players'].values()):  # 如果 game_data['players'] 中已经有相同用户名的玩家
        emit('error', {'message': f'用户名 "{player_name}" 已被使用!'})  # 發送 'error' 事件給客戶端，提示用户名已被使用
        return  # 結束函數執行

    game_data['players'][player_id] = {'name': player_name, 'score': 0, 'guesses': 0}  # 將玩家數據添加到 game_data['players'] 中
    emit('player_joined', {'players': game_data['players'], 'guesses': game_data['guesses']}, broadcast=True)  # 發送 'player_joined' 事件給所有客戶端，更新玩家列表和猜測列表
    print(f"Player joined: {player_name}")  # 在伺服器端打印玩家加入訊息

    # 只在遊戲開始時 (也就是第一個玩家加入時) 加入電腦玩家
    if len(game_data['players']) == 1:  # 如果當前只有一個玩家
        computer_join()  # 加入電腦玩家
        computer_guess() # 讓電腦玩家立即猜測一次

@socketio.on('guess')  # 使用 socketio.on 裝飾器，當收到 'guess' 事件時，執行 on_guess 函數
def on_guess(data):
    global last_guess_time  # 聲明 last_guess_time 為全域變數
    player_id = request.sid  # 取得玩家 ID
    guess = data['guess']  # 取得玩家猜測的數字
    player = game_data['players'][player_id]  # 取得玩家資料

    if player['guesses'] >= MAX_GUESSES:  # 如果玩家已經猜測了 MAX_GUESSES 次
        emit('game_lost', {'player_id': player_id})  # 發送 'game_lost' 事件給客戶端，提示玩家遊戲結束
        return  # 結束函數執行

    player['guesses'] += 1  # 增加玩家的猜測次數
    hint = generate_hint(guess)  # 根據玩家的猜測生成提示

    current_time = time.time()  # 取得當前時間
    if last_guess_time is None or current_time - last_guess_time > 1:  # 如果是第一次猜測，或者距離上次猜測超過 1 秒
        new_guess = {'player': player['name'], 'guess': guess, 'hint': hint}  # 建立新的猜測資料
        game_data['guesses'].insert(0, new_guess)  # 將新的猜測資料添加到 game_data['guesses'] 的開頭
        emit('new_guess', new_guess, broadcast=True)  # 發送 'new_guess' 事件給所有客戶端，更新猜測列表
        last_guess_time = current_time  # 更新 last_guess_time
    else:  # 如果距離上次猜測不到 1 秒
        delay = 1 - (current_time - last_guess_time)  # 計算延遲時間
        socketio.start_background_task(target=lambda: socketio.sleep(delay) and on_guess(data))  # 延遲 delay 秒後再次呼叫 on_guess 函數

    print(f"Guess received: {player['name']} guessed {guess}, hint: {hint}")  # 在伺服器端打印玩家猜測訊息

    if guess == game_data['correct_answer']:  # 如果玩家猜中
        player['score'] += 1  # 增加玩家得分
        emit('correct_answer', {'player_name': player['name'], 'correct_answer': guess}, broadcast=True)  # 發送 'correct_answer' 事件給所有客戶端，宣布獲勝者
        start_new_round()  # 開始新一輪遊戲
        return  # 結束函數執行

    emit('game_update', {'players': game_data['players'], 'guesses': game_data['guesses']}, broadcast=True)  # 發送 'game_update' 事件給所有客戶端，更新玩家列表和猜測列表
    
    # 在使用者猜測後，讓電腦玩家也猜測一次
    if player_id != 'computer': # 檢查是否為電腦玩家自己猜的
        computer_guess() # 呼叫電腦玩家猜測邏輯

def generate_hint(guess):  # 根據玩家的猜測生成提示
    if guess < game_data['correct_answer']:  # 如果猜測的數字小於正確答案
        return 'Too low'  # 返回 'Too low' 提示
    elif guess > game_data['correct_answer']:  # 如果猜測的數字大於正確答案
        return 'Too high'  # 返回 'Too high' 提示
    return 'Correct!'  # 如果猜測的數字等於正確答案，返回 'Correct!' 提示

      
def start_new_round():  # 開始新一輪遊戲
    global min_value, max_value  # 聲明 min_value, max_value 為全域變數
    game_data['guesses'] = []  # 清空猜測列表
    game_data['correct_answer'] = random.randint(1, 100)  # 生成新的正確答案

    # 重置所有玩家的猜測次數，**不包含**電腦玩家
    for player_id in game_data['players']:  # 遍歷所有玩家
        if player_id != 'computer':
            game_data['players'][player_id]['guesses'] = 0  # 將玩家的猜測次數重置為 0

    # 電腦玩家猜測次數從 1 起跳
    computer_id = 'computer'  # 電腦玩家的 ID
    game_data['players'][computer_id]['guesses'] = 1  # 將電腦玩家數據添加到 game_data['players'] 中

    # 重置電腦玩家的猜測範圍
    min_value = 1
    max_value = 100

    emit('new_round_update', {'players': game_data['players'], 'guesses': game_data['guesses']}, broadcast=True)  # 發送 'new_round_update' 事件給所有客戶端，更新玩家列表和猜測列表

    print("New round started")  # 在伺服器端打印新一輪遊戲開始訊息
    

def computer_guess():  # 電腦玩家猜測邏輯
    global min_value, max_value  # 聲明 min_value, max_value 為全域變數
    computer_id = 'computer'  # 電腦玩家的 ID
    computer_player = game_data['players'][computer_id]  # 取得電腦玩家資料

    if computer_player['guesses'] < MAX_GUESSES:  # 如果電腦玩家的猜測次數小於 MAX_GUESSES

        # 根據所有玩家的猜測結果調整猜測範圍
        for guess_data in game_data['guesses']:  # 遍歷所有猜測記錄
            guess = guess_data['guess']  # 取得猜測的數字
            hint = guess_data['hint']  # 取得提示
            if hint == 'Too low':  # 如果提示是 'Too low'
                min_value = max(min_value, guess + 1)  # 更新最小值
            elif hint == 'Too high':  # 如果提示是 'Too high'
                max_value = min(max_value, guess - 1)  # 更新最大值

        guess = random.randint(min_value, max_value)  # 在最小值和最大值之間生成一個隨機數字作為猜測
        hint = generate_hint(guess)  # 生成提示
        computer_guess_data = {'player': 'computer', 'guess': guess, 'hint': hint}  # 建立電腦玩家的猜測資料

        # 將電腦玩家的猜測添加到 game_data['guesses'] 列表
        game_data['guesses'].insert(0, computer_guess_data)  # 將電腦玩家的猜測添加到 game_data['guesses'] 的開頭

        # 使用 socketio.emit() 將猜測結果發送給所有玩家
        emit('new_guess', computer_guess_data, broadcast=True)  # 發送 'new_guess' 事件給所有客戶端，更新猜測列表
        computer_player['guesses'] += 1  # 增加電腦玩家的猜測次數

        # 如果電腦猜中，開始新一輪遊戲
        if guess == game_data['correct_answer']:
            computer_player['score'] += 1
            emit('correct_answer', {'player_name': computer_player['name'], 'correct_answer': guess}, broadcast=True)  # 發送 'correct_answer' 事件給所有客戶端，宣布獲勝者
            start_new_round() 

def computer_join():  # 加入電腦玩家
    computer_id = 'computer'  # 電腦玩家的 ID
    # computer 加入後隨即猜第一次, 因此 guesses 從 1 起跳
    # **修改**: 只在電腦玩家還不存在於 game_data['players'] 時才加入
    if computer_id not in game_data['players']:
        game_data['players'][computer_id] = {'name': 'computer', 'score': 0, 'guesses': 1}  # 將電腦玩家數據添加到 game_data['players'] 中
        emit('player_joined', {'players': game_data['players'], 'guesses': game_data['guesses']}, broadcast=True)  # 發送 'player_joined' 事件給所有客戶端，更新玩家列表和猜測列表
        print(f"Player joined: computer")  # 在伺服器端打印電腦玩家加入訊息

if __name__ == '__main__':  # 如果程式是直接執行的
    socketio.run(app, host='120.113.99.47', port=88, debug=True)  # 執行 Flask 應用程式，監聽 140.130.17.229:88 位址，開啟除錯模式