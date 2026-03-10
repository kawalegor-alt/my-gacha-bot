import asyncio
import logging
import random
import os
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import (
    Message, BotCommand, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    TelegramObject,
)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from typing import Any, Callable, Dict, Awaitable

# ╔══════════════════════════════════════════════════════════════╗
# ║                      КОНФИГУРАЦИЯ                           ║
# ╚══════════════════════════════════════════════════════════════╝

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1548461377"))
DB_PATH = "gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# ╔══════════════════════════════════════════════════════════════╗
# ║                       КОНСТАНТЫ                             ║
# ╚══════════════════════════════════════════════════════════════╝

RARITY_NAMES = {
    1: "Обычная ⚪", 2: "Редкая 🟢", 3: "Эпическая 🔵",
    4: "Легендарная 🟣", 5: "Мифическая 🔴",
}
RARITY_STARS = {r: "⭐" * r for r in range(1, 6)}

REWARDS = {
    1: {"n": 100, "d": 50},
    2: {"n": 150, "d": 75},
    3: {"n": 250, "d": 100},
    4: {"n": 500, "d": 250},
    5: {"n": 1000, "d": 700},
}

SHOP_CATALOG = [
    {"id": "reset_cd",       "name": "⏳ Сброс КД Гачи",        "price": 1500,  "unique": False},
    {"id": "buy_bbc",        "name": "💎 Купить BBC (×N)",       "price": 5000,  "unique": False},
    {"id": "title_master",   "name": "🏷 Титул «Мастер»",       "price": 3000,  "unique": True},
    {"id": "title_legend",   "name": "🏷 Титул «Легенда»",      "price": 10000, "unique": True},
    {"id": "title_champion", "name": "🏷 Титул «Чемпион»",      "price": 7000,  "unique": True},
    {"id": "vip_7d",         "name": "👑 VIP-статус (7 дней)",   "price": 20000, "unique": True},
    {"id": "mult_15",        "name": "💹 Множитель x1.5",       "price": 15000, "unique": True},
    {"id": "rank_elite",     "name": "🎖 Ранг «Элита»",         "price": 25000, "unique": True},
]

BANK_PLANS = {
    "24h": {"hours": 24, "rate": 0.05, "label": "24 ч — 5 %"},
    "48h": {"hours": 48, "rate": 0.12, "label": "48 ч — 12 %"},
    "72h": {"hours": 72, "rate": 0.20, "label": "72 ч — 20 %"},
}

DUEL_HP = 3
DUEL_HIT_CHANCE = 0.55
BET_PRESETS = [100, 500, 1000, 5000]

# ╔══════════════════════════════════════════════════════════════╗
# ║                  ГЛОБАЛЬНОЕ СОСТОЯНИЕ                       ║
# ╚══════════════════════════════════════════════════════════════╝

active_duels: Dict[int, dict] = {}
crash_games: Dict[int, dict] = {}
casino_mode: str = "normal"

# ╔══════════════════════════════════════════════════════════════╗
# ║                     FSM-СОСТОЯНИЯ                           ║
# ╚══════════════════════════════════════════════════════════════╝

class AdminStates(StatesGroup):
    waiting_for_promo_data = State()
    waiting_for_target_id = State()
    waiting_for_amount = State()
    waiting_for_promo_delete = State()
    waiting_for_card_rarity = State()


class ShopStates(StatesGroup):
    waiting_for_quantity = State()


class GameStates(StatesGroup):
    waiting_for_bet = State()


class BankStates(StatesGroup):
    waiting_for_amount = State()


# ╔══════════════════════════════════════════════════════════════╗
# ║              MIDDLEWARE — ЧЁРНЫЙ СПИСОК (БАН)               ║
# ╚══════════════════════════════════════════════════════════════╝

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT is_banned FROM users WHERE user_id = ?",
                    (user.id,),
                )
                row = await cur.fetchone()
                if row and row[0] == 1:
                    if isinstance(event, CallbackQuery):
                        await event.answer()
                    return
        return await handler(event, data)


dp.message.middleware(BanCheckMiddleware())
dp.callback_query.middleware(BanCheckMiddleware())

# ╔══════════════════════════════════════════════════════════════╗
# ║              БАЗА ДАННЫХ — СОЗДАНИЕ И МИГРАЦИЯ              ║
# ╚══════════════════════════════════════════════════════════════╝

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
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
            winstreak INTEGER DEFAULT 0,
            spouse_id INTEGER DEFAULT 0,
            marriage_date TEXT,
            is_banned INTEGER DEFAULT 0,
            vip_until TEXT,
            coin_multiplier REAL DEFAULT 1.0
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rarity INTEGER,
            file_id TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            card_id INTEGER,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, card_id)
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward_type TEXT,
            reward_val INTEGER,
            uses_left INTEGER
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promo_used (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS bank_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            interest_rate REAL,
            deposit_date TEXT,
            mature_date TEXT,
            collected INTEGER DEFAULT 0
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS game_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        await db.commit()


async def migrate_db():
    global casino_mode
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("PRAGMA table_info(users)")
        existing = {row[1] for row in await cur.fetchall()}
        migrations = {
            "winstreak":       "INTEGER DEFAULT 0",
            "spouse_id":       "INTEGER DEFAULT 0",
            "marriage_date":   "TEXT",
            "is_banned":       "INTEGER DEFAULT 0",
            "vip_until":       "TEXT",
            "coin_multiplier": "REAL DEFAULT 1.0",
        }
        for col, typedef in migrations.items():
            if col not in existing:
                await db.execute(
                    f"ALTER TABLE users ADD COLUMN {col} {typedef}"
                )
                logging.info("[MIGRATION] users: added '%s'", col)
        for ddl in (
            """CREATE TABLE IF NOT EXISTS promo_used (
                user_id INTEGER, code TEXT, PRIMARY KEY (user_id, code))""",
            """CREATE TABLE IF NOT EXISTS bank_deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, amount INTEGER, interest_rate REAL,
                deposit_date TEXT, mature_date TEXT,
                collected INTEGER DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS game_settings (
                key TEXT PRIMARY KEY, value TEXT)""",
        ):
            await db.execute(ddl)
        cur = await db.execute(
            "SELECT value FROM game_settings WHERE key = 'casino_mode'"
        )
        row = await cur.fetchone()
        if row:
            casino_mode = row[0]
        await db.commit()
    logging.info("[MIGRATION] completed")


# ╔══════════════════════════════════════════════════════════════╗
# ║                    ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ                  ║
# ╚══════════════════════════════════════════════════════════════╝

def is_vip(vip_until: str | None) -> bool:
    if not vip_until:
        return False
    try:
        return datetime.now() < datetime.fromisoformat(vip_until)
    except Exception:
        return False


def apply_multiplier(base: int, mult: float) -> int:
    return int(base * (mult if mult and mult > 0 else 1.0))


def parse_positive_int(text: str) -> int | None:
    try:
        val = int(text)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None


async def safe_edit(msg: Message, text: str, kb=None):
    try:
        await msg.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await msg.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"),
         InlineKeyboardButton(text="🎴 Гача", callback_data="menu_draw")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="menu_shop"),
         InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton(text="🏦 Банк", callback_data="menu_bank"),
         InlineKeyboardButton(text="🏆 Топы", callback_data="menu_tops")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv")],
        [InlineKeyboardButton(text="📅 Бонус", callback_data="menu_daily"),
         InlineKeyboardButton(text="💼 Работа", callback_data="menu_work")],
    ])


def back_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")]
    ])


