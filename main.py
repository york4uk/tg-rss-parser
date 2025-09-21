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
CHANNELS_LIST = os.getenv("CHANNELS_LIST", "")  # список каналов через запятую
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))  # интервал проверки в секундах

# 🔑 Ключевые слова для фильтрации
KEYWORDS = {
    "розыгрыш", "дарим", "подарим", "giveaway", "конкурс", "выиграй", "подарок",
    "разыгрываем", "приз", "лот", "акция", "бесплатно", "участвуй",
    "репост", "подписка", "промо", "лотерея", "win", "подарки"
}

# 🤖 Инициализация клиента
app = Client("universal_parser", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# 🔍 Функция: проверить, содержит ли текст ключевые слова
def contains_keyword(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for keyword in KEYWORDS:
        if keyword in text_lower:
            return True
    return False

# 📥 Функция: получить последние посты из RSS канала
def get_channel_posts(channel_username: str, minutes_ago: int = 15):
    url = f"https://t.me/s/{channel_username}"
    feed = feedparser.parse(url)
    posts = []
    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_ago)

    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.utcnow()
        if pub_date > cutoff_time:
            posts.append({
                "title": entry.title if hasattr(entry, 'title') else "",
                "summary": entry.summary if hasattr(entry, 'summary') else "",
                "link": entry.link if hasattr(entry, 'link') else "",
                "published": pub_date,
                "source": f"@{channel_username}"
            })
    return posts

# 📥 Функция: получить последние сообщения из группы
async def get_group_messages(client: Client, chat_id: int, minutes_ago: int = 15):
    messages = []
    cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
    async for message in client.get_chat_history(chat_id, limit=20):
        if message.date < cutoff_time:
            break
        if message.text:
            messages.append({
                "text": message.text,
                "link": f"tg://openmessage?chat_id={chat_id}&message_id={message.id}",
                "source": message.chat.title or "Группа",
                "date": message.date
            })
    return messages

# 🔄 Основной цикл парсинга
async def main():
    await app.start()
    print("🚀 Универсальный парсер запущен")
    print(f"⏱️  Проверка каждые {CHECK_INTERVAL} секунд")

    # Получаем список групп
    print("[+] Получаем список групп...")
    groups = []
    async for dialog in app.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            groups.append({
                "id": dialog.chat.id,
                "title": dialog.chat.title,
                "type": dialog.chat.type
            })
    print(f"[+] Найдено {len(groups)} групп")

    # Получаем список каналов
    channels = []
    if CHANNELS_LIST:
        channels = [ch.strip() for ch in CHANNELS_LIST.split(",") if ch.strip()]
    print(f"[+] Отслеживаем {len(channels)} каналов: {', '.join(channels)}")

    processed_links = set()  # чтобы не дублировать

    while True:
        try:
            print(f"\n[🕒] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Проверка новых постов...")

            # 1. Проверяем каналы через RSS
            for channel_username in channels:
                try:
                    posts = get_channel_posts(channel_username, minutes_ago=15)
                    for post in posts:
                        link = post["link"]
                        if link in processed_links:
                            continue

                        full_text = f"{post['title']} {post['summary']}"
                        if contains_keyword(full_text):
                            message_text = (
                                f"🎁 **Найден розыгрыш!**\n\n"
                                f"📌 Источник: {post['source']}\n\n"
                                f"{full_text[:3000]}\n\n"
                                f"🔗 [Читать полностью]({link})"
                            )
                            await app.send_message(TARGET_CHAT_ID, message_text, disable_web_page_preview=False)
                            print(f"[+] ✅ Канал: {post['source']} | {link}")
                            processed_links.add(link)
                except Exception as e:
                    print(f"[-] Ошибка при парсинге канала @{channel_username}: {e}")

            # 2. Проверяем группы через историю сообщений
            for group in groups:
                try:
                    messages = await get_group_messages(app, group["id"], minutes_ago=15)
                    for msg in messages:
                        link = msg["link"]
                        if link in processed_links:
                            continue

                        if contains_keyword(msg["text"]):
                            message_text = (
                                f"🎁 **Найден розыгрыш!**\n\n"
                                f"📌 Источник: {msg['source']}\n\n"
                                f"{msg['text'][:3000]}\n\n"
                                f"🔗 Перейти: {link}"
                            )
                            await app.send_message(TARGET_CHAT_ID, message_text, disable_web_page_preview=True)
                            print(f"[+] ✅ Группа: {msg['source']} | {link}")
                            processed_links.add(link)
                except Exception as e:
                    print(f"[-] Ошибка при проверке группы {group['title']}: {e}")

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"[-] Критическая ошибка: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    app.run(main())


