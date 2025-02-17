from flask import Flask, render_template, request, jsonify
import src.ai_search as ais
import asyncio
import markdown2

app = Flask(__name__)

async def process_text(text):
    # Имитация обработки данных
    search = ais.Searcherer()
    answer, per_theme, theme_name, raw_sources = await search.search(
        query=text,
    )
    
    # Пример списка источников
    # sources = [
    #     {"title": "Источник 1", "url": "https://example.com/source1"},
    #     {"title": "Источник 2", "url": "https://example.com/source2"},
    #     {"title": "Источник 3", "url": "https://example.com/source3"}
    # ]

    sources = [{"title": url[url.index("//")+2:50], "url": url} for url in raw_sources]
    
    return {
        "content": markdown2.markdown(per_theme),
        "sources": sources
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    text = data.get('text', '')
    
    # Запуск асинхронной функции
    result = asyncio.run(process_text(text))
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
    )