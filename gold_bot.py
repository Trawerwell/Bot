import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yfinance as yf

logging.basicConfig(level=logging.INFO)

# Токен теперь берется безопасно из настроек сервера
API_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

users_data = {}

def get_gold_price():
    try:
        gold = yf.Ticker("GC=F")
        data = gold.history(period="1d", interval="1m")
        if not data.empty:
            return round(data['Close'].iloc[-1], 2)
    except Exception as e:
        logging.error(f"Ошибка получения цены: {e}")
    return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    current_price = get_gold_price()

    users_data[chat_id] = {
        "threshold": 10.0,
        "last_price": current_price
    }

    text = (
        "👋 Привет! Я слежу за курсом золота.\n\n"
        f"💰 Текущая цена: **${current_price}** за унцию.\n"
        "📢 По умолчанию я пришлю уведомление, если цена изменится на **$10**.\n\n"
        "✍️ Чтобы изменить этот порог, просто **напишите мне число** (например: `15` или `5.5`)."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message()
async def change_threshold(message: types.Message):
    chat_id = message.chat.id
    try:
        new_threshold = float(message.text.replace(',', '.'))
        if new_threshold <= 0:
            await message.answer("❌ Порог должен быть больше нуля!")
            return

        current_price = get_gold_price()
        users_data[chat_id] = {
            "threshold": new_threshold,
            "last_price": current_price
        }
        await message.answer(
            f"✅ Успешно! Теперь вы получите уведомление, если золото вырастет или упадет на **${new_threshold}**.\n"
            f"Фиксированная базовая цена сейчас: **${current_price}**"
        )
    except ValueError:
        await message.answer("⚠️ Пожалуйста, отправьте корректное число (например: 10 или 12.5).")

async def check_gold_prices_job():
    if not users_data:
        return
    current_price = get_gold_price()
    if not current_price:
        return

    for chat_id, data in list(users_data.items()):
        last_price = data.get("last_price")
        threshold = data.get("threshold")

        if last_price is None:
            users_data[chat_id]["last_price"] = current_price
            continue

        price_diff = current_price - last_price

        if price_diff >= threshold:
            await bot.send_message(
                chat_id, 
                f"🚀 **Золото пошло вверх!**\n\n"
                f"📈 Новая цена: **${current_price}**\n"
                f"Изменение: +${round(price_diff, 2)} (с момента последней фиксации ${last_price})"
            )
            users_data[chat_id]["last_price"] = current_price

        elif price_diff <= -threshold:
            await bot.send_message(
                chat_id, 
                f"📉 **Золото падает!**\n\n"
                f"📉 Новая цена: **${current_price}**\n"
                f"Изменение: -${round(abs(price_diff), 2)} (с момента последней фиксации ${last_price})"
            )
            users_data[chat_id]["last_price"] = current_price

async def main():
    scheduler.add_job(check_gold_prices_job, "interval", minutes=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())