def bet_buttons(game: str) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for a in BET_PRESETS:
        row.append(
            InlineKeyboardButton(text=f"{a} 💰", callback_data=f"gbet_{game}_{a}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="♻️ Всё", callback_data=f"gbet_{game}_all"),
        InlineKeyboardButton(text="✏️ Другая", callback_data=f"gbet_{game}_cust"),
    ])
    rows.append([InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def casino_win_check(base_chance: float) -> bool:
    if casino_mode == "luck":
        chance = min(base_chance * 1.7, 0.90)
    elif casino_mode == "drain":
        chance = base_chance * 0.35
    else:
        chance = base_chance
    return random.random() < chance


def generate_crash_point() -> float:
    lam = {"luck": 0.4, "drain": 2.0}.get(casino_mode, 0.7)
    cp = round(1.0 + random.expovariate(lam), 2)
    return min(max(cp, 1.10), 15.0)


def is_in_duel(uid: int) -> bool:
    for d in active_duels.values():
        if uid in (d["challenger"], d["opponent"]) and d["status"] in (
            "pending",
            "active",
        ):
            return True
    return False


async def transfer_all_assets(db, winner_id: int, loser_id: int):
    cur = await db.execute(
        "SELECT money, bbc_money, rank, spouse_id FROM users WHERE user_id = ?",
        (loser_id,),
    )
    loser = await cur.fetchone()
    if not loser:
        return
    lmoney, lbbc, lrank, lspouse = loser

    await db.execute(
        "UPDATE users SET money = money + ?, bbc_money = bbc_money + ?, "
        "winstreak = winstreak + 1 WHERE user_id = ?",
        (lmoney, lbbc, winner_id),
    )

    rank_order = {"Бронза": 0, "Элита": 1, "Мифрил": 2}
    cur2 = await db.execute(
        "SELECT rank FROM users WHERE user_id = ?", (winner_id,)
    )
    w_rank = (await cur2.fetchone())[0]
    if rank_order.get(lrank, 0) > rank_order.get(w_rank, 0):
        await db.execute(
            "UPDATE users SET rank = ? WHERE user_id = ?", (lrank, winner_id)
        )

    cur3 = await db.execute(
        "SELECT card_id, count FROM inventory WHERE user_id = ?", (loser_id,)
    )
    for card_id, cnt in await cur3.fetchall():
        cur4 = await db.execute(
            "SELECT count FROM inventory WHERE user_id = ? AND card_id = ?",
            (winner_id, card_id),
        )
        ex = await cur4.fetchone()
        if ex:
            await db.execute(
                "UPDATE inventory SET count = count + ? "
                "WHERE user_id = ? AND card_id = ?",
                (cnt, winner_id, card_id),
            )
        else:
            await db.execute(
                "INSERT INTO inventory (user_id, card_id, count) VALUES (?,?,?)",
                (winner_id, card_id, cnt),
            )

    if lspouse:
        await db.execute(
            "UPDATE users SET spouse_id = 0, marriage_date = NULL "
            "WHERE user_id = ?",
            (lspouse,),
        )

    await db.execute("DELETE FROM users WHERE user_id = ?", (loser_id,))
    await db.execute("DELETE FROM inventory WHERE user_id = ?", (loser_id,))
    await db.execute("DELETE FROM bank_deposits WHERE user_id = ?", (loser_id,))
    await db.execute("DELETE FROM promo_used WHERE user_id = ?", (loser_id,))
    await db.commit()


async def set_commands(bot: Bot):
    cmds = [
        BotCommand(command="start", description="🏠 Регистрация / Меню"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="daily", description="📅 Ежедневный бонус"),
        BotCommand(command="work", description="💼 Работа"),
        BotCommand(command="inventory", description="🎒 Инвентарь"),
        BotCommand(command="top", description="🏆 Лидеры"),
        BotCommand(command="shop", description="🛒 Магазин"),
        BotCommand(command="casino", description="🎰 Казино"),
        BotCommand(command="bank", description="🏦 Банк"),
        BotCommand(command="duel", description="⚔️ Дуэль"),
        BotCommand(command="marry", description="💍 Предложить брак"),
        BotCommand(command="divorce", description="💔 Развод"),
        BotCommand(command="transfer", description="💸 Перевод монет"),
        BotCommand(command="promo", description="🎁 Промокод"),
    ]
    await bot.set_my_commands(cmds)


# ╔══════════════════════════════════════════════════════════════╗
# ║               /start  /menu  — ГЛАВНОЕ МЕНЮ                ║
# ╚══════════════════════════════════════════════════════════════╝

@dp.message(Command("start"))
async def start_cmd(m: Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        r = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?,?,?)",
            (m.from_user.id, m.from_user.first_name, r),
        )
        await db.commit()
    await m.answer(
        "🏠 <b>Добро пожаловать!</b>\nРегистрация пройдена. Выбери действие:",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("menu"))
async def menu_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "📋 <b>Главное меню</b>",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "menu_back")
async def menu_back_cb(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(c.message, "📋 <b>Главное меню</b>", main_menu_kb())
    await c.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║                          ПРОФИЛЬ                            ║
# ╚══════════════════════════════════════════════════════════════╝

async def _build_profile(db, user_id: int, bot: Bot | None = None) -> tuple[str, int | None]:
    cur = await db.execute(
        "SELECT nickname, rank, money, bbc_money, titles, draw_count, "
        "winstreak, spouse_id, marriage_date, vip_until, coin_multiplier "
        "FROM users WHERE user_id = ?",
        (user_id,),
    )
    u = await cur.fetchone()
    if not u:
        return "❌ Профиль не найден. Нажми /start", None

    nick, rank, money, bbc, titles, dc, ws, sp_id, m_date, vip_u, mult = u

    cur2 = await db.execute(
        "SELECT SUM(count) FROM inventory WHERE user_id = ?", (user_id,)
    )
    inv_cnt = (await cur2.fetchone())[0] or 0

    vip_str = "✅ активен" if is_vip(vip_u) else "нет"
    mult_str = f"x{mult:.1f}" if mult and mult > 1.0 else "x1.0"

    marriage_str = "нет"
    if sp_id:
        cur3 = await db.execute(
            "SELECT nickname FROM users WHERE user_id = ?", (sp_id,)
        )
        sp = await cur3.fetchone()
        if sp and m_date:
            delta = datetime.now() - datetime.fromisoformat(m_date)
            marriage_str = f"{sp[0]} ({delta.days}д. {delta.seconds // 3600}ч.)"
        elif not sp:
            await db.execute(
                "UPDATE users SET spouse_id = 0, marriage_date = NULL "
                "WHERE user_id = ?",
                (user_id,),
            )
            await db.commit()

    text = (
        f"<b>🪪 ПРОФИЛЬ:</b> {nick}\n\n"
        f"🏅 Ранг: {rank}\n"
        f"👑 VIP: {vip_str}\n"
        f"🏷 Титул: {titles}\n"
        f"💰 Монеты: {money:,} | 💎 BBC: {bbc}\n"
        f"📊 Множитель: {mult_str}\n"
        f"🎴 Карт: {inv_cnt}\n"
        f"🔄 До гаранта (5⭐): {max(0, 50 - dc)}\n"
        f"⚔️ Серия побед: {ws}\n"
        f"💍 Брак: {marriage_str}"
    )
    return text, None


@dp.message(Command("profile"))
async def profile_cmd(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        text, _ = await _build_profile(db, m.from_user.id, bot)
    try:
        photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
        if photos.total_count > 0:
            await m.answer_photo(
                photos.photos[0][0].file_id,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=back_menu_kb(),
            )
            return
    except Exception:
        pass
    await m.answer(text, parse_mode=ParseMode.HTML, reply_markup=back_menu_kb())


@dp.callback_query(F.data == "menu_profile")
async def profile_cb(c: CallbackQuery, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        text, _ = await _build_profile(db, c.from_user.id, bot)
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║                           ГАЧА                              ║
# ╚══════════════════════════════════════════════════════════════╝

@dp.message(F.text.lower().in_({"карта", "карту", "/draw"}))
async def draw_text_cmd(m: Message):
    await _do_draw(m)


@dp.callback_query(F.data == "menu_draw")
async def draw_cb(c: CallbackQuery):
    await c.answer()
    await _do_draw(c.message, user=c.from_user)


async def _do_draw(m: Message, user=None):
    u = user or m.from_user
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT rank, last_draw, draw_count, vip_until, coin_multiplier "
            "FROM users WHERE user_id = ?",
            (u.id,),
        )
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ Сначала /start")
        rank, ld, dc, vip_u, mult = row

        if rank == "Мифрил":
            cd = timedelta(seconds=10)
        elif is_vip(vip_u) or rank == "Элита":
            cd = timedelta(hours=10)
        else:
            cd = timedelta(hours=24)

        if ld and datetime.now() < datetime.fromisoformat(ld) + cd:
            wait = (datetime.fromisoformat(ld) + cd) - datetime.now()
            h = int(wait.total_seconds()) // 3600
            mn = (int(wait.total_seconds()) // 60) % 60
            return await m.answer(
                f"⏳ Подожди ещё {h}ч. {mn}мин.",
                reply_markup=back_menu_kb(),
            )

        p = random.random()
        if rank == "Мифрил":
            rar = 5 if p < 0.15 else (4 if p < 0.35 else (3 if p < 0.65 else 2))
        elif is_vip(vip_u) or rank == "Элита":
            rar = 5 if p < 0.04 else (4 if p < 0.12 else (3 if p < 0.35 else 2))
        else:
            rar = (
                5 if p < 0.015
                else (4 if p < 0.07 else (3 if p < 0.20 else (2 if p < 0.50 else 1)))
            )

        if dc >= 49:
            rar = 5

        cur2 = await db.execute(
            "SELECT card_id, name, file_id FROM cards "
            "WHERE rarity = ? ORDER BY RANDOM() LIMIT 1",
            (rar,),
        )
        card = await cur2.fetchone()
        if not card:
            return await m.answer(
                f"⚠️ Карт редкости {rar}⭐ нет в базе. Сообщи админу!"
            )

        cur3 = await db.execute(
            "SELECT count FROM inventory WHERE user_id = ? AND card_id = ?",
            (u.id, card[0]),
        )
        is_dup = await cur3.fetchone()
        rew = REWARDS[rar]["d" if is_dup else "n"]
        rew = apply_multiplier(rew, mult)

        if is_dup:
            await db.execute(
                "UPDATE inventory SET count = count + 1 "
                "WHERE user_id = ? AND card_id = ?",
                (u.id, card[0]),
            )
        else:
            await db.execute(
                "INSERT INTO inventory VALUES (?,?,1)", (u.id, card[0])
            )

        await db.execute(
            "UPDATE users SET money = money + ?, last_draw = ?, draw_count = ? "
            "WHERE user_id = ?",
            (rew, datetime.now().isoformat(), 0 if rar == 5 else dc + 1, u.id),
        )
        await db.commit()

    cap = (
        f"🃏 <b>{card[1]}</b>\n\n"
        f"Редкость: {'⭐' * rar} ({RARITY_NAMES.get(rar, '?')})\n"
        f"{'♻️ Дубликат!' if is_dup else '✨ Новая карта!'}\n"
        f"💰 +{rew} монет"
    )
    await m.answer_photo(
        card[2], caption=cap, parse_mode=ParseMode.HTML, reply_markup=back_menu_kb()
    )


# ╔══════════════════════════════════════════════════════════════╗
# ║               ЭКОНОМИКА — /daily /work /transfer            ║
# ╚══════════════════════════════════════════════════════════════╝

async def _do_daily(user_id: int, msg: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT last_daily, coin_multiplier FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            return await msg.answer("❌ /start сначала")
        ld, mult = row
        if ld and datetime.now() < datetime.fromisoformat(ld) + timedelta(days=1):
            return await msg.answer(
                "📅 Бонус раз в 24 часа!", reply_markup=back_menu_kb()
            )
        reward = apply_multiplier(random.randint(200, 500), mult)
        await db.execute(
            "UPDATE users SET money = money + ?, last_daily = ? WHERE user_id = ?",
            (reward, datetime.now().isoformat(), user_id),
        )
        await db.commit()
    await msg.answer(
        f"🎁 Ежедневная награда: <b>{reward}</b> монет!",
        parse_mode=ParseMode.HTML,
        reply_markup=back_menu_kb(),
    )


@dp.message(Command("daily"))
async def daily_cmd(m: Message):
    await _do_daily(m.from_user.id, m)


@dp.callback_query(F.data == "menu_daily")
async def daily_cb(c: CallbackQuery):
    await c.answer()
    await _do_daily(c.from_user.id, c.message)


async def _do_work(user_id: int, msg: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT last_work, coin_multiplier FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            return await msg.answer("❌ /start сначала")
        lw, mult = row
        if lw and datetime.now() < datetime.fromisoformat(lw) + timedelta(hours=1):
            return await msg.answer(
                "💼 Ты устал. Отдохни часик.", reply_markup=back_menu_kb()
            )
        reward = apply_multiplier(random.randint(50, 150), mult)
        await db.execute(
            "UPDATE users SET money = money + ?, last_work = ? WHERE user_id = ?",
            (reward, datetime.now().isoformat(), user_id),
        )
        await db.commit()
    await msg.answer(
        f"⚒ Ты заработал <b>{reward}</b> монет!",
        parse_mode=ParseMode.HTML,
        reply_markup=back_menu_kb(),
    )


@dp.message(Command("work"))
async def work_cmd(m: Message):
    await _do_work(m.from_user.id, m)


@dp.callback_query(F.data == "menu_work")
async def work_cb(c: CallbackQuery):
    await c.answer()
    await _do_work(c.from_user.id, c.message)


@dp.message(Command("transfer"))
async def transfer_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 3:
        return await m.answer(
            "💸 Формат: /transfer [ID] [сумма]", reply_markup=back_menu_kb()
        )
    target_id = parse_positive_int(args[1])
    amount = parse_positive_int(args[2])
    if target_id is None or amount is None:
        return await m.answer("❌ ID и сумма должны быть целыми числами > 0!")
    if target_id == m.from_user.id:
        return await m.answer("❌ Нельзя перевести самому себе!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money FROM users WHERE user_id = ?", (m.from_user.id,)
        )
        sender = await cur.fetchone()
        if not sender:
            return await m.answer("❌ /start сначала")
        if sender[0] < amount:
            return await m.answer("❌ Недостаточно монет!")
        cur2 = await db.execute(
            "SELECT nickname FROM users WHERE user_id = ?", (target_id,)
        )
        recip = await cur2.fetchone()
        if not recip:
            return await m.answer("❌ Получатель не найден!")
        await db.execute(
            "UPDATE users SET money = money - ? WHERE user_id = ?",
            (amount, m.from_user.id),
        )
        await db.execute(
            "UPDATE users SET money = money + ? WHERE user_id = ?",
            (amount, target_id),
        )
        await db.commit()
    await m.answer(f"✅ Переведено {amount} монет игроку {recip[0]}!")


# ╔══════════════════════════════════════════════════════════════╗
# ║                       МАГАЗИН 2.0                           ║
# ╚══════════════════════════════════════════════════════════════╝

def shop_kb() -> InlineKeyboardMarkup:
    rows = []
    for item in SHOP_CATALOG:
        rows.append([
            InlineKeyboardButton(
                text=f"{item['name']} — {item['price']} 💰",
                callback_data=f"sbuy_{item['id']}",
            )
        ])
    rows.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("shop"))
async def shop_cmd(m: Message):
    await m.answer(
        "🛒 <b>МАГАЗИН 2.0</b>\nВыбери товар:",
        reply_markup=shop_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "menu_shop")
async def shop_cb(c: CallbackQuery):
    await safe_edit(c.message, "🛒 <b>МАГАЗИН 2.0</b>\nВыбери товар:", shop_kb())
    await c.answer()


@dp.callback_query(F.data.startswith("sbuy_"))
async def shop_buy_cb(c: CallbackQuery, state: FSMContext):
    item_id = c.data[5:]
    item = next((i for i in SHOP_CATALOG if i["id"] == item_id), None)
    if not item:
        return await c.answer("❌ Товар не найден", show_alert=True)
    await state.update_data(shop_item_id=item_id)
    await state.set_state(ShopStates.waiting_for_quantity)
    if item["unique"]:
        hint = "Этот товар уникальный — введи <b>1</b>."
    else:
        hint = "Введи нужное количество."
    await safe_edit(
        c.message,
        f"🛒 <b>{item['name']}</b>\nЦена за 1: {item['price']} 💰\n\n{hint}",
    )
    await c.answer()


@dp.message(ShopStates.waiting_for_quantity)
async def shop_quantity_handler(m: Message, state: FSMContext):
    qty = parse_positive_int(m.text)
    if qty is None:
        await state.clear()
        return await m.answer("❌ Нужно целое число > 0!", reply_markup=back_menu_kb())

    data = await state.get_data()
    item_id = data.get("shop_item_id")
    item = next((i for i in SHOP_CATALOG if i["id"] == item_id), None)
    if not item:
        await state.clear()
        return await m.answer("❌ Товар не найден.", reply_markup=back_menu_kb())

    if item["unique"] and qty != 1:
        await state.clear()
        return await m.answer(
            "❌ Уникальный товар — можно купить только 1 шт.",
            reply_markup=back_menu_kb(),
        )

    total = item["price"] * qty
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money, titles, rank, coin_multiplier, vip_until "
            "FROM users WHERE user_id = ?",
            (m.from_user.id,),
        )
        u = await cur.fetchone()
        if not u:
            await state.clear()
            return await m.answer("❌ /start сначала")
        money, titles, rank, cur_mult, vip_u = u

        if money < total:
            await state.clear()
            return await m.answer(
                f"❌ Нужно {total} 💰, а у тебя {money}.",
                reply_markup=back_menu_kb(),
            )

        # -- выполняем покупку --
        result_msg = ""
        if item_id == "reset_cd":
            past = (datetime.now() - timedelta(days=2)).isoformat()
            await db.execute(
                "UPDATE users SET money = money - ?, last_draw = ? WHERE user_id = ?",
                (total, past, m.from_user.id),
            )
            result_msg = f"⏳ КД гачи сброшен (x{qty})!"

        elif item_id == "buy_bbc":
            await db.execute(
                "UPDATE users SET money = money - ?, bbc_money = bbc_money + ? "
                "WHERE user_id = ?",
                (total, qty, m.from_user.id),
            )
            result_msg = f"💎 Куплено {qty} BBC!"

        elif item_id.startswith("title_"):
            title_map = {
                "title_master": "Мастер",
                "title_legend": "Легенда",
                "title_champion": "Чемпион",
            }
            new_title = title_map.get(item_id, "Новичок")
            if new_title in (titles or ""):
                await state.clear()
                return await m.answer(
                    "❌ У тебя уже есть этот титул!", reply_markup=back_menu_kb()
                )
            combined = f"{titles}, {new_title}" if titles and titles != "Новичок" else new_title
            await db.execute(
                "UPDATE users SET money = money - ?, titles = ? WHERE user_id = ?",
                (total, combined, m.from_user.id),
            )
            result_msg = f"🏷 Титул «{new_title}» получен!"

        elif item_id == "vip_7d":
            if is_vip(vip_u):
                await state.clear()
                return await m.answer(
                    "❌ VIP уже активен!", reply_markup=back_menu_kb()
                )
            end = (datetime.now() + timedelta(days=7)).isoformat()
            await db.execute(
                "UPDATE users SET money = money - ?, vip_until = ? WHERE user_id = ?",
                (total, end, m.from_user.id),
            )
            result_msg = "👑 VIP-статус на 7 дней активирован!"

        elif item_id == "mult_15":
            if cur_mult and cur_mult >= 1.5:
                await state.clear()
                return await m.answer(
                    "❌ Множитель уже x1.5!", reply_markup=back_menu_kb()
                )
            await db.execute(
                "UPDATE users SET money = money - ?, coin_multiplier = 1.5 "
                "WHERE user_id = ?",
                (total, m.from_user.id),
            )
            result_msg = "💹 Множитель x1.5 установлен навсегда!"

        elif item_id == "rank_elite":
            if rank in ("Элита", "Мифрил"):
                await state.clear()
                return await m.answer(
                    "❌ Ранг уже «Элита» или выше!", reply_markup=back_menu_kb()
                )
            await db.execute(
                "UPDATE users SET money = money - ?, rank = 'Элита' WHERE user_id = ?",
                (total, m.from_user.id),
            )
            result_msg = "🎖 Ранг «Элита» присвоен!"

        await db.commit()
    await state.clear()
    await m.answer(
        f"✅ {result_msg}\n💰 Списано: {total}",
        reply_markup=back_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


# ╔══════════════════════════════════════════════════════════════╗
# ║                ИГРОВОЙ ЦЕНТР — МЕНЮ И СТАВКИ               ║
# ╚══════════════════════════════════════════════════════════════╝

def game_center_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Рулетка", callback_data="gs_roul"),
         InlineKeyboardButton(text="🎲 Кости", callback_data="gs_dice")],
        [InlineKeyboardButton(text="🪙 Монетка", callback_data="gs_coin"),
         InlineKeyboardButton(text="📈 Краш", callback_data="gs_crash")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])


@dp.callback_query(F.data == "menu_games")
async def games_menu_cb(c: CallbackQuery):
    await safe_edit(
        c.message,
        "🎮 <b>ИГРОВОЙ ЦЕНТР</b>\nВыбери игру:",
        game_center_kb(),
    )
    await c.answer()


@dp.callback_query(F.data.in_({"gs_roul", "gs_dice", "gs_coin", "gs_crash"}))
async def game_select_cb(c: CallbackQuery):
    game = c.data[3:]
    names = {"roul": "🎰 Рулетка", "dice": "🎲 Кости", "coin": "🪙 Монетка", "crash": "📈 Краш"}
    await safe_edit(
        c.message,
        f"{names[game]}\n💰 Выбери ставку:",
        bet_buttons(game),
    )
    await c.answer()


@dp.callback_query(F.data.startswith("gbet_"))
async def game_bet_cb(c: CallbackQuery, state: FSMContext):
    parts = c.data.split("_")
    game = parts[1]
    raw_amt = parts[2]

    if raw_amt == "cust":
        await state.update_data(game_type=game)
        await state.set_state(GameStates.waiting_for_bet)
        await safe_edit(c.message, "✏️ Введи сумму ставки:")
        return await c.answer()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money FROM users WHERE user_id = ?", (c.from_user.id,)
        )
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        money = row[0]

    if raw_amt == "all":
        bet = money
    else:
        bet = parse_positive_int(raw_amt)

    if not bet or bet <= 0:
        return await c.answer("❌ Некорректная ставка", show_alert=True)
    if money < bet:
        return await c.answer("❌ Недостаточно монет!", show_alert=True)

    await _show_game_choice(c.message, game, bet, c)
    await c.answer()


@dp.message(GameStates.waiting_for_bet)
async def game_custom_bet(m: Message, state: FSMContext):
    data = await state.get_data()
    game = data.get("game_type", "roul")
    bet = parse_positive_int(m.text)
    if bet is None:
        await state.clear()
        return await m.answer("❌ Целое число > 0!", reply_markup=back_menu_kb())

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money FROM users WHERE user_id = ?", (m.from_user.id,)
        )
        row = await cur.fetchone()
    if not row or row[0] < bet:
        await state.clear()
        return await m.answer("❌ Недостаточно монет!", reply_markup=back_menu_kb())

    await state.clear()
    await _show_game_choice(m, game, bet)


