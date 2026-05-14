import os
import requests
import yfinance as yf

# Настройки бота (токен и твой ID чата)
# Токен мы уже знаем, а ID чата скрипт узнает автоматически из последнего сообщения
TOKEN = "8827554209:AAGpVWF2oHXK_BmoUuM1DiLo3GwI1MZFg2w"
CONFIG_FILE = "config.txt"

def get_gold_price():
    """Получает текущую цену золота"""
    try:
        gold = yf.Ticker("GC=F")
        data = gold.history(period="1d", interval="1m")
        if not data.empty:
            return round(data['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"Ошибка получения цены: {e}")
    return None

def load_config():
    """Загружает сохраненные настройки (базовую цену и порог)"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            lines = f.read().splitlines()
            if len(lines) >= 3:
                return lines[0], float(lines[1]), float(lines[2])
    return None, None, 10.0  # По умолчанию порог 10$

def save_config(chat_id, last_price, threshold):
    """Сохраняет настройки в файл"""
    with open(CONFIG_FILE, "w") as f:
        f.write(f"{chat_id}\n{last_price}\n{threshold}")

def get_last_chat_id_and_threshold():
    """Проверяет новые сообщения в боте, чтобы узнать лимит от юзера"""
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res.get("ok") and res.get("result"):
            # Берем самое последнее сообщение
            last_update = res["result"][-1]
            chat_id = last_update["message"]["chat"]["id"]
            text = last_update["message"]["text"].strip()
            
            # Если юзер написал число, это новый порог
            try:
                new_threshold = float(text.replace(',', '.'))
                return str(chat_id), new_threshold
            except ValueError:
                return str(chat_id), None
    except Exception as e:
        print(f"Ошибка Telegram API: {e}")
    return None, None

def send_telegram_message(chat_id, text):
    """Отправляет текстовое сообщение в телеграм"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    current_price = get_gold_price()
    if not current_price:
        return

    # 1. Читаем старые настройки из файла
    saved_chat_id, last_price, threshold = load_config()

    # 2. Проверяем, не написал ли юзер в бот новое число (изменение порога)
    active_chat_id, new_threshold = get_last_chat_id_and_threshold()
    
    if active_chat_id:
        chat_id = active_chat_id
        if new_threshold is not None:
            threshold = new_threshold
            last_price = current_price  # Сбрасываем точку отсчета под новый порог
            save_config(chat_id, last_price, threshold)
            send_telegram_message(chat_id, f"✅ Порог изменен на **${threshold}**.\nТекущая базовая цена золота: **${current_price}**")
            return
    else:
        chat_id = saved_chat_id

    # Если бот запускается вообще в первый раз и файлов нет
    if not chat_id:
        print("Бот еще не получал сообщений. Напишите ему что-нибудь в Телеграм!")
        return

    if last_price is None:
        save_config(chat_id, current_price, threshold)
        send_telegram_message(chat_id, f"🏃‍♂️ Бот запущен! Слежу за золотом.\nТекущая цена: **${current_price}**\nПорог оповещения: **${threshold}**")
        return

    # 3. Проверяем изменение цены
    price_diff = current_price - last_price

    if price_diff >= threshold:
        send_telegram_message(chat_id, f"🚀 **Золото растет!**\n\n📈 Цена: **${current_price}** (+${round(price_diff, 2)})")
        save_config(chat_id, current_price, threshold)  # Обновляем базовую цену
    elif price_diff <= -threshold:
        send_telegram_message(chat_id, f"📉 **Золото падает!**\n\n📉 Цена: **${current_price}** (-${round(abs(price_diff), 2)})")
        save_config(chat_id, current_price, threshold)  # Обновляем базовую цену
    else:
        # Если ничего не изменилось, просто перезаписываем текущие настройки, чтобы не потерять
        save_config(chat_id, last_price, threshold)
        print(f"Изменений нет. Цена: ${current_price}, База: ${last_price}, Порог: ${threshold}")

if __name__ == "__main__":
    main()
