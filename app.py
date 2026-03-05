import asyncio, logging, random, os, aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ParseMode

# --- КОНФИГУРАЦИЯ ---
TOKEN = "ТВОЙ_ТОКЕН" 
ADMIN_ID = 1548461377 
DB_PATH = "gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

def is_private(m: Message):
    return m.chat.type == "private"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица юзеров
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, bbc_money INTEGER DEFAULT 0, last_draw TEXT, 
            titles TEXT DEFAULT 'Новичок', draw_count INTEGER DEFAULT 0, 
            last_daily TEXT, last_work TEXT)''')
        # Таблица карт
        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        # Таблица инвентаря
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        # Таблица промокодов
        await db.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, reward_type TEXT, reward_val INTEGER, uses_left INTEGER)''')
        await db.commit()

# Команды меню
async def set_commands(bot: Bot):
    cmds = [
        BotCommand(command="start", description="🏠 Регистрация"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="draw", description="🃏 Крутить гачу"),
        BotCommand(command="daily", description="📅 Бонус"),
        BotCommand(command="work", description="💼 Работа"),
        BotCommand(command="shop", description="🛒 Магазин"),
        BotCommand(command="casino", description="🎰 Казино"),
        BotCommand(command="inventory", description="🎒 Рюкзак"),
        BotCommand(command="top", description="🏆 Лидеры"),
        BotCommand(command="promo", description="🎁 Промокод")
    ]
    await bot.set_my_commands(cmds)

@dp.message(Command("start"))
async def start_cmd(m: Message):
    if not is_private(m): return await m.answer("🤖 Регистрация только в ЛС бота!")
    async with aiosqlite.connect(DB_PATH) as db:
        r = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?,?,?)", 
                         (m.from_user.id, m.from_user.first_name, r))
        await db.commit()
    await m.answer("✅ Ты успешно зарегистрирован! Напиши /help, чтобы увидеть все возможности.")

@dp.message(Command("profile"))
async def profile_cmd(m: Message):
    if not is_private(m): return await m.answer("👤 Твой профиль доступен только в ЛС.")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles, draw_count FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
    
    text = (f"<b>🪪 ПРОФИЛЬ:</b> {u[0]}\n"
            f"🏅 Ранг: {u[1]}\n"
            f"💰 Монеты: {u[2]} | 💎 BBC: {u[3]}\n"
            f"🎴 Карт в коллекции: {inv_cnt}\n"
            f"🔄 До гаранта (5⭐): {50 - u[5]}")
    await m.answer(text, parse_mode=ParseMode.HTML)
    REWARDS = {1:{"n":100,"d":50}, 2:{"n":150,"d":75}, 3:{"n":250,"d":100}, 4:{"n":500,"d":250}, 5:{"n":1000,"d":700}}

# --- ГАЧА МЕХАНИКА ---
@dp.message(Command("draw"))
async def draw_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, draw_count FROM users WHERE user_id = ?", (m.from_user.id,))
        r, ld, dc = await res.fetchone()
        
        # Кулдауны
        cd = timedelta(seconds=10) if r == "Мифрил" else (timedelta(hours=10) if r == "VIP" else timedelta(hours=24))
        if ld and datetime.now() < datetime.fromisoformat(ld) + cd:
            wait = (datetime.fromisoformat(ld) + cd) - datetime.now()
            return await m.answer(f"⏳ Жди еще {wait.seconds // 3600}ч. {(wait.seconds // 60) % 60}мин.")

        # Шансы
        p = random.random()
        if r == "Мифрил": rar = 5 if p < 0.15 else (4 if p < 0.35 else (3 if p < 0.65 else 2))
        elif r == "VIP": rar = 5 if p < 0.03 else (4 if p < 0.10 else (3 if p < 0.30 else 2))
        else: rar = 5 if p < 0.01 else (4 if p < 0.05 else (3 if p < 0.15 else 2))
        
        if dc >= 49: rar = 5 # Гарант

        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rar,))
        card = await res.fetchone()
        if not card: return await m.answer("⚠️ В базе еще нет карт такой редкости!")

        res = await db.execute("SELECT count FROM inventory WHERE user_id=? AND card_id=?", (m.from_user.id, card[0]))
        is_dup = await res.fetchone()
        rew = REWARDS[rar]["d" if is_dup else "n"]
        
        if is_dup: await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id=? AND card_id=?", (m.from_user.id, card[0]))
        else: await db.execute("INSERT INTO inventory VALUES (?,?,1)", (m.from_user.id, card[0]))

        await db.execute("UPDATE users SET money=money+?, last_draw=?, draw_count=? WHERE user_id=?", 
                         (rew, datetime.now().isoformat(), 0 if rar == 5 else dc+1, m.from_user.id))
        await db.commit()
        await m.answer_photo(card[2], caption=f"🃏 {card[1]} ({rar}⭐)\n💰 +{rew} монет")

