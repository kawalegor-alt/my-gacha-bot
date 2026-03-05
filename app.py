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

# --- НАСТРОЙКИ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 1548461377 
DB_PATH = "/app/data/gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- КЛАВИАТУРА ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🃏 Получить карту"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🏪 Магазин")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="promo", description="🎁 Ввести промокод"),
        BotCommand(command="help", description="📖 Инструкция"),
        BotCommand(command="adminhelp", description="🛠 Админ-панель")
    ]
    await bot.set_my_commands(commands)

# --- БАЗА ДАННЫХ ---
async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, bbc_money INTEGER DEFAULT 0, last_draw TEXT, 
            titles TEXT DEFAULT 'Новичок', unlocked_titles TEXT DEFAULT 'Новичок')''')
        
        # Миграция колонок (на случай если БД старая)
        try: await db.execute("ALTER TABLE users ADD COLUMN bbc_money INTEGER DEFAULT 0")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN unlocked_titles TEXT DEFAULT 'Новичок'")
        except: pass

        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, reward_type TEXT, reward_val INTEGER, uses_left INTEGER, expires_at TEXT)''')
        await db.commit()

# --- ЛОГИКА ВЫПАДЕНИЯ ---
def get_rarity(rank, titles):
    r = random.uniform(0, 100)
    premium_bonus = 2 if any(t in titles for t in ["Элита", "Легенда", "главный кисер"]) else 0
    if rank == "Мифрил":
        if r <= (15 + premium_bonus): return 5
        if r <= 35: return 4
        if r <= 60: return 3
        if r <= 90: return 2
        return 1
    bonus = 5 if rank == "Серебро" else 0
    if r <= (1 + bonus * 0.25 + premium_bonus): return 5 
    if r <= (4 + bonus * 0.5): return 4
    if r <= (10 + bonus * 1.0): return 3
    if r <= (30 + bonus * 1.5): return 2
    return 1

REWARDS = {1: {"new": 100, "dup": 50}, 2: {"new": 150, "dup": 75}, 3: {"new": 250, "dup": 100}, 4: {"new": 500, "dup": 250}, 5: {"new": 1000, "dup": 700}}
@dp.message(Command("start"))
async def start(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        default_title = "главный кисер" if m.from_user.id == ADMIN_ID else "Новичок"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank, titles, unlocked_titles) VALUES (?, ?, ?, ?, ?)", 
                         (m.from_user.id, m.from_user.first_name, user_rank, default_title, default_title))
        await db.commit()
    await profile(m, bot)

