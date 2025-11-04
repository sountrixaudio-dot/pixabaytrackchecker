import requests
import time
from bs4 import BeautifulSoup
import json
import telebot

# === НАСТРОЙКИ ===
PIXABAY_USER_URL = "https://pixabay.com/users/sountrixaudio-52768843/"   # <-- вставь свой URL
CHECK_INTERVAL = 300  # интервал проверки в секундах (каждые 5 минут)
BOT_TOKEN = "8568244160:AAGrGu8fYuop1qUPPffgmlNvnX_IO6lhr3Q"
CHAT_ID = "659461309"
HISTORY_FILE = "published_history.json"

bot = telebot.TeleBot(BOT_TOKEN)


def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_published_tracks():
    response = requests.get(PIXABAY_USER_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("a.link--h3bPW")  # карточки работ
    track_urls = ["https://pixabay.com" + i["href"] for i in items]

    return track_urls


def notify_new_track(url):
    message = f"✅ Новый трек опубликован!\n{url}"
    bot.send_message(CHAT_ID, message)


def main():
    print("✅ BOT STARTED")
    history = load_history()

    while True:
        try:
            current_tracks = get_published_tracks()

            for track in current_tracks:
                if track not in history:
                    history.append(track)
                    notify_new_track(track)

            save_history(history)

        except Exception as e:
            bot.send_message(CHAT_ID, f"⚠️ Ошибка: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
