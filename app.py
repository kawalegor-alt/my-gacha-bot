import asyncio, logging, random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import aiosqlite

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

REWARDS = {
    1: {"n": 100, "d": 50}, 
    2: {"n": 150, "d": 75}, 
    3: {"n": 250, "d": 100}, 
    4: {"n": 500, "d": 250}, 
    5: {"n": 1000, "d": 700}
}

def is_private(m: Message):
    return m.chat and m.chat.type == "private"

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
        BotCommand(command="draw", description="🃏 Крутить гачу (или пиши 'карта')"),
        BotCommand(command="daily", description="📅 Ежедневный бонус"),
        BotCommand(command="work", description="💼 Работа"),
        BotCommand(command="shop", description="🛒 Магазин"),
        BotCommand(command="casino", description="🎰 Казино"),
        BotCommand(command="inventory", description="🎒 Рюкзак"),
        BotCommand(command="top", description="🏆 Лидеры"),
        BotCommand(command="promo", description="🎁 Промокод")
    ]
    await bot.set_my_commands(cmds)

# --- БАЗОВЫЕ КОМАНДЫ ---
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
async def profile_cmd(m: Message, bot: Bot):
    if not is_private(m): return await m.answer("👤 Твой профиль доступен только в ЛС.")
    
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles, draw_count FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return await m.answer("❌ Ты не зарегистрирован! Напиши /start")
        
        res = await db.execute("SELECT sum(count) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0] or 0
    
    text = (f"<b>🪪 ПРОФИЛЬ:</b> {u[0]}\n\n"
            f"🏅 <b>Ранг:</b> {u[1]}\n"
            f"💰 <b>Монеты:</b> {u[2]}\n"
            f"💎 <b>BBC:</b> {u[3]}\n\n"
            f"🎴 <b>Карт в коллекции:</b> {inv_cnt}\n"
            f"🔄 <b>До гаранта (5⭐):</b> {50 - u[5]}")

    photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
    if photos.total_count > 0:
        await m.answer_photo(photos.photos[0][0].file_id, caption=text, parse_mode=ParseMode.HTML)
    else:
        await m.answer(text, parse_mode=ParseMode.HTML)

# --- ГАЧА МЕХАНИКА ---
@dp.message(F.text.lower().in_({"карта", "карту", "/draw"}))
async def draw_cmd(m: Message):
    if not is_private(m): return
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, draw_count FROM users WHERE user_id = ?", (m.from_user.id,))
        user_data = await res.fetchone()
        if not user_data: return await m.answer("Напиши /start для регистрации!")
        r, ld, dc = user_data
        
        cd = timedelta(seconds=10) if r == "Мифрил" else (timedelta(hours=10) if r == "VIP" else timedelta(hours=24))
        if ld and datetime.now() < datetime.fromisoformat(ld) + cd:
            wait = (datetime.fromisoformat(ld) + cd) - datetime.now()
            hours, remainder = divmod(wait.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return await m.answer(f"⏳ Гача заряжается... Жди еще {hours}ч. {minutes}мин.")

        p = random.random()
        if r == "Мифрил": rar = 5 if p < 0.15 else (4 if p < 0.35 else (3 if p < 0.65 else 2))
        elif r == "VIP": rar = 5 if p < 0.03 else (4 if p < 0.10 else (3 if p < 0.30 else 2))
        else: rar = 5 if p < 0.01 else (4 if p < 0.05 else (3 if p < 0.15 else 1)) 
        
        if dc >= 49: rar = 5 

        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rar,))
        card = await res.fetchone()
        if not card: return await m.answer(f"⚠️ В базе еще нет карт редкости {rar}⭐! Добавь их через админку.")

        res = await db.execute("SELECT count FROM inventory WHERE user_id=? AND card_id=?", (m.from_user.id, card[0]))
        is_dup = await res.fetchone()
        rew = REWARDS[rar]["d" if is_dup else "n"]
        
        if is_dup: 
            await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id=? AND card_id=?", (m.from_user.id, card[0]))
        else: 
            await db.execute("INSERT INTO inventory VALUES (?,?,1)", (m.from_user.id, card[0]))

        await db.execute("UPDATE users SET money=money+?, last_draw=?, draw_count=? WHERE user_id=?", 
                         (rew, datetime.now().isoformat(), 0 if rar == 5 else dc+1, m.from_user.id))
        await db.commit()
        
        stars = "⭐" * rar
        rarity_name = RARITY_NAMES.get(rar, "Неизвестная")
        dup_text = " (Дубликат)" if is_dup else " (Новая карта!)"
        
        caption = (f"🃏 <b>{card[1]}</b>\n\n"
                   f"{stars} <b>{rarity_name}</b>{dup_text}\n\n"
                   f"💰 Бонус: +{rew} монет")
        
        await m.answer_photo(card[2], caption=caption, parse_mode=ParseMode.HTML)

