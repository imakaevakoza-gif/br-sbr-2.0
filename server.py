import os
import requests
import queue
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Разрешаем вашему Web App на GitHub Pages отправлять запросы
CORS(app)

# Создаем внутреннюю безопасную очередь для логов в оперативной памяти
log_queue = queue.Queue()

def discord_worker():
    """Фоновый поток, который плавно берет логи из очереди и шлет в Discord"""
    while True:
        try:
            # Ждем появления новой записи в очереди
            payload = log_queue.get()
            webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
            
            if webhook_url:
                response = requests.post(
                    webhook_url, 
                    json=payload, 
                    headers={"Content-Type": "application/json"}, 
                    timeout=10
                )
                
                # Если Дискорд выдал лимит 429, возвращаем лог обратно в очередь
                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", 5)
                    print(f"[ЛИМИТ] Discord перегружен. Ожидание {retry_after} сек...")
                    time.sleep(retry_after)
                    log_queue.put(payload)
                else:
                    # Обязательная пауза между сообщениями для предотвращения банов
                    time.sleep(2.0)
            else:
                print("[ОШИБКА] Переменная DISCORD_WEBHOOK_URL пуста во вкладке Environment на Render!")
            
            log_queue.task_done()
        except Exception as e:
            print(f"[ОШИБКА ВОРКЕРА]: {e}")
            time.sleep(2)

# Запускаем фоновый поток при старте сервера
threading.Thread(target=discord_worker, daemon=True).start()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "working", "message": "Python queue-backend is running cleanly!"}), 200

@app.route('/api/log', methods=['POST'])
def proxy_log():
    try:
        # Получаем готовый JSON-пакет с embeds от index.html
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "Empty JSON"}), 400
            
        # Помещаем входящие данные в очередь отправки
        log_queue.put(data)
        
        # Мгновенно отвечаем телефону, чтобы интерфейс лаунчера не зависал
        return jsonify({"success": True, "message": "Data queued successfully"}), 200
        
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА БЭКЕНДА]: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
