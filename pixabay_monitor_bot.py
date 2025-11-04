import os
import time
import json
import requests
from bs4 import BeautifulSoup
import telebot
from threading import Thread

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # строкой ок
PIXABAY_USER_URL = os.getenv("PIXABAY_USER_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))  # сек, можно задать в Render

HISTORY_FILE = "published_history.json"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------- утилиты ----------
def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def fetch_track_urls():
    r = requests.get(PIXABAY_USER_URL, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    # селектор может меняться — при необходимости подправь:
    items = soup.select("a.link--h3bPW")
    return ["https://pixabay.com" + i["href"] for i in items]

def send(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Send error:", e, flush=True)

def check_once():
    print("Checking Pixabay…", flush=True)
    history = load_history()
    current = fetch_track_urls()
    new_items = [u for u in current if u not in history]
    if new_items:
        for url in new_items:
            send(f"✅ Новый трек опубликован!\n{url}")
            history.append(url)
        save_history(history)
    else:
        print("No new tracks.", flush=True)

# ---------- приём команд ----------
@bot.message_handler(commands=["start", "ping"])
def ping(m):
    bot.reply_to(m, "✅ Бот активен. Проверяю каждые {} сек.".format(CHECK_INTERVAL))

@bot.message_handler(commands=["check"])
def manual_check(m):
    bot.reply_to(m, "⏳ Запускаю ручную проверку…")
    try:
        check_once()
        bot.reply_to(m, "✅ Проверка завершена.")
    except Exception as e:
        bot.reply_to(m, f"⚠️ Ошибка: {e}")

def run_polling():
    # отдельный поток для приёма сообщений, чтобы не мешать циклу
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

# ---------- основной цикл ----------
def main():
    print("✅ BOT STARTED", flush=True)
    send("🤖 Бот запущен. Мониторинг активен.")
    Thread(target=run_polling, daemon=True).start()

    while True:
        try:
            check_once()
        except Exception as e:
            print("Loop error:", e, flush=True)
            send(f"⚠️ Ошибка мониторинга: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
