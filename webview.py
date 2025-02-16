from flask import Flask, render_template, request, jsonify
import src.ai_search as ais
import asyncio
import markdown2

app = Flask(__name__)

async def process_text(text):
    # Имитация обработки данных
    search = ais.Searcherer()
    answer, per_theme, theme_name = await search.search(
        query=text,
    )
    
    return markdown2.markdown(per_theme)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    text = data.get('text', '')
    
    # Запуск асинхронной функции
    result = asyncio.run(process_text(text))
    
    return jsonify({'result': result})

if __name__ == '__main__':
    app.run()