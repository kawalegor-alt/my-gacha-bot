import asyncio
import logging
import random
import os
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

# --- НАСТРОЙКИ ---
# Твой токен. На Railway лучше добавить его в Variables как BOT_TOKEN
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 1548461377 
# Путь к базе данных в защищенном хранилище Railway
DB_PATH = "/app/data/gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
async def init_db():
    # Создаем папку, если её нет (важно для Railway Volume)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, admin_money INTEGER DEFAULT 0,
            last_draw TEXT, titles TEXT DEFAULT 'Новичок')''')
        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        await db.commit()

# --- ЛОГИКА ШАНСОВ ---
def get_rarity(rank):
    r = random.uniform(0, 100)
    if rank == "Мифрил":
        if r <= 15: return 5
        if r <= 35: return 4
        if r <= 60: return 3
        if r <= 90: return 2
        return 1
    bonus = 5 if rank == "Серебро" else 0
    if r <= (1 + bonus * 0.25): return 5 
    if r <= (4 + bonus * 0.5): return 4
    if r <= (10 + bonus * 1.0): return 3
    if r <= (30 + bonus * 1.5): return 2
    return 1

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?, ?, ?)", 
                         (m.from_user.id, m.from_user.first_name, user_rank))
        await db.commit()
    await m.answer("👋 Бот запущен на Railway! Напиши 'карта' или /profile")

@dp.message(F.text.lower().in_(["карта", "карту", "нев", "невер"]))
async def draw(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        rank, last_draw = u
        cd = timedelta(hours=24) if rank != "Мифрил" else timedelta(seconds=10)
        now = datetime.now()
        if last_draw and now < datetime.fromisoformat(last_draw) + cd:
            rem = (datetime.fromisoformat(last_draw) + cd) - now
            return await m.answer(f"⏳ Кулдаун! Осталось: {str(rem).split('.')[0]}")
        
        rarity = get_rarity(rank)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer("Карт пока нет в базе!")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        if await res.fetchone():
            bonus = rarity * 20
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bonus, m.from_user.id))
            cap = f"🃏 Повторка: {c_name} ({rarity}⭐)\n💰 +{bonus} мошенников"
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, c_id))
            cap = f"🎉 НОВАЯ: {c_name} ({rarity}⭐)"
        
        await db.execute("UPDATE users SET last_draw = ? WHERE user_id = ?", (now.isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap)

@dp.message(Command("profile"))
async def profile(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
        res = await db.execute("SELECT COUNT(*) FROM cards")
        total = (await res.fetchone())[0]
    
    text = (f"👤 {u[0]} | Титул: {u[3]}\n🏅 Ранг: {u[1]}\n💰 Мошенники: {u[2]}\n🎴 Карты: {inv_cnt}/{total}")
    await m.answer(text)

@dp.message(F.photo)
async def add_card_photo(m: Message, bot: Bot):
    if m.from_user.id != ADMIN_ID or not m.caption or not m.caption.startswith("/add_card"): return
    try:
        args = m.caption.split()
        rarity = int(args[-1])
        name = " ".join(args[1:-1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?, ?, ?)", (name, rarity, m.photo[-1].file_id))
            await db.commit()
        await m.answer(f"✅ Добавлено: {name} ({rarity}⭐)")
    except:
        await m.answer("Ошибка! Формат: /add_card Имя 5 (и прикрепи фото)")

# --- ЗАПУСК ---
async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
