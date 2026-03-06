import asyncio, logging, random, os, aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA" 
ADMIN_ID = 1548461377 
DB_PATH = "gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# Названия редкостей
RARITY_NAMES = {1: "Обычная", 2: "Редкая", 3: "Эпическая", 4: "Легендарная", 5: "Мифическая"}

# Награды (n - новая, d - дубликат)
REWARDS = {
    1: {"n": 100, "d": 50}, 2: {"n": 150, "d": 75}, 
    3: {"n": 250, "d": 100}, 4: {"n": 500, "d": 250}, 5: {"n": 1000, "d": 700}
}

# Состояния
class BotStates(StatesGroup):
    waiting_for_promo_data = State()
    waiting_for_give_money = State()
    waiting_for_give_bbc = State()
    waiting_for_rename = State()
    waiting_for_custom_title = State()

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
        await db.execute('''CREATE TABLE IF NOT EXISTS used_promos (
            user_id INTEGER, code TEXT, PRIMARY KEY (user_id, code))''')
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
        BotCommand(command="duel", description="🔫 Дуэль со ставкой"),
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
            f"👑 Титул: {u[4]}\n"
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
        
        cd = timedelta(seconds=10) if r == "Мифрил" else (timedelta(hours=2) if r == "VIP" else timedelta(hours=4))
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
        [InlineKeyboardButton(text="💎 Купить 1 BBC — 5000 💰", callback_data="shop_buy_bbc")],
        [InlineKeyboardButton(text="🎁 Мистический Лутбокс — 3000 💰", callback_data="shop_buy_box")],
        [InlineKeyboardButton(text="✏️ Сменить никнейм — 2000 💰", callback_data="shop_buy_rename")],
        [InlineKeyboardButton(text="👑 Купить статус VIP — 25000 💰", callback_data="shop_buy_vip")],
        [InlineKeyboardButton(text="🎴 Случайная 4⭐ Карта — 10000 💰", callback_data="shop_buy_4star")],
        [InlineKeyboardButton(text="✨ Случайная 5⭐ Карта — 15 💎", callback_data="shop_buy_5star")],
        [InlineKeyboardButton(text="🏆 Свой Кастомный Титул — 20 💎", callback_data="shop_buy_custom_title")]
    ])
    await m.answer("🛒 <b>МАГАЗИН</b>\nПотрать свои монеты и BBC с умом:", reply_markup=kb, parse_mode=ParseMode.HTML)
    @dp.callback_query(F.data.startswith("shop_"))
