# Aiogram version
import asyncio
import math
import json as jn
import src.ai_search as ais
import random as rnd

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.types import Message

from ytelegraph import TelegraphAPI

TOKEN = jn.load(open("./assets/bot_config.json"))["api_token"]

dp = Dispatcher()
bot = None

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer("Это бот, основанный на проекте **OmicronSearch**. \n\nНапишите мне ваш вопрос, и я постараюсь проанализировать тему и выдать максимально подробный ответ. Также вам нужно указать формат ответа:\n\n\t`/text вопрос` - __ответ будет выведен в качестве сообщения__\n\n\t`/telegraph вопрос` - __ответ будет в качестве ссылки на статью на телеграф (учтите, что в таком случае код будет отражаться не верно, а также, вероятно ответ будет разбит на несколько статей)__\n\n\t`/file вопрос` - __ответ будет в качестве файла формата маркдаун__\n\nПодсказка: чем более структурированный и конкретный вопрос, тем лучше будет ответ.\n\n\tЕсли вы добавите `_file` на конец типа, то вы также получите версию ответа в файле (помимо указанной ранее)\n\nПредупреждение: бот ищет информацию **ДОЛГО** (2-3 минуты), дождитесь, пожалуйста, ответа.")

@dp.message()
async def echo_handler(message: Message) -> None:
    question = " ".join(message.md_text.split()[1:])
    qtype = message.text.split()[0]
    is_backuping = qtype.endswith("_file") and qtype != "/file_file"
    qtype = qtype[:-5] if is_backuping else qtype

    if not (qtype in ["/text", "/telegraph", "/file"]):
        await message.answer("Неправильный формат ответа. Доступные форматы:\n\n\t`/text вопрос` - __ответ будет выведен в качестве сообщения__\n\n\t`/telegraph вопрос` - __ответ будет в качестве ссылки на статью на телеграф (учтите, что в таком случае код будет отражаться не верно, а также, вероятно ответ будет разбит на несколько статей)__\n\n\t`/file вопрос` - __ответ будет в качестве файла формата маркдаун__\n\n")
        return

    await message.answer(f"Поиск по вопросу \"{question}\"")

    proxy = jn.load(open("./assets/proxy.json"))
    search = ais.Searcherer(proxy)

    answer, per_theme, theme_name = await search.search(
        query=question
    )

    await message.answer("Ответ на вопрос: ")

    if qtype == "/text":
        i = 0
        while True:
            if i >= len(per_theme):
                break
            await message.answer(
                per_theme[i:i+4000]
            )
            i += 4000

    elif qtype == "/file":
        token = rnd.randint(0, 10000000)
        with open(f"./assets/answer_{token}.md", "w") as f:
            f.write(per_theme)
        
        docfile = FSInputFile(f"./assets/answer_{token}.md", filename=theme_name)
        await message.answer_document(docfile)
    elif qtype == "/telegraph":
        per_theme = per_theme[per_theme.index("\n"):]
        ph = TelegraphAPI()
        links = []
        step = 12*1024
        i, iteri = 0, 0
        while True:
            if i >= len(per_theme):
                break
            links.append(ph.create_page_md(f"{theme_name} ({iteri+1})", per_theme[i:i+step]))
            i += step
            iteri += 1
        
        await message.answer(f"Ссылки:\n{'\n'.join(links)}")

    if is_backuping:
        token = rnd.randint(0, 10000000)
        with open(f"./assets/answer_{token}.md", "w") as f:
            f.write(per_theme)
        
        docfile = FSInputFile(f"./assets/answer_{token}.md", filename=theme_name)
        await message.answer_document(docfile)

async def main() -> None:
    global bot
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    
    while True:
        try:
            await dp.start_polling(bot)
        except KeyboardInterrupt:
            return
        except Exception as ex:
            print(f"Error: {ex}")

if __name__ == "__main__":
    asyncio.run(main())