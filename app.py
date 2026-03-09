import asyncio, logging, random, aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                            InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 1548461377
DB_PATH = "gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()
bot = Bot(token=TOKEN)

RARITY_NAMES = {
    1: "Обычная", 2: "Редкая", 3: "Эпическая",
    4: "Легендарная", 5: "Мифическая"
}
REWARDS = {
    1: {"n": 100,  "d": 50},
    2: {"n": 150,  "d": 75},
    3: {"n": 250,  "d": 100},
    4: {"n": 500,  "d": 250},
    5: {"n": 1000, "d": 700}
}
RANK_PRICES = {
    "Серебро": 100_000,
    "Золото":  250_000,
    "Платина": 500_000,
    "Алмаз":   1_000_000,
    "Титан":   2_500_000
}
ITEM_PRICES = {
    "Амулет": 50,
    "Кирка":  50,
    "Часы":   60
}

CASINO_RIG_CHANCE = None


class AdminStates(StatesGroup):
    waiting_for_promo_data = State()
    waiting_for_rig        = State()
    waiting_for_mythril    = State()


class DuelStates(StatesGroup):
    waiting_for_accept = State()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT,
                rank TEXT DEFAULT 'Бронза',
                money INTEGER DEFAULT 0,
                bbc_money INTEGER DEFAULT 0,
                last_draw TEXT,
                titles TEXT DEFAULT 'Новичок',
                draw_count INTEGER DEFAULT 0,
                last_daily TEXT,
                last_work TEXT,
                is_banned INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                bank_balance INTEGER DEFAULT 0,
                bank_last_update TEXT,
                biz_level INTEGER DEFAULT 0,
                biz_last_collect TEXT,
                equipped_item TEXT DEFAULT NULL,
                clan_id INTEGER DEFAULT 0
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, rarity INTEGER, file_id TEXT
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER, card_id INTEGER,
                count INTEGER DEFAULT 1, level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, card_id)
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, owner_id INTEGER,
                points INTEGER DEFAULT 0,
                bank_m INTEGER DEFAULT 0, bank_b INTEGER DEFAULT 0
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS clan_members (
                user_id INTEGER PRIMARY KEY,
                clan_id INTEGER,
                role TEXT DEFAULT 'Участник'
            )''')
        await db.commit()


async def add_exp(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT exp, level FROM users WHERE user_id = ?", (user_id,))
        row = await res.fetchone()
        if not row:
            return
        exp, lvl = row[0] + amount, row[1]
        if exp >= lvl * 100:
            lvl += 1
            exp -= lvl * 100
        await db.execute(
            "UPDATE users SET exp = ?, level = ? WHERE user_id = ?",
            (exp, lvl, user_id))
        await db.commit()
        @dp.message(Command("start"))
      async def start_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        r = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, nickname, rank, bank_last_update) "
            "VALUES (?,?,?,?)",
            (m.from_user.id, m.from_user.first_name, r, datetime.now().isoformat()))
        await db.commit()

    await m.answer("👋 Бот запущен на Railway!")
    await profile_cmd(m)
    await help_cmd(m)


@dp.message(Command("help") | F.text.lower().in_({"помощь", "команды", "меню"}))
async def help_cmd(m: Message):
    text = (
        "📜 <b>СПИСОК КОМАНД:</b>\n\n"
        "Вы можете использовать как команды через <code>/</code>, "
        "так и просто писать слова:\n\n"
        "👤 <b>Профиль</b> — показать твою статистику\n"
        "🎴 <b>Карта</b> — вытянуть новую карту\n"
        "🛒 <b>Магазин</b> — магазин рангов и предметов\n"
        "🏦 <b>Банк [dep/with] [сумма]</b> — управление счётом\n"
        "🏢 <b>Бизнес</b> — управление твоим ларьком\n"
        "🛡 <b>Клан</b> — меню клана\n"
        "💸 <b>Передать [ID] [сумма]</b> — перевод денег\n\n"
        "🎮 <b>Мини-игры:</b>\n"
        "🎰 <b>Казино [ставка]</b> — рулетка\n"
        "🪙 <b>Монетка [ставка] [орел/решка]</b> — подбросить монету\n"
        "🔫 <b>Дуэль</b> — смертельная игра (ответом на сообщение)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛒 Магазин",  callback_data="help_shop"),
        InlineKeyboardButton(text="🏦 Банк",     callback_data="help_econ")
    ]])
    await m.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ✅ ИСПРАВЛЕНО: добавлен отсутствовавший обработчик help-кнопок
@dp.callback_query(F.data.in_({"help_shop", "help_econ"}))
async def help_nav_cb(c: CallbackQuery):
    if c.data == "help_shop":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Ранги",
                                  callback_data=f"shop_{c.from_user.id}_ranks"),
             InlineKeyboardButton(text="⚔️ Предметы",
                                  callback_data=f"shop_{c.from_user.id}_items")],
            [InlineKeyboardButton(text="⭐️ Купить BBC (За Звёзды)",
                                  url="t.me/gde_DiadSoul")]
        ])
        await c.message.edit_text(
            "🛒 <b>МАГАЗИН</b>\nПокупка BBC и апгрейд карт за Telegram Stars: "
            "пиши в ЛС @gde_DiadSoul\n\nВыбери категорию:",
            reply_markup=kb, parse_mode=ParseMode.HTML)
    elif c.data == "help_econ":
        await c.message.edit_text(
            "🏦 <b>Банк</b>\n\nКоманды:\n"
            "• <code>банк</code> — посмотреть баланс\n"
            "• <code>банк dep [сумма]</code> — положить деньги\n"
            "• <code>банк with [сумма]</code> — снять деньги\n\n"
            "💡 Деньги в банке приносят 1% в час.",
            parse_mode=ParseMode.HTML)
    await c.answer()


@dp.message(Command("profile") | F.text.lower().in_({"профиль", "мой профиль", "стата"}))
async def profile_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT nickname, rank, money, bbc_money, titles, draw_count, "
            "is_banned, level, exp, equipped_item FROM users WHERE user_id = ?",
            (m.from_user.id,))
        u = await res.fetchone()
        if not u:
            return await m.answer("Сначала напиши /start")
        if u[6]:
            return await m.answer("⛔ Ваш аккаунт заблокирован.")
        res = await db.execute(
            "SELECT SUM(count) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0] or 0

    next_lvl  = u[7] * 100
    item_str  = f" | 🎒 Предмет: {u[9]}" if u[9] else ""
    text = (
        f"<b>🪪 МИНИ-ПРОФИЛЬ:</b> {u[0]}\n"
        f"🏅 Ранг: {u[1]} | 🏆 Титул: {u[4]}\n"
        f"🌟 Уровень: {u[7]} (EXP: {u[8]}/{next_lvl})\n"
        f"💰 Монеты: {u[2]} | 💎 BBC: {u[3]}{item_str}\n"
        f"🎴 Карт: {inv_cnt} | 🔄 До гаранта (5⭐): {50 - u[5]}"
    )
    try:
        photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
        if photos.total_count > 0:
            await m.answer_photo(photos.photos[0][0].file_id,
                                 caption=text, parse_mode=ParseMode.HTML)
        else:
            await m.answer(text, parse_mode=ParseMode.HTML)
    except Exception:
        await m.answer(text, parse_mode=ParseMode.HTML)
# ✅ ИСПРАВЛЕНО: декоратор был вдавлен внутрь profile_cmd
@dp.message(Command("bank") | F.text.lower().startswith("банк"))
async def bank_cmd(m: Message):
    args = m.text.lower().split()
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT money, bank_balance, bank_last_update FROM users WHERE user_id=?",
            (m.from_user.id,))
        row = await res.fetchone()
        if not row:
            return

        last_upd     = datetime.fromisoformat(row[2])
        hours_passed = (datetime.now() - last_upd).total_seconds() // 3600
        new_bank     = row[1]

        if hours_passed >= 1 and new_bank > 0:
            new_bank += int(new_bank * 0.01 * hours_passed)
            await db.execute(
                "UPDATE users SET bank_balance=?, bank_last_update=? WHERE user_id=?",
                (new_bank, datetime.now().isoformat(), m.from_user.id))
            await db.commit()

        if len(args) == 1:
            return await m.answer(
                f"🏦 <b>Ваш Банк</b>\n"
                f"Баланс: {new_bank} 💰\nНаличные: {row[0]} 💰\n\n"
                f"Пример: <i>банк dep 100</i> или <i>банк with 50</i>",
                parse_mode=ParseMode.HTML)

        action = args[1]
        if len(args) < 3 or not args[2].isdigit():
            return await m.answer("Формат: банк [dep/with] [сумма]")

        amt = int(args[2])
        if action == "dep":
            if row[0] < amt:
                return await m.answer("❌ Недостаточно наличных!")
            await db.execute(
                "UPDATE users SET money=money-?, bank_balance=bank_balance+? WHERE user_id=?",
                (amt, amt, m.from_user.id))
        elif action == "with":
            if new_bank < amt:
                return await m.answer("❌ Недостаточно средств в банке!")
            await db.execute(
                "UPDATE users SET money=money+?, bank_balance=bank_balance-? WHERE user_id=?",
                (amt, amt, m.from_user.id))

        await db.commit()
        await m.answer("✅ Операция успешна!")


@dp.message(Command("biz") | F.text.lower().in_({"бизнес", "биз"}))
async def biz_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT money, biz_level, biz_last_collect FROM users WHERE user_id=?",
            (m.from_user.id,))
        row = await res.fetchone()
        if not row:
            return

        if row[1] == 0:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Купить ларёк (10 000 💰)",
                                     callback_data="biz_buy")
            ]])
            return await m.answer("🏢 У вас нет бизнеса.", reply_markup=kb)

        last_col = datetime.fromisoformat(row[2]) if row[2] else datetime.now()
        hours    = (datetime.now() - last_col).total_seconds() // 3600
        pending  = int(hours * (50 * row[1]))

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 Собрать прибыль",
                                  callback_data="biz_collect")],
            [InlineKeyboardButton(text=f"⬆ Улучшить ({(row[1]+1)*15000} 💰)",
                                  callback_data="biz_upgrade")]
        ])
        await m.answer(
            f"🏢 <b>Ваш Бизнес (Ур. {row[1]})</b>\nНакоплено: {pending} 💰",
            reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("biz_"))
async def biz_cb(c: CallbackQuery):
    action = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT money, biz_level, biz_last_collect FROM users WHERE user_id=?",
            (c.from_user.id,))
        row = await res.fetchone()
        if not row:
            return await c.answer("Профиль не найден!", show_alert=True)

        if action == "buy" and row[1] == 0:
            if row[0] < 10000:
                return await c.answer("❌ Нужно 10000 монет!", show_alert=True)
            await db.execute(
                "UPDATE users SET money=money-10000, biz_level=1, "
                "biz_last_collect=? WHERE user_id=?",
                (datetime.now().isoformat(), c.from_user.id))
            await c.message.edit_text("✅ Вы купили бизнес!")

        elif action == "collect" and row[1] > 0:
            # ✅ ИСПРАВЛЕНО: защита от NULL
            last_col = datetime.fromisoformat(row[2]) if row[2] else datetime.now()
            hours    = (datetime.now() - last_col).total_seconds() // 3600
            if hours < 1:
                return await c.answer("⏳ Прибыль копится (минимум 1 час)!",
                                      show_alert=True)
            profit = int(hours * (50 * row[1]))
            await db.execute(
                "UPDATE users SET money=money+?, biz_last_collect=? WHERE user_id=?",
                (profit, datetime.now().isoformat(), c.from_user.id))
            await c.message.edit_text(f"✅ Собрано {profit} 💰!")
            await add_exp(c.from_user.id, 5)

        elif action == "upgrade" and row[1] > 0:
            cost = (row[1] + 1) * 15000
            if row[0] < cost:
                return await c.answer(f"❌ Нужно {cost} монет!", show_alert=True)
            await db.execute(
                "UPDATE users SET money=money-?, biz_level=biz_level+1 WHERE user_id=?",
                (cost, c.from_user.id))
            await c.message.edit_text(f"✅ Бизнес улучшен до {row[1]+1} уровня!")

        await db.commit()
        # ✅ ИСПРАВЛЕНО: декоратор был вдавлен внутрь draw_cmd
@dp.message(Command("draw") | F.text.lower().in_({"карта", "карту", "крутить"}))
async def draw_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT rank, last_draw, draw_count, is_banned, equipped_item "
            "FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await res.fetchone()
        if not row or row[3]:
            return

        r, ld, dc, item = row[0], row[1], row[2], row[4]

        cd_hours = 4
        if r == "Мифрил":                        cd_hours = 0.003
        elif r == "Титан":                        cd_hours = 2
        elif r in ("Алмаз", "Платина", "VIP"):   cd_hours = 3
        if item == "Часы":
            cd_hours *= 0.8
        cd = timedelta(hours=cd_hours)

        if ld and datetime.now() < datetime.fromisoformat(ld) + cd:
            wait = (datetime.fromisoformat(ld) + cd) - datetime.now()
            return await m.answer(
                f"⏳ Рано! Жди {wait.seconds // 3600}ч. "
                f"{(wait.seconds // 60) % 60}мин.")

        p   = random.random()
        rar = 1
        if p < 0.015:   rar = 5
        elif p < 0.07:  rar = 4
        elif p < 0.20:  rar = 3
        elif p < 0.50:  rar = 2
        if dc >= 49:    rar = 5   # гарант

        card = await (await db.execute(
            "SELECT card_id, name, file_id FROM cards "
            "WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rar,))).fetchone()
        if not card:
            return await m.answer("⚠️ Ошибка: карт нет в базе.")

        is_dup = await (await db.execute(
            "SELECT count FROM inventory WHERE user_id=? AND card_id=?",
            (m.from_user.id, card[0]))).fetchone()
        rew = REWARDS[rar]["d" if is_dup else "n"]

        if is_dup:
            await db.execute(
                "UPDATE inventory SET count=count+1 WHERE user_id=? AND card_id=?",
                (m.from_user.id, card[0]))
        else:
            await db.execute(
                "INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,1)",
                (m.from_user.id, card[0]))

        await db.execute(
            "UPDATE users SET money=money+?, last_draw=?, draw_count=? WHERE user_id=?",
            (rew, datetime.now().isoformat(), 0 if rar == 5 else dc + 1, m.from_user.id))
        await db.commit()

    await add_exp(m.from_user.id, 10)
    cap = (
        f"🃏 <b>{card[1]}</b> (ID: {card[0]})\n"
        f"Ранг: {'⭐' * rar} ({RARITY_NAMES.get(rar)})\n"
        f"{'♻️ Дубликат!' if is_dup else '✨ Новая карта!'}\n"
        f"💰 +{rew} монет"
    )
    await m.answer_photo(card[2], caption=cap, parse_mode=ParseMode.HTML)


@dp.message(Command("clan") | F.text.lower().startswith("клан"))
async def clan_cmd(m: Message):
    args = m.text.lower().split()
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT clan_id FROM users WHERE user_id=?", (m.from_user.id,))
        u = await res.fetchone()

        if not u or u[0] == 0:
            if len(args) >= 3 and args[1] in ("create", "создать"):
                name = " ".join(args[2:])
                b = await (await db.execute(
                    "SELECT bbc_money FROM users WHERE user_id=?",
                    (m.from_user.id,))).fetchone()
                if b[0] < 100:
                    return await m.answer("❌ Нужно 100 BBC для создания клана!")
                await db.execute(
                    "UPDATE users SET bbc_money=bbc_money-100 WHERE user_id=?",
                    (m.from_user.id,))
                await db.execute(
                    "INSERT INTO clans (name, owner_id) VALUES (?,?)",
                    (name, m.from_user.id))
                clan_id = (await (await db.execute(
                    "SELECT last_insert_rowid()")).fetchone())[0]
                await db.execute(
                    "UPDATE users SET clan_id=? WHERE user_id=?",
                    (clan_id, m.from_user.id))
                await db.execute(
                    "INSERT INTO clan_members VALUES (?,?,?)",
                    (m.from_user.id, clan_id, "Глава"))
                await db.commit()
                return await m.answer(
                    f"🛡 Клан <b>{name}</b> успешно создан!",
                    parse_mode=ParseMode.HTML)
            return await m.answer(
                "У вас нет клана. Создать: клан создать [Название] (Цена: 100 BBC)")

        c = await (await db.execute(
            "SELECT name, points, bank_m, bank_b FROM clans WHERE clan_id=?",
            (u[0],))).fetchone()
        await m.answer(
            f"🛡 <b>Клан: {c[0]}</b>\nОчки: {c[1]}\n"
            f"Банк: {c[2]} 💰 | {c[3]} 💎",
            parse_mode=ParseMode.HTML)


@dp.message(Command("shop") | F.text.lower().in_({"магазин", "шоп", "маркет"}))
async def shop_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Ранги",
                              callback_data=f"shop_{m.from_user.id}_ranks"),
         InlineKeyboardButton(text="⚔️ Предметы",
                              callback_data=f"shop_{m.from_user.id}_items")],
        [InlineKeyboardButton(text="⭐️ Купить BBC (За Звёзды)",
                              url="t.me/gde_DiadSoul")]
    ])
    await m.answer(
        "🛒 <b>МАГАЗИН</b>\n"
        "Покупка BBC и апгрейд карт за Telegram Stars: пиши в ЛС @gde_DiadSoul\n\n"
        "Выбери категорию:",
        reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("shop_"))
async def shop_cb(c: CallbackQuery):
    parts = c.data.split("_")
    if int(parts[1]) != c.from_user.id:
        return await c.answer("❌ Это не твой магазин!", show_alert=True)

    action = parts[2]
    if action == "ranks":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Серебро (100k)",
                                  callback_data=f"buy_{c.from_user.id}_rank_Серебро")],
            [InlineKeyboardButton(text="Золото (250k)",
                                  callback_data=f"buy_{c.from_user.id}_rank_Золото")],
            [InlineKeyboardButton(text="Платина (500k)",
                                  callback_data=f"buy_{c.from_user.id}_rank_Платина")],
            [InlineKeyboardButton(text="Алмаз (1kk)",
                                  callback_data=f"buy_{c.from_user.id}_rank_Алмаз")],
            [InlineKeyboardButton(text="Титан (2.5kk)",
                                  callback_data=f"buy_{c.from_user.id}_rank_Титан")]
        ])
        await c.message.edit_text(
            "💰 <b>Покупка Рангов (за монеты):</b>",
            reply_markup=kb, parse_mode=ParseMode.HTML)

    elif action == "items":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🍀 Амулет удачи (+шанс) (50 💎)",
                                  callback_data=f"buy_{c.from_user.id}_item_Амулет")],
            [InlineKeyboardButton(text="⛏ Кирка (+работа) (50 💎)",
                                  callback_data=f"buy_{c.from_user.id}_item_Кирка")],
            [InlineKeyboardButton(text="⏱ Часы (-кд гачи) (60 💎)",
                                  callback_data=f"buy_{c.from_user.id}_item_Часы")]
        ])
        await c.message.edit_text(
            "💎 <b>Покупка Предметов (за BBC):</b>\nЭкипировать можно только 1!",
            reply_markup=kb, parse_mode=ParseMode.HTML)


# ✅ ИСПРАВЛЕНО: добавлен отсутствовавший обработчик покупок
@dp.callback_query(F.data.startswith("buy_"))
async def buy_cb(c: CallbackQuery):
    parts = c.data.split("_")
    if int(parts[1]) != c.from_user.id:
        return await c.answer("❌ Это не твой магазин!", show_alert=True)

    category  = parts[2]   # "rank" или "item"
    item_name = parts[3]

    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute(
            "SELECT money, bbc_money FROM users WHERE user_id=?",
            (c.from_user.id,))
        row = await res.fetchone()
        if not row:
            return await c.answer("❌ Профиль не найден!", show_alert=True)

        if category == "rank":
            price = RANK_PRICES.get(item_name)
            if not price:
                return await c.answer("❌ Ранг не найден!", show_alert=True)
            if row[0] < price:
                return await c.answer(f"❌ Нужно {price:,} монет!", show_alert=True)
            await db.execute(
                "UPDATE users SET money=money-?, rank=? WHERE user_id=?",
                (price, item_name, c.from_user.id))
            await db.commit()
            await c.message.edit_text(
                f"✅ Вы купили ранг <b>{item_name}</b>!",
                parse_mode=ParseMode.HTML)

        elif category == "item":
            price = ITEM_PRICES.get(item_name)
            if not price:
                return await c.answer("❌ Предмет не найден!", show_alert=True)
            if row[1] < price:
                return await c.answer(f"❌ Нужно {price} BBC!", show_alert=True)
            await db.execute(
                "UPDATE users SET bbc_money=bbc_money-?, equipped_item=? WHERE user_id=?",
                (price, item_name, c.from_user.id))
            await db.commit()
            await c.message.edit_text(
                f"✅ Вы купили и экипировали <b>{item_name}</b>!",
                parse_mode=ParseMode.HTML)

    await c.answer()
        async def get_win_chance(user_id, base_chance):
    global CASINO_RIG_CHANCE
    if CASINO_RIG_CHANCE is not None:
        chance = CASINO_RIG_CHANCE
        CASINO_RIG_CHANCE = None
        return chance
    async with aiosqlite.connect(DB_PATH) as db:
        item = await (await db.execute(
            "SELECT equipped_item FROM users WHERE user_id=?",
            (user_id,))).fetchone()
        if item and item[0] == "Амулет":
            return base_chance + 10
    return base_chance


@dp.message(Command("casino") | F.text.lower().startswith("казино"))
async def casino_cmd(m: Message):
    args = m.text.lower().split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.answer("🎰 Формат: казино [ставка]")
    bet = int(args[1])

    async with aiosqlite.connect(DB_PATH) as db:
        u = await (await db.execute(
            "SELECT money FROM users WHERE user_id = ?",
            (m.from_user.id,))).fetchone()
        if not u or u[0] < bet:
            return await m.answer("❌ Недостаточно монет!")

        chance = await get_win_chance(m.from_user.id, 25)
        if random.randint(1, 100) <= chance:
            await db.execute(
                "UPDATE users SET money = money + ? WHERE user_id = ?",
                (bet, m.from_user.id))
            txt = f"✅ Победа! Выигрыш: {bet * 2}"
        else:
            await db.execute(
                "UPDATE users SET money = money - ? WHERE user_id = ?",
                (bet, m.from_user.id))
            txt = f"💀 Проигрыш. Минус {bet} монет."
        await db.commit()

    await add_exp(m.from_user.id, 1)
    await m.answer(f"🎰 {txt}")


@dp.message(Command("coin") | F.text.lower().startswith("монетка"))
async def coin_cmd(m: Message):
    args = m.text.lower().split()
    if len(args) < 3 or not args[1].isdigit() or args[2] not in ("орел", "решка"):
        return await m.answer("🪙 Формат: монетка [ставка] [орел/решка]")

    bet, choice = int(args[1]), args[2]

    async with aiosqlite.connect(DB_PATH) as db:
        u = await (await db.execute(
            "SELECT money FROM users WHERE user_id = ?",
            (m.from_user.id,))).fetchone()
        if not u or u[0] < bet:
            return await m.answer("❌ Недостаточно монет!")

        chance = await get_win_chance(m.from_user.id, 50)
        if random.randint(1, 100) <= chance:
            await db.execute(
                "UPDATE users SET money = money + ? WHERE user_id = ?",
                (bet, m.from_user.id))
            txt = f"✅ Выпал {choice}! Ты выиграл {bet * 2} монет."
        else:
            await db.execute(
                "UPDATE users SET money = money - ? WHERE user_id = ?",
                (bet, m.from_user.id))
            lose = "решка" if choice == "орел" else "орел"
            txt  = f"💀 Выпал(а) {lose}. Ты проиграл {bet} монет."
        await db.commit()

    await add_exp(m.from_user.id, 1)
    await m.answer(f"🪙 {txt}")


@dp.message(Command("duel") | F.text.lower().in_({"дуэль"}))
async def duel_cmd(m: Message, state: FSMContext):
    if not m.reply_to_message:
        return await m.answer(
            "🔫 Ответь на сообщение игрока словом «дуэль», чтобы бросить вызов!\n"
            "Проигравший БАНИТСЯ и отдаёт ВСЁ!")

    target_id = m.reply_to_message.from_user.id
    if target_id == m.from_user.id or m.reply_to_message.from_user.is_bot:
        return

    await state.update_data(p1=m.from_user.id, p2=target_id)
    await state.set_state(DuelStates.waiting_for_accept)
    await m.answer(
        f"⚠️ {m.reply_to_message.from_user.first_name}, тебя вызвали на "
        f"смертельную дуэль!\nШанс выстрела 20%. Проигравший потеряет аккаунт.\n"
        f"Напиши «принять» для старта.")


@dp.message(DuelStates.waiting_for_accept)
async def duel_accept(m: Message, state: FSMContext):
    data = await state.get_data()
    if m.from_user.id != data["p2"]:
        return
    if m.text.lower() != "принять":
        await state.clear()
        return await m.answer("Отмена дуэли.")

    await m.answer("🔫 Барабан крутится...")
    await asyncio.sleep(2)

    p1, p2  = data["p1"], data["p2"]
    shot    = random.randint(1, 100)
    loser   = None
    if shot <= 20:  loser = p1
    elif shot <= 40: loser = p2

    if not loser:
        await state.clear()
        return await m.answer("💨 Щелчок... Пистолет дал осечку. Оба живы.")

    winner = p2 if loser == p1 else p1

    async with aiosqlite.connect(DB_PATH) as db:
        l_data = await (await db.execute(
            "SELECT money, bbc_money FROM users WHERE user_id=?",
            (loser,))).fetchone()
        if l_data:
            await db.execute(
                "UPDATE users SET money=money+?, bbc_money=bbc_money+? WHERE user_id=?",
                (l_data[0], l_data[1], winner))
        await db.execute(
            "UPDATE users SET is_banned=1, money=0, bbc_money=0 WHERE user_id=?",
            (loser,))
        await db.commit()

    await state.clear()
    await m.answer(f"💥 ВЫСТРЕЛ!\nИгрок {loser} убит и забанен. Победитель забирает всё!")


@dp.message(Command("pay") | F.text.lower().startswith("передать"))
async def pay_cmd(m: Message):
    args      = m.text.lower().split()
    target_id = None
    amount    = 0   # ✅ ИСПРАВЛЕНО: инициализация во избежание NameError

    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
        amount    = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
    elif len(args) >= 3 and args[1].isdigit() and args[2].isdigit():
        target_id, amount = int(args[1]), int(args[2])

    if not target_id or amount <= 0:
        return await m.answer(
            "💸 Формат: передать [ID] [сумма] "
            "или ответом на сообщение: передать [сумма]")

    async with aiosqlite.connect(DB_PATH) as db:
        sender = await (await db.execute(
            "SELECT money FROM users WHERE user_id=?",
            (m.from_user.id,))).fetchone()
        if not sender or sender[0] < amount:
            return await m.answer("❌ Недостаточно средств!")

        tax = int(amount * 0.03)
        await db.execute(
            "UPDATE users SET money=money-? WHERE user_id=?",
            (amount, m.from_user.id))
        await db.execute(
            "UPDATE users SET money=money+? WHERE user_id=?",
            (amount - tax, target_id))
        await db.commit()
    await m.answer(f"✅ Перевод успешен. Удержана комиссия 3% ({tax}).")


# ──────────────────────────── АДМИНКА ────────────────────────────

@dp.message(Command("adminhelp"))
async def admin_help_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    text = (
        "👑 <b>Справка по Админке:</b>\n\n"
        "<code>/add_card [редкость]</code> — В ответ на сообщение с фото.\n"
        "<code>/up_card</code> — В ответ на юзера, повышает уровень его последней карты.\n"
        "<code>/rig [процент]</code> — Подкрутить шанс следующей мини-игры.\n"
        "<code>/mythril [ID]</code> — Выдать уникальный ранг Мифрил.\n"
    )
    await m.answer(text, parse_mode=ParseMode.HTML)


# ✅ ИСПРАВЛЕНО: убран невалидный F.photo из фильтра;
#    файл берётся из reply-сообщения, а не из сообщения админа
@dp.message(Command("add_card"))
async def add_card_reply(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    if not m.reply_to_message:
        return await m.answer("Ответь на сообщение пользователя с фото!")
    if not m.reply_to_message.photo:
        return await m.answer("В сообщении, на которое ты отвечаешь, нет фото!")

    args   = m.text.split()
    rarity = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    name   = (m.reply_to_message.from_user.username
              or m.reply_to_message.from_user.first_name)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)",
            (name, rarity, m.reply_to_message.photo[-1].file_id))
        await db.commit()
    await m.answer(f"✅ Персональная карта {name} (⭐{rarity}) добавлена в базу!")


@dp.message(Command("rig"))
async def rig_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return
    global CASINO_RIG_CHANCE
    CASINO_RIG_CHANCE = int(args[1])
    await m.answer(f"⚙️ Подкрут активирован! Шанс {CASINO_RIG_CHANCE}% для следующей игры.")


@dp.message(Command("mythril"))
async def mythril_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    args = m.text.split()
    if len(args) < 2:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET rank='Мифрил' WHERE user_id=?", (int(args[1]),))
        await db.commit()
    await m.answer("👑 Игроку выдан ранг МИФРИЛ!")


@dp.message(Command("up_card"))
async def up_card_cmd(m: Message):
    if m.from_user.id != ADMIN_ID or not m.reply_to_message:
        return
    target_id = m.reply_to_message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        res  = await db.execute(
            "SELECT card_id, level FROM inventory "
            "WHERE user_id=? ORDER BY ROWID DESC LIMIT 1", (target_id,))
        card = await res.fetchone()
        if card:
            await db.execute(
                "UPDATE inventory SET level=level+1 WHERE user_id=? AND card_id=?",
                (target_id, card[0]))
            await db.commit()
            await m.answer(
                f"✅ Карта ID {card[0]} игрока {target_id} "
                f"улучшена до {card[1]+1} уровня!")


# ─────────────────────────────── MAIN ───────────────────────────

async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
