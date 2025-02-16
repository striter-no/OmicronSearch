# Aiogram version
import asyncio
import json as jn
import src.ai_search as ais

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.types import Message

TOKEN = jn.load(open("./assets/bot_config.json"))["api_token"]

dp = Dispatcher()
bot = None

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer("Это бот, основанный на проекте OmicronSearch. \n\nНапишите мне ваш вопрос, и я постараюсь проанализировать тему и выдать максимально подробный ответ.\n\nПодсказка: чем более структурированный и конкретный вопрос, тем лучше будет ответ.")

@dp.message()
async def echo_handler(message: Message) -> None:
    question = message.md_text

    await message.answer(f"Поиск по вопросу \"{message.text}\"")

    proxy = jn.load(open("./assets/proxy.json"))
    search = ais.Searcherer(proxy)

    answer, per_theme = await search.search(
        query=question
    )

    await message.answer("Ответ на вопрос: ")
    await message.answer(per_theme)

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