async def shop_cb(c: CallbackQuery, state: FSMContext):
    action = c.data.split("_")[2:] # shop_buy_...
    
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money, bbc_money, rank, titles FROM users WHERE user_id = ?", (c.from_user.id,))
        user_data = await res.fetchone()
        user_money, user_bbc, rank, titles = user_data

        if c.data == "shop_reset_cd":
            if user_money < 1500: return await c.answer("❌ Нужно 1500 монет", show_alert=True)
            past_date = (datetime.now() - timedelta(days=2)).isoformat()
            await db.execute("UPDATE users SET money = money - 1500, last_draw = ? WHERE user_id = ?", (past_date, c.from_user.id))
            await db.commit()
            await c.message.edit_text("✅ Ты успешно сбросил кулдаун на гачу! Можешь тянуть карту.")
            
        elif c.data == "shop_buy_bbc":
            if user_money < 5000: return await c.answer("❌ Нужно 5000 монет", show_alert=True)
            await db.execute("UPDATE users SET money = money - 5000, bbc_money = bbc_money + 1 WHERE user_id = ?", (c.from_user.id,))
            await db.commit()
            await c.message.edit_text("💎 Поздравляю! Ты купил 1 BBC.")

        elif c.data == "shop_buy_vip":
            if user_money < 25000: return await c.answer("❌ Нужно 25000 монет", show_alert=True)
            if rank in ["VIP", "Мифрил"]: return await c.answer("❌ У тебя уже есть этот (или лучший) статус!", show_alert=True)
            await db.execute("UPDATE users SET money = money - 25000, rank = 'VIP' WHERE user_id = ?", (c.from_user.id,))
            await db.commit()
            await c.message.edit_text("👑 Поздравляю! Ты приобрел статус VIP.")

        elif c.data == "shop_buy_rename":
            if user_money < 2000: return await c.answer("❌ Нужно 2000 монет", show_alert=True)
            await state.set_state(BotStates.waiting_for_rename)
            await c.message.edit_text("✏️ Напиши свой новый никнейм (до 20 символов):")

        elif c.data == "shop_buy_custom_title":
            if user_bbc < 20: return await c.answer("❌ Нужно 20 BBC", show_alert=True)
            await state.set_state(BotStates.waiting_for_custom_title)
            await c.message.edit_text("🏆 Напиши свой новый уникальный титул (до 25 символов):")

        elif c.data == "shop_buy_box":
            if user_money < 3000: return await c.answer("❌ Нужно 3000 монет", show_alert=True)
            prize_type = random.choices(["money", "bbc", "nothing"], weights=[50, 20, 30])[0]
            if prize_type == "money":
                win = random.randint(1000, 7000)
                await db.execute("UPDATE users SET money = money - 3000 + ? WHERE user_id = ?", (win, c.from_user.id))
                msg = f"🎁 Из лутбокса выпало <b>{win} монет</b>!"
            elif prize_type == "bbc":
                win = random.randint(1, 3)
                await db.execute("UPDATE users SET money = money - 3000, bbc_money = bbc_money + ? WHERE user_id = ?", (win, c.from_user.id))
                msg = f"🎁 Из лутбокса выпало <b>{win} BBC</b>!"
            else:
                await db.execute("UPDATE users SET money = money - 3000 WHERE user_id = ?", (c.from_user.id,))
                msg = "🎁 Из лутбокса выпала... <b>Пустота</b>. Не повезло!"
            await db.commit()
            await c.message.edit_text(msg, parse_mode=ParseMode.HTML)

        elif c.data in ["shop_buy_4star", "shop_buy_5star"]:
            req_rarity = 4 if c.data == "shop_buy_4star" else 5
            if req_rarity == 4 and user_money < 10000: return await c.answer("❌ Нужно 10000 монет", show_alert=True)
            if req_rarity == 5 and user_bbc < 15: return await c.answer("❌ Нужно 15 BBC", show_alert=True)
            
            res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (req_rarity,))
            card = await res.fetchone()
            if not card: return await c.answer(f"❌ В базе нет карт {req_rarity}⭐", show_alert=True)
            
            if req_rarity == 4:
                await db.execute("UPDATE users SET money = money - 10000 WHERE user_id = ?", (c.from_user.id,))
            else:
                await db.execute("UPDATE users SET bbc_money = bbc_money - 15 WHERE user_id = ?", (c.from_user.id,))
                
            res = await db.execute("SELECT count FROM inventory WHERE user_id=? AND card_id=?", (c.from_user.id, card[0]))
            is_dup = await res.fetchone()
            if is_dup: await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id=? AND card_id=?", (c.from_user.id, card[0]))
            else: await db.execute("INSERT INTO inventory VALUES (?,?,1)", (c.from_user.id, card[0]))
            await db.commit()
            await c.message.delete()
            await c.message.answer_photo(card[2], caption=f"✨ Покупка {req_rarity}⭐ карты!\n\n🃏 <b>{card[1]}</b>\n{'♻️ Дубликат!' if is_dup else '✨ Новая карта!'}", parse_mode=ParseMode.HTML)
    await c.answer()

@dp.message(BotStates.waiting_for_rename)
async def process_rename(m: Message, state: FSMContext):
    new_name = m.text[:20]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money = money - 2000, nickname = ? WHERE user_id = ?", (new_name, m.from_user.id))
        await db.commit()
    await m.answer(f"✅ Никнейм успешно изменен на <b>{new_name}</b>!", parse_mode=ParseMode.HTML)
    await state.clear()

@dp.message(BotStates.waiting_for_custom_title)
async def process_custom_title(m: Message, state: FSMContext):
    new_title = m.text[:25]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bbc_money = bbc_money - 20, titles = ? WHERE user_id = ?", (new_title, m.from_user.id))
        await db.commit()
    await m.answer(f"✅ Твой новый титул: <b>{new_title}</b>!", parse_mode=ParseMode.HTML)
    await state.clear()

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

@dp.message(Command("duel"))
async def duel_cmd(m: Message):
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🔫 Формат: /duel 100 (где 100 - ваша ставка)")
    bet = int(args[1])
    if bet < 10: return await m.answer("❌ Минимальная ставка - 10 монет.")

    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money, nickname FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u or u[0] < bet: return await m.answer("❌ Недостаточно монет для ставки!")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚔️ Принять вызов", callback_data=f"duel_{m.from_user.id}_{bet}")
    ]])
    await m.answer(f"💥 Игрок <b>{u[1]}</b> вызывает на дуэль!\n💰 Ставка: <b>{bet}</b> монет.\nКто осмелится принять?", 
                   reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("duel_"))