async def _show_game_choice(msg: Message, game: str, bet: int, c: CallbackQuery | None = None):
    if game == "roul":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Красное", callback_data=f"rp_{bet}_r"),
             InlineKeyboardButton(text="⚫ Чёрное", callback_data=f"rp_{bet}_b")],
            [InlineKeyboardButton(text="🟢 Зелёное (x14)", callback_data=f"rp_{bet}_g")],
            [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
        ])
        text = f"🎰 Ставка: <b>{bet}</b> 💰\nВыбери цвет:"
    elif game == "dice":
        rows = [
            [InlineKeyboardButton(text=str(i), callback_data=f"dp_{bet}_{i}") for i in range(1, 4)],
            [InlineKeyboardButton(text=str(i), callback_data=f"dp_{bet}_{i}") for i in range(4, 7)],
            [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        text = f"🎲 Ставка: <b>{bet}</b> 💰\nУгадай число (1-6):"
    elif game == "coin":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🦅 Орёл", callback_data=f"cp_{bet}_h"),
             InlineKeyboardButton(text="🌸 Решка", callback_data=f"cp_{bet}_t")],
            [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
        ])
        text = f"🪙 Ставка: <b>{bet}</b> 💰\nОрёл или решка?"
    elif game == "crash":
        await _start_crash(msg, c.from_user.id if c else msg.from_user.id if hasattr(msg, 'from_user') and msg.from_user else 0, bet)
        return
    else:
        return

    if c:
        await safe_edit(msg, text, kb)
    else:
        await msg.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ── РУЛЕТКА ──────────────────────────────────────────────────