@dp.message(F.text == "👤 Профиль")
@dp.message(Command("profile"))
async def profile(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
        res = await db.execute("SELECT COUNT(*) FROM cards")
        total = (await res.fetchone())[0]
    
    text = (f"<b>✨ ЛИЧНОЕ ДОСЬЕ ✨</b>\n━━━━━━━━━━━━━━━━━━\n👤 <b>Игрок:</b> {u[0]}\n"
            f"🏅 <b>Ранг:</b> <code>{u[1]}</code>\n🏷 <b>Титул:</b> <i>{u[4]}</i>\n"
            f"💰 <b>Монеты:</b> {u[2]}\n💎 <b>BBC:</b> {u[3]}\n🎴 <b>Коллекция:</b> {inv_cnt} / {total}\n━━━━━━━━━━━━━━━━━━")
    try:
        photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
        if photos.total_count > 0: await m.answer_photo(photos.photos[0][-1].file_id, caption=text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
        else: await m.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
    except: await m.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(F.text.lower().in_(["🃏 получить карту", "карта", "карту"]))
async def draw(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        rank, last_draw, titles = await res.fetchone()
        cd = timedelta(hours=24) if rank != "Мифрил" else timedelta(seconds=10)
        now = datetime.now()
        if last_draw and now < datetime.fromisoformat(last_draw) + cd:
            rem = (datetime.fromisoformat(last_draw) + cd) - now
            return await m.answer(f"⏳ Подожди еще: <code>{str(rem).split('.')[0]}</code>", parse_mode=ParseMode.HTML)
        
        rarity = get_rarity(rank, titles)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer("⚠️ В базе пока нет карт такой редкости!")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        is_dup = await res.fetchone()
        reward = REWARDS[rarity]["dup"] if is_dup else REWARDS[rarity]["new"]
        
        if is_dup:
            await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
            cap = f"♻️ <b>ПОВТОРКА!</b>\n🏷 {c_name}\n✨ {rarity}⭐\n💰 +{reward} монет"
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, c_id))
            cap = f"🎉 <b>НОВАЯ!</b>\n🏷 {c_name}\n✨ {rarity}⭐\n💰 +{reward} монет"
        
        await db.execute("UPDATE users SET money = money + ?, last_draw = ? WHERE user_id = ?", (reward, now.isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap, parse_mode=ParseMode.HTML)

@dp.message(F.text == "🎒 Инвентарь")
async def inventory_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute('''SELECT c.name, c.rarity, i.count FROM inventory i JOIN cards c ON i.card_id = c.card_id 
                                  WHERE i.user_id = ? ORDER BY c.rarity DESC LIMIT 30''', (m.from_user.id,))
        cards = await res.fetchall()
    if not cards: return await m.answer("🎒 Твой инвентарь пуст!")
    text = "🎒 <b>ТВОИ КАРТЫ:</b>\n━━━━━━━━━━━━━━\n" + "\n".join([f"{r}⭐ | {n} (x{c})" for n, r, c in cards])
    await m.answer(text, parse_mode=ParseMode.HTML)
        @dp.message(F.text == "🏆 Топ")
async def top_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎴 Карты", callback_data="top_cards"), InlineKeyboardButton(text="💰 Монеты", callback_data="top_money")],
        [InlineKeyboardButton(text="💎 BBC", callback_data="top_bbc")]
    ])
    await m.answer("🏆 <b>ЛИДЕРЫ:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("top_"))
async def top_cb(c: CallbackQuery):
    cat = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        if cat == "cards": res = await db.execute("SELECT u.nickname, COUNT(i.card_id) as cnt FROM users u JOIN inventory i ON u.user_id=i.user_id GROUP BY u.user_id ORDER BY cnt DESC LIMIT 10")
        elif cat == "money": res = await db.execute("SELECT nickname, money FROM users ORDER BY money DESC LIMIT 10")
        else: res = await db.execute("SELECT nickname, bbc_money FROM users ORDER BY bbc_money DESC LIMIT 10")
        data = await res.fetchall()
    
    text = f"🏆 <b>ТОП {cat.upper()}</b>\n\n" + "\n".join([f"{i+1}. {n} — {v}" for i, (n, v) in enumerate(data)])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="top_main")]])
    try: await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except TelegramBadRequest: await c.answer()

@dp.message(Command("promo"))
async def use_promo(m: Message):
    args = m.text.split()
    if len(args) < 2: return await m.answer("⚠️ Введи: <code>/promo КОД</code>")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT reward_type, reward_val, uses_left, expires_at FROM promocodes WHERE code=?", (args[1],))
        p = await res.fetchone()
        if not p or p[2] <= 0 or datetime.fromisoformat(p[3]) < datetime.now(): return await m.answer("❌ Код недействителен.")
        
        if p[0] == "cash": await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (p[1], m.from_user.id))
        elif p[0] == "bbc": await db.execute("UPDATE users SET bbc_money=bbc_money+? WHERE user_id=?", (p[1], m.from_user.id))
        else: await db.execute("INSERT OR IGNORE INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, p[1]))
        
        await db.execute("UPDATE promocodes SET uses_left=uses_left-1 WHERE code=?", (args[1],))
        await db.commit()
        await m.answer(f"✅ Получено: {p[1]} {p[0]}")

@dp.message(Command("create_promo"))
async def create_promo(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        _, code, r_type, r_val, limit, days = m.text.split()
        exp = (datetime.now() + timedelta(days=int(days))).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO promocodes VALUES (?,?,?,?,?)", (code, r_type, int(r_val), int(limit), exp))
            await db.commit()
        await m.answer(f"✅ Промокод <code>{code}</code> создан!")
    except: await m.answer("❌ Формат: `/create_promo GIFT bbc 100 50 7`")

@dp.message(F.photo)
async def add_card_photo(m: Message):
    if m.from_user.id == ADMIN_ID and m.caption and m.caption.startswith("/add_card"):
        try:
            parts = m.caption.split()
            rarity, name = int(parts[-1]), " ".join(parts[1:-1])
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?, ?, ?)", (name, rarity, m.photo[-1].file_id))
                await db.commit()
            await m.answer(f"✅ Карта <b>{name}</b> добавлена!")
        except: await m.answer("❌ Формат подписи: `/add_card Имя 5`")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass
             
