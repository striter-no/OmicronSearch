from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_socketio import SocketIO
from datetime import datetime
import src.ai_search as ais
import asyncio
import markdown2
import src.easy_db as db
import hashlib

def sha256hash(pswd: str) -> str:
    return hashlib.sha256(pswd.encode()).hexdigest()

app = Flask(__name__)
socketio = SocketIO(app)
users_db = db.DataBase("./databases/users.json")

async def process_text(text, sid=None):

    async def asyDebugPoster(message: str):
        if sid:
            socketio.emit('debug_message', {'message': message}, room=sid)

    # await asyncio.sleep(2)

    # with open("./assets/answer_9863252.md") as f:
    #     per_theme = f.read()
    # sources = [
    #     {"title": "Источник 1_0", "url": "https://example.com/source1"},
    #     {"title": "Источник 2_1", "url": "https://example.com/source2"},
    #     {"title": "Источник 3_2", "url": "https://example.com/source3"}
    # ]

    # Имитация обработки данных
    search = ais.Searcherer()
    answer, per_theme, theme_name, raw_sources = await search.search(
        query=text,
        debug=True,
        debugHandler=asyDebugPoster
    )
    sources = [{"title": url[url.index("//")+2:50], "url": url} for url in raw_sources]
    
    with open("./ans.md", "w") as f:
        f.write(answer)

    return {
        "content": markdown2.markdown(per_theme),
        "sources": sources,
        "raw": per_theme,
    }

@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route("/background")
def backgrounds():
    return send_file("./assets/background.jpg", mimetype="image/jpeg")

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    print(f"login: {username} {password}")

    message = "Ошибка. Невозможно определить пользователя"
    status = False

    if users_db.exists(username):
        message = "Неверный пароль и/или логин"
        if users_db.get(username)["passwd_hash"] == password:
            message = "Успешный вход!"
            status = True
    
    else:
        message = "Новый пользователь создан"
        users_db.set(username, {"passwd_hash": password})
        status = True

    response = jsonify({
        "message": message,
        "status": status
    })
    
    # response.set_cookie('session', '', expires=0)
    return response

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    text = data.get('text', '')
    print(data)
    username, password = data.get('username', ''), data.get('password', '')

    if not users_db.exists(username):
        return jsonify({"status": "Сначала вам нужно зарегистрироваться"})
    if users_db.get(username)["passwd_hash"] != password:
        return jsonify({"status": "Неверный логин и/или пароль. Сначала вам нужно зарегистрироваться"})
    # Запуск асинхронной функции
    sid = data.get('sid', None)
    result = asyncio.run(process_text(text, sid))
    result["status"] = "ok"

    if users_db.exists(username):
        history = users_db.get(username).get('history', [])
        history.append({
            'question': text,
            'answer': result['raw'],
            'sources': result['sources'],
            'timestamp': datetime.now().isoformat()
        })
        users_db.set(username, {
            **users_db.get(username),
            'history': history  # Сохраняем последние 10 запросов
        })

    return jsonify(result)

@app.route('/get_history')
def get_history():
    data = request.json
    username, password = data.get('username', ''), data.get('password', '')

    if not users_db.exists(username):
        return jsonify({"status": "Сначала вам нужно зарегистрироваться"})
    if users_db.get(username)["passwd_hash"] != password:
        return jsonify({"status": "Неверный логин и/или пароль. Сначала вам нужно зарегистрироваться"})

    history = users_db.get(username).get('history', [])
    return jsonify({
        "status": "ok",
        "history": history
    })

@app.route('/get_theme_data', methods=['POST'])
def get_theme_data():
    data = request.json
    theme = data.get('theme', '')
    username = data.get('username', '')
    password = data.get('password', '')

    # Проверка авторизации
    if not users_db.exists(username):
        return jsonify({"status": "error", "message": "Сначала вам нужно зарегистрироваться"})
    if users_db.get(username)["passwd_hash"] != password:
        return jsonify({"status": "error", "message": "Неверный логин и/или пароль"})

    # Здесь можно добавить логику получения данных по теме
    # Пока возвращаем заглушку
    
    history = users_db.get(username).get('history', [])
    this_hist = {}

    for item in history:
        if item['question'] == theme:
            this_hist = item

    return jsonify({
        'status': 'ok',
        'theme': theme,
        'question': markdown2.markdown(this_hist.get("answer", "Ничего не нашлось...")),
        "sources": this_hist.get("sources", [])
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080)