@dp.callback_query(F.data.regexp(r"^rp_\d+_[rbg]$"))
async def roulette_play(c: CallbackQuery):
    parts = c.data.split("_")
    bet = int(parts[1])
    pick = parts[2]

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money, coin_multiplier FROM users WHERE user_id = ?",
            (c.from_user.id,),
        )
        row = await cur.fetchone()
        if not row or row[0] < bet:
            return await c.answer("❌ Недостаточно монет!", show_alert=True)
        money, mult = row

        num = random.randint(0, 36)
        if num == 0:
            color = "g"
        elif num <= 18:
            color = "r"
        else:
            color = "b"

        won = pick == color
        # rig
        if casino_mode == "luck" and not won and random.random() < 0.4:
            color = pick
            won = True
        elif casino_mode == "drain" and won and random.random() < 0.5:
            color = random.choice([x for x in "rbg" if x != pick])
            won = False

        color_name = {"r": "🔴 Красное", "b": "⚫ Чёрное", "g": "🟢 Зелёное"}

        if won:
            w_mult = 14 if pick == "g" else 2
            winnings = apply_multiplier(bet * w_mult, mult)
            profit = winnings - bet
            await db.execute(
                "UPDATE users SET money = money + ? WHERE user_id = ?",
                (profit, c.from_user.id),
            )
            text = (
                f"🎰 Выпало: <b>{color_name[color]}</b> ({num})\n\n"
                f"🎉 Победа! x{w_mult} → +{winnings} 💰"
            )
        else:
            await db.execute(
                "UPDATE users SET money = money - ? WHERE user_id = ?",
                (bet, c.from_user.id),
            )
            text = (
                f"🎰 Выпало: <b>{color_name[color]}</b> ({num})\n\n"
                f"💀 Проигрыш: -{bet} 💰"
            )
        await db.commit()
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ── КОСТИ ────────────────────────────────────────────────────

@dp.callback_query(F.data.regexp(r"^dp_\d+_[1-6]$"))
async def dice_play(c: CallbackQuery):
    parts = c.data.split("_")
    bet = int(parts[1])
    guess = int(parts[2])

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money, coin_multiplier FROM users WHERE user_id = ?",
            (c.from_user.id,),
        )
        row = await cur.fetchone()
        if not row or row[0] < bet:
            return await c.answer("❌ Недостаточно монет!", show_alert=True)
        money, mult = row

        result = random.randint(1, 6)
        won = result == guess
        if casino_mode == "luck" and not won and random.random() < 0.35:
            result = guess
            won = True
        elif casino_mode == "drain" and won and random.random() < 0.5:
            result = random.choice([x for x in range(1, 7) if x != guess])
            won = False

        if won:
            winnings = apply_multiplier(bet * 6, mult)
            profit = winnings - bet
            await db.execute(
                "UPDATE users SET money = money + ? WHERE user_id = ?",
                (profit, c.from_user.id),
            )
            text = f"🎲 Выпало: <b>{result}</b>\n\n🎉 Угадал! x6 → +{winnings} 💰"
        else:
            await db.execute(
                "UPDATE users SET money = money - ? WHERE user_id = ?",
                (bet, c.from_user.id),
            )
            text = f"🎲 Выпало: <b>{result}</b>\n\n💀 Мимо! Ты ставил на {guess}. -{bet} 💰"
        await db.commit()
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ── МОНЕТКА ──────────────────────────────────────────────────

@dp.callback_query(F.data.regexp(r"^cp_\d+_[ht]$"))
async def coin_play(c: CallbackQuery):
    parts = c.data.split("_")
    bet = int(parts[1])
    pick = parts[2]

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money, coin_multiplier FROM users WHERE user_id = ?",
            (c.from_user.id,),
        )
        row = await cur.fetchone()
        if not row or row[0] < bet:
            return await c.answer("❌ Недостаточно монет!", show_alert=True)
        money, mult = row

        result = random.choice(["h", "t"])
        won = result == pick
        if casino_mode == "luck" and not won and random.random() < 0.35:
            result = pick
            won = True
        elif casino_mode == "drain" and won and random.random() < 0.45:
            result = "t" if pick == "h" else "h"
            won = False

        side_name = {"h": "🦅 Орёл", "t": "🌸 Решка"}

        if won:
            winnings = apply_multiplier(int(bet * 1.9), mult)
            profit = winnings - bet
            await db.execute(
                "UPDATE users SET money = money + ? WHERE user_id = ?",
                (profit, c.from_user.id),
            )
            text = f"🪙 {side_name[result]}\n\n🎉 Победа! x1.9 → +{winnings} 💰"
        else:
            await db.execute(
                "UPDATE users SET money = money - ? WHERE user_id = ?",
                (bet, c.from_user.id),
            )
            text = f"🪙 {side_name[result]}\n\n💀 Проигрыш: -{bet} 💰"
        await db.commit()
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ── КРАШ ─────────────────────────────────────────────────────

async def _start_crash(msg: Message, user_id: int, bet: int):
    cp = generate_crash_point()
    crash_games[user_id] = {
        "bet": bet,
        "crash_point": cp,
        "mult": 1.00,
        "chat_id": msg.chat.id,
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔼 Повысить", callback_data="crash_up"),
         InlineKeyboardButton(text="💰 Забрать", callback_data="crash_out")],
    ])
    text = (
        f"📈 <b>КРАШ</b>\nСтавка: {bet} 💰\n\n"
        f"Множитель: <b>x1.00</b>\nПотенц. выигрыш: {bet}"
    )
    sent = await msg.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    crash_games[user_id]["msg_id"] = sent.message_id


@dp.callback_query(F.data == "crash_up")
async def crash_up_cb(c: CallbackQuery):
    g = crash_games.get(c.from_user.id)
    if not g:
        return await c.answer("❌ Нет активной игры", show_alert=True)

    step = round(random.uniform(0.15, 0.50), 2)
    g["mult"] = round(g["mult"] + step, 2)

    if g["mult"] >= g["crash_point"]:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET money = money - ? WHERE user_id = ?",
                (g["bet"], c.from_user.id),
            )
            await db.commit()
        text = (
            f"📈 <b>КРАШ!</b> 💥\n\n"
            f"Крашнулось на <b>x{g['crash_point']}</b>\n"
            f"Твой множитель: x{g['mult']}\n"
            f"💀 Потеряно: {g['bet']} 💰"
        )
        del crash_games[c.from_user.id]
        await safe_edit(c.message, text, back_menu_kb())
    else:
        pot = int(g["bet"] * g["mult"])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔼 Повысить", callback_data="crash_up"),
             InlineKeyboardButton(text="💰 Забрать", callback_data="crash_out")],
        ])
        text = (
            f"📈 <b>КРАШ</b>\nСтавка: {g['bet']} 💰\n\n"
            f"Множитель: <b>x{g['mult']}</b>\n"
            f"Потенц. выигрыш: {pot}"
        )
        await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "crash_out")
