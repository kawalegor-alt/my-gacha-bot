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

RARITY_NAMES = {1: "Обычная", 2: "Редкая", 3: "Эпическая", 4: "Легендарная", 5: "Мифическая"}
REWARDS = {1: {"n": 100, "d": 50}, 2: {"n": 150, "d": 75}, 3: {"n": 250, "d": 100}, 4: {"n": 500, "d": 250}, 5: {"n": 1000, "d": 700}}

class AdminStates(StatesGroup):
    waiting_for_promo_data = State()
    waiting_for_broadcast = State()
    waiting_for_give_money = State()
    waiting_for_give_bbc = State()
    waiting_for_ban = State()
    waiting_for_unban = State()
    waiting_for_user_info = State()
    waiting_for_take_money = State()
    waiting_for_wipe_account = State()
    waiting_for_del_promo = State()

class ShopStates(StatesGroup):
    waiting_for_title = State()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, bbc_money INTEGER DEFAULT 0, last_draw TEXT, 
            titles TEXT DEFAULT 'Новичок', draw_count INTEGER DEFAULT 0, 
            last_daily TEXT, last_work TEXT, is_banned INTEGER DEFAULT 0)''')
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
        BotCommand(command="games", description="🎮 Мини-игры"),
        BotCommand(command="promo", description="🎁 Промокод"),
        BotCommand(command="pay", description="💸 Перевод монет")
    ]
    await bot.set_my_commands(cmds)

@dp.message(Command("start"))
async def start_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        r = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?,?,?)", (m.from_user.id, m.from_user.first_name, r))
        await db.commit()
    await m.answer("✅ Регистрация успешна! Пиши 'карта' чтобы выбить персонажа, или /games для списка игр.")

@dp.message(Command("profile"))
async def profile_cmd(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles, draw_count, is_banned FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return await m.answer("Сначала напиши /start")
        if u[6]: return await m.answer("⛔ Ваш аккаунт заблокирован.")
        
        res = await db.execute("SELECT SUM(count) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0] or 0
    
    text = (f"<b>🪪 ПРОФИЛЬ:</b> {u[0]}\n🆔 ID: <code>{m.from_user.id}</code>\n\n🏅 Ранг: {u[1]}\n🏆 Титул: {u[4]}\n"
            f"💰 Монеты: {u[2]} | 💎 BBC: {u[3]}\n🎴 Карт: {inv_cnt}\n🔄 До гаранта (5⭐): {50 - u[5]}")

    try:
        photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
        if photos.total_count > 0: await m.answer_photo(photos.photos[0][0].file_id, caption=text, parse_mode=ParseMode.HTML)
        else: await m.answer(text, parse_mode=ParseMode.HTML)
    except: await m.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("top"))
async def top_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Монеты", callback_data="top_m"), InlineKeyboardButton(text="💎 BBC", callback_data="top_b")],
        [InlineKeyboardButton(text="🎴 По картам", callback_data="top_c")]
    ])
    await m.answer("🏆 Выберите таблицу лидеров:", reply_markup=kb)

@dp.callback_query(F.data.startswith("top_"))
async def top_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        if c.data == "top_m":
            res = await db.execute("SELECT nickname, money FROM users ORDER BY money DESC LIMIT 10")
            title, suf = "💰 ТОП ПО МОНЕТАМ", ""
        elif c.data == "top_b":
            res = await db.execute("SELECT nickname, bbc_money FROM users ORDER BY bbc_money DESC LIMIT 10")
            title, suf = "💎 ТОП ПО BBC", ""
        else:
            res = await db.execute("""SELECT u.nickname, COALESCE(SUM(i.count), 0) as cnt 
                                      FROM users u LEFT JOIN inventory i ON u.user_id = i.user_id 
                                      GROUP BY u.user_id ORDER BY cnt DESC LIMIT 10""")
            title, suf = "🎴 ТОП ПО КОЛ-ВУ КАРТ", " шт."
        users = await res.fetchall()
    
    text = f"🏆 <b>{title}:</b>\n\n" + "\n".join([f"{i+1}. {u[0]} — {u[1]}{suf}" for i, u in enumerate(users)])
    await c.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=c.message.reply_markup)
    await c.answer()
# --- ГАЧА ---
@dp.message(F.text.lower().in_({"карта", "карту", "/draw"}))
async def draw_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, draw_count, is_banned FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await res.fetchone()
        if not row: return await m.answer("Напиши /start")
        if row[3]: return await m.answer("⛔ Вы заблокированы.")
        r, ld, dc = row[0], row[1], row[2]
        
        if r == "Мифрил": cd = timedelta(seconds=10)
        elif r == "Титан": cd = timedelta(hours=2)
        elif r == "VIP": cd = timedelta(hours=3)
        else: cd = timedelta(hours=4)
        
        if ld and datetime.now() < datetime.fromisoformat(ld) + cd:
            wait = (datetime.fromisoformat(ld) + cd) - datetime.now()
            return await m.answer(f"⏳ Рано! Жди {wait.seconds // 3600}ч. {(wait.seconds // 60) % 60}мин.")

        p = random.random()
        if r == "Мифрил": rar = 5 if p < 0.15 else (4 if p < 0.35 else (3 if p < 0.65 else 2))
        elif r == "Титан": rar = 5 if p < 0.08 else (4 if p < 0.20 else (3 if p < 0.45 else 2))
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

        cap = (f"🃏 <b>{card[1]}</b>\n\nРанг: {'⭐'*rar} ({RARITY_NAMES.get(rar)})\n"
               f"{'♻️ Дубликат!' if is_dup else '✨ Новая карта!'}\n💰 +{rew} монет")
        await m.answer_photo(card[2], caption=cap, parse_mode=ParseMode.HTML)

# --- БАЗОВАЯ ЭКОНОМИКА ---
@dp.message(Command("daily"))
async def daily_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT last_daily, is_banned FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await res.fetchone()
        if not row or row[1]: return
        if row[0] and datetime.now() < datetime.fromisoformat(row[0]) + timedelta(days=1):
            return await m.answer("📅 Бонус можно брать раз в 24 часа!")
        reward = random.randint(200, 500)
        await db.execute("UPDATE users SET money=money+?, last_daily=? WHERE user_id=?", (reward, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
        await m.answer(f"🎁 Ежедневная награда: {reward} монет!")

@dp.message(Command("work"))
async def work_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT last_work, is_banned FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await res.fetchone()
        if not row or row[1]: return
        if row[0] and datetime.now() < datetime.fromisoformat(row[0]) + timedelta(hours=1):
            return await m.answer("💼 Ты устал. Отдохни часик.")
        reward = random.randint(50, 150)
        await db.execute("UPDATE users SET money=money+?, last_work=? WHERE user_id=?", (reward, datetime.now().isoformat(), m.from_user.id))
        await db.commit()
        await m.answer(f"⚒ Ты поработал и получил {reward} монет!")

@dp.message(Command("inventory"))
async def inventory_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT c.name, c.rarity, i.count FROM inventory i JOIN cards c ON i.card_id = c.card_id WHERE i.user_id = ? ORDER BY c.rarity DESC", (m.from_user.id,))
        cards = await res.fetchall()
    if not cards: return await m.answer("🎒 Твой рюкзак пуст.")
    msg = "🎒 <b>ТВОИ КАРТЫ:</b>\n\n"
    for name, rar, count in cards[:40]: msg += f"{'⭐'*rar} {name} (x{count})\n"
    await m.answer(msg, parse_mode=ParseMode.HTML)

# --- МИНИ-ИГРЫ ---
@dp.message(Command("games"))
async def games_cmd(m: Message):
    text = ("🎮 <b>ДОСТУПНЫЕ МИНИ-ИГРЫ:</b>\n\n"
            "🎰 <code>/casino [ставка]</code> — Классическое казино (шанс 30% на х2 или х5)\n"
            "🪙 <code>/coinflip [ставка] [орел/решка]</code> — Монетка (шанс 50%, х2)\n"
            "🎲 <code>/dice [ставка]</code> — Кубики против бота\n"
            "🍒 <code>/slots [ставка]</code> — Игровые автоматы (собери 3 в ряд)\n"
            "🎡 <code>/roulette [ставка] [красное/черное/зеленое]</code> — Рулетка (к/ч - х2, з - х14)")
    await m.answer(text, parse_mode=ParseMode.HTML)

async def check_balance_and_ban(user_id, bet):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money, is_banned FROM users WHERE user_id = ?", (user_id,))
        row = await res.fetchone()
        if not row or row[1] or row[0] < bet: return False
    return True

@dp.message(Command("casino"))
async def casino_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎰 Формат: /casino [ставка]")
    bet = int(args[1])
    if not await check_balance_and_ban(m.from_user.id, bet): return await m.answer("❌ Недостаточно монет или вы в бане!")
    
    async with aiosqlite.connect(DB_PATH) as db:
        if random.randint(1, 100) <= 30:
            mult = 2 if random.random() > 0.1 else 5
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bet * (mult-1), m.from_user.id))
            txt = f"✅ Победа! Множитель x{mult}. Выигрыш: {bet*mult}"
        else:
            await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (bet, m.from_user.id))
            txt = f"💀 Проигрыш. Минус {bet} монет."
        await db.commit()
    await m.answer(f"🎰 {txt}")

@dp.message(Command("coinflip"))
async def coinflip_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 3 or not args[1].isdigit() or args[2].lower() not in ["орел", "решка"]:
        return await m.answer("🪙 Формат: /coinflip [ставка] [орел/решка]")
    bet, choice = int(args[1]), args[2].lower()
    if not await check_balance_and_ban(m.from_user.id, bet): return await m.answer("❌ Недостаточно монет или вы в бане!")
    
    result = random.choice(["орел", "решка"])
    async with aiosqlite.connect(DB_PATH) as db:
        if choice == result:
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bet, m.from_user.id))
            await m.answer(f"🪙 Выпал {result}! Ты выиграл {bet} монет.")
        else:
            await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (bet, m.from_user.id))
            await m.answer(f"🪙 Выпал {result}. Ты проиграл {bet} монет.")
        await db.commit()
        @dp.message(Command("dice"))
        
    async def dice_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🎲 Формат: /dice [ставка]")
    bet = int(args[1])
    if not await check_balance_and_ban(m.from_user.id, bet): return await m.answer("❌ Недостаточно монет или вы в бане!")
    
    bot_roll, user_roll = random.randint(1, 6), random.randint(1, 6)
    txt = f"🎲 Бот бросил: {bot_roll}\n🎲 Ты бросил: {user_roll}\n\n"
    async with aiosqlite.connect(DB_PATH) as db:
        if user_roll > bot_roll:
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bet, m.from_user.id))
            txt += f"✅ Ты выиграл {bet} монет!"
        elif user_roll < bot_roll:
            await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (bet, m.from_user.id))
            txt += f"💀 Ты проиграл {bet} монет."
        else: txt += "🤝 Ничья! Деньги остаются."
        await db.commit()
    await m.answer(txt)

@dp.message(Command("slots"))
async def slots_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 2 or not args[1].isdigit(): return await m.answer("🍒 Формат: /slots [ставка]")
    bet = int(args[1])
    if not await check_balance_and_ban(m.from_user.id, bet): return await m.answer("❌ Недостаточно монет или вы в бане!")
    
    items = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
    r1, r2, r3 = random.choice(items), random.choice(items), random.choice(items)
    txt = f"🎰 <b>СЛОТЫ</b> 🎰\n[ {r1} | {r2} | {r3} ]\n\n"
    
    async with aiosqlite.connect(DB_PATH) as db:
        if r1 == r2 == r3:
            mult = 10 if r1 == "7️⃣" else (5 if r1 == "💎" else 3)
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bet * (mult-1), m.from_user.id))
            txt += f"ДЖЕКПОТ! Множитель x{mult}. Выигрыш: {bet*mult}"
        elif r1 == r2 or r2 == r3 or r1 == r3:
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (int(bet * 0.5), m.from_user.id))
            txt += f"Пара! Ты получил {int(bet * 1.5)} монет (х1.5)."
        else:
            await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (bet, m.from_user.id))
            txt += f"Ничего не совпало. Проигрыш {bet} монет."
        await db.commit()
    await m.answer(txt, parse_mode=ParseMode.HTML)

@dp.message(Command("roulette"))
async def roulette_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 3 or not args[1].isdigit() or args[2].lower() not in ["красное", "черное", "зеленое"]:
        return await m.answer("🎡 Формат: /roulette [ставка] [красное/черное/зеленое]")
    bet, color = int(args[1]), args[2].lower()
    if not await check_balance_and_ban(m.from_user.id, bet): return await m.answer("❌ Недостаточно монет или вы в бане!")
    
    res_num = random.randint(0, 36)
    if res_num == 0: res_color = "зеленое"
    elif res_num % 2 == 0: res_color = "черное"
    else: res_color = "красное"
    
    async with aiosqlite.connect(DB_PATH) as db:
        if color == res_color:
            mult = 14 if res_color == "зеленое" else 2
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bet * (mult-1), m.from_user.id))
            await m.answer(f"🎡 Выпало {res_num} ({res_color})! Выигрыш: {bet*mult} монет.")
        else:
            await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (bet, m.from_user.id))
            await m.answer(f"🎡 Выпало {res_num} ({res_color}). Ты проиграл {bet} монет.")
        await db.commit()

# --- МАГАЗИН И ПРОМОКОДЫ ---
@dp.message(Command("shop"))
async def shop_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 За Монеты", callback_data="shop_cat_money"), InlineKeyboardButton(text="💎 За BBC", callback_data="shop_cat_bbc")]
    ])
    await m.answer("🛒 <b>МАГАЗИН</b>\nВыбери категорию:", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("shop_"))
async def shop_cb(c: CallbackQuery, state: FSMContext):
    action = c.data.split("_")[1:]
    
    if action[0] == "cat":
        if action[1] == "money":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏳ Сброс КД (1 500 💰)", callback_data="shop_buy_cd")],
                [InlineKeyboardButton(text="🎁 Коробка Удачи (5 000 💰)", callback_data="shop_buy_lootbox")],
                [InlineKeyboardButton(text="💎 1 BBC (50 000 💰)", callback_data="shop_buy_bbccoin")],
                [InlineKeyboardButton(text="👑 Ранг VIP (100 000 💰)", callback_data="shop_buy_rank_VIP")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="shop_back")]
            ])
            await c.message.edit_text("💰 <b>Магазин Монет:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
        elif action[1] == "bbc":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎫 Ранг Титан (50 💎)", callback_data="shop_buy_rank_Титан")],
                [InlineKeyboardButton(text="🔥 4⭐ Карта (50 💎)", callback_data="shop_buy_card_4")],
                [InlineKeyboardButton(text="🌟 5⭐ Карта (150 💎)", callback_data="shop_buy_card_5")],
                [InlineKeyboardButton(text="📝 Сменить титул (10 💎)", callback_data="shop_buy_title")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="shop_back")]
            ])
            await c.message.edit_text("💎 <b>Магазин BBC:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
        return await c.answer()

    if action[0] == "back": return await shop_cmd(c.message)

    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money, bbc_money FROM users WHERE user_id = ?", (c.from_user.id,))
        u = await res.fetchone()
        if not u: return
        u_money, u_bbc = u

        if action[1] == "cd" and u_money >= 1500:
            await db.execute("UPDATE users SET money=money-1500, last_draw=? WHERE user_id=?", ((datetime.now() - timedelta(days=2)).isoformat(), c.from_user.id))
            await c.message.edit_text("✅ Кулдаун сброшен!")
        elif action[1] == "lootbox" and u_money >= 5000:
            win = random.randint(1000, 15000)
            await db.execute("UPDATE users SET money=money-5000+? WHERE user_id=?", (win, c.from_user.id))
            await c.message.edit_text(f"🎁 Из коробки выпало {win} монет!")
        elif action[1] == "bbccoin" and u_money >= 50000:
            await db.execute("UPDATE users SET money=money-50000, bbc_money=bbc_money+1 WHERE user_id=?", (c.from_user.id,))
            await c.message.edit_text("💎 Куплен 1 BBC!")
        elif action[1] == "title" and u_bbc >= 10:
            await state.set_state(ShopStates.waiting_for_title)
            await c.message.edit_text("📝 Напиши в чат свой новый крутой титул:")
        elif action[1] == "rank":
            r_name = action[2]
            if r_name == "VIP" and u_money >= 100000:
                await db.execute("UPDATE users SET money=money-100000, rank=? WHERE user_id=?", (r_name, c.from_user.id))
                await c.message.edit_text("👑 Куплен VIP!")
            elif r_name == "Титан" and u_bbc >= 50:
                await db.execute("UPDATE users SET bbc_money=bbc_money-50, rank=? WHERE user_id=?", (r_name, c.from_user.id))
                await c.message.edit_text("🎫 Куплен Титан!")
            else: return await c.answer("❌ Мало средств!", show_alert=True)
        elif action[1] == "card":
            rar, price = int(action[2]), 50 if action[2] == "4" else 150
            if u_bbc < price: return await c.answer(f"❌ Нужно {price} BBC!", show_alert=True)
            card = await (await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rar,))).fetchone()
            if not card: return await c.answer("⚠️ Карт нет!", show_alert=True)
            is_dup = await (await db.execute("SELECT count FROM inventory WHERE user_id=? AND card_id=?", (c.from_user.id, card[0]))).fetchone()
            if is_dup: await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id=? AND card_id=?", (c.from_user.id, card[0]))
            else: await db.execute("INSERT INTO inventory VALUES (?,?,1)", (c.from_user.id, card[0]))
            await db.execute("UPDATE users SET bbc_money=bbc_money-? WHERE user_id=?", (price, c.from_user.id))
            await c.message.delete()
            await c.message.answer_photo(card[2], caption=f"🎉 Карта за BBC!\n🃏 <b>{card[1]}</b> {'(Дубликат)' if is_dup else ''}", parse_mode=ParseMode.HTML)
        else: return await c.answer("❌ Мало средств!", show_alert=True)
        await db.commit()
    await c.answer()

@dp.message(ShopStates.waiting_for_title)
async def process_new_title(m: Message, state: FSMContext):
    new_title = m.text[:30]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bbc_money=bbc_money-10, titles=? WHERE user_id=?", (new_title, m.from_user.id))
        await db.commit()
    await m.answer(f"✅ Твой новый титул: <b>{new_title}</b>", parse_mode=ParseMode.HTML)
    await state.clear()

@dp.message(Command("promo"))
async def promo_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 2: return await m.answer("🎁 Использование: /promo КОД")
    code = args[1]
    async with aiosqlite.connect(DB_PATH) as db:
        if await (await db.execute("SELECT 1 FROM used_promos WHERE user_id=? AND code=?", (m.from_user.id, code))).fetchone():
            return await m.answer("❌ Код уже активирован!")
        p = await (await db.execute("SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?", (code,))).fetchone()
        if not p or p[2] <= 0: return await m.answer("❌ Код не найден или закончился.")
        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(f"UPDATE users SET {col}={col}+? WHERE user_id=?", (p[1], m.from_user.id))
        await db.execute("UPDATE promocodes SET uses_left=uses_left-1 WHERE code=?", (code,))
        await db.execute("INSERT INTO used_promos VALUES (?, ?)", (m.from_user.id, code))
        await db.commit()
    await m.answer(f"✅ Промокод активирован! +{p[1]} {'Монет' if p[0] == 'money' else 'BBC'}")

@dp.message(Command("pay"))
async def pay_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 3 or not args[1].isdigit() or not args[2].isdigit():
        return await m.answer("💸 Формат: <code>/pay [ID_игрока] [сумма]</code>", parse_mode=ParseMode.HTML)
    
    target_id, amount = int(args[1]), int(args[2])
    if amount <= 0: return await m.answer("❌ Сумма должна быть больше нуля!")
    if target_id == m.from_user.id: return await m.answer("❌ Нельзя перевести самому себе!")

    async with aiosqlite.connect(DB_PATH) as db:
        sender = await (await db.execute("SELECT money, is_banned FROM users WHERE user_id=?", (m.from_user.id,))).fetchone()
        if not sender or sender[1] or sender[0] < amount:
            return await m.answer("❌ Недостаточно средств или вы в бане!")
        
        receiver = await (await db.execute("SELECT 1 FROM users WHERE user_id=?", (target_id,))).fetchone()
        if not receiver:
            return await m.answer("❌ Игрок не найден в базе данных! Убедись, что он нажимал /start")
        
        tax = int(amount * 0.03) # Комиссия 3%
        final_amount = amount - tax

        await db.execute("UPDATE users SET money=money-? WHERE user_id=?", (amount, m.from_user.id))
        await db.execute("UPDATE users SET money=money+? WHERE user_id=?", (final_amount, target_id))
        await db.commit()
        
    await m.answer(f"✅ Успешный перевод!\nОтправлено: {amount} 💰\nКомиссия системы (3%): {tax} 💰\nИгрок получил: {final_amount} 💰")
                               # --- МЕГА-АДМИНКА ---
@dp.message(Command("admin"))
async def admin_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"), InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🎁 Созд. Промо", callback_data="adm_promo"), InlineKeyboardButton(text="📋 Список Промо", callback_data="adm_promolist")],
        [InlineKeyboardButton(text="❌ Удал. Промо", callback_data="adm_delpromo"), InlineKeyboardButton(text="🔍 Профиль", callback_data="adm_info")],
        [InlineKeyboardButton(text="💰 Дать монеты", callback_data="adm_give_m"), InlineKeyboardButton(text="💎 Дать BBC", callback_data="adm_give_b")],
        [InlineKeyboardButton(text="📉 Отнять монеты", callback_data="adm_take_m"), InlineKeyboardButton(text="🗑 Обнулить акк", callback_data="adm_wipe")],
        [InlineKeyboardButton(text="🚫 Выдать Бан", callback_data="adm_ban"), InlineKeyboardButton(text="🕊 Снять Бан", callback_data="adm_unban")]
    ])
    await m.answer("👑 <b>Главная Админ-панель</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("adm_"))
async def admin_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    action = c.data.split("_")[1]
    
    if action == "stats":
        async with aiosqlite.connect(DB_PATH) as db:
            uc = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            cc = (await (await db.execute("SELECT COUNT(*) FROM cards")).fetchone())[0]
        await c.message.edit_text(f"📊 <b>Статистика:</b>\n👥 Игроков: {uc}\n🃏 Карт: {cc}", parse_mode=ParseMode.HTML)
    elif action == "promolist":
        async with aiosqlite.connect(DB_PATH) as db:
            promos = await (await db.execute("SELECT code, reward_type, reward_val, uses_left FROM promocodes")).fetchall()
        if not promos:
            await c.message.answer("📝 Нет активных промокодов.")
        else:
            txt = "📋 <b>Активные промокоды:</b>\n\n"
            for p in promos: txt += f"Код: <code>{p[0]}</code> | {p[1]} | +{p[2]} | Остаток: {p[3]}\n"
            await c.message.answer(txt, parse_mode=ParseMode.HTML)
    elif action == "promo":
        await c.message.answer("Формат: <code>[Код] [money/bbc_money] [Сумма] [Активации]</code>", parse_mode=ParseMode.HTML)
        await state.set_state(AdminStates.waiting_for_promo_data)
    elif action == "delpromo":
        await c.message.answer("Введите код для удаления:")
        await state.set_state(AdminStates.waiting_for_del_promo)
    elif action == "broadcast":
        await c.message.answer("Текст рассылки:")
        await state.set_state(AdminStates.waiting_for_broadcast)
    elif action == "take":
        await c.message.answer(f"Формат: <code>ID СУММА</code>", parse_mode=ParseMode.HTML)
        await state.set_state(AdminStates.waiting_for_take_money)
    elif action == "wipe":
        await c.message.answer("ID юзера для ПОЛНОГО ОБНУЛЕНИЯ:")
        await state.set_state(AdminStates.waiting_for_wipe_account)
    elif action in ("give", "ban", "unban", "info"):
        t = c.data.split("_")[2] if action == "give" else None
        if action == "give": 
            await c.message.answer(f"Формат: <code>ID СУММА</code>", parse_mode=ParseMode.HTML)
            await state.set_state(AdminStates.waiting_for_give_money if t == "m" else AdminStates.waiting_for_give_bbc)
        elif action == "ban":
            await c.message.answer("ID юзера для бана:")
            await state.set_state(AdminStates.waiting_for_ban)
        elif action == "unban":
            await c.message.answer("ID юзера для разбана:")
            await state.set_state(AdminStates.waiting_for_unban)
        elif action == "info":
            await c.message.answer("Введи ID юзера:")
            await state.set_state(AdminStates.waiting_for_user_info)
    await c.answer()

@dp.message(AdminStates.waiting_for_promo_data)
async def process_promo(m: Message, state: FSMContext):
    args = m.text.split()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO promocodes VALUES (?,?,?,?)", (args[0], args[1], int(args[2]), int(args[3])))
            await db.commit()
        await m.answer(f"✅ Промокод создан!")
    except: await m.answer("❌ Ошибка!")
    await state.clear()

@dp.message(AdminStates.waiting_for_del_promo)
async def process_del_promo(m: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promocodes WHERE code=?", (m.text,))
        await db.commit()
    await m.answer(f"✅ Промокод {m.text} удален из базы.")
    await state.clear()

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(m: Message, state: FSMContext, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db: users = await (await db.execute("SELECT user_id FROM users")).fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"📢 <b>Рассылка:</b>\n\n{m.text}", parse_mode=ParseMode.HTML)
            sent += 1
        except: pass
    await m.answer(f"✅ Доставлено: {sent}/{len(users)}")
    await state.clear()

@dp.message(AdminStates.waiting_for_give_money)
async def process_give_m(m: Message, state: FSMContext): await _process_give(m, state, "money")
@dp.message(AdminStates.waiting_for_give_bbc)
async def process_give_b(m: Message, state: FSMContext): await _process_give(m, state, "bbc_money")

async def _process_give(m: Message, state: FSMContext, col: str):
    args = m.text.split()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (int(args[1]), int(args[0])))
        await db.commit()
    await m.answer("✅ Выдано.")
    await state.clear()

@dp.message(AdminStates.waiting_for_take_money)
async def process_take_m(m: Message, state: FSMContext):
    args = m.text.split()
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        return await m.answer("❌ Ошибка формата! Введи: ID СУММА")
    uid, amt = int(args[0]), int(args[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money = CASE WHEN money - ? < 0 THEN 0 ELSE money - ? END WHERE user_id = ?", (amt, amt, uid))
        await db.commit()
    await m.answer(f"✅ Успешно списано {amt} монет у пользователя {uid}.")
    await state.clear()

@dp.message(AdminStates.waiting_for_wipe_account)
async def process_wipe(m: Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("❌ ID должен быть числом.")
    uid = int(m.text)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id=?", (uid,))
        await db.execute("DELETE FROM inventory WHERE user_id=?", (uid,))
        await db.execute("DELETE FROM used_promos WHERE user_id=?", (uid,))
        await db.commit()
    await m.answer(f"🗑 Аккаунт {uid} полностью обнулен и удален из базы.")
    await state.clear()

@dp.message(AdminStates.waiting_for_ban)
async def process_ban(m: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (int(m.text),))
        await db.commit()
    await m.answer(f"🚫 Пользователь {m.text} забанен.")
    await state.clear()

@dp.message(AdminStates.waiting_for_unban)
async def process_unban(m: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (int(m.text),))
        await db.commit()
    await m.answer(f"🕊 Пользователь {m.text} разбанен.")
    await state.clear()

@dp.message(AdminStates.waiting_for_user_info)
async def process_user_info(m: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        u = await (await db.execute("SELECT nickname, money, bbc_money, is_banned FROM users WHERE user_id=?", (int(m.text),))).fetchone()
    if u: await m.answer(f"👤 <b>{u[0]}</b>\n💰 {u[1]} | 💎 {u[2]}\nБан: {'Да 🚫' if u[3] else 'Нет ✅'}", parse_mode=ParseMode.HTML)
    else: await m.answer("❌ Юзер не найден.")
    await state.clear()

@dp.message(F.photo & F.caption.startswith("/add_card"))
async def add_card(m: Message):
    if m.from_user.id != ADMIN_ID: return
    p = m.caption.split()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)", (" ".join(p[1:-1]), int(p[-1]), m.photo[-1].file_id))
        await db.commit()
    await m.answer("✅ Карта добавлена!")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
