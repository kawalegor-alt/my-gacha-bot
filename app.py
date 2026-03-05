import asyncio, logging, random, os, aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ParseMode

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 1548461377 
DB_PATH = "/app/data/gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

async def set_commands(bot: Bot):
    cmds = [
        BotCommand(command="start", description="🏠 Старт"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="draw", description="🃏 Получить карту"),
        BotCommand(command="inventory", description="🎒 Инвентарь"),
        BotCommand(command="top", description="🏆 Топ"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="promo", description="🎁 Промокод"),
        BotCommand(command="adminhelp", description="🛠 Админ-панель")
    ]
    await bot.set_my_commands(cmds)

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, bbc_money INTEGER DEFAULT 0, last_draw TEXT, 
            titles TEXT DEFAULT 'Новичок', unlocked_titles TEXT DEFAULT 'Новичок')''')
        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, reward_type TEXT, reward_val INTEGER, uses_left INTEGER, expires_at TEXT)''')
        await db.commit()

def get_rarity(rank, titles):
    r = random.uniform(0, 100)
    bonus = 2 if titles and "главный кисер" in titles else 0
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

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        title = "главный кисер" if m.from_user.id == ADMIN_ID else "Новичок"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank, titles, unlocked_titles) VALUES (?,?,?,?,?)", 
                         (m.from_user.id, m.from_user.first_name, rank, title, title))
        await db.commit()
    await m.answer("✅ Готово! Пиши 'карта' или используй меню.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("profile") | F.text.lower().contains("профиль"))
async def profile_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return await m.answer("Напиши /start")
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
    await m.answer(f"<b>👤 Игрок:</b> {u[0]}\n🏅 <b>Ранг:</b> {u[1]}\n🏷 <b>Титул:</b> {u[4]}\n💰 <b>Монеты:</b> {u[2]}\n💎 <b>BBC:</b> {u[3]}\n🎴 <b>Карт:</b> {inv_cnt}", parse_mode=ParseMode.HTML)

@dp.message(Command("draw") | F.text.lower().contains("карт"))
async def draw_card(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await res.fetchone()
        
        if not row:
            rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
            title = "главный кисер" if m.from_user.id == ADMIN_ID else "Новичок"
            await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank, titles, unlocked_titles) VALUES (?,?,?,?,?)", 
                             (m.from_user.id, m.from_user.first_name, rank, title, title))
            await db.commit()
            res = await db.execute("SELECT rank, last_draw, titles FROM users WHERE user_id = ?", (m.from_user.id,))
            row = await res.fetchone()

        rank, last_draw, titles = row
        cd = timedelta(seconds=10) if rank == "Мифрил" else timedelta(hours=24)
        if last_draw and datetime.now() < datetime.fromisoformat(last_draw) + cd:
            return await m.answer("⏳ Еще не время!")
        
        rarity = get_rarity(rank, titles)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer(f"⚠️ Нет карт {rarity}⭐. Добавь через /add_card")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        is_dup = await res.fetchone()
        rew = REWARDS[rarity]["d"] if is_dup else REWARDS[rarity]["n"]
        
        if is_dup:
            await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
            cap = f"♻️ ПОВТОРКА: {c_name} ({rarity}⭐)\n💰 +{rew}"
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,1)", (m.from_user.id, c_id))
            cap = f"🎉 НОВАЯ: {c_name} ({rarity}⭐)\n💰 +{rew}"
        
        await db.execute("UPDATE users SET money=money+?, last_draw=? WHERE user_id=?", (rew, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap)

@dp.message(Command("inventory") | F.text.lower().contains("инвент"))
async def inv_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT c.name, c.rarity, i.count FROM inventory i JOIN cards c ON i.card_id=c.card_id WHERE i.user_id=?", (m.from_user.id,))
        cards = await res.fetchall()
    if not cards: return await m.answer("Пусто!")
    await m.answer("🎒 КАРТЫ:\n" + "\n".join([f"{r}⭐ {n} x{c}" for n,r,c in cards]))

@dp.message(Command("top") | F.text.lower().contains("топ"))
async def top_menu(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 Монеты", callback_data="top_money"),
        InlineKeyboardButton(text="💎 BBC", callback_data="top_bbc")
    ]])
    await m.answer("🏆 Лидеры:", reply_markup=kb)

@dp.callback_query(F.data.startswith("top_"))
async def top_callback(c: CallbackQuery):
    cat = c.data.split("_")[1]
    col = "money" if cat == "money" else "bbc_money"
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(f"SELECT nickname, {col} FROM users ORDER BY {col} DESC LIMIT 10")
        data = await res.fetchall()
    text = f"🏆 ТОП {cat.upper()}:\n" + "\n".join([f"{i+1}. {n} — {v}" for i,(n,v) in enumerate(data)])
    try: await c.message.edit_text(text, parse_mode=ParseMode.HTML)
    except: await c.answer()

@dp.message(Command("adminhelp"))
async def admin_help_cmd(m: Message):
    if m.from_user.id == ADMIN_ID:
        await m.answer("🛠 <b>АДМИН</b>\n/id_cards — ID карт\n/add_card Имя Редкость (под фото)\n/create_promo Код Тип Сумма Лимит Дни", parse_mode=ParseMode.HTML)

@dp.message(Command("id_cards"))
async def list_ids(m: Message):
    if m.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT card_id, name, rarity FROM cards")
        cards = await res.fetchall()
    await m.answer("🆔 ID КАРТ:\n" + "\n".join([f"<code>{c[0]}</code> | {c[1]} ({c[2]}⭐)" for c in cards]), parse_mode=ParseMode.HTML)

@dp.message(F.photo & F.caption.startswith("/add_card"))
async def admin_add_card(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        p = m.caption.split()
        rarity, name = int(p[-1]), " ".join(p[1:-1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)", (name, rarity, m.photo[-1].file_id))
            await db.commit()
        await m.answer(f"✅ Добавлена: {name}")
    except: await m.answer("❌ Формат: /add_card Имя 5")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