async def crash_out_cb(c: CallbackQuery):
    g = crash_games.get(c.from_user.id)
    if not g:
        return await c.answer("❌ Нет активной игры", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT coin_multiplier FROM users WHERE user_id = ?",
            (c.from_user.id,),
        )
        mult = ((await cur.fetchone()) or (1.0,))[0]
        winnings = apply_multiplier(int(g["bet"] * g["mult"]), mult)
        profit = winnings - g["bet"]
        await db.execute(
            "UPDATE users SET money = money + ? WHERE user_id = ?",
            (profit, c.from_user.id),
        )
        await db.commit()

    text = (
        f"📈 <b>Забрал!</b> ✅\n\n"
        f"Множитель: x{g['mult']}\n"
        f"💰 Выигрыш: {winnings} (профит: +{profit})"
    )
    del crash_games[c.from_user.id]
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ── /casino (совместимость со старой командой) ──────────────

@dp.message(Command("casino"))
async def casino_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer(
            "🎰 <b>Казино</b>\nЗайди через меню или используй /casino [ставка]",
            reply_markup=game_center_kb(),
            parse_mode=ParseMode.HTML,
        )
    bet = parse_positive_int(args[1])
    if bet is None:
        return await m.answer("❌ Ставка — целое число > 0!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money, coin_multiplier FROM users WHERE user_id = ?",
            (m.from_user.id,),
        )
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ /start сначала")
        if row[0] < bet:
            return await m.answer("❌ Недостаточно монет!")
        money, mult = row
        won = casino_win_check(0.30)
        if won:
            w_mult = 5 if random.random() < 0.1 else 2
            winnings = apply_multiplier(bet * w_mult, mult)
            profit = winnings - bet
            await db.execute(
                "UPDATE users SET money = money + ? WHERE user_id = ?",
                (profit, m.from_user.id),
            )
            txt = f"🎉 Победа! x{w_mult} → +{winnings} 💰"
        else:
            await db.execute(
                "UPDATE users SET money = money - ? WHERE user_id = ?",
                (bet, m.from_user.id),
            )
            txt = f"💀 Проигрыш: -{bet} 💰"
        await db.commit()
    await m.answer(f"🎰 {txt}", reply_markup=back_menu_kb())


# ╔══════════════════════════════════════════════════════════════╗
# ║              ДУЭЛЬ НА ВЫЖИВАНИЕ — /duel                     ║
# ╚══════════════════════════════════════════════════════════════╝

@dp.message(Command("duel"))
async def duel_cmd(m: Message):
    target_id = None
    if m.reply_to_message and m.reply_to_message.from_user:
        target_id = m.reply_to_message.from_user.id
    else:
        args = (m.text or "").split()
        if len(args) >= 2:
            target_id = parse_positive_int(args[1])
    if not target_id:
        return await m.answer(
            "⚔️ Ответь на сообщение игрока или /duel [ID]",
            reply_markup=back_menu_kb(),
        )
    if target_id == m.from_user.id:
        return await m.answer("❌ Нельзя вызвать самого себя!")
    if is_in_duel(m.from_user.id):
        return await m.answer("❌ Ты уже в дуэли!")
    if is_in_duel(target_id):
        return await m.answer("❌ Этот игрок уже в дуэли!")

    async with aiosqlite.connect(DB_PATH) as db:
        cur1 = await db.execute(
            "SELECT nickname FROM users WHERE user_id = ?", (m.from_user.id,)
        )
        cur2 = await db.execute(
            "SELECT nickname FROM users WHERE user_id = ?", (target_id,)
        )
        u1 = await cur1.fetchone()
        u2 = await cur2.fetchone()
        if not u1:
            return await m.answer("❌ /start сначала")
        if not u2:
            return await m.answer("❌ Противник не зарегистрирован!")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⚔️ Принять вызов",
            callback_data=f"duel_acc_{m.from_user.id}",
        )],
        [InlineKeyboardButton(
            text="🚫 Отклонить",
            callback_data=f"duel_dec_{m.from_user.id}",
        )],
    ])
    sent = await m.answer(
        f"⚔️ <b>ВЫЗОВ НА ДУЭЛЬ!</b>\n\n"
        f"🗡 <b>{u1[0]}</b> вызывает <b>{u2[0]}</b>!\n\n"
        f"⚠️ <i>Проигравший теряет ВСЁ: монеты, BBC, карты, ранг.\n"
        f"Аккаунт проигравшего аннулируется навсегда.</i>\n\n"
        f"Только {u2[0]} может принять.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    active_duels[m.from_user.id] = {
        "challenger": m.from_user.id,
        "opponent": target_id,
        "status": "pending",
        "chat_id": m.chat.id,
        "msg_id": sent.message_id,
        "ch_name": u1[0],
        "op_name": u2[0],
    }


@dp.callback_query(F.data.startswith("duel_acc_"))
async def duel_accept_cb(c: CallbackQuery, bot: Bot):
    ch_id = parse_positive_int(c.data.split("_")[2])
    duel = active_duels.get(ch_id)
    if not duel or duel["status"] != "pending":
        return await c.answer("❌ Дуэль не найдена", show_alert=True)
    if c.from_user.id != duel["opponent"]:
        return await c.answer("❌ Это не твой вызов!", show_alert=True)

    duel["status"] = "active"
    duel["hp"] = {duel["challenger"]: DUEL_HP, duel["opponent"]: DUEL_HP}
    duel["turn"] = duel["challenger"]

    turn_name = duel["ch_name"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔫 Выстрелить",
            callback_data=f"duel_shoot_{ch_id}",
        )]
    ])
    await safe_edit(
        c.message,
        f"⚔️ <b>ДУЭЛЬ НАЧАЛАСЬ!</b>\n\n"
        f"❤️ {duel['ch_name']}: {'🟥' * duel['hp'][duel['challenger']]}\n"
        f"❤️ {duel['op_name']}: {'🟥' * duel['hp'][duel['opponent']]}\n\n"
        f"🎯 Ход: <b>{turn_name}</b> — жми кнопку!",
        kb,
    )
    await c.answer()


@dp.callback_query(F.data.startswith("duel_dec_"))
async def duel_decline_cb(c: CallbackQuery):
    ch_id = parse_positive_int(c.data.split("_")[2])
    duel = active_duels.get(ch_id)
    if not duel or duel["status"] != "pending":
        return await c.answer("❌ Дуэль не найдена", show_alert=True)
    if c.from_user.id != duel["opponent"]:
        return await c.answer("❌ Это не твой вызов!", show_alert=True)
    del active_duels[ch_id]
    await safe_edit(c.message, "🚫 Дуэль отклонена.", back_menu_kb())
    await c.answer()


@dp.callback_query(F.data.startswith("duel_shoot_"))
async def duel_shoot_cb(c: CallbackQuery, bot: Bot):
    ch_id = parse_positive_int(c.data.split("_")[2])
    duel = active_duels.get(ch_id)
    if not duel or duel["status"] != "active":
        return await c.answer("❌ Дуэль не активна", show_alert=True)
    if c.from_user.id != duel["turn"]:
        return await c.answer("❌ Не твой ход!", show_alert=True)

    shooter = c.from_user.id
    target = (
        duel["opponent"] if shooter == duel["challenger"] else duel["challenger"]
    )
    hit = random.random() < DUEL_HIT_CHANCE

    log = ""
    shooter_name = duel["ch_name"] if shooter == duel["challenger"] else duel["op_name"]
    target_name = duel["op_name"] if target == duel["opponent"] else duel["ch_name"]

    if hit:
        duel["hp"][target] -= 1
        log = f"💥 <b>{shooter_name}</b> попал! (-1 HP у {target_name})"
    else:
        log = f"💨 <b>{shooter_name}</b> промахнулся!"

    if duel["hp"][target] <= 0:
        winner_id = shooter
        loser_id = target
        winner_name = shooter_name
        loser_name = target_name

        async with aiosqlite.connect(DB_PATH) as db:
            await transfer_all_assets(db, winner_id, loser_id)

        del active_duels[ch_id]
        await safe_edit(
            c.message,
            f"⚔️ <b>ДУЭЛЬ ОКОНЧЕНА!</b>\n\n"
            f"{log}\n\n"
            f"🏆 Победитель: <b>{winner_name}</b>\n"
            f"💀 <b>{loser_name}</b> — аккаунт аннулирован.\n\n"
            f"Все монеты, BBC, карты и ранг переданы победителю!",
            back_menu_kb(),
        )
    else:
        duel["turn"] = target
        next_name = target_name
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔫 Выстрелить",
                callback_data=f"duel_shoot_{ch_id}",
            )]
        ])
        await safe_edit(
            c.message,
            f"⚔️ <b>ДУЭЛЬ</b>\n\n"
            f"{log}\n\n"
            f"❤️ {duel['ch_name']}: {'🟥' * duel['hp'][duel['challenger']]}{'⬛' * (DUEL_HP - duel['hp'][duel['challenger']])}\n"
            f"❤️ {duel['op_name']}: {'🟥' * duel['hp'][duel['opponent']]}{'⬛' * (DUEL_HP - duel['hp'][duel['opponent']])}\n\n"
            f"🎯 Ход: <b>{next_name}</b>",
            kb,
        )
    await c.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║                         БАНК                                ║
# ╚══════════════════════════════════════════════════════════════╝

def bank_menu_kb() -> InlineKeyboardMarkup:
    rows = []
    for plan_id, info in BANK_PLANS.items():
        rows.append([InlineKeyboardButton(
            text=f"📥 {info['label']}",
            callback_data=f"bank_dep_{plan_id}",
        )])
    rows.append([InlineKeyboardButton(text="📋 Мои вклады", callback_data="bank_check")])
    rows.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("bank"))
async def bank_cmd(m: Message):
    await m.answer(
        "🏦 <b>БАНК</b>\nВложи монеты под проценты.\n"
        "⚠️ Досрочное снятие невозможно!",
        reply_markup=bank_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "menu_bank")
async def bank_cb(c: CallbackQuery):
    await safe_edit(
        c.message,
        "🏦 <b>БАНК</b>\nВложи монеты под проценты.\n"
        "⚠️ Досрочное снятие невозможно!",
        bank_menu_kb(),
    )
    await c.answer()


