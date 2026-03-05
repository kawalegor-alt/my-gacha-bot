import asyncio
import logging
import random
import os
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from aiogram.enums import ParseMode

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
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

# --- МЕНЮ КОМАНД ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню / Профиль"),
        BotCommand(command="profile", description="👤 Мой профиль"),
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
            money INTEGER DEFAULT 0, last_draw TEXT, titles TEXT DEFAULT 'Новичок')''')
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
async def start(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?, ?, ?)", 
                         (m.from_user.id, m.from_user.first_name, user_rank))
        await db.commit()
    await profile(m, bot)

@dp.message(F.text == "👤 Профиль")
@dp.message(Command("profile"))
async def profile(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
        res = await db.execute("SELECT COUNT(*) FROM cards")
        total = (await res.fetchone())[0]
    
    profile_text = (
        f"<b>✨ ЛИЧНОЕ ДОСЬЕ ✨</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Игрок:</b> {u[0]}\n"
        f"🏅 <b>Ранг:</b> <code>{u[1]}</code>\n"
        f"🏷 <b>Титул:</b> <i>{u[3]}</i>\n"
        f"💰 <b>Валюта:</b> {u[2]} монеток\n"
        f"🎴 <b>Коллекция:</b> {inv_cnt} / {total}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Собери их все!</i>"
    )

    try:
        photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
        if photos.total_count > 0:
            await m.answer_photo(photos.photos[0][-1].file_id, caption=profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
        else:
            await m.answer(profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
    except:
        await m.answer(profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(F.text.lower().in_(["🃏 получить карту", "карта", "карту", "нев", "невер"]))
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
            return await m.answer(f"⏳ <b>Отдых!</b>\nПодожди ещё: <code>{str(rem).split('.')[0]}</code>", parse_mode=ParseMode.HTML)
        
        rarity = get_rarity(rank)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer("⚠️ База карт пуста!")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        
        if await res.fetchone():
            bonus = rarity * 20
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bonus, m.from_user.id))
            cap = f"🃏 <b>Повторка:</b> {c_name}\n💎 Редкость: {rarity}⭐\n💰 <b>Компенсация:</b> +{bonus} монет"
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, c_id))
            cap = f"🎉 <b>НОВАЯ КАРТА!</b>\n┃ 🏷 <b>Название:</b> {c_name}\n┃ ✨ <b>Редкость:</b> {rarity}⭐"
        
        await db.execute("UPDATE users SET last_draw = ? WHERE user_id = ?", (now.isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap, parse_mode=ParseMode.HTML)

@dp.message(F.text == "❓ Помощь")
@dp.message(Command("help"))
async def help_cmd(m: Message):
    help_text = (
        "📖 <b>ИНСТРУКЦИЯ</b>\n\n"
        "Нажимай кнопку <b>'Получить карту'</b> раз в сутки.\n"
        "Собирай редких персонажей и копи монеты!\n\n"
        "📌 <i>Все команды — в меню '/'</i>"
    )
    await m.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message(Command("adminhelp"))
async def admin_help(m: Message):
    if m.from_user.id != ADMIN_ID: return
    admin_text = (
        "🛠 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "<b>Добавить карту:</b> Отправь фото с подписью:\n"
        "<code>/add_card Название Редкость</code>\n"
        "<i>Например: /add_card Дракон 5</i>"
    )
    await m.answer(admin_text, parse_mode=ParseMode.HTML)

@dp.message(F.photo)
async def add_card_photo(m: Message):
    if m.from_user.id != ADMIN_ID or not m.caption or not m.caption.startswith("/add_card"): return
    try:
        args = m.caption.split()
        rarity = int(args[-1])
        name = " ".join(args[1:-1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?, ?, ?)", (name, rarity, m.photo[-1].file_id))
            await db.commit()
        await m.answer(f"✅ Карта <b>{name}</b> добавлена!", parse_mode=ParseMode.HTML)
    except:
        await m.answer("❌ Ошибка! Формат: <code>/add_card Имя 5</code>")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
        
