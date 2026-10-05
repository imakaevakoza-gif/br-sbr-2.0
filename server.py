import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Разрешаем фронтенду с GitHub Pages отправлять запросы на этот сервер
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "working", "message": "Python backend is running cleanly!"}), 200

@app.route('/api/log', methods=['POST'])
def proxy_log():
    try:
        # Сервер берет секретную ссылку из панели управления Render
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        
        if not webhook_url:
            print("[ОШИБКА] DISCORD_WEBHOOK_URL не настроен в Environment Variables на Render!")
            return jsonify({"success": False, "error": "Server configuration error"}), 500
        
        # Получаем данные, которые отправил телефон
        data = request.get_json()
        
        # Мгновенно пересылаем Embed-карточку в ваш Discord-канал
        response = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"}, timeout=10)
        
        # ИСПРАВЛЕНО: Правильная проверка успешных статус-кодов Дискорда (200, 201, 204)
        if response.status_code in [200, 201, 204]:
            return jsonify({"success": True}), 200
        else:
            print(f"[ДИСКОРД ОТКЛОНИЛ] Код: {response.status_code}, Ответ: {response.text}")
            return jsonify({"success": False, "error": "Discord rejected request"}), response.status_code
            
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА БЭКЕНДА]: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