@dp.callback_query(F.data.startswith("bank_dep_"))
async def bank_deposit_cb(c: CallbackQuery, state: FSMContext):
    plan_id = c.data[9:]
    if plan_id not in BANK_PLANS:
        return await c.answer("❌ План не найден", show_alert=True)
    plan = BANK_PLANS[plan_id]
    await state.update_data(bank_plan=plan_id)
    await state.set_state(BankStates.waiting_for_amount)
    await safe_edit(
        c.message,
        f"🏦 План: <b>{plan['label']}</b>\n"
        f"Введи сумму вклада (целое число > 0):",
    )
    await c.answer()


@dp.message(BankStates.waiting_for_amount)
async def bank_amount_handler(m: Message, state: FSMContext):
    amount = parse_positive_int(m.text)
    if amount is None:
        await state.clear()
        return await m.answer("❌ Целое число > 0!", reply_markup=back_menu_kb())

    data = await state.get_data()
    plan_id = data.get("bank_plan")
    plan = BANK_PLANS.get(plan_id)
    if not plan:
        await state.clear()
        return await m.answer("❌ Ошибка плана.", reply_markup=back_menu_kb())

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT money FROM users WHERE user_id = ?", (m.from_user.id,)
        )
        row = await cur.fetchone()
        if not row or row[0] < amount:
            await state.clear()
            return await m.answer("❌ Недостаточно монет!", reply_markup=back_menu_kb())

        now = datetime.now()
        mature = now + timedelta(hours=plan["hours"])
        await db.execute(
            "UPDATE users SET money = money - ? WHERE user_id = ?",
            (amount, m.from_user.id),
        )
        await db.execute(
            "INSERT INTO bank_deposits "
            "(user_id, amount, interest_rate, deposit_date, mature_date) "
            "VALUES (?,?,?,?,?)",
            (m.from_user.id, amount, plan["rate"], now.isoformat(), mature.isoformat()),
        )
        await db.commit()

    ret = int(amount * (1 + plan["rate"]))
    await state.clear()
    await m.answer(
        f"✅ Вклад открыт!\n"
        f"💰 Сумма: {amount}\n"
        f"📈 Вернётся: {ret}\n"
        f"⏰ Срок: {plan['label']}",
        reply_markup=back_menu_kb(),
    )


@dp.callback_query(F.data == "bank_check")
async def bank_check_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, amount, interest_rate, mature_date, collected "
            "FROM bank_deposits WHERE user_id = ? ORDER BY id",
            (c.from_user.id,),
        )
        deps = await cur.fetchall()

    if not deps:
        await safe_edit(c.message, "📋 У тебя нет вкладов.", bank_menu_kb())
        return await c.answer()

    rows = []
    text = "📋 <b>Твои вклады:</b>\n\n"
    now = datetime.now()
    for dep_id, amount, rate, mature, collected in deps:
        if collected:
            continue
        ret = int(amount * (1 + rate))
        m_dt = datetime.fromisoformat(mature)
        if now >= m_dt:
            status = "✅ Готов"
            rows.append([InlineKeyboardButton(
                text=f"💰 Забрать #{dep_id} ({ret})",
                callback_data=f"bank_col_{dep_id}",
            )])
        else:
            left = m_dt - now
            h = int(left.total_seconds()) // 3600
            mn = (int(left.total_seconds()) // 60) % 60
            status = f"⏳ {h}ч. {mn}мин."
        text += f"#{dep_id} | {amount} → {ret} | {status}\n"

    if not any(not d[4] for d in deps):
        text += "<i>Все вклады собраны.</i>"

    rows.append([InlineKeyboardButton(text="🔙 Банк", callback_data="menu_bank")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("bank_col_"))
async def bank_collect_cb(c: CallbackQuery):
    dep_id = parse_positive_int(c.data[9:])
    if dep_id is None:
        return await c.answer("❌ Ошибка", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT amount, interest_rate, mature_date, collected "
            "FROM bank_deposits WHERE id = ? AND user_id = ?",
            (dep_id, c.from_user.id),
        )
        dep = await cur.fetchone()
        if not dep:
            return await c.answer("❌ Вклад не найден!", show_alert=True)
        if dep[3] == 1:
            return await c.answer("❌ Уже забрано!", show_alert=True)
        m_dt = datetime.fromisoformat(dep[2])
        if datetime.now() < m_dt:
            return await c.answer("❌ Срок ещё не истёк!", show_alert=True)

        total = int(dep[0] * (1 + dep[1]))
        await db.execute(
            "UPDATE bank_deposits SET collected = 1 WHERE id = ?", (dep_id,)
        )
        await db.execute(
            "UPDATE users SET money = money + ? WHERE user_id = ?",
            (total, c.from_user.id),
        )
        await db.commit()

    await safe_edit(
        c.message,
        f"✅ Вклад #{dep_id} собран!\n💰 Начислено: {total}",
        bank_menu_kb(),
    )
    await c.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║                 БРАК — /marry  /divorce                     ║
# ╚══════════════════════════════════════════════════════════════╝

@dp.message(Command("marry"))
async def marry_cmd(m: Message):
    target_id = None
    if m.reply_to_message and m.reply_to_message.from_user:
        target_id = m.reply_to_message.from_user.id
    else:
        args = (m.text or "").split()
        if len(args) >= 2:
            target_id = parse_positive_int(args[1])
    if not target_id:
        return await m.answer("💍 Ответь на сообщение или /marry [ID]")
    if target_id == m.from_user.id:
        return await m.answer("❌ Нельзя жениться на себе!")

    async with aiosqlite.connect(DB_PATH) as db:
        cur1 = await db.execute(
            "SELECT nickname, spouse_id FROM users WHERE user_id = ?",
            (m.from_user.id,),
        )
        u1 = await cur1.fetchone()
        if not u1:
            return await m.answer("❌ /start сначала")
        if u1[1]:
            return await m.answer("❌ Ты уже в браке!")

        cur2 = await db.execute(
            "SELECT nickname, spouse_id FROM users WHERE user_id = ?",
            (target_id,),
        )
        u2 = await cur2.fetchone()
        if not u2:
            return await m.answer("❌ Игрок не найден!")
        if u2[1]:
            return await m.answer("❌ Этот игрок уже в браке!")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💍 Принять",
            callback_data=f"marry_acc_{m.from_user.id}_{target_id}",
        )],
        [InlineKeyboardButton(
            text="🚫 Отклонить",
            callback_data=f"marry_dec_{m.from_user.id}_{target_id}",
        )],
    ])
    await m.answer(
        f"💍 <b>{u1[0]}</b> делает предложение <b>{u2[0]}</b>!\n\n"
        f"Только {u2[0]} может ответить.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("marry_acc_"))
async def marry_accept_cb(c: CallbackQuery):
    parts = c.data.split("_")
    proposer_id = int(parts[2])
    target_id = int(parts[3])
    if c.from_user.id != target_id:
        return await c.answer("❌ Это не тебе!", show_alert=True)

    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur1 = await db.execute(
            "SELECT spouse_id FROM users WHERE user_id = ?", (proposer_id,)
        )
        cur2 = await db.execute(
            "SELECT spouse_id FROM users WHERE user_id = ?", (target_id,)
        )
        r1 = await cur1.fetchone()
        r2 = await cur2.fetchone()
        if (r1 and r1[0]) or (r2 and r2[0]):
            return await c.answer("❌ Кто-то уже в браке!", show_alert=True)

        await db.execute(
            "UPDATE users SET spouse_id = ?, marriage_date = ? WHERE user_id = ?",
            (target_id, now, proposer_id),
        )
        await db.execute(
            "UPDATE users SET spouse_id = ?, marriage_date = ? WHERE user_id = ?",
            (proposer_id, now, target_id),
        )
        await db.commit()

    await safe_edit(
        c.message,
        "💍 <b>Поздравляем!</b> Брак заключён! 🎉\n"
        "Информация появится в профилях обоих игроков.",
        back_menu_kb(),
    )
    await c.answer()


@dp.callback_query(F.data.startswith("marry_dec_"))
async def marry_decline_cb(c: CallbackQuery):
    parts = c.data.split("_")
    target_id = int(parts[3])
    if c.from_user.id != target_id:
        return await c.answer("❌ Это не тебе!", show_alert=True)
    await safe_edit(c.message, "💔 Предложение отклонено.", back_menu_kb())
    await c.answer()


@dp.message(Command("divorce"))
async def divorce_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT spouse_id FROM users WHERE user_id = ?", (m.from_user.id,)
        )
        row = await cur.fetchone()
        if not row or not row[0]:
            return await m.answer("❌ Ты не в браке!")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💔 Подтвердить развод", callback_data="div_yes"),
         InlineKeyboardButton(text="🔙 Отмена", callback_data="menu_back")],
    ])
    await m.answer("💔 Ты уверен, что хочешь развестись?", reply_markup=kb)


@dp.callback_query(F.data == "div_yes")
async def divorce_confirm_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT spouse_id FROM users WHERE user_id = ?", (c.from_user.id,)
        )
        row = await cur.fetchone()
        if not row or not row[0]:
            return await c.answer("❌ Ты не в браке!", show_alert=True)
        spouse_id = row[0]
        await db.execute(
            "UPDATE users SET spouse_id = 0, marriage_date = NULL WHERE user_id = ?",
            (c.from_user.id,),
        )
        await db.execute(
            "UPDATE users SET spouse_id = 0, marriage_date = NULL WHERE user_id = ?",
            (spouse_id,),
        )
        await db.commit()
    await safe_edit(c.message, "💔 Развод оформлен.", back_menu_kb())
    await c.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║                       ИНВЕНТАРЬ                             ║
# ╚══════════════════════════════════════════════════════════════╝

