import feedparser
import asyncio
import time
import os
from datetime import datetime, timedelta
from pyrogram import Client
from pyrogram.types import Message

# ⚙️ Переменные окружения
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))  # ID группы, куда отправлять посты
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "skidki_bеларуси")  # username без @
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))  # интервал проверки в секундах (по умолчанию 5 минут)

# 🔑 Ключевые слова для фильтрации
KEYWORDS = {
    "розыгрыш", "дарим", "giveaway", "конкурс", "выиграй", "подарок",
    "разыгрываем", "подарим", "участвуй",
    "участвую", "подарки", "розыгрывается"
}

# 🤖 Инициализация клиента
app = Client("rss_parser", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# 🔍 Функция: проверить, содержит ли текст ключевые слова
def contains_keyword(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for keyword in KEYWORDS:
        if keyword in text_lower:
            return True
    return False

# 📥 Функция: получить последние посты из RSS
def get_latest_posts(channel_username: str, minutes_ago: int = 10):
    url = f"https://t.me/s/{channel_username}"
    feed = feedparser.parse(url)
    posts = []
    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_ago)

    for entry in feed.entries:
        # Парсим дату публикации
        pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.utcnow()
        if pub_date > cutoff_time:
            posts.append({
                "title": entry.title if hasattr(entry, 'title') else "",
                "summary": entry.summary if hasattr(entry, 'summary') else "",
                "link": entry.link if hasattr(entry, 'link') else "",
                "published": pub_date
            })
    return posts

# 🔄 Основной цикл парсинга
async def main():
    await app.start()
    print(f"🚀 RSS-парсер запущен для канала @{CHANNEL_USERNAME}")
    print(f"⏱️  Проверка каждые {CHECK_INTERVAL} секунд")

    processed_links = set()  # чтобы не дублировать посты

    while True:
        try:
            print(f"\n[🕒] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Проверка новых постов...")
            posts = get_latest_posts(CHANNEL_USERNAME, minutes_ago=15)

            for post in posts:
                link = post["link"]
                if link in processed_links:
                    continue  # уже обработан

                full_text = f"{post['title']} {post['summary']}"
                if contains_keyword(full_text):
                    message_text = (
                        f"🎁 **Найден розыгрыш!**\n\n"
                        f"{full_text[:3000]}\n\n"
                        f"🔗 [Читать полностью]({link})"
                    )
                    try:
                        await app.send_message(TARGET_CHAT_ID, message_text, disable_web_page_preview=False)
                        print(f"[+] ✅ Отправлен пост: {link}")
                        processed_links.add(link)
                    except Exception as e:
                        print(f"[-] Ошибка отправки: {e}")

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"[-] Критическая ошибка: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":

    app.run(main())
