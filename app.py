import asyncio, logging, random, os, aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA" 
ADMIN_ID = 1548461377 
DB_PATH = "gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# Названия редкостей
RARITY_NAMES = {
    1: "Обычная",
    2: "Редкая",
    3: "Эпическая",
    4: "Легендарная",
    5: "Мифическая"
}

# Награды (n - новая, d - дубликат)
REWARDS = {
    1: {"n": 100, "d": 50}, 
    2: {"n": 150, "d": 75}, 
    3: {"n": 250, "d": 100}, 
    4: {"n": 500, "d": 250}, 
    5: {"n": 1000, "d": 700}
}

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, bbc_money INTEGER DEFAULT 0, last_draw TEXT, 
            titles TEXT DEFAULT 'Новичок', draw_count INTEGER DEFAULT 0, 
            last_daily TEXT, last_work TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, reward_type TEXT, reward_val INTEGER, uses_left INTEGER)''')
        await db.commit()

async def set_commands(bot: Bot):
    cmds = [
        BotCommand(command="start", description="🏠 Регистрация"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="daily", description="📅 Бонус"),
        BotCommand(command="work", description="💼 Работа"),
        BotCommand(command="inventory", description="🎒 Инвентарь"),
        BotCommand(command="top", description="🏆 Лидеры"),
        BotCommand(command="shop", description="🛒 Магазин"),
        BotCommand(command="casino", description="🎰 Казино"),
        BotCommand(command="promo", description="🎁 Промокод")
    ]
    await bot.set_my_commands(cmds)

# --- ОСНОВНАЯ ЛОГИКА ---

@dp.message(Command("start"))
async def start_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        r = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?,?,?)", 
                         (m.from_user.id, m.from_user.first_name, r))
        await db.commit()
    await m.answer("✅ Регистрация прошла успешно! Пиши 'карта' или /draw, чтобы начать.")

@dp.message(Command("profile"))
async def profile_cmd(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles, draw_count FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return await m.answer("Сначала напиши /start")
        
        res = await db.execute("SELECT SUM(count) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0] or 0
    
    text = (f"<b>🪪 ПРОФИЛЬ:</b> {u[0]}\n\n"
            f"🏅 Ранг: {u[1]}\n"
            f"💰 Монеты: {u[2]} | 💎 BBC: {u[3]}\n"
            f"🎴 Карт в коллекции: {inv_cnt}\n"
            f"🔄 До гаранта (5⭐): {50 - u[5]}")

    try:
        photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
        if photos.total_count > 0:
            await m.answer_photo(photos.photos[0][0].file_id, caption=text, parse_mode=ParseMode.HTML)
        else:
            await m.answer(text, parse_mode=ParseMode.HTML)
    except:
        await m.answer(text, parse_mode=ParseMode.HTML)

# --- ГАЧА (ВЫЗОВ СЛОВОМ И КОМАНДОЙ) ---
@dp.message(F.text.lower().in_({"карта", "карту", "/draw"}) | Command("draw"))
async def draw_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, draw_count FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await res.fetchone()
        if not row: return await m.answer("Напиши /start")
        r, ld, dc = row
        
        cd = timedelta(seconds=10) if r == "Мифрил" else (timedelta(hours=10) if r == "VIP" else timedelta(hours=24))
        if ld and datetime.now() < datetime.fromisoformat(ld) + cd:
            wait = (datetime.fromisoformat(ld) + cd) - datetime.now()
            return await m.answer(f"⏳ Рано! Жди {wait.seconds // 3600}ч. {(wait.seconds // 60) % 60}мин.")

        p = random.random()
        if r == "Мифрил": rar = 5 if p < 0.15 else (4 if p < 0.35 else (3 if p < 0.65 else 2))
        elif r == "VIP": rar = 5 if p < 0.04 else (4 if p < 0.12 else (3 if p < 0.35 else 2))
        else: rar = 5 if p < 0.015 else (4 if p < 0.07 else (3 if p < 0.20 else (2 if p < 0.50 else 1)))
        
        if dc >= 49: rar = 5 

        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rar,))
        card = await res.fetchone()
        if not card: return await m.answer(f"⚠️ Ошибка: Карт {rar}⭐ нет в базе. Зови админа!")

        res = await db.execute("SELECT count FROM inventory WHERE user_id=? AND card_id=?", (m.from_user.id, card[0]))
        is_dup = await res.fetchone()
        rew = REWARDS[rar]["d" if is_dup else "n"]
        
        if is_dup: await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id=? AND card_id=?", (m.from_user.id, card[0]))
        else: await db.execute("INSERT INTO inventory VALUES (?,?,1)", (m.from_user.id, card[0]))

        await db.execute("UPDATE users SET money=money+?, last_draw=?, draw_count=? WHERE user_id=?", 
                         (rew, datetime.now().isoformat(), 0 if rar == 5 else dc+1, m.from_user.id))
        await db.commit()

        stars_str = "⭐" * rar
        rar_name = RARITY_NAMES.get(rar, "Неизвестно")
        cap = (f"🃏 <b>{card[1]}</b>\n\n"
               f"Ранг: {stars_str} ({rar_name})\n"
               f"{'♻️ Дубликат!' if is_dup else '✨ Новая карта!'}\n"
               f"💰 +{rew} монет")
        await m.answer_photo(card[2], caption=cap, parse_mode=ParseMode.HTML)

# --- ЭКОНОМИКА ---

@dp.message(Command("daily"))
async def daily_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (m.from_user.id,))
        ld = (await res.fetchone())[0]
        if ld and datetime.now() < datetime.fromisoformat(ld) + timedelta(days=1):
            return await m.answer("📅 Бонус можно брать раз в 24 часа!")
        
        reward = random.randint(200, 500)
        await db.execute("UPDATE users SET money=money+?, last_daily=? WHERE user_id=?", (reward, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
        await m.answer(f"🎁 Ежедневная награда: {reward} монет!")

@dp.message(Command("work"))
async def work_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT last_work FROM users WHERE user_id = ?", (m.from_user.id,))
        lw = (await res.fetchone())[0]
        if lw and datetime.now() < datetime.fromisoformat(lw) + timedelta(hours=1):
            return await m.answer("💼 Ты устал. Отдохни часик.")
        
        reward = random.randint(50, 150)
        await db.execute("UPDATE users SET money=money+?, last_work=? WHERE user_id=?", (reward, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
        await m.answer(f"⚒ Ты поработал и получил {reward} монет!")

@dp.message(Command("inventory"))
async def inventory_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("""SELECT c.name, c.rarity, i.count FROM inventory i 
                               JOIN cards c ON i.card_id = c.card_id WHERE i.user_id = ? 
                               ORDER BY c.rarity DESC""", (m.from_user.id,))
        cards = await res.fetchall()
    
    if not cards: return await m.answer("🎒 Твой рюкзак пуст.")
    
    msg = "🎒 <b>ТВОИ КАРТЫ:</b>\n\n"
    for name, rar, count in cards[:30]:
        msg += f"{'⭐'*rar} {name} (x{count})\n"
    await m.answer(msg, parse_mode=ParseMode.HTML)

# --- ОСТАЛЬНОЕ ---

@dp.message(Command("casino"))
async def casino_cmd(m: Message):
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎰 Формат: /casino 100")
    bet = int(args[1])
    
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money FROM users WHERE user_id = ?", (m.from_user.id,))
        money = (await res.fetchone())[0]
        if money < bet: return await m.answer("❌ Недостаточно монет!")
        
        if random.randint(1, 100) <= 30:
            mult = 2 if random.random() > 0.1 else 5
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bet * (mult-1), m.from_user.id))
            txt = f"✅ Победа! Множитель x{mult}. Выигрыш: {bet*mult}"
        else:
            await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (bet, m.from_user.id))
            txt = f"💀 Проигрыш. Минус {bet} монет."
        await db.commit()
    await m.answer(f"🎰 {txt}")

@dp.message(Command("top"))
async def top_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 Монеты", callback_data="top_m"),
        InlineKeyboardButton(text="💎 BBC", callback_data="top_b")
    ]])
    await m.answer("🏆 Выберите таблицу лидеров:", reply_markup=kb)

@dp.callback_query(F.data.startswith("top_"))
async def top_cb(c: CallbackQuery):
    col = "money" if c.data == "top_m" else "bbc_money"
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(f"SELECT nickname, {col} FROM users ORDER BY {col} DESC LIMIT 10")
        users = await res.fetchall()
    text = "🏆 <b>ТОП 10:</b>\n\n" + "\n".join([f"{i+1}. {u[0]} — {u[1]}" for i, u in enumerate(users)])
    await c.message.edit_text(text, parse_mode=ParseMode.HTML)

@dp.message(F.photo & F.caption.startswith("/add_card"))
async def add_card(m: Message):
    if m.from_user.id != ADMIN_ID: return
    p = m.caption.split()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)", 
                         (" ".join(p[1:-1]), int(p[-1]), m.photo[-1].file_id))
        await db.commit()
    await m.answer("✅ Карта добавлена!")

@dp.message(Command("promo"))
async def promo_cmd(m: Message):
    args = m.text.split()
    if len(args) < 2: return await m.answer("🎁 /promo КОД")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?", (args[1],))
        p = await res.fetchone()
        if not p or p[2] <= 0: return await m.answer("❌ Код не найден.")
        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (p[1], m.from_user.id))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (args[1],))
        await db.commit()
    await m.answer(f"✅ +{p[1]} {p[0]}!")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
