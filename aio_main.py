# Aiogram version
import asyncio
import math
import json as jn
import src.ai_search as ais
import random as rnd
import time

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.types import Message

from ytelegraph import TelegraphAPI

def time_passed(start):
    elapsed_time = time.time() - start
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    return (hours, minutes, seconds)

def minutes_passed(start):
    elapsed_time = time.time() - start
    return elapsed_time // 60

users = dict()
TOKEN = jn.load(open("./assets/bot_config.json"))["api_token"]

dp = Dispatcher()
bot = None

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer("Это бот, основанный на проекте **OmicronSearch**. \n\nНапишите мне ваш вопрос, и я постараюсь проанализировать тему и выдать максимально подробный ответ. Также вам нужно указать формат ответа:\n\n\t`/text вопрос` - __ответ будет выведен в качестве сообщения__\n\n\t`/telegraph вопрос` - __ответ будет в качестве ссылки на статью на телеграф (учтите, что в таком случае код будет отражаться не верно, а также, вероятно ответ будет разбит на несколько статей)__\n\n\t`/file вопрос` - __ответ будет в качестве файла формата маркдаун__\n\nПодсказка: чем более структурированный и конкретный вопрос, тем лучше будет ответ.\n\n\tЕсли вы добавите `_file` на конец типа, то вы также получите версию ответа в файле (помимо указанной ранее)\n\nПредупреждение: бот ищет информацию **ДОЛГО** (2-3 минуты), дождитесь, пожалуйста, ответа.\n\nСейчас у всех пользователей лимит в 5 запросов за 30 минут!")

@dp.message()
async def message_handler(message: Message) -> None:
    print(f"[{message.from_user.id}] Новый запрос")
    if not message.text:
        await message.answer("Пожалуйста, напишите вопрос. /start для помощи")
        return
    
    if message.from_user.id != 5243956136:
        if message.from_user.id not in users:
            users[message.from_user.id] = {
                "attempts": 0,
                "start_time": time.time()
            }
            user = users[message.from_user.id]
        else:
            user = users[message.from_user.id]

            if minutes_passed(user["start_time"]) >= 30 and user["attempts"] >= 3:
                users[message.from_user.id]["attempts"] = 0
                users[message.from_user.id]["start_time"] = time.time()

            if user["attempts"] >= 5:
                await message.answer("Вы привысили лимит в 5 запросов в 30 минут. Пожалуйста, подождите и попробуйте еще раз.")
                return

    question = " ".join(message.md_text.split()[1:])
    qtype = message.text.split()[0]
    is_backuping = qtype.endswith("_file") and qtype != "/file_file"
    qtype = qtype[:-5] if is_backuping else qtype

    if not (qtype in ["/text", "/telegraph", "/file"]):
        await message.answer("Неправильный формат ответа. Доступные форматы:\n\n\t`/text вопрос` - __ответ будет выведен в качестве сообщения__\n\n\t`/telegraph вопрос` - __ответ будет в качестве ссылки на статью на телеграф (учтите, что в таком случае код будет отражаться не верно, а также, вероятно ответ будет разбит на несколько статей)__\n\n\t`/file вопрос` - __ответ будет в качестве файла формата маркдаун__\n\n")
        return

    if message.from_user.id != 5243956136:
        users[message.from_user.id]["attempts"] += 1
    
    print(f"[{message.from_user.id}] Вопрос: {question} ({qtype})")
    await message.answer(f"Поиск по вопросу \"{question}\"")

    proxy = jn.load(open("./assets/proxy.json"))
    search = ais.Searcherer(proxy)

    answer, per_theme, theme_name = await search.search(
        query=question,
        debug=True
    )

    print(f"[{message.from_user.id}] Ответ готов")
    await message.answer("Ответ на вопрос: ")

    try:
        if qtype == "/text":
            
            i = 0
            
            while True:
                if i >= len(per_theme):
                    break
                try:
                    await message.answer(
                        per_theme[i:i+4000]
                    )
                except:
                    await message.answer(
                        per_theme[i:i+4000],
                        parse_mode=None
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
            ph = TelegraphAPI(short_name="OmicronSearch AI")
            links = []
            step = 10*1024
            i, iteri = 0, 0
            while True:
                if i >= len(per_theme):
                    break
                links.append(ph.create_page_md(f"{theme_name} ({iteri+1})", per_theme[i:i+step]))
                i += step
                iteri += 1
            
            await message.answer(f"Ссылки:\n{'\n'.join(links)}")
    except Exception as ex:
        print(f"[{message.from_user.id}] Не получилось отослать ответ: {ex}")
        await message.answer("Не получилось отослать ответ, высылаю файловую версию")
        
        token = rnd.randint(0, 10000000)
        with open(f"./assets/answer_{token}.md", "w") as f:
            f.write(per_theme)
        
        docfile = FSInputFile(f"./assets/answer_{token}.md", filename=theme_name)
        await message.answer_document(docfile)
        return

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