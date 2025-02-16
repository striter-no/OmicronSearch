import asyncio as asy
import src.ai_search as ais
import json as jn

async def main():
    proxy = jn.load(open("./assets/proxy.json"))
    search = ais.Searcherer(proxy)

    answer, per_theme = await search.search(
        query="Как использовать ESP32 для создания сниффера пакетов и получения WiFi хэндшейков? Расскажи процесс создания такого а-ля конкурента airmon-ng",
    )

    with open("./answer_1.md", "w") as f:
        f.write(answer)

    with open("./per_theme_1.md", "w") as f:
        f.write(per_theme)

if __name__ == "__main__":
    asy.run(main())