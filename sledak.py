import os
import asyncio
import sqlite3
from datetime import datetime
from pyrogram import Client
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

API_ID = 'ид'  # Замените на ваш API ID
API_HASH = 'хэш'  # Замените на ваш API Hash
BOT_TOKEN = 'токен бота'  # Замените на токен вашего бота



pyro_client = Client("my_session", api_id=API_ID, api_hash=API_HASH)


aiogram_bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def init_db():
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_title TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            username TEXT,
            text TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_message(chat_title: str, message_id: int, username: str, text: str, date: str):
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (chat_title, message_id, username, text, date)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_title, message_id, username, text, date))
    conn.commit()
    conn.close()


def normalize_group_name(link: str) -> str:
    if link.startswith("https://t.me/"):
        link = link.split("https://t.me/")[-1]
    elif link.startswith("t.me/"):
        link = link.split("t.me/")[-1]
    elif link.startswith("@"):
        link = link[1:]
    return link.split("/")[0]


@dp.message(Command("add"))
async def add_group(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Укажите ссылки на группы, например:\n/add t.me/chat1\nt.me/chat2\nt.me/chat3")
        return

    try:
        links = args[1].split()
        for link in links:
            group_name = normalize_group_name(link)
            if not group_name:
                await message.reply(f"Некорректная ссылка: {link}. Пропускаю.")
                continue

            await message.reply(f"Начинаю сбор сообщений из группы {group_name}...")

            async for msg in pyro_client.get_chat_history(group_name):
                if msg.text:
                    date = msg.date.strftime("%d.%m.%y %H:%M")
                    save_message(group_name, msg.id, msg.from_user.username, msg.text, date)

            await message.reply(f"Сообщения из группы {group_name} сохранены в базу данных!")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")


@dp.message(lambda message: message.text and message.text.startswith("@"))
async def search_by_username(message: types.Message):
    username = message.text.strip("@")
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT chat_title, message_id, text, date
        FROM messages
        WHERE username = ?
    """, (username,))
    results = cursor.fetchall()
    conn.close()

    if results:
        response = []
        for chat_title, message_id, text, date in results:
            # Обрезаем текст до 10 символов
            truncated_text = (text[:10] + "...") if len(text) > 10 else text
            # Формируем гиперссылку
            link = f"https://t.me/{chat_title}/{message_id}"
            # Добавляем результат в формате: текст (гиперссылка), дата
            response.append(f'<a href="{link}">{truncated_text}</a> - {date}')
        await message.reply("\n".join(response), parse_mode=ParseMode.HTML)
    else:
        await message.reply(f"Сообщений от @{username} не найдено.")


async def main():
    init_db()


    await pyro_client.start()
    print("Pyrogram клиент авторизован!")

    await dp.start_polling(aiogram_bot)

if __name__ == "__main__":
    asyncio.run(main())