# --- ЭКОНОМИКА (РАБОТА И ДЕЙЛИК) ---
@dp.message(Command("daily"))
async def daily_cmd(m: Message):
    if not is_private(m): return
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        
        ld = u[0]
        if ld and datetime.now() < datetime.fromisoformat(ld) + timedelta(days=1):
            wait = (datetime.fromisoformat(ld) + timedelta(days=1)) - datetime.now()
            hours, remainder = divmod(wait.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return await m.answer(f"⏳ Следующий бонус через {hours}ч. {minutes}мин.")
            
        reward = random.randint(300, 800)
        await db.execute("UPDATE users SET money = money + ?, last_daily = ? WHERE user_id = ?", 
                         (reward, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
    await m.answer(f"📅 Ты забрал ежедневный бонус!\n💰 +{reward} монет.")

@dp.message(Command("work"))
async def work_cmd(m: Message):
    if not is_private(m): return
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT last_work FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        
        lw = u[0]
        if lw and datetime.now() < datetime.fromisoformat(lw) + timedelta(hours=2):
            wait = (datetime.fromisoformat(lw) + timedelta(hours=2)) - datetime.now()
            minutes, _ = divmod(wait.seconds, 60)
            return await m.answer(f"⏳ Ты слишком устал. Отдохни еще {minutes} минут.")
            
        reward = random.randint(50, 200)
        await db.execute("UPDATE users SET money = money + ?, last_work = ? WHERE user_id = ?", 
                         (reward, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
    await m.answer(f"💼 Ты усердно поработал и заработал {reward} монет 💰")

# --- ИНВЕНТАРЬ ---
@dp.message(Command("inventory"))
async def inventory_cmd(m: Message):
    if not is_private(m): return
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("""
            SELECT c.name, c.rarity, i.count 
            FROM inventory i 
            JOIN cards c ON i.card_id = c.card_id 
            WHERE i.user_id = ? 
            ORDER BY c.rarity DESC, c.name ASC
        """, (m.from_user.id,))
        cards = await res.fetchall()
        
    if not cards:
        return await m.answer("🎒 Твой рюкзак пока пуст. Крути гачу!")
        
    text = "🎒 <b>ТВОЙ ИНВЕНТАРЬ:</b>\n\n"
    for c in cards[:50]: 
        text += f"{'⭐'*c[1]} {c[0]} — {c[2]} шт.\n"
        
    if len(cards) > 50:
        text += f"\n<i>...и еще {len(cards) - 50} видов карт.</i>"
        
    await m.answer(text, parse_mode=ParseMode.HTML)

# --- КАЗИНО 70/30 ---
@dp.message(Command("casino"))
async def casino_cmd(m: Message):
    if not is_private(m): return await m.answer("🎰 Казино доступно только в ЛС!")
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎰 Формат: /casino 100")
    bet = int(args[1])
    if bet <= 0: return await m.answer("❌ Ставка должна быть больше нуля!")
    
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

@dp.callback_query(F.data.in_({"buy_vip", "buy_ex"}))
async def shop_stub_cb(c: CallbackQuery):
    await c.answer("🛠 Функция в разработке!", show_alert=True)

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
    
    text = f"🏆 <b>ТОП 10 ({'Монеты' if col == 'money' else 'BBC'}):</b>\n\n" 
    text += "\n".join([f"{i+1}. {u[0]} — {u[1]}" for i, u in enumerate(users)])
    
    await c.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=c.message.reply_markup)
    await c.answer() 

# --- ПРОМОКОДЫ ---
@dp.message(Command("promo"))
async def promo_cmd(m: Message):
    if not is_private(m): return
    args = m.text.split()
    if len(args) < 2: return await m.answer("🎁 Формат: /promo КОД")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?", (args[1],))
        p = await res.fetchone()
        if not p or p[2] <= 0: return await m.answer("❌ Код неверный или закончился.")
        
        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (p[1], m.from_user.id))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (args[1],))
        await db.commit()
    await m.answer(f"✅ Активировано! +{p[1]} {'монет' if p[0] == 'money' else 'BBC'}")

# --- АДМИНКА ---
@dp.message(F.photo & F.caption.startswith("/add_card"))
async def add_card(m: Message):
    if m.from_user.id != ADMIN_ID: return
    p = m.caption.split()
    if len(p) < 3: return await m.answer("⚠️ Формат: /add_card Название Редкость(1-5)")
    
    try:
        rarity = int(p[-1])
        name = " ".join(p[1:-1])
    except ValueError:
        return await m.answer("⚠️ Ошибка. Редкость должна быть числом от 1 до 5.")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)", 
                         (name, rarity, m.photo[-1].file_id))
        await db.commit()
    await m.answer(f"✅ Карта '{name}' ({rarity}⭐) добавлена!")

@dp.message(Command("create_promo"))
async def create_promo(m: Message):
    if m.from_user.id != ADMIN_ID: return
    p = m.text.split() 
    if len(p) < 5: return await m.answer("⚠️ Формат: /create_promo КОД money/bbc 1000 50")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO promocodes VALUES (?,?,?,?)", 
                         (p[1], p[2], int(p[3]), int(p[4])))
        await db.commit()
    await m.answer(f"✅ Промокод {p[1]} на {p[3]} {p[2]} (Лимит: {p[4]}) создан!")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
        
