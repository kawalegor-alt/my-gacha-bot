import asyncio, logging, random, os, aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- КОНФИГУРАЦИЯ ---
# ВАЖНО: Никогда не свети свой токен в открытом доступе. Лучше убери его в .env файл!
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

# Состояния для админки
class AdminStates(StatesGroup):
    waiting_for_promo_data = State()

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

# --- ГАЧА ---
@dp.message(F.text.lower().in_({"карта", "карту", "/draw"}))
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
        # --- ЭКОНОМИКА И МАГАЗИН ---

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

@dp.message(Command("shop"))
async def shop_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Сбросить КД на Гачу — 1500 💰", callback_data="shop_reset_cd")],
        [InlineKeyboardButton(text="💎 Купить 1 BBC — 5000 💰", callback_data="shop_buy_bbc")]
    ])
    await m.answer("🛒 <b>МАГАЗИН</b>\nПотрать свои монеты с умом:", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("shop_"))
async def shop_cb(c: CallbackQuery):
    action = c.data.split("_")[1:]
    
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money FROM users WHERE user_id = ?", (c.from_user.id,))
        user_money = (await res.fetchone())[0]

        if action[0] == "reset" and action[1] == "cd":
            if user_money < 1500:
                return await c.answer("❌ Недостаточно монет (Нужно 1500)", show_alert=True)
            # Устанавливаем старую дату, чтобы сбросить кулдаун
            past_date = (datetime.now() - timedelta(days=2)).isoformat()
            await db.execute("UPDATE users SET money = money - 1500, last_draw = ? WHERE user_id = ?", (past_date, c.from_user.id))
            await db.commit()
            await c.message.edit_text("✅ Ты успешно сбросил кулдаун на гачу! Можешь тянуть карту.")
            
        elif action[0] == "buy" and action[1] == "bbc":
            if user_money < 5000:
                return await c.answer("❌ Недостаточно монет (Нужно 5000)", show_alert=True)
            await db.execute("UPDATE users SET money = money - 5000, bbc_money = bbc_money + 1 WHERE user_id = ?", (c.from_user.id,))
            await db.commit()
            await c.message.edit_text("💎 Поздравляю! Ты купил 1 BBC.")
            
    await c.answer()

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

# --- ИГРЫ И ТОП ---

@dp.message(Command("casino"))
async def casino_cmd(m: Message):
    text = m.text or m.caption or ""
    args = text.split()
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
    await c.answer()

# --- АДМИН ПАНЕЛЬ И ПРОМОКОДЫ ---

@dp.message(Command("admin"))
async def admin_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")]
    ])
    await m.answer("👑 <b>Админ-панель</b>\nВыбери действие:", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_PATH) as db:
        users_count = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        cards_count = (await (await db.execute("SELECT COUNT(*) FROM cards")).fetchone())[0]
    await c.message.edit_text(f"📊 <b>Статистика:</b>\n👥 Игроков: {users_count}\n🃏 Карт в базе: {cards_count}", parse_mode=ParseMode.HTML)
    await c.answer()

@dp.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    await c.message.answer(
        "Введите данные промокода через пробел:\n"
        "<code>[Название] [Тип: money/bbc_money] [Сумма] [Кол-во активаций]</code>\n\n"
        "Пример: <code>NEWYEAR money 1000 50</code>", 
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_for_promo_data)
    await c.answer()

@dp.message(AdminStates.waiting_for_promo_data)
async def process_promo_data(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split()
    if len(args) != 4 or args[1] not in ["money", "bbc_money"] or not args[2].isdigit() or not args[3].isdigit():
        await state.clear()
        return await m.answer("❌ Ошибка формата. Попробуй снова через /admin.")
    
    code, rew_type, rew_val, uses = args[0], args[1], int(args[2]), int(args[3])
    
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO promocodes (code, reward_type, reward_val, uses_left) VALUES (?,?,?,?)", 
                             (code, rew_type, rew_val, uses))
            await db.commit()
            await m.answer(f"✅ Промокод <code>{code}</code> успешно создан!", parse_mode=ParseMode.HTML)
        except aiosqlite.IntegrityError:
            await m.answer("❌ Такой промокод уже существует!")
            
    await state.clear()

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
    text = m.text or m.caption or ""
    args = text.split()
    if len(args) < 2: return await m.answer("🎁 /promo КОД")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?", (args[1],))
        p = await res.fetchone()
        if not p or p[2] <= 0: return await m.answer("❌ Код не найден или закончились активации.")
        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (p[1], m.from_user.id))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (args[1],))
        await db.commit()
    
    val_name = "Монет" if p[0] == "money" else "BBC"
    await m.answer(f"✅ Промокод активирован! Начислено: {p[1]} {val_name}")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
