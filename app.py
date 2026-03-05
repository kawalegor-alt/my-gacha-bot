import asyncio
import logging
import random
import os
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# --- КОНФИГ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 1548461377 
DB_PATH = "/app/data/gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- МЕНЮ ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🃏 Получить карту"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🏆 Топ")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Старт"),
        BotCommand(command="promo", description="🎁 Промокод"),
        BotCommand(command="adminhelp", description="🛠 Админ")
    ]
    await bot.set_my_commands(commands)

# --- ИНИЦИАЛИЗАЦИЯ БД ---
async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, bbc_money INTEGER DEFAULT 0, last_draw TEXT, 
            titles TEXT DEFAULT 'Новичок', unlocked_titles TEXT DEFAULT 'Новичок')''')
        
        # Проверка колонок для старых БД
        try: await db.execute("ALTER TABLE users ADD COLUMN bbc_money INTEGER DEFAULT 0")
        except: pass
        
        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, reward_type TEXT, reward_val INTEGER, uses_left INTEGER, expires_at TEXT)''')
        await db.commit()

# --- ШАНСЫ ---
def get_rarity(rank, titles):
    r = random.uniform(0, 100)
    bonus = 2 if "главный кисер" in titles else 0
    if rank == "Мифрил":
        if r <= (15 + bonus): return 5
        if r <= 35: return 4
        if r <= 60: return 3
        return 2 if r <= 90 else 1
    if r <= (1 + bonus): return 5
    if r <= 5: return 4
    if r <= 15: return 3
    return 2 if r <= 40 else 1

REWARDS = {1:{"n":100,"d":50}, 2:{"n":150,"d":75}, 3:{"n":250,"d":100}, 4:{"n":500,"d":250}, 5:{"n":1000,"d":700}}
@dp.message(Command("start"))
async def start_cmd(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        title = "главный кисер" if m.from_user.id == ADMIN_ID else "Новичок"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank, titles, unlocked_titles) VALUES (?,?,?,?,?)", 
                         (m.from_user.id, m.from_user.first_name, user_rank, title, title))
        await db.commit()
    await profile_cmd(m, bot)

@dp.message(F.text == "👤 Профиль")
async def profile_cmd(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
    
    text = (f"<b>👤 Игрок:</b> {u[0]}\n🏅 <b>Ранг:</b> {u[1]}\n🏷 <b>Титул:</b> {u[4]}\n"
            f"💰 <b>Монеты:</b> {u[2]}\n💎 <b>BBC:</b> {u[3]}\n🎴 <b>Карт:</b> {inv_cnt}")
    await m.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(F.text == "🃏 Получить карту")
async def draw_card(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        rank, last_draw, titles = await res.fetchone()
        cd = timedelta(seconds=10) if rank == "Мифрил" else timedelta(hours=24)
        if last_draw and datetime.now() < datetime.fromisoformat(last_draw) + cd:
            return await m.answer("⏳ Еще не время!")
        
        rarity = get_rarity(rank, titles)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer("⚠️ Карт этой редкости нет в базе.")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        is_dup = await res.fetchone()
        rew = REWARDS[rarity]["d"] if is_dup else REWARDS[rarity]["n"]
        
        if is_dup:
            await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
            cap = f"♻️ ПОВТОРКА: {c_name} ({rarity}⭐)\n💰 +{rew}"
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?,?)", (m.from_user.id, c_id))
            cap = f"🎉 НОВАЯ: {c_name} ({rarity}⭐)\n💰 +{rew}"
        
        await db.execute("UPDATE users SET money=money+?, last_draw=? WHERE user_id=?", (rew, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap)
        @dp.message(F.text == "🏆 Топ")
async def top_menu(m:Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Монеты", callback_data="top_money"), InlineKeyboardButton(text="💎 BBC", callback_data="top_bbc")]
    ])
    await m.answer("🏆 Выбери категорию:", reply_markup=kb)

@dp.callback_query(F.data.startswith("top_"))
async def top_callback(c: CallbackQuery):
    cat = c.data.split("_")[1]
    col = "money" if cat == "money" else "bbc_money"
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(f"SELECT nickname, {col} FROM users ORDER BY {col} DESC LIMIT 10")
        data = await res.fetchall()
    
    text = f"🏆 ТОП {cat.upper()}:\n" + "\n".join([f"{i+1}. {n} — {v}" for i,(n,v) in enumerate(data)])
    try:
        await c.message.edit_text(text, parse_mode=ParseMode.HTML)
    except TelegramBadRequest:
        await c.answer()

@dp.message(Command("promo"))
async def use_promo(m: Message):
    code = m.text.split()[1] if len(m.text.split()) > 1 else ""
    if not code: return await m.answer("⚠️ Введи: /promo КОД")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT reward_type, reward_val, uses_left, expires_at FROM promocodes WHERE code=?", (code,))
        p = await res.fetchone()
        if not p or p[2] <= 0 or datetime.fromisoformat(p[3]) < datetime.now():
            return await m.answer("❌ Код не работает.")
        
        if p[0] == "cash": await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (p[1], m.from_user.id))
        elif p[0] == "bbc": await db.execute("UPDATE users SET bbc_money=bbc_money+? WHERE user_id=?", (p[1], m.from_user.id))
        
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code=?", (code,))
        await db.commit()
        await m.answer(f"✅ Получено: {p[1]} {p[0]}")

@dp.message(F.photo & F.caption.startswith("/add_card"))
async def admin_add_card(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        parts = m.caption.split()
        rarity = int(parts[-1])
        name = " ".join(parts[1:-1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)", (name, rarity, m.photo[-1].file_id))
            await db.commit()
        await m.answer(f"✅ Карта {name} добавлена!")
    except: await m.answer("❌ Ошибка. Формат: /add_card Имя 5")

@dp.message(Command("create_promo"))
async def admin_promo(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        _, code, r_type, val, limit, days = m.text.split()
        exp = (datetime.now() + timedelta(days=int(days))).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO promocodes VALUES (?,?,?,?,?)", (code, r_type, int(val), int(limit), exp))
            await db.commit()
        await m.answer(f"✅ Промо {code} создан!")
    except: await m.answer("❌ Ошибка. Пример: /create_promo GIFT bbc 100 50 7")

@dp.message(F.text == "🎒 Инвентарь")
async def inv_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT c.name, c.rarity, i.count FROM inventory i JOIN cards c ON i.card_id=c.card_id WHERE i.user_id=?", (m.from_user.id,))
        cards = await res.fetchall()
    if not cards: return await m.answer("Пусто!")
    await m.answer("🎒 ТВОИ КАРТЫ:\n" + "\n".join([f"{r}⭐ {n} x{c}" for n,r,c in cards]))

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
