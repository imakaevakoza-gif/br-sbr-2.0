import os
import requests
import queue
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Разрешаем запросы с вашего Telegram Web App на GitHub Pages
CORS(app)

# Создаем внутреннюю безопасную очередь для логов в оперативной памяти сервера
log_queue = queue.Queue()

def discord_worker():
    """Фоновый поток, который берет логи из очереди и шлет в Discord без флуда"""
    while True:
        try:
            # Ждем появления нового лога в очереди
            data = log_queue.get()
            webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
            
            if webhook_url:
                response = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"}, timeout=10)
                
                # Если Дискорд выдал лимит 429
                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", 5)
                    print(f"[ЛИМИТ ДОСТИГНУТ] Discord перегружен. Ждем {retry_after} сек...")
                    time.sleep(retry_after)
                    log_queue.put(data) # Возвращаем лог обратно в очередь, чтобы не потерять
                else:
                    # ВАЖНО: Делаем обязательную паузу в 1.5 секунды между отправками.
                    # Это полностью защищает сервер от бана 429 со стороны Discord!
                    time.sleep(1.5)
            
            log_queue.task_done()
        except Exception as e:
            print(f"[ОШИБКА ФОНОВОГО ПОТОКА]: {e}")
            time.sleep(2)

# Запускаем фоновую отправку при старте сервера
threading.Thread(target=discord_worker, daemon=True).start()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "working", "message": "Python queue-backend is running cleanly!"}), 200

@app.route('/api/log', methods=['POST'])
def proxy_log():
    try:
        data = request.get_json()
        
        # Просто кидаем лог в очередь и МГНОВЕННО отвечаем телефону "success: true"
        # Телефон пользователя не зависает в Web App и не ждет ответа от Discord
        log_queue.put(data)
        return jsonify({"success": True, "message": "Data put into queue successfully"}), 200
        
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА БЭКЕНДА]: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
