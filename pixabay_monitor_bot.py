# pixabay_monitor_bot.py
import os
import time
import json
import requests
from bs4 import BeautifulSoup
import telebot
from threading import Thread

# ===== Настройки через переменные окружения =====
BOT_TOKEN = os.getenv("BOT_TOKEN")                     # токен бота (обязательно)
CHAT_ID = os.getenv("CHAT_ID")                         # твой Telegram user ID (обязательно)
PIXABAY_USER_URL = os.getenv("PIXABAY_USER_URL") or "https://pixabay.com/users/sountrixaudio-52768843/"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))  # сек: 300=5мин, можно менять в Render

HISTORY_FILE = "published_history.json"
bot = telebot.TeleBot(BOT_TOKEN or "", parse_mode="HTML")

# “Человеческие” заголовки, чтобы избежать 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    "Referer": "https://pixabay.com/",
    "Cache-Control": "no-cache",
}

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

def normalize_profile_url(url: str) -> str:
    """Гарантируем публичный URL с табом/сортировкой."""
    u = (url or "").strip().rstrip("/")
    if not u:
        u = "https://pixabay.com/users/sountrixaudio-52768843/"
    if "tab=" not in u:
        u += "/?tab=all&order=latest"
    return u

def fetch_track_urls():
    url = normalize_profile_url(PIXABAY_USER_URL)
    r = requests.get(url, headers=HEADERS, timeout=25)
    if r.status_code == 403:
        # бросаем, чтобы верхний уровень сделал бэкофф
        raise RuntimeError("403 Forbidden from Pixabay")
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # Берём любые ссылки на треки: /music/...
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/music/"):
            links.append("https://pixabay.com" + href)

    # Убираем дубли, сохраняем порядок
    links = list(dict.fromkeys(links))
    return links

def send(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram creds missing; cannot send message.", flush=True)
        return
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Send error:", e, flush=True)

def check_once():
    print("Checking Pixabay…", flush=True)
    history = load_history()
    try:
        current = fetch_track_urls()
    except RuntimeError as e:
        # 403 — делаем мягкую паузу и выходим из итерации
        print(f"{e}. Backing off 10 minutes…", flush=True)
        time.sleep(600)
        return
    except Exception as e:
        print("Fetch error:", e, flush=True)
        return

    new_items = [u for u in current if u not in history]
    if new_items:
        for url in new_items:
            send(f"✅ Новый трек опубликован!\n{url}")
            history.append(url)
        save_history(history)
        print(f"Found {len(new_items)} new track(s).", flush=True)
    else:
        print("No new tracks.", flush=True)

# ---------- команды бота ----------
@bot.message_handler(commands=["start", "ping"])
def ping(m):
    bot.reply_to(
        m,
        "✅ Бот активен.\n"
        f"Проверяю каждые {CHECK_INTERVAL} сек.\n"
        f"Профиль: {normalize_profile_url(PIXABAY_USER_URL)}"
    )

@bot.message_handler(commands=["check"])
def manual_check(m):
    bot.reply_to(m, "⏳ Запускаю ручную проверку…")
    try:
        check_once()
        bot.reply_to(m, "✅ Проверка завершена.")
    except Exception as e:
        bot.reply_to(m, f"⚠️ Ошибка: {e}")

def run_polling():
    # отдельный поток для приёма команд
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Polling error:", e, flush=True)

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
