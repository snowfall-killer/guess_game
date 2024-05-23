'''
在這個 Flask 程式碼中，需要使用 eventlet.import_patched('socket') 來修補 socket 模組的原因是為了支援非同步操作以及提升伺服器效能。

Flask-SocketIO 是一個擴充 Flask 的函式庫，它透過 WebSocket 協定實現了即時雙向通訊。然而，預設的 Python socket 模組是同步執行的，這意味著每當有連線請求到達時，伺服器都必須等待該請求完成後才能處理下一個請求。這樣的同步模式會大大降低伺服器的效能，尤其是在需要處理大量並發連線的情況下。

eventlet 是一個高效能的並行程式庫，它提供了一種輕量級的協同程式模型，允許單個線程同時執行多個任務。通過修補 socket 模組，eventlet 可以實現非阻塞的非同步 I/O 操作，從而提高伺服器的並發處理能力。

當 Flask-SocketIO 初始化時，它會根據指定的 async_mode 參數來選擇適當的非同步模式。在這個程式碼中，使用了 async_mode='eventlet'，這表示要使用 eventlet 作為非同步模式。為了確保 eventlet 正常運作，我們需要先使用 eventlet.import_patched('socket') 來修補 socket 模組。

總結來說，修補 socket 模組的目的是為了讓 Flask-SocketIO 能夠利用 eventlet 提供的非阻塞 I/O 和協同程式功能，從而提高伺服器的並發處理能力和效能。這對於需要處理大量即時連線的應用程式非常有用。
'''

from flask import Flask, render_template
from flask_socketio import SocketIO, emit  # 導入 SocketIO 相關模組，用於建立即時通訊


app = Flask(__name__)  # 建立 Flask 應用程式
socketio = SocketIO(app, async_mode='eventlet')  # 建立 SocketIO 物件，使用 eventlet 作為非同步模式

# 啟用 Eventlet
import eventlet  # 導入 eventlet 模組
eventlet.import_patched('socket')  # 使用 eventlet 修補 socket 模組

@app.route('/')  # 設定路由，當使用者訪問根目錄時，執行 index 函數
def index():
    return render_template('guess_game.html')  # 渲染 guess_game.html 模板，並回傳給使用者
    
if __name__ == '__main__':  # 如果程式是直接執行的
    socketio.run(app, host='120.113.99.47', port=88, debug=True)  # 執行 Flask 應用程式，監聽 120.113.99.47:88 