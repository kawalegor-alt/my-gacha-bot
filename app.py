import asyncio, logging, random, aiosqlite
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

RARITY_NAMES = {1: "Обычная", 2: "Редкая", 3: "Эпическая", 4: "Легендарная", 5: "Мифическая"}
REWARDS = {1: {"n": 100, "d": 50}, 2: {"n": 150, "d": 75}, 3: {"n": 250, "d": 100}, 4: {"n": 500, "d": 250}, 5: {"n": 1000, "d": 700}}

class AdminStates(StatesGroup):
    waiting_for_promo_data = State()
    waiting_for_give_money = State()
    waiting_for_give_bbc = State()
    waiting_for_mail = State()

class ShopStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_nickname = State()

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
        await db.execute('''CREATE TABLE IF NOT EXISTS used_promocodes (
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
        BotCommand(command="dice", description="🎲 Кости"),
        BotCommand(command="coinflip", description="🪙 Монетка"),
        BotCommand(command="slots", description="🎰 Слоты"),
        BotCommand(command="promo", description="🎁 Промокод")
    ]
    await bot.set_my_commands(cmds)

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
    except: await m.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("daily"))
async def daily_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (m.from_user.id,))
        ld = (await res.fetchone())[0]
        if ld and datetime.now() < datetime.fromisoformat(ld) + timedelta(days=1):
            return await m.answer("📅 Бонус можно брать раз в 24 часа!")
        
        reward = random.randint(500, 1500)
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
        
        reward = random.randint(150, 400)
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
    for name, rar, count in cards[:40]:
        msg += f"{'⭐'*rar} {name} (x{count})\n"
    await m.answer(msg[:4000], parse_mode=ParseMode.HTML)

@dp.message(Command("top"))
async def top_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Монеты", callback_data="top_m"), InlineKeyboardButton(text="💎 BBC", callback_data="top_b")],
        [InlineKeyboardButton(text="🎴 Количество карт", callback_data="top_c")]
    ])
    await m.answer("🏆 Выберите таблицу лидеров:", reply_markup=kb)

@dp.callback_query(F.data.startswith("top_"))
async def top_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        if c.data == "top_c":
            res = await db.execute("SELECT u.nickname, COALESCE(SUM(i.count), 0) as tc FROM users u LEFT JOIN inventory i ON u.user_id = i.user_id GROUP BY u.user_id ORDER BY tc DESC LIMIT 10")
            users = await res.fetchall()
            text = "🏆 <b>ТОП 10 ПО КАРТАМ:</b>\n\n" + "\n".join([f"{i+1}. {u[0]} — {u[1]} шт." for i, u in enumerate(users)])
        else:
            col = "money" if c.data == "top_m" else "bbc_money"
            res = await db.execute(f"SELECT nickname, {col} FROM users ORDER BY {col} DESC LIMIT 10")
            users = await res.fetchall()
            val = "МОНЕТАМ" if c.data == "top_m" else "BBC"
            text = f"🏆 <b>ТОП 10 ПО {val}:</b>\n\n" + "\n".join([f"{i+1}. {u[0]} — {u[1]}" for i, u in enumerate(users)])
    await c.message.edit_text(text, parse_mode=ParseMode.HTML)
    await c.answer()
    # --- ГАЧА ---
@dp.message(F.text.lower().in_({"карта", "карту", "/draw"}))
async def draw_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, draw_count FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await res.fetchone()
        if not row: return await m.answer("Напиши /start")
        r, ld, dc = row
        
        # Обновленные кулдауны: База - 4 часа, VIP - 3 часа, Элита - 2 часа, Мифрил - 10 секунд
        cd = timedelta(seconds=10) if r == "Мифрил" else (timedelta(hours=2) if r == "Элита" else (timedelta(hours=3) if r == "VIP" else timedelta(hours=4)))
        
        if ld and datetime.now() < datetime.fromisoformat(ld) + cd:
            wait = (datetime.fromisoformat(ld) + cd) - datetime.now()
            return await m.answer(f"⏳ Рано! Жди {wait.seconds // 3600}ч. {(wait.seconds // 60) % 60}мин.")

        p = random.random()
        if r == "Мифрил": rar = 5 if p < 0.15 else (4 if p < 0.35 else (3 if p < 0.65 else 2))
        elif r == "Элита": rar = 5 if p < 0.08 else (4 if p < 0.20 else (3 if p < 0.45 else 2))
        elif r == "VIP": rar = 5 if p < 0.04 else (4 if p < 0.12 else (3 if p < 0.35 else 2))
        else: rar = 5 if p < 0.015 else (4 if p < 0.07 else (3 if p < 0.20 else (2 if p < 0.50 else 1)))
        
        if dc >= 49: rar = 5 

        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rar,))
        card = await res.fetchone()
        if not card: return await m.answer(f"⚠️ Ошибка: Карт {rar}⭐ нет в базе.")

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
        cap = (f"🃏 <b>{card[1]}</b>\n\nРанг: {stars_str} ({rar_name})\n"
               f"{'♻️ Дубликат!' if is_dup else '✨ Новая карта!'}\n💰 +{rew} монет")
        await m.answer_photo(card[2], caption=cap, parse_mode=ParseMode.HTML)

# --- НОВЫЙ МАГАЗИН ---
@dp.message(Command("shop"))
async def shop_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Магазин Монет", callback_data="shop_menu_money")],
        [InlineKeyboardButton(text="💎 Магазин BBC", callback_data="shop_menu_bbc")]
    ])
    await m.answer("🛒 <b>МАГАЗИН</b>\nВыбери отдел:", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("shop_menu_"))
async def shop_menu_cb(c: CallbackQuery):
    menu_type = c.data.split("_")[2]
    if menu_type == "money":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Сброс КД (1 500 💰)", callback_data="shop_buy_cd")],
            [InlineKeyboardButton(text="💎 Купить 1 BBC (50 000 💰)", callback_data="shop_buy_1bbc")],
            [InlineKeyboardButton(text="✨ Случайная 4⭐ карта (25 000 💰)", callback_data="shop_buy_rand4_m")],
            [InlineKeyboardButton(text="👑 Ранг VIP [КД 3ч] (50 000 💰)", callback_data="shop_buy_vip_m")],
            [InlineKeyboardButton(text="🔥 Ранг Элита [КД 2ч] (150 000 💰)", callback_data="shop_buy_elite_m")],
            [InlineKeyboardButton(text="✍️ Свой Титул (10 000 💰)", callback_data="shop_buy_title")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="shop_back")]
        ])
        await c.message.edit_text("💰 <b>МАГАЗИН МОНЕТ</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
    elif menu_type == "bbc":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏷 Сменить Ник (5 💎)", callback_data="shop_buy_nick")],
            [InlineKeyboardButton(text="🎁 Пак (10 карт) (20 💎)", callback_data="shop_buy_pack")],
            [InlineKeyboardButton(text="🌟 Гарант 5⭐ (50 💎)", callback_data="shop_buy_rand5_b")],
            [InlineKeyboardButton(text="🔥 Мега-Пак (30 карт) (75 💎)", callback_data="shop_buy_mega_b")],
            [InlineKeyboardButton(text="👑 Набор 'Легенда' (150 💎)", callback_data="shop_buy_god_b")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="shop_back")]
        ])
        await c.message.edit_text("💎 <b>МАГАЗИН BBC</b>\nНабор 'Легенда': Гарант 5⭐ + 500k монет + Титул", reply_markup=kb, parse_mode=ParseMode.HTML)
    await c.answer()

@dp.callback_query(F.data == "shop_back")
async def shop_back_cb(c: CallbackQuery):
    await shop_cmd(c.message)
    await c.message.delete()

@dp.callback_query(F.data.startswith("shop_buy_"))
async def shop_buy_cb(c: CallbackQuery, state: FSMContext):
    item = c.data.replace("shop_buy_", "")
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money, bbc_money FROM users WHERE user_id = ?", (c.from_user.id,))
        money, bbc = await res.fetchone()

        # Покупки за монеты
        if item == "cd":
            if money < 1500: return await c.answer("❌ Нужно 1500 💰", show_alert=True)
            past = (datetime.now() - timedelta(days=2)).isoformat()
            await db.execute("UPDATE users SET money=money-1500, last_draw=? WHERE user_id=?", (past, c.from_user.id))
            await c.message.edit_text("✅ Кулдаун сброшен!")
        elif item == "1bbc":
            if money < 50000: return await c.answer("❌ Нужно 50 000 💰", show_alert=True)
            await db.execute("UPDATE users SET money=money-50000, bbc_money=bbc_money+1 WHERE user_id=?", (c.from_user.id,))
            await c.message.edit_text("✅ Куплен 1 BBC!")
        elif item == "rand4_m":
            if money < 25000: return await c.answer("❌ Нужно 25 000 💰", show_alert=True)
            res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity=4 ORDER BY RANDOM() LIMIT 1")
            card = await res.fetchone()
            if not card: return await c.answer("❌ В базе нет 4⭐ карт", show_alert=True)
            await db.execute("UPDATE users SET money=money-25000 WHERE user_id=?", (c.from_user.id,))
            await db.execute("INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,1) ON CONFLICT(user_id, card_id) DO UPDATE SET count=count+1", (c.from_user.id, card[0]))
            await c.message.delete()
            return await c.message.answer_photo(card[2], caption=f"✨ Удача! Ты купил 4⭐ карту:\n<b>{card[1]}</b>", parse_mode=ParseMode.HTML)
        elif item == "vip_m":
            if money < 50000: return await c.answer("❌ Нужно 50 000 💰", show_alert=True)
            await db.execute("UPDATE users SET money=money-50000, rank='VIP' WHERE user_id=?", (c.from_user.id,))
            await c.message.edit_text("👑 Теперь у тебя ранг VIP! Кулдаун карт: 3 часа.")
        elif item == "elite_m":
            if money < 150000: return await c.answer("❌ Нужно 150 000 💰", show_alert=True)
            await db.execute("UPDATE users SET money=money-150000, rank='Элита' WHERE user_id=?", (c.from_user.id,))
            await c.message.edit_text("🔥 Теперь у тебя ранг Элита! Кулдаун карт: 2 часа + повышенный шанс!")
        elif item == "title":
            if money < 10000: return await c.answer("❌ Нужно 10 000 💰", show_alert=True)
            await state.set_state(ShopStates.waiting_for_title)
            await c.message.edit_text("✍️ Напиши желаемый титул (снимется 10000 💰):")

        # Покупки за BBC
        elif item == "nick":
            if bbc < 5: return await c.answer("❌ Нужно 5 💎", show_alert=True)
            await state.set_state(ShopStates.waiting_for_nickname)
            await c.message.edit_text("🏷 Напиши новый никнейм (снимется 5 💎):")
        elif item == "pack":
            if bbc < 20: return await c.answer("❌ Нужно 20 💎", show_alert=True)
            await db.execute("UPDATE users SET bbc_money=bbc_money-20 WHERE user_id=?", (c.from_user.id,))
            cards_won = []
            for _ in range(10):
                card = await (await db.execute("SELECT card_id, name, rarity FROM cards ORDER BY RANDOM() LIMIT 1")).fetchone()
                if card:
                    await db.execute("INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,1) ON CONFLICT(user_id, card_id) DO UPDATE SET count=count+1", (c.from_user.id, card[0]))
                    cards_won.append(f"{'⭐'*card[2]} {card[1]}")
            await c.message.edit_text("🎁 <b>Открыт Пак из 10 карт!</b>\n" + "\n".join(cards_won), parse_mode=ParseMode.HTML)
        elif item == "rand5_b":
            if bbc < 50: return await c.answer("❌ Нужно 50 💎", show_alert=True)
            res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity=5 ORDER BY RANDOM() LIMIT 1")
            card = await res.fetchone()
            if not card: return await c.answer("❌ В базе нет 5⭐ карт", show_alert=True)
            await db.execute("UPDATE users SET bbc_money=bbc_money-50 WHERE user_id=?", (c.from_user.id,))
            await db.execute("INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,1) ON CONFLICT(user_id, card_id) DO UPDATE SET count=count+1", (c.from_user.id, card[0]))
            await c.message.delete()
            return await c.message.answer_photo(card[2], caption=f"🌟 Гарант сработал! Выбита МИФИЧЕСКАЯ 5⭐:\n<b>{card[1]}</b>", parse_mode=ParseMode.HTML)
        elif item == "mega_b":
            if bbc < 75: return await c.answer("❌ Нужно 75 💎", show_alert=True)
            await db.execute("UPDATE users SET bbc_money=bbc_money-75 WHERE user_id=?", (c.from_user.id,))
            for _ in range(30):
                card = await (await db.execute("SELECT card_id FROM cards ORDER BY RANDOM() LIMIT 1")).fetchone()
                if card: await db.execute("INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,1) ON CONFLICT(user_id, card_id) DO UPDATE SET count=count+1", (c.from_user.id, card[0]))
            await c.message.edit_text("🔥 <b>Мега-Пак открыт!</b>\n30 случайных карт добавлены в твой инвентарь.", parse_mode=ParseMode.HTML)
        elif item == "god_b":
            if bbc < 150: return await c.answer("❌ Нужно 150 💎", show_alert=True)
            res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity=5 ORDER BY RANDOM() LIMIT 1")
            card = await res.fetchone()
            if not card: return await c.answer("❌ В базе нет 5⭐ карт", show_alert=True)
            await db.execute("UPDATE users SET bbc_money=bbc_money-150, money=money+500000, titles='ЛЕГЕНДА' WHERE user_id=?", (c.from_user.id,))
            await db.execute("INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,1) ON CONFLICT(user_id, card_id) DO UPDATE SET count=count+1", (c.from_user.id, card[0]))
            await c.message.delete()
            return await c.message.answer_photo(card[2], caption=f"👑 <b>НАБОР 'ЛЕГЕНДА' КУПЛЕН!</b>\n\n💰 Начислено 500 000 монет\n✍️ Выдан титул 'ЛЕГЕНДА'\n🌟 Гарант 5⭐: <b>{card[1]}</b>", parse_mode=ParseMode.HTML)

        await db.commit()
    await c.answer()

@dp.message(ShopStates.waiting_for_title)
async def process_buy_title(m: Message, state: FSMContext):
    new_title = m.text[:30]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money=money-10000, titles=? WHERE user_id=?", (new_title, m.from_user.id))
        await db.commit()
    await m.answer(f"✅ Твой новый титул: {new_title}")
    await state.clear()

@dp.message(ShopStates.waiting_for_nickname)
async def process_buy_nick(m: Message, state: FSMContext):
    new_nick = m.text[:20]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bbc_money=bbc_money-5, nickname=? WHERE user_id=?", (new_nick, m.from_user.id))
        await db.commit()
    await m.answer(f"✅ Твой новый никнейм: {new_nick}")
    await state.clear()


# --- ИГРЫ ---
@dp.message(Command("casino"))
async def casino_cmd(m: Message):
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎰 Формат: /casino [ставка]")
    bet = int(args[1])
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money FROM users WHERE user_id = ?", (m.from_user.id,))
        money = (await res.fetchone())[0]
        if money < bet: return await m.answer("❌ Недостаточно монет!")
        
        if random.randint(1, 100) <= 30:
            mult = 2 if random.random() > 0.1 else 5
            await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (bet*(mult-1), m.from_user.id))
            txt = f"✅ Победа! Множитель x{mult}. Выигрыш: {bet*mult}"
        else:
            await db.execute("UPDATE users SET money=money-? WHERE user_id=?", (bet, m.from_user.id))
            txt = f"💀 Проигрыш. Минус {bet} монет."
        await db.commit()
    await m.answer(f"🎰 {txt}")

@dp.message(Command("coinflip"))
async def coinflip_cmd(m: Message):
    args = m.text.split()
    if len(args) < 3 or args[1].lower() not in ['орел', 'решка'] or not args[2].isdigit():
        return await m.answer("🪙 Формат: /coinflip [орел/решка] [ставка]")
    guess, bet = args[1].lower(), int(args[2])
    
    async with aiosqlite.connect(DB_PATH) as db:
        money = (await (await db.execute("SELECT money FROM users WHERE user_id=?", (m.from_user.id,))).fetchone())[0]
        if money < bet: return await m.answer("❌ Недостаточно монет!")
        
        result = random.choice(['орел', 'решка'])
        if guess == result:
            await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (bet, m.from_user.id))
            await m.answer(f"🪙 Выпал {result}! Ты выиграл {bet*2} 💰")
        else:
            await db.execute("UPDATE users SET money=money-? WHERE user_id=?", (bet, m.from_user.id))
            await m.answer(f"🪙 Выпал {result}. Ты проиграл {bet} 💰")
        await db.commit()

@dp.message(Command("dice"))
async def dice_cmd(m: Message, bot: Bot):
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎲 Формат: /dice [ставка]")
    bet = int(args[1])
    
    async with aiosqlite.connect(DB_PATH) as db:
        money = (await (await db.execute("SELECT money FROM users WHERE user_id=?", (m.from_user.id,))).fetchone())[0]
        if money < bet: return await m.answer("❌ Недостаточно монет!")
        await db.execute("UPDATE users SET money=money-? WHERE user_id=?", (bet, m.from_user.id))
        await db.commit()

    await m.answer("Твой бросок:")
    user_dice = await m.answer_dice("🎲")
    await asyncio.sleep(2)
    await m.answer("Бросок бота:")
    bot_dice = await m.answer_dice("🎲")
    await asyncio.sleep(2)
    
    async with aiosqlite.connect(DB_PATH) as db:
        if user_dice.dice.value > bot_dice.dice.value:
            await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (bet*2, m.from_user.id))
            await m.answer(f"🎉 Ты победил и забрал {bet*2} 💰!")
        elif user_dice.dice.value < bot_dice.dice.value:
            await m.answer(f"💀 Ты проиграл {bet} 💰!")
        else:
            await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (bet, m.from_user.id))
            await m.answer("🤝 Ничья! Ставка возвращена.")
        await db.commit()

@dp.message(Command("slots"))
async def slots_cmd(m: Message, bot: Bot):
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎰 Формат: /slots [ставка]")
    bet = int(args[1])
    
    async with aiosqlite.connect(DB_PATH) as db:
        money = (await (await db.execute("SELECT money FROM users WHERE user_id=?", (m.from_user.id,))).fetchone())[0]
        if money < bet: return await m.answer("❌ Недостаточно монет!")
        await db.execute("UPDATE users SET money=money-? WHERE user_id=?", (bet, m.from_user.id))
        await db.commit()

    slot_msg = await m.answer_dice("🎰")
    val = slot_msg.dice.value
    await asyncio.sleep(2)
    
    win = 0
    if val == 64: win = bet * 10
    elif val in [1, 22, 43]: win = bet * 3
    
    async with aiosqlite.connect(DB_PATH) as db:
        if win > 0:
            await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (win, m.from_user.id))
            await m.answer(f"🔥 ДЖЕКПОТ! Ты выиграл {win} 💰!")
        else:
            await m.answer("💸 Ничего не совпало. Ставка сгорела.")
        await db.commit()

# --- ПРОМОКОДЫ И АДМИНКА ---
@dp.message(Command("promo"))
async def promo_cmd(m: Message):
    args = m.text.split()
    if len(args) < 2: return await m.answer("🎁 /promo [КОД]")
    code = args[1]
    
    async with aiosqlite.connect(DB_PATH) as db:
        check = await db.execute("SELECT 1 FROM used_promocodes WHERE user_id=? AND code=?", (m.from_user.id, code))
        if await check.fetchone(): return await m.answer("⚠️ Ты уже использовал этот промокод!")

        res = await db.execute("SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?", (code,))
        p = await res.fetchone()
        if not p or p[2] <= 0: return await m.answer("❌ Код не найден или закончились активации.")
        
        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (p[1], m.from_user.id))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        await db.execute("INSERT INTO used_promocodes (user_id, code) VALUES (?,?)", (m.from_user.id, code))
        await db.commit()
    
    val_name = "Монет" if p[0] == "money" else "BBC"
    await m.answer(f"✅ Промокод активирован! Начислено: {p[1]} {val_name}")

@dp.message(Command("admin"))
async def admin_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_promo")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="💰 Выдать Монеты", callback_data="admin_give_m"), InlineKeyboardButton(text="💎 Выдать BBC", callback_data="admin_give_b")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_mail")]
    ])
    await m.answer("👑 <b>Админ-панель</b>\nВыбери действие:", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("admin_"))
async def admin_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    action = c.data.replace("admin_", "")
    
    if action == "stats":
        async with aiosqlite.connect(DB_PATH) as db:
            uc = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            cc = (await (await db.execute("SELECT COUNT(*) FROM cards")).fetchone())[0]
            mc = (await (await db.execute("SELECT SUM(money) FROM users")).fetchone())[0]
        await c.message.edit_text(f"📊 <b>Статистика:</b>\n👥 Игроков: {uc}\n🃏 Карт: {cc}\n💰 Всего монет в экономике: {mc}", parse_mode=ParseMode.HTML)
    elif action == "promo":
        await c.message.answer("Формат: <code>[Код] [money/bbc_money] [Сумма] [Активации]</code>", parse_mode=ParseMode.HTML)
        await state.set_state(AdminStates.waiting_for_promo_data)
    elif action == "give_m":
        await c.message.answer("Формат: <code>[ID_Юзера] [Сумма]</code>", parse_mode=ParseMode.HTML)
                await state.set_state(AdminStates.waiting_for_give_money)
    elif action == "give_b":
        await c.message.answer("Формат: <code>[ID_Юзера] [Сумма BBC]</code>", parse_mode=ParseMode.HTML)
        await state.set_state(AdminStates.waiting_for_give_bbc)
    elif action == "mail":
        await c.message.answer("Введите текст рассылки (можно с фото/видео):")
        await state.set_state(AdminStates.waiting_for_mail)
    await c.answer()

@dp.message(AdminStates.waiting_for_promo_data)
async def process_promo(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split()
    if len(args) != 4 or args[1] not in ["money", "bbc_money"] or not args[2].isdigit() or not args[3].isdigit():
        return await m.answer("❌ Ошибка формата.")
    
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO promocodes VALUES (?,?,?,?)", (args[0], args[1], int(args[2]), int(args[3])))
            await db.commit()
            await m.answer(f"✅ Промокод <code>{args[0]}</code> создан!", parse_mode=ParseMode.HTML)
        except: await m.answer("❌ Такой промокод уже есть!")
    await state.clear()

@dp.message(AdminStates.waiting_for_give_money)
async def process_give_money(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    try:
        uid, amt = map(int, m.text.split())
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (amt, uid))
            await db.commit()
        await m.answer(f"✅ Выдано {amt} монет пользователю {uid}.")
    except: await m.answer("❌ Ошибка формата.")
    await state.clear()

@dp.message(AdminStates.waiting_for_give_bbc)
async def process_give_bbc(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    try:
        uid, amt = map(int, m.text.split())
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET bbc_money=bbc_money+? WHERE user_id=?", (amt, uid))
            await db.commit()
        await m.answer(f"✅ Выдано {amt} BBC пользователю {uid}.")
    except: await m.answer("❌ Ошибка формата.")
    await state.clear()

@dp.message(AdminStates.waiting_for_mail)
async def process_mail(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    count = 0
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT user_id FROM users")
        users = await res.fetchall()
    
    await m.answer("📢 Начинаю рассылку...")
    for (uid,) in users:
        try:
            await m.copy_to(uid)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    
    await m.answer(f"✅ Рассылка завершена. Доставлено: {count} пользователям.")
    await state.clear()

@dp.message(F.photo & F.caption.startswith("/add_card"))
async def add_card(m: Message):
    if m.from_user.id != ADMIN_ID: return
    p = m.caption.split()
    # Формат: /add_card Название_Карты Редкость(1-5)
    try:
        rarity = int(p[-1])
        name = " ".join(p[1:-1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)", 
                             (name, rarity, m.photo[-1].file_id))
            await db.commit()
        await m.answer(f"✅ Карта '{name}' ({rarity}⭐) успешно добавлена!")
    except:
        await m.answer("❌ Ошибка! Используй формат: /add_card Имя 5 (и прикрепи фото)")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
                