async def _show_inventory(msg: Message, user_id: int, edit: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, c.rarity, i.count FROM inventory i "
            "JOIN cards c ON i.card_id = c.card_id "
            "WHERE i.user_id = ? ORDER BY c.rarity DESC",
            (user_id,),
        )
        cards = await cur.fetchall()
    if not cards:
        text = "🎒 Инвентарь пуст."
    else:
        text = "🎒 <b>ТВОИ КАРТЫ:</b>\n\n"
        for name, rar, cnt in cards[:30]:
            text += f"{'⭐' * rar} {name} (x{cnt})\n"
        if len(cards) > 30:
            text += f"\n<i>... и ещё {len(cards) - 30}</i>"
    if edit:
        await safe_edit(msg, text, back_menu_kb())
    else:
        await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=back_menu_kb())


@dp.message(Command("inventory"))
async def inventory_cmd(m: Message):
    await _show_inventory(m, m.from_user.id)


@dp.callback_query(F.data == "menu_inv")
async def inventory_cb(c: CallbackQuery):
    await _show_inventory(c.message, c.from_user.id, edit=True)
    await c.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║                 ТОПЫ / ЛИДЕРБОРДЫ                           ║
# ╚══════════════════════════════════════════════════════════════╝

def top_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 По монетам", callback_data="top_money"),
         InlineKeyboardButton(text="💎 По BBC-картам", callback_data="top_cards")],
        [InlineKeyboardButton(text="⚔️ По серии побед", callback_data="top_wins")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])


@dp.message(Command("top"))
async def top_cmd(m: Message):
    await m.answer(
        "🏆 <b>ЛИДЕРБОРДЫ</b>\nВыбери категорию:",
        reply_markup=top_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "menu_tops")
async def tops_cb(c: CallbackQuery):
    await safe_edit(
        c.message,
        "🏆 <b>ЛИДЕРБОРДЫ</b>\nВыбери категорию:",
        top_menu_kb(),
    )
    await c.answer()


@dp.callback_query(F.data.startswith("top_"))
async def top_view_cb(c: CallbackQuery):
    cat = c.data[4:]
    async with aiosqlite.connect(DB_PATH) as db:
        if cat == "money":
            cur = await db.execute(
                "SELECT nickname, money FROM users ORDER BY money DESC LIMIT 10"
            )
            rows = await cur.fetchall()
            title = "💰 ТОП ПО МОНЕТАМ"
            lines = [f"{i+1}. {r[0]} — {r[1]:,}" for i, r in enumerate(rows)]

        elif cat == "cards":
            cur = await db.execute(
                "SELECT u.nickname, COALESCE(SUM(c.rarity * i.count), 0) AS score "
                "FROM users u "
                "LEFT JOIN inventory i ON u.user_id = i.user_id "
                "LEFT JOIN cards c ON i.card_id = c.card_id "
                "GROUP BY u.user_id "
                "ORDER BY score DESC LIMIT 10"
            )
            rows = await cur.fetchall()
            title = "💎 ТОП ПО BBC-КАРТАМ"
            lines = [f"{i+1}. {r[0]} — {int(r[1])} очков" for i, r in enumerate(rows)]

        elif cat == "wins":
            cur = await db.execute(
                "SELECT nickname, winstreak FROM users "
                "ORDER BY winstreak DESC LIMIT 10"
            )
            rows = await cur.fetchall()
            title = "⚔️ ТОП ПО СЕРИИ ПОБЕД"
            lines = [f"{i+1}. {r[0]} — {r[1]} побед" for i, r in enumerate(rows)]
        else:
            return await c.answer()

    text = f"🏆 <b>{title}</b>\n\n" + "\n".join(lines) if lines else "Пусто."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Топы", callback_data="menu_tops")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║                     ПРОМОКОДЫ — /promo                      ║
# ╚══════════════════════════════════════════════════════════════╝

@dp.message(Command("promo"))
async def promo_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer("🎁 Формат: /promo [КОД]")
    code = args[1].strip()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT reward_type, reward_val, uses_left FROM promocodes WHERE code = ?",
            (code,),
        )
        p = await cur.fetchone()
        if not p or p[2] <= 0:
            return await m.answer("❌ Код не найден или закончился.")

        cur2 = await db.execute(
            "SELECT 1 FROM promo_used WHERE user_id = ? AND code = ?",
            (m.from_user.id, code),
        )
        if await cur2.fetchone():
            return await m.answer("❌ Ты уже активировал этот промокод!")

        col = "money" if p[0] == "money" else "bbc_money"
        await db.execute(
            f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?",
            (p[1], m.from_user.id),
        )
        await db.execute(
            "UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?",
            (code,),
        )
        await db.execute(
            "INSERT OR IGNORE INTO promo_used (user_id, code) VALUES (?,?)",
            (m.from_user.id, code),
        )
        await db.execute("DELETE FROM promocodes WHERE uses_left <= 0")
        await db.commit()

    emoji = "💰" if p[0] == "money" else "💎"
    name = "монет" if p[0] == "money" else "BBC"
    await m.answer(f"✅ Промокод активирован! {emoji} +{p[1]} {name}")


# ╔══════════════════════════════════════════════════════════════╗
# ║              ДОБАВЛЕНИЕ КАРТЫ — /addcard (АДМИН)            ║
# ╚══════════════════════════════════════════════════════════════╝

@dp.message(F.photo, F.caption.startswith("/addcard"))
async def add_card_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    parts = (m.caption or "").split()
    if len(parts) < 3:
        return await m.answer("❌ Формат: /addcard Имя Карты РЕДКОСТЬ(1-5)")
    try:
        rarity = int(parts[-1])
        if not 1 <= rarity <= 5:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Редкость: число 1-5!")
    name = " ".join(parts[1:-1])
    file_id = m.photo[-1].file_id

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO cards (name, rarity, file_id) VALUES (?,?,?)",
            (name, rarity, file_id),
        )
        card_id = cursor.lastrowid
        await db.commit()

    await m.answer(
        f"✅ Карта добавлена!\n"
        f"🆔 ID: <code>{card_id}</code>\n"
        f"📛 {name}\n"
        f"{'⭐' * rarity} ({RARITY_NAMES.get(rarity, '?')})",
        parse_mode=ParseMode.HTML,
    )


# ╔══════════════════════════════════════════════════════════════╗
# ║              СКРЫТАЯ ПОДКРУТКА — /rig (АДМИН)               ║
# ╚══════════════════════════════════════════════════════════════╝

@dp.message(Command("rig"))
async def rig_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) < 2 or args[1] not in ("luck", "drain", "normal"):
        return await m.answer("Формат: /rig luck|drain|normal")
    global casino_mode
    casino_mode = args[1]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO game_settings (key, value) VALUES ('casino_mode', ?)",
            (casino_mode,),
        )
        await db.commit()
    labels = {"luck": "🍀 Удача", "drain": "💀 Слив", "normal": "⚖️ Норма"}
    await m.answer(f"🎰 Режим казино: {labels[casino_mode]}")


# ╔══════════════════════════════════════════════════════════════╗
# ║                    АДМИН-ПАНЕЛЬ — /admin                    ║
# ╚══════════════════════════════════════════════════════════════╝

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm_promo"),
         InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players")],
        [InlineKeyboardButton(text="💰 Экономика", callback_data="adm_econ"),
         InlineKeyboardButton(text="🃏 Карты", callback_data="adm_cards")],
        [InlineKeyboardButton(text="🎰 Подкрутка", callback_data="adm_rig"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
    ])


@dp.message(Command("admin"))
async def admin_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer(
        "👑 <b>АДМИН-ПАНЕЛЬ</b>",
        reply_markup=admin_main_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "adm_back")
async def admin_back_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await safe_edit(c.message, "👑 <b>АДМИН-ПАНЕЛЬ</b>", admin_main_kb())
    await c.answer()


# ── Статистика ────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_stats")
async def adm_stats_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        uc = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        cc = (await (await db.execute("SELECT COUNT(*) FROM cards")).fetchone())[0]
        pc = (await (await db.execute("SELECT COUNT(*) FROM promocodes")).fetchone())[0]
        bc = (await (await db.execute(
            "SELECT COUNT(*) FROM bank_deposits WHERE collected = 0"
        )).fetchone())[0]
    labels = {"luck": "🍀 Удача", "drain": "💀 Слив", "normal": "⚖️ Норма"}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")]
    ])
    await safe_edit(
        c.message,
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Игроков: {uc}\n"
        f"🃏 Карт в базе: {cc}\n"
        f"🎁 Промокодов: {pc}\n"
        f"🏦 Активных вкладов: {bc}\n"
        f"🎰 Режим казино: {labels.get(casino_mode, casino_mode)}",
        kb,
    )
    await c.answer()


# ── Промокоды ─────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_promo")
async def adm_promo_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать", callback_data="adm_promo_new")],
        [InlineKeyboardButton(text="📋 Список", callback_data="adm_promo_list")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="adm_promo_del")],
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")],
    ])
    await safe_edit(c.message, "🎁 <b>Управление промокодами</b>", kb)
    await c.answer()


@dp.callback_query(F.data == "adm_promo_new")
async def adm_promo_new_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_promo_data)
    await safe_edit(
        c.message,
        "Введи данные промокода:\n"
        "<code>КОД ТИП(money/bbc_money) СУММА АКТИВАЦИИ</code>\n\n"
        "Пример: <code>NEWYEAR money 1000 50</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_promo_data)
async def process_promo_data(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 4 or args[1] not in ("money", "bbc_money"):
        await state.clear()
        return await m.answer("❌ Неверный формат. Попробуй через /admin.")
    val = parse_positive_int(args[2])
    uses = parse_positive_int(args[3])
    if val is None or uses is None:
        await state.clear()
        return await m.answer("❌ Сумма и кол-во — целые числа > 0!")

    code = args[0]
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO promocodes (code, reward_type, reward_val, uses_left) "
                "VALUES (?,?,?,?)",
                (code, args[1], val, uses),
            )
            await db.commit()
            await m.answer(
                f"✅ Промокод <code>{code}</code> создан!",
                parse_mode=ParseMode.HTML,
            )
        except aiosqlite.IntegrityError:
            await m.answer("❌ Такой код уже существует!")
    await state.clear()


@dp.callback_query(F.data == "adm_promo_list")
async def adm_promo_list_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT code, reward_type, reward_val, uses_left FROM promocodes"
        )
        promos = await cur.fetchall()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Промокоды", callback_data="adm_promo")]
    ])
    if not promos:
        await safe_edit(c.message, "📋 Промокодов нет.", kb)
        return await c.answer()

    text = "📋 <b>Промокоды:</b>\n\n"
    for code, rtype, rval, uses in promos:
        emoji = "💰" if rtype == "money" else "💎"
        text += f"<code>{code}</code> — {emoji} {rval} | Осталось: {uses}\n"
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "adm_promo_del")
async def adm_promo_del_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_promo_delete)
    await safe_edit(c.message, "🗑 Введи код промокода для удаления:")
    await c.answer()