async def duel_cb(c: CallbackQuery):
    _, creator_id_str, bet_str = c.data.split("_")
    creator_id, bet = int(creator_id_str), int(bet_str)
    
    if c.from_user.id == creator_id:
        return await c.answer("❌ Нельзя драться с самим собой!", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        res1 = await db.execute("SELECT money, nickname FROM users WHERE user_id = ?", (creator_id,))
        u1 = await res1.fetchone()
        res2 = await db.execute("SELECT money, nickname FROM users WHERE user_id = ?", (c.from_user.id,))
        u2 = await res2.fetchone()

        if not u1 or u1[0] < bet: return await c.answer("❌ У создателя дуэли уже нет нужной суммы.", show_alert=True)
        if not u2 or u2[0] < bet: return await c.answer("❌ У тебя не хватает монет для этой ставки!", show_alert=True)

        # Бой начался, снимаем деньги у обоих
        await db.execute("UPDATE users SET money = money - ? WHERE user_id IN (?, ?)", (bet, creator_id, c.from_user.id))
        
        # Определяем победителя (50/50)
        if random.choice([True, False]):
            winner_id, loser_id = creator_id, c.from_user.id
            winner_name, loser_name = u1[1], u2[1]
        else:
            winner_id, loser_id = c.from_user.id, creator_id
            winner_name, loser_name = u2[1], u1[1]

        # Выдаем банк
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bet * 2, winner_id))
        await db.commit()

        battle_text = (f"🔫 <b>ДУЭЛЬ: {u1[1]} VS {u2[1]}</b> 🔫\n\n"
                       f"🔸 <i>{loser_name}</i> делает выстрел (Шанс 65%)... <b>ПРОМАХ!</b>\n"
                       f"🔸 <i>{winner_name}</i> хладнокровно стреляет в ответ... <b>ТОЧНО В ЦЕЛЬ!</b>\n\n"
                       f"🏆 <b>{winner_name}</b> побеждает и забирает банк: <b>{bet * 2}</b> монет!")
        
        await c.message.edit_text(battle_text, parse_mode=ParseMode.HTML)
        await c.answer()

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
        [InlineKeyboardButton(text="💰 Выдать монеты", callback_data="admin_give_money")],
        [InlineKeyboardButton(text="💎 Выдать BBC", callback_data="admin_give_bbc")],
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
    await c.message.answer("Формат: <code>[Код] [money/bbc_money] [Сумма] [Активации]</code>\nПример: <code>NEWYEAR money 1000 50</code>", parse_mode=ParseMode.HTML)
    await state.set_state(BotStates.waiting_for_promo_data)
    await c.answer()

@dp.message(BotStates.waiting_for_promo_data)
async def process_promo_data(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split()
    if len(args) != 4 or args[1] not in ["money", "bbc_money"] or not args[2].isdigit() or not args[3].isdigit():
        await state.clear()
        return await m.answer("❌ Ошибка формата.")
    
    code, rew_type, rew_val, uses = args[0], args[1], int(args[2]), int(args[3])
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO promocodes VALUES (?,?,?,?)", (code, rew_type, rew_val, uses))
            await db.commit()
            await m.answer(f"✅ Промокод <code>{code}</code> создан!", parse_mode=ParseMode.HTML)
        except aiosqlite.IntegrityError:
            await m.answer("❌ Такой промокод уже существует!")
    await state.clear()

@dp.callback_query(F.data == "admin_give_money")
async def admin_give_money_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    await c.message.answer("Введите <code>[ID пользователя] [Сумма монет]</code>", parse_mode=ParseMode.HTML)
    await state.set_state(BotStates.waiting_for_give_money)
    await c.answer()

@dp.message(BotStates.waiting_for_give_money)
async def process_give_money(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split()
    if len(args) != 2 or not args[0].isdigit() or not args[1].lstrip('-').isdigit():
        return await state.clear()
    
    target_id, amount = int(args[0]), int(args[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, target_id))
        if db.total_changes > 0: await m.answer(f"✅ Успешно выдано {amount} монет.")
        else: await m.answer("❌ Пользователь не найден.")
        await db.commit()
    await state.clear()

@dp.callback_query(F.data == "admin_give_bbc")
async def admin_give_bbc_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    await c.message.answer("Введите <code>[ID пользователя] [Сумма BBC]</code>", parse_mode=ParseMode.HTML)
    await state.set_state(BotStates.waiting_for_give_bbc)
    await c.answer()

@dp.message(BotStates.waiting_for_give_bbc)
async def process_give_bbc(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split()
    if len(args) != 2 or not args[0].isdigit() or not args[1].lstrip('-').isdigit():
        return await state.clear()
    
    target_id, amount = int(args[0]), int(args[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bbc_money = bbc_money + ? WHERE user_id = ?", (amount, target_id))
        if db.total_changes > 0: await m.answer(f"✅ Успешно выдано {amount} BBC.")
        else: await m.answer("❌ Пользователь не найден.")
        await db.commit()
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
    args = (m.text or m.caption or "").split()
    if len(args) < 2: return await m.answer("🎁 /promo КОД")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT 1 FROM used_promos WHERE user_id = ? AND code = ?", (m.from_user.id, args[1]))
        if await res.fetchone(): return await m.answer("❌ Ты уже использовал этот промокод.")

        res = await db.execute("SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?", (args[1],))
        p = await res.fetchone()
        if not p or p[2] <= 0: return await m.answer("❌ Код не найден или закончились активации.")
        
        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (p[1], m.from_user.id))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (args[1],))
        await db.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (m.from_user.id, args[1]))
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