# --- КАЗИНО 70/30 ---
@dp.message(Command("casino"))
async def casino_cmd(m: Message):
    if not is_private(m): return await m.answer("🎰 Казино доступно только в ЛС!")
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎰 Формат: /casino 100")
    bet = int(args[1])
    
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money FROM users WHERE user_id = ?", (m.from_user.id,))
        money = (await res.fetchone())[0]
        if money < bet: return await m.answer("❌ Недостаточно монет!")
        
        roll = random.randint(1, 100)
        if roll <= 5: win, mult, txt = True, 5, "ДЖЕКПОТ! 🔥"
        elif roll <= 30: win, mult, txt = True, 2, "Победа! ✅"
        else: win, mult, txt = False, 0, "Проигрыш... 💀"
        
        change = (bet * (mult - 1)) if win else -bet
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (change, m.from_user.id))
        await db.commit()
    await m.answer(f"🎰 {txt}\n{'Выигрыш' if win else 'Потеряно'}: {bet*mult if win else bet} 💰")

# --- МАГАЗИН И ТОП ---
@dp.message(Command("shop"))
async def shop_cmd(m: Message):
    if not is_private(m): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎖 VIP (100 💎)", callback_data="buy_vip")],
        [InlineKeyboardButton(text="🔄 10,000💰 -> 10 💎", callback_data="buy_ex")]
    ])
    await m.answer("🛒 <b>МАГАЗИН</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.message(Command("top"))
async def top_cmd(m: Message):
    if not is_private(m): return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 По монетам", callback_data="top_m"),
        InlineKeyboardButton(text="💎 По BBC", callback_data="top_b")
    ]])
    await m.answer("🏆 <b>ТАБЛИЦА ЛИДЕРОВ:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("top_"))
async def top_cb(c: CallbackQuery):
    col = "money" if c.data == "top_m" else "bbc_money"
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(f"SELECT nickname, {col} FROM users ORDER BY {col} DESC LIMIT 10")
        users = await res.fetchall()
    text = "🏆 <b>ТОП 10:</b>\n\n" + "\n".join([f"{i+1}. {u[0]} — {u[1]}" for i, u in enumerate(users)])
    await c.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=c.message.reply_markup)

# --- ПРОМОКОДЫ ---
@dp.message(Command("promo"))
async def promo_cmd(m: Message):
    if not is_private(m): return
    args = m.text.split()
    if len(args) < 2: return await m.answer("🎁 Введи: /promo КОД")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?", (args[1],))
        p = await res.fetchone()
        if not p or p[2] <= 0: return await m.answer("❌ Код неверный или закончился.")
        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (p[1], m.from_user.id))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (args[1],))
        await db.commit()
    await m.answer(f"✅ Активировано! +{p[1]} {p[0]}")

# --- АДМИНКА ---
@dp.message(F.photo & F.caption.startswith("/add_card"))
async def add_card(m: Message):
    if m.from_user.id != ADMIN_ID: return
    p = m.caption.split()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)", (" ".join(p[1:-1]), int(p[-1]), m.photo[-1].file_id))
        await db.commit()
    await m.answer("✅ Карта добавлена!")

@dp.message(Command("create_promo"))
async def create_promo(m: Message):
    if m.from_user.id != ADMIN_ID: return
    p = m.text.split() # /create_promo CODE money 1000 50
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO promocodes VALUES (?,?,?,?)", (p[1], p[2], int(p[3]), int(p[4])))
        await db.commit()
    await m.answer("✅ Промокод создан!")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