@dp.message(AdminStates.waiting_for_promo_delete)
async def adm_promo_del_handler(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    code = (m.text or "").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT code FROM promocodes WHERE code = ?", (code,)
        )
        if not await cur.fetchone():
            await state.clear()
            return await m.answer("❌ Промокод не найден.")
        await db.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        await db.commit()
    await state.clear()
    await m.answer(f"✅ Промокод <code>{code}</code> удалён.", parse_mode=ParseMode.HTML)


# ── Игроки ────────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_players")
async def adm_players_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Бан", callback_data="adm_p_ban"),
         InlineKeyboardButton(text="✅ Разбан", callback_data="adm_p_unban")],
        [InlineKeyboardButton(text="💀 Аннулировать", callback_data="adm_p_wipe"),
         InlineKeyboardButton(text="🔮 Мифрил", callback_data="adm_p_myth")],
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")],
    ])
    await safe_edit(c.message, "👥 <b>Управление игроками</b>", kb)
    await c.answer()


@dp.callback_query(F.data.in_({"adm_p_ban", "adm_p_unban", "adm_p_wipe", "adm_p_myth"}))
async def adm_player_action_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    action = c.data[6:]  # ban, unban, wipe, myth
    await state.update_data(admin_action=action)
    await state.set_state(AdminStates.waiting_for_target_id)
    await safe_edit(c.message, "📝 Введи ID игрока:")
    await c.answer()


# ── Экономика ─────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_econ")
async def adm_econ_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать монеты", callback_data="adm_e_give_m"),
         InlineKeyboardButton(text="💰 Снять монеты", callback_data="adm_e_take_m")],
        [InlineKeyboardButton(text="💎 Выдать BBC", callback_data="adm_e_give_b"),
         InlineKeyboardButton(text="💎 Снять BBC", callback_data="adm_e_take_b")],
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")],
    ])
    await safe_edit(c.message, "💰 <b>Управление экономикой</b>", kb)
    await c.answer()


@dp.callback_query(F.data.in_({"adm_e_give_m", "adm_e_take_m", "adm_e_give_b", "adm_e_take_b"}))
async def adm_econ_action_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    action = c.data[6:]  # give_m, take_m, give_b, take_b
    await state.update_data(admin_action=action)
    await state.set_state(AdminStates.waiting_for_target_id)
    await safe_edit(c.message, "📝 Введи ID игрока:")
    await c.answer()


# ── Карты ─────────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_cards")
async def adm_cards_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_card_rarity)
    await safe_edit(
        c.message,
        "🃏 Введи ID карты и новую редкость через пробел:\n"
        "<code>ID РЕДКОСТЬ</code>\nПример: <code>42 5</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_card_rarity)
async def adm_card_rarity_handler(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    parts = (m.text or "").split()
    if len(parts) != 2:
        await state.clear()
        return await m.answer("❌ Формат: ID РЕДКОСТЬ")
    card_id = parse_positive_int(parts[0])
    rarity = parse_positive_int(parts[1])
    if card_id is None or rarity is None or not 1 <= rarity <= 5:
        await state.clear()
        return await m.answer("❌ ID > 0, редкость 1-5!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name FROM cards WHERE card_id = ?", (card_id,)
        )
        card = await cur.fetchone()
        if not card:
            await state.clear()
            return await m.answer("❌ Карта не найдена!")
        await db.execute(
            "UPDATE cards SET rarity = ? WHERE card_id = ?", (rarity, card_id)
        )
        await db.commit()
    await state.clear()
    await m.answer(
        f"✅ Карта «{card[0]}» (#{card_id}) → {'⭐' * rarity}",
        parse_mode=ParseMode.HTML,
    )


# ── Подкрутка ─────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_rig")
async def adm_rig_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    labels = {"luck": "🍀 Удача", "drain": "💀 Слив", "normal": "⚖️ Норма"}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍀 Удача", callback_data="adm_rig_luck"),
         InlineKeyboardButton(text="💀 Слив", callback_data="adm_rig_drain")],
        [InlineKeyboardButton(text="⚖️ Нормальный", callback_data="adm_rig_normal")],
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")],
    ])
    await safe_edit(
        c.message,
        f"🎰 <b>Подкрутка казино</b>\n\nТекущий режим: {labels.get(casino_mode, casino_mode)}",
        kb,
    )
    await c.answer()


@dp.callback_query(F.data.in_({"adm_rig_luck", "adm_rig_drain", "adm_rig_normal"}))
async def adm_rig_set_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    global casino_mode
    mode = c.data.split("_")[2]
    casino_mode = mode
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO game_settings (key, value) VALUES ('casino_mode', ?)",
            (mode,),
        )
        await db.commit()
    labels = {"luck": "🍀 Удача", "drain": "💀 Слив", "normal": "⚖️ Норма"}
    await safe_edit(
        c.message,
        f"✅ Режим казино: <b>{labels[mode]}</b>",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Подкрутка", callback_data="adm_rig")]
        ]),
    )
    await c.answer()


# ── Общий FSM-обработчик для ID и суммы (админ) ──────────────

@dp.message(AdminStates.waiting_for_target_id)
async def adm_target_id_handler(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    target_id = parse_positive_int(m.text)
    if target_id is None:
        await state.clear()
        return await m.answer("❌ Некорректный ID!")

    data = await state.get_data()
    action = data.get("admin_action", "")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname FROM users WHERE user_id = ?", (target_id,)
        )
        user_row = await cur.fetchone()
        if not user_row:
            await state.clear()
            return await m.answer("❌ Игрок не найден!")
        name = user_row[0]

        if action == "ban":
            await db.execute(
                "UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,)
            )
            await db.commit()
            await state.clear()
            return await m.answer(f"🚫 {name} забанен!")

        elif action == "unban":
            await db.execute(
                "UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,)
            )
            await db.commit()
            await state.clear()
            return await m.answer(f"✅ {name} разбанен!")

        elif action == "wipe":
            sp_cur = await db.execute(
                "SELECT spouse_id FROM users WHERE user_id = ?", (target_id,)
            )
            sp_row = await sp_cur.fetchone()
            if sp_row and sp_row[0]:
                await db.execute(
                    "UPDATE users SET spouse_id = 0, marriage_date = NULL "
                    "WHERE user_id = ?",
                    (sp_row[0],),
                )
            await db.execute("DELETE FROM users WHERE user_id = ?", (target_id,))
            await db.execute("DELETE FROM inventory WHERE user_id = ?", (target_id,))
            await db.execute("DELETE FROM bank_deposits WHERE user_id = ?", (target_id,))
            await db.execute("DELETE FROM promo_used WHERE user_id = ?", (target_id,))
            await db.commit()
            await state.clear()
            return await m.answer(f"💀 Аккаунт {name} полностью аннулирован!")

        elif action == "myth":
            await db.execute(
                "UPDATE users SET rank = 'Мифрил' WHERE user_id = ?", (target_id,)
            )
            await db.commit()
            await state.clear()
            return await m.answer(f"🔮 {name} получил ранг «Мифрил»!")

        elif action in ("give_m", "take_m", "give_b", "take_b"):
            await state.update_data(target_id=target_id, target_name=name)
            await state.set_state(AdminStates.waiting_for_amount)
            return await m.answer(f"💰 Введи сумму для {name}:")

    await state.clear()


@dp.message(AdminStates.waiting_for_amount)
async def adm_amount_handler(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    amount = parse_positive_int(m.text)
    if amount is None:
        await state.clear()
        return await m.answer("❌ Целое число > 0!")

    data = await state.get_data()
    action = data.get("admin_action", "")
    target_id = data.get("target_id")
    target_name = data.get("target_name", "?")

    async with aiosqlite.connect(DB_PATH) as db:
        if action == "give_m":
            await db.execute(
                "UPDATE users SET money = money + ? WHERE user_id = ?",
                (amount, target_id),
            )
            msg = f"✅ Выдано {amount} 💰 игроку {target_name}"
        elif action == "take_m":
            await db.execute(
                "UPDATE users SET money = MAX(money - ?, 0) WHERE user_id = ?",
                (amount, target_id),
            )
            msg = f"✅ Снято {amount} 💰 у {target_name}"
        elif action == "give_b":
            await db.execute(
                "UPDATE users SET bbc_money = bbc_money + ? WHERE user_id = ?",
                (amount, target_id),
            )
            msg = f"✅ Выдано {amount} 💎 игроку {target_name}"
        elif action == "take_b":
            await db.execute(
                "UPDATE users SET bbc_money = MAX(bbc_money - ?, 0) WHERE user_id = ?",
                (amount, target_id),
            )
            msg = f"✅ Снято {amount} 💎 у {target_name}"
        else:
            msg = "❌ Неизвестное действие"
        await db.commit()

    await state.clear()
    await m.answer(msg)


# ╔══════════════════════════════════════════════════════════════╗
# ║                           MAIN                              ║
# ╚══════════════════════════════════════════════════════════════╝

async def main():
    await init_db()
    await migrate_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_commands(bot)
    logging.info("Bot started! Casino mode: %s", casino_mode)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
