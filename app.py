# ╔══════════════════════════════════════════════════════════════╗
# ║  GAME BOT v3.0  —  Полная игровая платформа                ║
# ║  aiogram 3.x  ·  aiosqlite  ·  Telegram                    ║
# ╚══════════════════════════════════════════════════════════════╝

import os
import logging
import random
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# ── Конфиг ───────────────────────────────────────────────────
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 7513326564
DB_PATH = "game_bot.db"
GACHA_CD = 14400       # 4 часа
DAILY_CD = 86400       # 24 ч
WORK_CD = 3600         # 1 ч
ROB_CD = 7200          # 2 ч
WHEEL_CD = 86400       # 24 ч
ANTISPAM_CD = 1.5      # секунд между командами
BASE_HIT_CHANCE = 55   # % попадания в дуэли
MITHRIL_HIT_BONUS = 15 # +15% для Мифрила
DUEL_HP = 3

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ── Константы ────────────────────────────────────────────────
RANK_NAMES = {
    0: "Нет ранга", 1: "🥉 Бронза", 2: "🥈 Серебро", 3: "🥇 Золото",
    4: "💎 Платина", 5: "💠 Алмаз", 6: "🏅 Мастер", 7: "🔱 Мифрил",
}
RARITY_STARS = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}

SHOP_CATALOG = [
    {"id": "title_king", "name": "👑 Титул «Король»", "price": 5000, "type": "title", "title": "👑 Король"},
    {"id": "title_demon", "name": "😈 Титул «Демон»", "price": 7500, "type": "title", "title": "😈 Демон"},
    {"id": "title_legend", "name": "🌟 Титул «Легенда»", "price": 15000, "type": "title", "title": "🌟 Легенда"},
    {"id": "vip_24h", "name": "⭐ VIP на 24 часа", "price": 10000, "type": "vip", "hours": 24},
    {"id": "vip_72h", "name": "💫 VIP на 72 часа", "price": 25000, "type": "vip", "hours": 72},
    {"id": "mult_x2", "name": "💰 Множитель x2 (24ч)", "price": 20000, "type": "multiplier", "mult": 2.0, "hours": 24},
    {"id": "rank_elite", "name": "🎖 Ранг «Элита» (5)", "price": 50000, "type": "rank", "rank": 5},
    {"id": "bbc_pack", "name": "💵 5 BBC", "price": 30000, "type": "bbc", "amount": 5},
    {"id": "reset_gacha", "name": "🔄 Сброс КД гачи", "price": 3000, "type": "reset_cd", "cd_field": "last_gacha"},
]

BBC_SHOP_CATALOG = [
    {"id": "bbc_chaos", "name": "🔮 Реликвия Хаоса", "desc": "Легендарный титул", "price": 5, "type": "title", "title": "🔮 Хаос"},
    {"id": "bbc_wargod", "name": "⚡ Титул «Бог Войны»", "desc": "Эпический титул", "price": 10, "type": "title", "title": "⚡ Бог Войны"},
    {"id": "bbc_shield", "name": "🛡️ Щит Бессмертия", "desc": "Выжить 1 раз в дуэли", "price": 15, "type": "shield"},
    {"id": "bbc_shadow", "name": "🎭 Титул «Теневой»", "desc": "Мистический титул", "price": 8, "type": "title", "title": "🎭 Теневой"},
    {"id": "bbc_lucky", "name": "🌀 Портал Удачи", "desc": "Гарантия 4+⭐ на гачу", "price": 12, "type": "lucky_gacha"},
    {"id": "bbc_convert", "name": "💎 Конвертер BBC→💰", "desc": "1 BBC = 3000 монет", "price": 3, "type": "convert", "coins_per": 3000},
    {"id": "bbc_mega", "name": "🌈 Титул «Мега Босс»", "desc": "Самый крутой титул", "price": 20, "type": "title", "title": "🌈 Мега Босс"},
]

ACHIEVEMENTS = {
    "first_win": ("🏆 Первая победа", "Выиграй в казино"),
    "rich_10k": ("💰 Богач", "Накопи 10 000 монет"),
    "rich_100k": ("💎 Миллионер", "Накопи 100 000 монет"),
    "collector_10": ("🃏 Коллекционер", "Собери 10 карт"),
    "collector_50": ("📚 Библиотекарь", "Собери 50 карт"),
    "duel_winner": ("⚔️ Дуэлянт", "Выиграй дуэль"),
    "streak_5": ("🔥 Серийный", "5 побед подряд в дуэлях"),
    "married": ("💍 Семьянин", "Вступи в брак"),
    "level_10": ("📊 Десятка", "Достигни 10 уровня"),
    "level_25": ("🌟 Четвертак", "Достигни 25 уровня"),
    "rob_master": ("🦹 Грабитель", "Успешно ограбь 10 раз"),
}

WHEEL_PRIZES = [
    ("coins", 100, "💰 100 монет"), ("coins", 250, "💰 250 монет"),
    ("coins", 500, "💰 500 монет"), ("coins", 1000, "💰 1000 монет"),
    ("bbc", 1, "💵 1 BBC"), ("bbc", 2, "💵 2 BBC"),
    ("xp", 50, "✨ 50 XP"), ("xp", 100, "✨ 100 XP"),
    ("nothing", 0, "💨 Пусто"), ("nothing", 0, "💨 Пусто"),
]

# ── Глобальное состояние ─────────────────────────────────────
rig_mode = "normal"
rig_remaining = 0
antispam: dict = {}

# ── FSM ──────────────────────────────────────────────────────
class ShopStates(StatesGroup):
    waiting_for_quantity = State()

class BbcShopStates(StatesGroup):
    waiting_for_quantity = State()

class GameStates(StatesGroup):
    waiting_for_bet = State()

class DuelStates(StatesGroup):
    in_progress = State()

class AdminStates(StatesGroup):
    waiting_for_promo_data = State()
    waiting_for_promo_del = State()
    waiting_for_ban_id = State()
    waiting_for_unban_id = State()
    waiting_for_wipe_id = State()
    waiting_for_myth_id = State()
    waiting_for_demyth_id = State()
    waiting_for_econ_data = State()
    waiting_for_card_rarity = State()
    waiting_for_rig_count = State()
    waiting_for_broadcast = State()
    waiting_for_lookup_id = State()


# ══════════════════════════════════════════════════════════════
# ║  MIDDLEWARE                                                ║
# ══════════════════════════════════════════════════════════════

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT is_banned FROM users WHERE user_id = ?", (user.id,)
                )
                row = await cur.fetchone()
                if row and row[0]:
                    if isinstance(event, CallbackQuery):
                        try:
                            await event.answer()
                        except Exception:
                            pass
                    return
        return await handler(event, data)


class AntiSpamMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and user.id != ADMIN_ID:
            now = time.time()
            last = antispam.get(user.id, 0)
            if now - last < ANTISPAM_CD:
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⏳ Не так быстро!", show_alert=False)
                    except Exception:
                        pass
                return
            antispam[user.id] = now
        return await handler(event, data)


dp.message.middleware(BanCheckMiddleware())
dp.callback_query.middleware(BanCheckMiddleware())
dp.message.middleware(AntiSpamMiddleware())
dp.callback_query.middleware(AntiSpamMiddleware())


# ══════════════════════════════════════════════════════════════
# ║  ERROR HANDLER                                             ║
# ══════════════════════════════════════════════════════════════

@dp.errors()
async def errors_handler(event, exception):
    if isinstance(exception, TelegramBadRequest):
        msg = str(exception)
        if "query is too old" in msg or "message is not modified" in msg:
            return True
    log.exception("Unhandled: %s", exception)
    return True


# ══════════════════════════════════════════════════════════════
# ║  DATABASE                                                  ║
# ══════════════════════════════════════════════════════════════

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            nickname TEXT,
            balance INTEGER DEFAULT 0,
            bbc_balance INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 0,
            title TEXT DEFAULT '',
            vip_until TEXT DEFAULT '',
            coin_multiplier REAL DEFAULT 1.0,
            spouse_id INTEGER DEFAULT 0,
            marriage_date TEXT DEFAULT '',
            winstreak INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            daily_streak INTEGER DEFAULT 0,
            last_streak_date TEXT DEFAULT '',
            rob_count INTEGER DEFAULT 0,
            last_rob TEXT DEFAULT '',
            lucky_gacha INTEGER DEFAULT 0,
            shield INTEGER DEFAULT 0,
            last_daily TEXT DEFAULT '',
            last_work TEXT DEFAULT '',
            last_gacha TEXT DEFAULT '',
            last_wheel TEXT DEFAULT ''
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rarity INTEGER DEFAULT 1,
            image_id TEXT DEFAULT ''
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS user_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_id INTEGER
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward_type TEXT,
            reward_value INTEGER,
            uses_left INTEGER
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promo_used (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS bank_deposits (
            dep_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            plan TEXT,
            rate REAL,
            created_at TEXT,
            finish_at TEXT,
            collected INTEGER DEFAULT 0
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            ach_id TEXT,
            achieved_at TEXT,
            PRIMARY KEY (user_id, ach_id)
        )""")
        await db.commit()
        await migrate_db(db)


async def migrate_db(db):
    cur = await db.execute("PRAGMA table_info(users)")
    cols = {r[1] for r in await cur.fetchall()}
    new = {
        "bbc_balance": "INTEGER DEFAULT 0",
        "rank": "INTEGER DEFAULT 0",
        "title": "TEXT DEFAULT ''",
        "vip_until": "TEXT DEFAULT ''",
        "coin_multiplier": "REAL DEFAULT 1.0",
        "spouse_id": "INTEGER DEFAULT 0",
        "marriage_date": "TEXT DEFAULT ''",
        "winstreak": "INTEGER DEFAULT 0",
        "is_banned": "INTEGER DEFAULT 0",
        "xp": "INTEGER DEFAULT 0",
        "level": "INTEGER DEFAULT 1",
        "daily_streak": "INTEGER DEFAULT 0",
        "last_streak_date": "TEXT DEFAULT ''",
        "rob_count": "INTEGER DEFAULT 0",
        "last_rob": "TEXT DEFAULT ''",
        "lucky_gacha": "INTEGER DEFAULT 0",
        "shield": "INTEGER DEFAULT 0",
        "last_daily": "TEXT DEFAULT ''",
        "last_work": "TEXT DEFAULT ''",
        "last_gacha": "TEXT DEFAULT ''",
        "last_wheel": "TEXT DEFAULT ''",
    }
    for col, td in new.items():
        if col not in cols:
            await db.execute(f"ALTER TABLE users ADD COLUMN {col} {td}")
            log.info("Migrated users.%s", col)
    cur2 = await db.execute("PRAGMA table_info(cards)")
    ccols = {r[1] for r in await cur2.fetchall()}
    if "image_id" not in ccols:
        await db.execute("ALTER TABLE cards ADD COLUMN image_id TEXT DEFAULT ''")
    await db.execute("""CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER, ach_id TEXT, achieved_at TEXT,
        PRIMARY KEY (user_id, ach_id))""")
    await db.commit()


# ══════════════════════════════════════════════════════════════
# ║  HELPERS                                                   ║
# ══════════════════════════════════════════════════════════════

def parse_positive_int(text) -> Optional[int]:
    try:
        v = int(text)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


async def safe_edit(msg: Message, text: str, kb=None):
    try:
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except TelegramBadRequest:
        pass


def back_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")]
    ])


def level_title(lvl: int) -> str:
    if lvl < 5:
        return "🌱 Новобранец"
    if lvl < 10:
        return "⚔️ Ветеран"
    if lvl < 20:
        return "🏆 Мастер"
    if lvl < 30:
        return "👑 Гуру"
    if lvl < 50:
        return "🌟 Легенда"
    return "🔥 Бог"


def xp_for_level(lvl: int) -> int:
    return lvl * 150


async def grant_xp(db, user_id: int, amount: int) -> Optional[str]:
    """Grant XP and auto-levelup. Returns level-up message or None."""
    cur = await db.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    if not row:
        return None
    xp, lvl = row[0] + amount, row[1]
    msg = None
    while xp >= xp_for_level(lvl):
        xp -= xp_for_level(lvl)
        lvl += 1
        msg = f"🎉 Уровень повышен! Теперь ты <b>{level_title(lvl)} [{lvl}]</b>"
    await db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (xp, lvl, user_id))
    # Check level achievements
    if lvl >= 10:
        await try_achievement(db, user_id, "level_10")
    if lvl >= 25:
        await try_achievement(db, user_id, "level_25")
    return msg


async def try_achievement(db, user_id: int, ach_id: str):
    try:
        await db.execute(
            "INSERT OR IGNORE INTO achievements (user_id, ach_id, achieved_at) VALUES (?, ?, ?)",
            (user_id, ach_id, datetime.now().isoformat()),
        )
    except Exception:
        pass


async def check_wealth_achievements(db, user_id: int, balance: int):
    if balance >= 10000:
        await try_achievement(db, user_id, "rich_10k")
    if balance >= 100000:
        await try_achievement(db, user_id, "rich_100k")


async def check_collection_achievements(db, user_id: int):
    cur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,))
    cnt = (await cur.fetchone())[0]
    if cnt >= 10:
        await try_achievement(db, user_id, "collector_10")
    if cnt >= 50:
        await try_achievement(db, user_id, "collector_50")


def cd_remaining(last_str: str, cd_sec: int) -> int:
    if not last_str:
        return 0
    try:
        last = datetime.fromisoformat(last_str)
        diff = (datetime.now() - last).total_seconds()
        return max(0, int(cd_sec - diff))
    except Exception:
        return 0


def fmt_seconds(s: int) -> str:
    if s >= 3600:
        return f"{s // 3600}ч {(s % 3600) // 60}мин"
    if s >= 60:
        return f"{s // 60}мин {s % 60}сек"
    return f"{s}сек"


def game_is_rigged() -> bool:
    global rig_remaining, rig_mode
    if rig_mode == "win100" and rig_remaining > 0:
        rig_remaining -= 1
        if rig_remaining == 0:
            rig_mode = "normal"
        return True
    return False


# ══════════════════════════════════════════════════════════════
# ║  START & MAIN MENU                                        ║
# ══════════════════════════════════════════════════════════════

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"),
         InlineKeyboardButton(text="🎴 Гача", callback_data="menu_gacha")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="menu_shop"),
         InlineKeyboardButton(text="💎 BBC Магазин", callback_data="menu_bbcshop")],
        [InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games"),
         InlineKeyboardButton(text="🏦 Банк", callback_data="menu_bank")],
        [InlineKeyboardButton(text="🏆 Топы", callback_data="menu_tops"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv")],
        [InlineKeyboardButton(text="📊 Уровень", callback_data="menu_level"),
         InlineKeyboardButton(text="🎡 Колесо", callback_data="menu_wheel")],
        [InlineKeyboardButton(text="🏅 Достижения", callback_data="menu_achs"),
         InlineKeyboardButton(text="💰 Ежедневка", callback_data="menu_daily")],
        [InlineKeyboardButton(text="🔨 Работа", callback_data="menu_work")],
    ])


@dp.message(CommandStart())
async def start_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (m.from_user.id,))
        if not await cur.fetchone():
            nick = m.from_user.full_name or f"User{m.from_user.id}"
            await db.execute(
                "INSERT INTO users (user_id, nickname) VALUES (?, ?)",
                (m.from_user.id, nick),
            )
            await db.commit()
    await m.answer(
        "🎮 <b>Добро пожаловать в Game Bot!</b>\n\nВыбери действие:",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "menu_back")
async def menu_back_cb(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(c.message, "🎮 <b>Главное меню</b>", main_menu_kb())
    await c.answer()


@dp.message(Command("menu"))
async def menu_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("🎮 <b>Главное меню</b>", reply_markup=main_menu_kb(), parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════
# ║  PROFILE                                                   ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_profile")
async def profile_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance, bbc_balance, rank, title, vip_until, "
            "coin_multiplier, spouse_id, marriage_date, winstreak, xp, level, "
            "daily_streak, shield FROM users WHERE user_id = ?",
            (uid,),
        )
        u = await cur.fetchone()
        if not u:
            return await c.answer("❌ /start сначала", show_alert=True)
        nick, bal, bbc, rank, title, vip, mult, sp_id, m_date, ws, xp, lvl, streak, shield = u

        cards_cur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (uid,))
        card_count = (await cards_cur.fetchone())[0]

        ach_cur = await db.execute("SELECT COUNT(*) FROM achievements WHERE user_id = ?", (uid,))
        ach_count = (await ach_cur.fetchone())[0]

        spouse_name = ""
        marriage_info = ""
        if sp_id:
            sc = await db.execute("SELECT nickname FROM users WHERE user_id = ?", (sp_id,))
            sr = await sc.fetchone()
            spouse_name = sr[0] if sr else "???"
            if m_date:
                try:
                    md = datetime.fromisoformat(m_date)
                    delta = datetime.now() - md
                    days = delta.days
                    hours = delta.seconds // 3600
                    marriage_info = f"💍 В браке с <b>{spouse_name}</b> ({days}д {hours}ч)"
                except Exception:
                    marriage_info = f"💍 В браке с <b>{spouse_name}</b>"

    vip_str = ""
    if vip:
        try:
            vip_end = datetime.fromisoformat(vip)
            if vip_end > datetime.now():
                vip_str = f"\n⭐ VIP до {vip_end.strftime('%d.%m %H:%M')}"
        except Exception:
            pass

    xp_need = xp_for_level(lvl)
    bar_len = 10
    filled = min(bar_len, int(xp / max(1, xp_need) * bar_len))
    bar = "█" * filled + "░" * (bar_len - filled)

    text = (
        f"👤 <b>{nick}</b>\n"
        f"{'📛 ' + title if title else ''}\n"
        f"{RANK_NAMES.get(rank, 'Нет ранга')}\n\n"
        f"💰 Монеты: <b>{bal:,}</b>\n"
        f"💵 BBC: <b>{bbc}</b>\n"
        f"📊 Уровень: <b>{lvl}</b> ({level_title(lvl)})\n"
        f"   {bar} {xp}/{xp_need} XP\n"
        f"🃏 Карт: {card_count}\n"
        f"🏅 Достижений: {ach_count}/{len(ACHIEVEMENTS)}\n"
        f"⚔️ Серия побед: {ws}\n"
        f"🔥 Дневной стрик: {streak}\n"
        f"{'🛡️ Щит активен!' if shield else ''}\n"
        f"{marriage_info}\n"
        f"💰 Множитель: x{mult}{vip_str}"
    )
    text = "\n".join(line for line in text.split("\n") if line.strip())
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


@dp.message(Command("profile"))
async def profile_cmd(m: Message):
    uid = m.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance, bbc_balance, rank, title, winstreak, xp, level "
            "FROM users WHERE user_id = ?", (uid,),
        )
        u = await cur.fetchone()
        if not u:
            return await m.answer("❌ /start сначала")
    xp_need = xp_for_level(u[7])
    await m.answer(
        f"👤 <b>{u[0]}</b>\n💰 {u[1]:,} | 💵 {u[2]} BBC\n"
        f"📊 Ур.{u[7]} | ⚔️ Стрик: {u[5]}\n✨ {u[6]}/{xp_need} XP",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════
# ║  GACHA (4h cooldown)                                       ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_gacha")
async def gacha_menu_cb(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎴 Крутить 1 раз", callback_data="gacha_1"),
         InlineKeyboardButton(text="🎴 x5", callback_data="gacha_5")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, "🎴 <b>ГАЧА</b>\n\nТяни карты! КД: 4 часа.", kb)
    await c.answer()


async def do_gacha(db, user_id: int, count: int, lucky: bool = False):
    cur = await db.execute("SELECT card_id, name, rarity, image_id FROM cards")
    all_cards = await cur.fetchall()
    if not all_cards:
        return [], "❌ В базе нет карт!"

    results = []
    for _ in range(count):
        if lucky:
            pool = [c for c in all_cards if c[2] >= 4] or all_cards
        else:
            weights = [max(1, 6 - c[2]) for c in all_cards]
            pool = random.choices(all_cards, weights=weights, k=1)
            pool = pool
        card = random.choice(pool) if lucky else pool[0]
        await db.execute(
            "INSERT INTO user_cards (user_id, card_id) VALUES (?, ?)",
            (user_id, card[0]),
        )
        results.append(card)
    return results, None


@dp.callback_query(F.data.startswith("gacha_"))
async def gacha_pull_cb(c: CallbackQuery):
    count = int(c.data.split("_")[1])
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_gacha, lucky_gacha FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        remaining = cd_remaining(row[0], GACHA_CD)
        if remaining > 0:
            return await c.answer(f"⏳ КД: {fmt_seconds(remaining)}", show_alert=True)

        lucky = bool(row[1])
        results, err = await do_gacha(db, uid, count, lucky)
        if err:
            return await c.answer(err, show_alert=True)

        if lucky:
            await db.execute("UPDATE users SET lucky_gacha = 0 WHERE user_id = ?", (uid,))
        await db.execute(
            "UPDATE users SET last_gacha = ? WHERE user_id = ?",
            (datetime.now().isoformat(), uid),
        )
        lvl_msg = await grant_xp(db, uid, 10 * count)
        await check_collection_achievements(db, uid)
        await db.commit()

    lines = []
    for card in results:
        lines.append(f"{RARITY_STARS.get(card[2], '⭐')} <b>{card[1]}</b>")
    text = "🎴 <b>Результат:</b>\n\n" + "\n".join(lines)
    if lucky:
        text += "\n\n🌀 <i>Портал Удачи использован!</i>"
    if lvl_msg:
        text += f"\n\n{lvl_msg}"
    text += f"\n\n✨ +{10 * count} XP"

    if len(results) == 1 and results[0][3]:
        try:
            await c.message.delete()
            await bot.send_photo(
                c.message.chat.id,
                results[0][3],
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=back_menu_kb(),
            )
        except Exception:
            await safe_edit(c.message, text, back_menu_kb())
    else:
        await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  ECONOMY — DAILY, WORK, PAY                                ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_daily")
async def daily_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT last_daily, coin_multiplier, daily_streak, last_streak_date FROM users WHERE user_id = ?",
            (uid,),
        )
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        remaining = cd_remaining(row[0], DAILY_CD)
        if remaining > 0:
            return await c.answer(f"⏳ КД: {fmt_seconds(remaining)}", show_alert=True)

        base = random.randint(500, 1500)
        mult = row[1] if row[1] else 1.0
        streak = row[2] or 0
        last_streak = row[3] or ""

        # Streak logic
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last_streak == yesterday:
            streak += 1
        elif last_streak != today:
            streak = 1

        streak_bonus = min(streak * 50, 500)
        total = int(base * mult) + streak_bonus

        await db.execute(
            "UPDATE users SET balance = balance + ?, last_daily = ?, "
            "daily_streak = ?, last_streak_date = ? WHERE user_id = ?",
            (total, datetime.now().isoformat(), streak, today, uid),
        )
        lvl_msg = await grant_xp(db, uid, 25)
        cur2 = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
        new_bal = (await cur2.fetchone())[0]
        await check_wealth_achievements(db, uid, new_bal)
        await db.commit()

    text = (
        f"💰 <b>Ежедневная награда!</b>\n\n"
        f"Базовая: {base} 💰\n"
        f"Множитель: x{mult}\n"
        f"🔥 Стрик: {streak} дн. (+{streak_bonus} 💰)\n"
        f"<b>Итого: +{total} 💰</b>\n✨ +25 XP"
    )
    if lvl_msg:
        text += f"\n{lvl_msg}"
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


@dp.callback_query(F.data == "menu_work")
async def work_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT last_work, coin_multiplier FROM users WHERE user_id = ?", (uid,),
        )
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        remaining = cd_remaining(row[0], WORK_CD)
        if remaining > 0:
            return await c.answer(f"⏳ КД: {fmt_seconds(remaining)}", show_alert=True)

        jobs = [
            ("👨‍💻 Программирование", 200, 600),
            ("🍳 Готовка", 150, 450),
            ("🚗 Таксист", 100, 500),
            ("🎨 Рисование", 180, 550),
            ("📦 Доставка", 120, 400),
            ("🔧 Ремонт", 250, 700),
            ("🎵 Музыкант", 160, 480),
        ]
        job, low, high = random.choice(jobs)
        base = random.randint(low, high)
        mult = row[1] if row[1] else 1.0
        total = int(base * mult)

        await db.execute(
            "UPDATE users SET balance = balance + ?, last_work = ? WHERE user_id = ?",
            (total, datetime.now().isoformat(), uid),
        )
        lvl_msg = await grant_xp(db, uid, 15)
        await db.commit()

    text = f"🔨 <b>{job}</b>\n\n💰 Заработано: <b>+{total}</b>\n✨ +15 XP"
    if lvl_msg:
        text += f"\n{lvl_msg}"
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


@dp.message(Command("pay"))
async def pay_cmd(m: Message):
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.answer("💸 Ответь на сообщение игрока: /pay [сумма]")
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer("💸 Формат: /pay [сумма]")
    amount = parse_positive_int(args[1])
    if not amount:
        return await m.answer("❌ Сумма — целое число > 0!")

    target_id = m.reply_to_message.from_user.id
    if target_id == m.from_user.id:
        return await m.answer("❌ Нельзя платить себе!")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (m.from_user.id,))
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ /start сначала")
        if row[0] < amount:
            return await m.answer(f"❌ Недостаточно монет! У тебя: {row[0]:,}")

        cur2 = await db.execute("SELECT nickname FROM users WHERE user_id = ?", (target_id,))
        target = await cur2.fetchone()
        if not target:
            return await m.answer("❌ Получатель не зарегистрирован!")

        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, m.from_user.id))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        await db.commit()

    await m.answer(
        f"✅ Перевод <b>{amount:,} 💰</b> → <b>{target[0]}</b>",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════
# ║  SHOP (монеты)                                             ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_shop")
async def shop_menu_cb(c: CallbackQuery):
    rows = []
    for item in SHOP_CATALOG:
        rows.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']:,}💰",
            callback_data=f"shop_buy_{item['id']}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await safe_edit(c.message, "🛒 <b>МАГАЗИН</b>\n\nВыбери товар:", kb)
    await c.answer()


@dp.callback_query(F.data.startswith("shop_buy_"))
async def shop_buy_cb(c: CallbackQuery, state: FSMContext):
    item_id = c.data.replace("shop_buy_", "")
    item = next((i for i in SHOP_CATALOG if i["id"] == item_id), None)
    if not item:
        return await c.answer("❌ Товар не найден!", show_alert=True)
    await state.set_state(ShopStates.waiting_for_quantity)
    await state.update_data(shop_item=item)
    await safe_edit(
        c.message,
        f"🛒 <b>{item['name']}</b>\n💰 Цена: {item['price']:,}\n\nВведи количество:",
    )
    await c.answer()


@dp.message(ShopStates.waiting_for_quantity)
async def shop_quantity(m: Message, state: FSMContext):
    qty = parse_positive_int(m.text)
    if not qty:
        await state.clear()
        return await m.answer("❌ Количество — целое число > 0!", reply_markup=back_menu_kb())
    data = await state.get_data()
    item = data.get("shop_item")
    if not item:
        await state.clear()
        return await m.answer("❌ Ошибка. Начни заново.", reply_markup=back_menu_kb())

    total_cost = item["price"] * qty
    uid = m.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row or row[0] < total_cost:
            await state.clear()
            return await m.answer(
                f"❌ Недостаточно монет! Нужно: {total_cost:,}, у тебя: {row[0] if row else 0:,}",
                reply_markup=back_menu_kb(),
            )

        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_cost, uid))

        t = item["type"]
        if t == "title":
            await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (item["title"], uid))
        elif t == "vip":
            until = (datetime.now() + timedelta(hours=item["hours"] * qty)).isoformat()
            await db.execute("UPDATE users SET vip_until = ? WHERE user_id = ?", (until, uid))
        elif t == "multiplier":
            await db.execute(
                "UPDATE users SET coin_multiplier = ? WHERE user_id = ?",
                (item["mult"], uid),
            )
        elif t == "rank":
            await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (item["rank"], uid))
        elif t == "bbc":
            await db.execute(
                "UPDATE users SET bbc_balance = bbc_balance + ? WHERE user_id = ?",
                (item["amount"] * qty, uid),
            )
        elif t == "reset_cd":
            await db.execute(
                f"UPDATE users SET {item['cd_field']} = '' WHERE user_id = ?", (uid,),
            )

        await db.commit()

    await state.clear()
    await m.answer(
        f"✅ Куплено: <b>{item['name']}</b> x{qty}\n💰 Потрачено: {total_cost:,}",
        parse_mode=ParseMode.HTML,
        reply_markup=back_menu_kb(),
    )


# ══════════════════════════════════════════════════════════════
# ║  BBC SHOP                                                  ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_bbcshop")
async def bbcshop_menu_cb(c: CallbackQuery):
    rows = []
    for item in BBC_SHOP_CATALOG:
        rows.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']} BBC",
            callback_data=f"bbcbuy_{item['id']}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await safe_edit(c.message, "💎 <b>BBC МАГАЗИН</b>\n\nТовары за BBC:", kb)
    await c.answer()


@dp.callback_query(F.data.startswith("bbcbuy_"))
async def bbcshop_buy_cb(c: CallbackQuery, state: FSMContext):
    item_id = c.data.replace("bbcbuy_", "")
    item = next((i for i in BBC_SHOP_CATALOG if i["id"] == item_id), None)
    if not item:
        return await c.answer("❌ Товар не найден!", show_alert=True)
    await state.set_state(BbcShopStates.waiting_for_quantity)
    await state.update_data(bbc_item=item)
    await safe_edit(
        c.message,
        f"💎 <b>{item['name']}</b>\n{item['desc']}\n💵 Цена: {item['price']} BBC\n\nВведи количество:",
    )
    await c.answer()


@dp.message(BbcShopStates.waiting_for_quantity)
async def bbcshop_quantity(m: Message, state: FSMContext):
    qty = parse_positive_int(m.text)
    if not qty:
        await state.clear()
        return await m.answer("❌ Количество — целое число > 0!", reply_markup=back_menu_kb())
    data = await state.get_data()
    item = data.get("bbc_item")
    if not item:
        await state.clear()
        return await m.answer("❌ Ошибка.", reply_markup=back_menu_kb())

    total_cost = item["price"] * qty
    uid = m.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT bbc_balance FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row or row[0] < total_cost:
            await state.clear()
            return await m.answer(
                f"❌ Недостаточно BBC! Нужно: {total_cost}, у тебя: {row[0] if row else 0}",
                reply_markup=back_menu_kb(),
            )

        await db.execute("UPDATE users SET bbc_balance = bbc_balance - ? WHERE user_id = ?", (total_cost, uid))

        t = item["type"]
        result_text = ""
        if t == "title":
            await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (item["title"], uid))
            result_text = f"Титул: {item['title']}"
        elif t == "shield":
            await db.execute(
                "UPDATE users SET shield = shield + ? WHERE user_id = ?", (qty, uid),
            )
            result_text = f"🛡️ Щитов: +{qty}"
        elif t == "lucky_gacha":
            await db.execute(
                "UPDATE users SET lucky_gacha = lucky_gacha + ? WHERE user_id = ?", (qty, uid),
            )
            result_text = f"🌀 Удачных гач: +{qty}"
        elif t == "convert":
            coins = item["coins_per"] * qty
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?", (coins, uid),
            )
            result_text = f"💰 +{coins:,} монет"

        await db.commit()

    await state.clear()
    await m.answer(
        f"✅ Куплено: <b>{item['name']}</b> x{qty}\n💵 Потрачено: {total_cost} BBC\n{result_text}",
        parse_mode=ParseMode.HTML,
        reply_markup=back_menu_kb(),
    )


# ══════════════════════════════════════════════════════════════
# ║  GAME CENTER                                               ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_games")
async def games_menu_cb(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Рулетка", callback_data="game_roulette"),
         InlineKeyboardButton(text="🎲 Кости", callback_data="game_dice")],
        [InlineKeyboardButton(text="🪙 Монетка", callback_data="game_coin"),
         InlineKeyboardButton(text="📈 Краш", callback_data="game_crash")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, "🎮 <b>ИГРОВОЙ ЦЕНТР</b>\n\nВыбери игру:", kb)
    await c.answer()


def bet_keyboard(game: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100", callback_data=f"bet_{game}_100"),
         InlineKeyboardButton(text="500", callback_data=f"bet_{game}_500"),
         InlineKeyboardButton(text="1000", callback_data=f"bet_{game}_1000")],
        [InlineKeyboardButton(text="5000", callback_data=f"bet_{game}_5000"),
         InlineKeyboardButton(text="ALL-IN", callback_data=f"bet_{game}_allin")],
        [InlineKeyboardButton(text="✏️ Своя", callback_data=f"bet_{game}_custom")],
        [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
    ])


@dp.callback_query(F.data.in_({"game_roulette", "game_dice", "game_coin", "game_crash"}))
async def game_select_cb(c: CallbackQuery):
    game = c.data.replace("game_", "")
    names = {"roulette": "🎰 Рулетка", "dice": "🎲 Кости", "coin": "🪙 Монетка", "crash": "📈 Краш"}
    descs = {
        "roulette": "Красное/Чёрное x2, Зелёное x14",
        "dice": "Угадай число 1-6, выигрыш x5",
        "coin": "Орёл или решка, выигрыш x1.9",
        "crash": "Множитель растёт. Успей забрать!",
    }
    await safe_edit(
        c.message,
        f"<b>{names[game]}</b>\n{descs[game]}\n\nВыбери ставку:",
        bet_keyboard(game),
    )
    await c.answer()


@dp.callback_query(F.data.regexp(r"^bet_\w+_\d+$"))
async def bet_preset_cb(c: CallbackQuery):
    parts = c.data.split("_")
    game = parts[1]
    amount = int(parts[2])
    await play_game(c, game, amount)


@dp.callback_query(F.data.regexp(r"^bet_\w+_allin$"))
async def bet_allin_cb(c: CallbackQuery):
    game = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (c.from_user.id,))
        row = await cur.fetchone()
        if not row or row[0] <= 0:
            return await c.answer("❌ У тебя 0 монет!", show_alert=True)
        await play_game(c, game, row[0])


@dp.callback_query(F.data.regexp(r"^bet_\w+_custom$"))
async def bet_custom_cb(c: CallbackQuery, state: FSMContext):
    game = c.data.split("_")[1]
    await state.set_state(GameStates.waiting_for_bet)
    await state.update_data(game_type=game)
    await safe_edit(c.message, "✏️ Введи сумму ставки:")
    await c.answer()


# (handler moved to smart_bet_input below)
async def bet_custom_input(m: Message, state: FSMContext):
    amount = parse_positive_int(m.text)
    if not amount:
        await state.clear()
        return await m.answer("❌ Ставка — целое число > 0!", reply_markup=back_menu_kb())
    data = await state.get_data()
    game = data.get("game_type", "roulette")
    await state.clear()

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.data = ""
        async def answer(self, *a, **kw):
            pass

    fc = FakeCallback(m, m.from_user)
    await play_game(fc, game, amount, is_message=True)


async def play_game(c, game: str, bet: int, is_message: bool = False):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row or row[0] < bet:
            if is_message:
                return await c.message.answer("❌ Недостаточно монет!", reply_markup=back_menu_kb())
            return await c.answer("❌ Недостаточно монет!", show_alert=True)

        rigged = game_is_rigged()
        won = False
        winnings = 0
        text = ""

        if game == "roulette":
            colors = ["🔴"] * 18 + ["⚫"] * 18 + ["🟢"]
            result = random.choice(colors) if not rigged else "🔴"
            if rigged or result == "🔴":
                won = True
                winnings = bet * 2
                text = f"🎰 Рулетка: {result}\n✅ <b>Победа! +{winnings:,} 💰</b>"
            elif result == "🟢" and rigged:
                won = True
                winnings = bet * 14
                text = f"🎰 Рулетка: 🟢\n🤑 <b>ЗЕЛЁНОЕ! +{winnings:,} 💰</b>"
            else:
                text = f"🎰 Рулетка: {result}\n❌ Проигрыш: -{bet:,} 💰"

        elif game == "dice":
            player = random.randint(1, 6)
            target = random.randint(1, 6)
            if rigged:
                target = player
            won = player == target
            if won:
                winnings = bet * 5
                text = f"🎲 Ты: {player} | Нужно: {target}\n✅ <b>Победа! +{winnings:,} 💰</b>"
            else:
                text = f"🎲 Ты: {player} | Нужно: {target}\n❌ Проигрыш: -{bet:,} 💰"

        elif game == "coin":
            flip = random.choice(["Орёл 🦅", "Решка 🪙"])
            if rigged:
                won = True
            else:
                won = random.random() < 0.5
            if won:
                winnings = int(bet * 1.9)
                text = f"🪙 {flip}\n✅ <b>Победа! +{winnings:,} 💰</b>"
            else:
                text = f"🪙 {flip}\n❌ Проигрыш: -{bet:,} 💰"

        elif game == "crash":
            if rigged:
                multiplier = round(random.uniform(3.0, 10.0), 2)
            else:
                r = random.random()
                if r < 0.4:
                    multiplier = round(random.uniform(0.0, 0.9), 2)
                elif r < 0.75:
                    multiplier = round(random.uniform(1.0, 2.0), 2)
                elif r < 0.9:
                    multiplier = round(random.uniform(2.0, 5.0), 2)
                else:
                    multiplier = round(random.uniform(5.0, 15.0), 2)

            if multiplier >= 1.0:
                won = True
                winnings = int(bet * multiplier)
                text = f"📈 Краш: x{multiplier}\n✅ <b>Победа! +{winnings:,} 💰</b>"
            else:
                text = f"📈 Краш: x{multiplier}\n💥 <b>КРАХ! -{bet:,} 💰</b>"

        if won:
            profit = winnings - bet
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (profit, uid),
            )
            lvl_msg = await grant_xp(db, uid, 30)
            await try_achievement(db, uid, "first_win")
            cur2 = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
            new_bal = (await cur2.fetchone())[0]
            await check_wealth_achievements(db, uid, new_bal)
        else:
            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (bet, uid),
            )
            lvl_msg = None
        await db.commit()

    text += "\n✨ +30 XP" if won else ""
    if won and lvl_msg:
        text += f"\n{lvl_msg}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё раз", callback_data=f"bet_{game}_{bet}"),
         InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])

    if is_message:
        await c.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await safe_edit(c.message, text, kb)
        await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  DUELS (Мифрил +15% попадания)                             ║
# ══════════════════════════════════════════════════════════════

active_duels: dict = {}


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
        return await m.answer("⚔️ Ответь на сообщение или /duel [ID]")
    if target_id == m.from_user.id:
        return await m.answer("❌ Нельзя вызвать себя!")

    chat_id = m.chat.id
    key = (chat_id, min(m.from_user.id, target_id), max(m.from_user.id, target_id))
    if key in active_duels:
        return await m.answer("❌ Дуэль уже идёт!")

    async with aiosqlite.connect(DB_PATH) as db:
        c1 = await db.execute("SELECT nickname FROM users WHERE user_id = ?", (m.from_user.id,))
        c2 = await db.execute("SELECT nickname FROM users WHERE user_id = ?", (target_id,))
        u1 = await c1.fetchone()
        u2 = await c2.fetchone()
        if not u1 or not u2:
            return await m.answer("❌ Оба игрока должны быть зарегистрированы!")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⚔️ Принять вызов",
            callback_data=f"duel_acc_{m.from_user.id}_{target_id}",
        )],
        [InlineKeyboardButton(
            text="🚫 Отклонить",
            callback_data=f"duel_dec_{m.from_user.id}_{target_id}",
        )],
    ])
    await m.answer(
        f"⚔️ <b>{u1[0]}</b> вызывает <b>{u2[0]}</b> на дуэль!\n\n"
        f"⚠️ <b>ВНИМАНИЕ:</b> Проигравший теряет ВСЁ!\n"
        f"Только вызванный игрок может ответить.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("duel_acc_"))
async def duel_accept_cb(c: CallbackQuery):
    parts = c.data.split("_")
    p1 = int(parts[2])
    p2 = int(parts[3])
    if c.from_user.id != p2:
        return await c.answer("❌ Это не тебе!", show_alert=True)

    chat_id = c.message.chat.id
    key = (chat_id, min(p1, p2), max(p1, p2))
    if key in active_duels:
        return await c.answer("❌ Дуэль уже идёт!", show_alert=True)

    # Get ranks for hit bonus
    async with aiosqlite.connect(DB_PATH) as db:
        c1 = await db.execute("SELECT nickname, rank FROM users WHERE user_id = ?", (p1,))
        c2 = await db.execute("SELECT nickname, rank FROM users WHERE user_id = ?", (p2,))
        u1 = await c1.fetchone()
        u2 = await c2.fetchone()

    active_duels[key] = {
        "p1": p1, "p2": p2,
        "hp1": DUEL_HP, "hp2": DUEL_HP,
        "turn": p1,
        "n1": u1[0] if u1 else "???", "n2": u2[0] if u2 else "???",
        "r1": u1[1] if u1 else 0, "r2": u2[1] if u2 else 0,
        "chat_id": chat_id,
    }

    await safe_edit(
        c.message,
        duel_status_text(active_duels[key]),
        duel_fire_kb(key, p1),
    )
    await c.answer()


@dp.callback_query(F.data.startswith("duel_dec_"))
async def duel_decline_cb(c: CallbackQuery):
    parts = c.data.split("_")
    p2 = int(parts[3])
    if c.from_user.id != p2:
        return await c.answer("❌ Это не тебе!", show_alert=True)
    await safe_edit(c.message, "🚫 Дуэль отклонена.", back_menu_kb())
    await c.answer()


def duel_status_text(d: dict) -> str:
    turn_name = d["n1"] if d["turn"] == d["p1"] else d["n2"]
    return (
        f"⚔️ <b>ДУЭЛЬ</b>\n\n"
        f"👤 {d['n1']}: {'❤️' * d['hp1']}{'🖤' * (DUEL_HP - d['hp1'])} ({d['hp1']} HP)\n"
        f"👤 {d['n2']}: {'❤️' * d['hp2']}{'🖤' * (DUEL_HP - d['hp2'])} ({d['hp2']} HP)\n\n"
        f"🔫 Ход: <b>{turn_name}</b>"
    )


def duel_fire_kb(key, turn_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔫 Выстрелить!",
            callback_data=f"duel_fire_{key[1]}_{key[2]}",
        )],
    ])


@dp.callback_query(F.data.startswith("duel_fire_"))
async def duel_fire_cb(c: CallbackQuery):
    parts = c.data.split("_")
    k1, k2 = int(parts[2]), int(parts[3])
    chat_id = c.message.chat.id
    key = (chat_id, k1, k2)
    d = active_duels.get(key)
    if not d:
        return await c.answer("❌ Дуэль не найдена!", show_alert=True)
    if c.from_user.id != d["turn"]:
        return await c.answer("❌ Сейчас не твой ход!", show_alert=True)

    shooter = c.from_user.id
    target = d["p2"] if shooter == d["p1"] else d["p1"]

    # Hit chance: base + mithril bonus
    shooter_rank = d["r1"] if shooter == d["p1"] else d["r2"]
    hit_chance = BASE_HIT_CHANCE
    if shooter_rank == 7:  # Мифрил
        hit_chance += MITHRIL_HIT_BONUS

    hit = random.randint(1, 100) <= hit_chance
    shooter_name = d["n1"] if shooter == d["p1"] else d["n2"]
    target_name = d["n2"] if target == d["p2"] else d["n1"]

    if hit:
        if target == d["p1"]:
            d["hp1"] -= 1
        else:
            d["hp2"] -= 1
        action = f"🔫 <b>{shooter_name}</b> попал в <b>{target_name}</b>! 💥"
    else:
        action = f"💨 <b>{shooter_name}</b> промахнулся!"

    # Check if someone died
    loser = None
    winner = None
    if d["hp1"] <= 0:
        loser, winner = d["p1"], d["p2"]
    elif d["hp2"] <= 0:
        loser, winner = d["p2"], d["p1"]

    if loser:
        del active_duels[key]
        winner_name = d["n1"] if winner == d["p1"] else d["n2"]
        loser_name = d["n1"] if loser == d["p1"] else d["n2"]

        async with aiosqlite.connect(DB_PATH) as db:
            # Check shield
            scur = await db.execute("SELECT shield FROM users WHERE user_id = ?", (loser,))
            srow = await scur.fetchone()
            if srow and srow[0] > 0:
                # Shield saves!
                await db.execute(
                    "UPDATE users SET shield = shield - 1 WHERE user_id = ?", (loser,),
                )
                await db.commit()
                text = (
                    f"{action}\n\n"
                    f"🛡️ <b>{loser_name}</b> использовал Щит Бессмертия и выжил!\n"
                    f"Дуэль завершена вничью."
                )
                await safe_edit(c.message, text, back_menu_kb())
                await c.answer()
                return

            # Transfer ALL assets from loser to winner
            lcur = await db.execute(
                "SELECT balance, bbc_balance, rank, winstreak FROM users WHERE user_id = ?",
                (loser,),
            )
            ldata = await lcur.fetchone()
            if ldata:
                await db.execute(
                    "UPDATE users SET balance = balance + ?, bbc_balance = bbc_balance + ? WHERE user_id = ?",
                    (ldata[0], ldata[1], winner),
                )

            # Transfer cards
            await db.execute(
                "UPDATE user_cards SET user_id = ? WHERE user_id = ?",
                (winner, loser),
            )

            # Update winner winstreak
            wcur = await db.execute("SELECT winstreak FROM users WHERE user_id = ?", (winner,))
            wrow = await wcur.fetchone()
            new_ws = (wrow[0] if wrow else 0) + 1
            await db.execute(
                "UPDATE users SET winstreak = ? WHERE user_id = ?",
                (new_ws, winner),
            )
            if new_ws >= 5:
                await try_achievement(db, winner, "streak_5")
            await try_achievement(db, winner, "duel_winner")
            await grant_xp(db, winner, 100)

            # WIPE loser completely
            await db.execute("DELETE FROM users WHERE user_id = ?", (loser,))
            await db.execute("DELETE FROM user_cards WHERE user_id = ?", (loser,))
            await db.execute("DELETE FROM bank_deposits WHERE user_id = ?", (loser,))
            await db.execute("DELETE FROM promo_used WHERE user_id = ?", (loser,))
            await db.execute("DELETE FROM achievements WHERE user_id = ?", (loser,))

            # Clear marriage if spouse
            await db.execute(
                "UPDATE users SET spouse_id = 0, marriage_date = '' WHERE spouse_id = ?",
                (loser,),
            )
            await db.commit()

        loot_text = ""
        if ldata:
            loot_text = f"\n💰 +{ldata[0]:,} монет, 💵 +{ldata[1]} BBC"

        text = (
            f"{action}\n\n"
            f"☠️ <b>{loser_name}</b> убит!\n"
            f"🏆 <b>{winner_name}</b> побеждает! (Серия: {new_ws})\n"
            f"{loot_text}\n"
            f"🗑️ Аккаунт {loser_name} уничтожен.\n\n"
            f"✨ +100 XP"
        )
        await safe_edit(c.message, text, back_menu_kb())
        await c.answer()
        return

    # Switch turns
    d["turn"] = target
    text = duel_status_text(d) + f"\n\n{action}"
    await safe_edit(c.message, text, duel_fire_kb(key, target))
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  BANK                                                      ║
# ══════════════════════════════════════════════════════════════

BANK_PLANS = [
    ("24h", "24 часа", 24, 0.05),
    ("48h", "48 часов", 48, 0.12),
    ("72h", "72 часа", 72, 0.20),
]


@dp.callback_query(F.data == "menu_bank")
async def bank_menu_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT dep_id, amount, plan, rate, finish_at, collected FROM bank_deposits "
            "WHERE user_id = ? AND collected = 0", (uid,),
        )
        deps = await cur.fetchall()

    text = "🏦 <b>БАНК</b>\n\n"
    if deps:
        text += "<b>Активные вклады:</b>\n"
        for dep in deps:
            try:
                finish = datetime.fromisoformat(dep[4])
                remaining = (finish - datetime.now()).total_seconds()
                if remaining <= 0:
                    status = "✅ Готов к снятию!"
                else:
                    status = f"⏳ {fmt_seconds(int(remaining))}"
            except Exception:
                status = "?"
            profit = int(dep[1] * dep[3])
            text += f"  #{dep[0]}: {dep[1]:,}💰 ({dep[2]}, +{profit:,}) — {status}\n"
    else:
        text += "У тебя нет вкладов.\n"

    text += "\n<b>Тарифы:</b>\n"
    for plan_id, name, hours, rate in BANK_PLANS:
        text += f"  📋 {name}: +{int(rate * 100)}%\n"

    rows = []
    for plan_id, name, hours, rate in BANK_PLANS:
        rows.append([InlineKeyboardButton(
            text=f"💰 Вложить ({name})",
            callback_data=f"bank_dep_{plan_id}",
        )])
    if deps:
        rows.append([InlineKeyboardButton(text="💸 Снять вклад", callback_data="bank_collect")])
    rows.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("bank_dep_"))
async def bank_deposit_cb(c: CallbackQuery, state: FSMContext):
    plan_id = c.data.replace("bank_dep_", "")
    plan = next((p for p in BANK_PLANS if p[0] == plan_id), None)
    if not plan:
        return await c.answer("❌ План не найден!", show_alert=True)
    await state.set_state(GameStates.waiting_for_bet)
    await state.update_data(bank_plan=plan)
    await safe_edit(c.message, f"🏦 Вклад: <b>{plan[1]}</b> (+{int(plan[3]*100)}%)\n\nВведи сумму:")
    await c.answer()


@dp.callback_query(F.data == "bank_collect")
async def bank_collect_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT dep_id, amount, rate, finish_at FROM bank_deposits "
            "WHERE user_id = ? AND collected = 0", (uid,),
        )
        deps = await cur.fetchall()
        collected_total = 0
        collected_count = 0
        not_ready = 0
        for dep in deps:
            try:
                finish = datetime.fromisoformat(dep[3])
                if datetime.now() >= finish:
                    payout = dep[1] + int(dep[1] * dep[2])
                    await db.execute(
                        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                        (payout, uid),
                    )
                    await db.execute(
                        "UPDATE bank_deposits SET collected = 1 WHERE dep_id = ?",
                        (dep[0],),
                    )
                    collected_total += payout
                    collected_count += 1
                else:
                    not_ready += 1
            except Exception:
                pass
        await db.commit()

    text = ""
    if collected_count:
        text += f"✅ Снято {collected_count} вклад(ов): <b>+{collected_total:,} 💰</b>\n"
    if not_ready:
        text += f"⏳ Ещё {not_ready} вклад(ов) не готовы."
    if not collected_count and not not_ready:
        text = "❌ Нет вкладов для снятия."
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  MARRIAGE                                                  ║
# ══════════════════════════════════════════════════════════════

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
        c1 = await db.execute(
            "SELECT nickname, spouse_id FROM users WHERE user_id = ?", (m.from_user.id,),
        )
        u1 = await c1.fetchone()
        if not u1:
            return await m.answer("❌ /start сначала")
        if u1[1]:
            return await m.answer("❌ Ты уже в браке!")

        c2 = await db.execute(
            "SELECT nickname, spouse_id FROM users WHERE user_id = ?", (target_id,),
        )
        u2 = await c2.fetchone()
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
        r1 = await (await db.execute("SELECT spouse_id FROM users WHERE user_id = ?", (proposer_id,))).fetchone()
        r2 = await (await db.execute("SELECT spouse_id FROM users WHERE user_id = ?", (target_id,))).fetchone()
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
        await try_achievement(db, proposer_id, "married")
        await try_achievement(db, target_id, "married")
        await db.commit()

    await safe_edit(c.message, "💍 <b>Поздравляем!</b> Брак заключён! 🎉", back_menu_kb())
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
        cur = await db.execute("SELECT spouse_id FROM users WHERE user_id = ?", (m.from_user.id,))
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
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT spouse_id FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row or not row[0]:
            return await c.answer("❌ Ты не в браке!", show_alert=True)
        spouse = row[0]
        await db.execute(
            "UPDATE users SET spouse_id = 0, marriage_date = '' WHERE user_id = ?", (uid,),
        )
        await db.execute(
            "UPDATE users SET spouse_id = 0, marriage_date = '' WHERE user_id = ?", (spouse,),
        )
        await db.commit()
    await safe_edit(c.message, "💔 Брак расторгнут.", back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  INVENTORY                                                 ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_inv")
async def inventory_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, c.rarity, COUNT(*) FROM user_cards uc "
            "JOIN cards c ON uc.card_id = c.card_id "
            "WHERE uc.user_id = ? GROUP BY c.card_id ORDER BY c.rarity DESC",
            (uid,),
        )
        cards = await cur.fetchall()
    if not cards:
        await safe_edit(c.message, "🎒 <b>Инвентарь пуст.</b>\n\nКрути гачу!", back_menu_kb())
    else:
        lines = [f"{RARITY_STARS.get(r, '⭐')} {name} x{cnt}" for name, r, cnt in cards]
        text = "🎒 <b>ИНВЕНТАРЬ</b>\n\n" + "\n".join(lines[:30])
        if len(lines) > 30:
            text += f"\n\n...и ещё {len(lines) - 30} типов"
        await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  LEADERBOARDS                                              ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_tops")
async def tops_menu_cb(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Монеты", callback_data="top_coins"),
         InlineKeyboardButton(text="🃏 BBC Карты", callback_data="top_cards")],
        [InlineKeyboardButton(text="⚔️ Серия побед", callback_data="top_streak"),
         InlineKeyboardButton(text="📊 Уровни", callback_data="top_levels")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, "🏆 <b>ТОПЫ</b>\n\nВыбери рейтинг:", kb)
    await c.answer()


@dp.callback_query(F.data == "top_coins")
async def top_coins_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance FROM users ORDER BY balance DESC LIMIT 10"
        )
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {r[0]}: {r[1]:,} 💰" for i, r in enumerate(rows)]
    await safe_edit(c.message, "💰 <b>ТОП ПО МОНЕТАМ</b>\n\n" + "\n".join(lines), back_menu_kb())
    await c.answer()


@dp.callback_query(F.data == "top_cards")
async def top_cards_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT u.nickname, SUM(c.rarity) as score, COUNT(*) as cnt "
            "FROM user_cards uc JOIN users u ON uc.user_id = u.user_id "
            "JOIN cards c ON uc.card_id = c.card_id "
            "GROUP BY uc.user_id ORDER BY score DESC LIMIT 10"
        )
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {r[0]}: {r[2]} карт (рейтинг: {r[1]})" for i, r in enumerate(rows)]
    await safe_edit(c.message, "🃏 <b>ТОП ПО КАРТАМ</b>\n\n" + "\n".join(lines or ["Пусто"]), back_menu_kb())
    await c.answer()


@dp.callback_query(F.data == "top_streak")
async def top_streak_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, winstreak FROM users WHERE winstreak > 0 "
            "ORDER BY winstreak DESC LIMIT 10"
        )
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {r[0]}: {r[1]} 🔥" for i, r in enumerate(rows)]
    await safe_edit(c.message, "⚔️ <b>ТОП ПО СЕРИИ ПОБЕД</b>\n\n" + "\n".join(lines or ["Пусто"]), back_menu_kb())
    await c.answer()


@dp.callback_query(F.data == "top_levels")
async def top_levels_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT 10"
        )
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {r[0]}: Ур.{r[1]} ({level_title(r[1])})" for i, r in enumerate(rows)]
    await safe_edit(c.message, "📊 <b>ТОП ПО УРОВНЯМ</b>\n\n" + "\n".join(lines or ["Пусто"]), back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  LEVEL SYSTEM                                              ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_level")
async def level_menu_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT xp, level FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
    xp, lvl = row
    need = xp_for_level(lvl)
    bar_len = 20
    filled = min(bar_len, int(xp / max(1, need) * bar_len))
    bar = "█" * filled + "░" * (bar_len - filled)
    pct = int(xp / max(1, need) * 100)

    text = (
        f"📊 <b>УРОВЕНЬ</b>\n\n"
        f"🎖 Звание: <b>{level_title(lvl)}</b>\n"
        f"📈 Уровень: <b>{lvl}</b>\n"
        f"✨ XP: {xp}/{need} ({pct}%)\n\n"
        f"[{bar}]\n\n"
        f"<b>Как получать XP:</b>\n"
        f"  💰 Ежедневка: +25 XP\n"
        f"  🔨 Работа: +15 XP\n"
        f"  🎴 Гача: +10 XP/карта\n"
        f"  🎮 Победа в казино: +30 XP\n"
        f"  ⚔️ Победа в дуэли: +100 XP\n"
        f"  🦹 Ограбление: +20 XP"
    )
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  EYE OF NEVER (/nev)                                       ║
# ══════════════════════════════════════════════════════════════

@dp.message(Command("nev"))
async def nev_cmd(m: Message):
    phases = [
        "🌑 Новолуние — удача скрыта",
        "🌒 Растущий серп — шансы улучшаются",
        "🌓 Первая четверть — баланс сил",
        "🌔 Прибывающая — удача на подъёме",
        "🌕 Полнолуние — максимальная сила!",
        "🌖 Убывающая — будь осторожен",
        "🌗 Последняя четверть — риск высок",
        "🌘 Старый серп — опасное время",
    ]
    luck = random.randint(1, 100)
    phase = random.choice(phases)

    if luck >= 80:
        verdict = "🟢 Сейчас отличное время для ставок!"
    elif luck >= 50:
        verdict = "🟡 Нормальные шансы. Рискуй с умом."
    elif luck >= 25:
        verdict = "🟠 Удача не на твоей стороне."
    else:
        verdict = "🔴 Сегодня лучше не играть!"

    text = (
        f"🔮 <b>ГЛАЗ НЕВЕРА</b>\n\n"
        f"Заглянул в будущее...\n\n"
        f"🎰 Рулетка: 48.6% (красное/чёрное)\n"
        f"🎲 Кости: 16.7% (угадать число)\n"
        f"🪙 Монетка: 50%\n"
        f"📈 Краш: ~60% (x1+), ~25% (x2+)\n\n"
        f"💫 <b>Твоя удача: {luck}%</b>\n"
        f"{phase}\n\n"
        f"{verdict}"
    )

    if m.from_user.id == ADMIN_ID and rig_mode == "win100":
        text += f"\n\n🎯 <i>ПОДКРУТ: 100% побед ({rig_remaining} игр)</i>"

    await m.answer(text, parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════
# ║  ROB (/rob)                                                ║
# ══════════════════════════════════════════════════════════════

@dp.message(Command("rob"))
async def rob_cmd(m: Message):
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.answer("🦹 Ответь на сообщение жертвы: /rob")
    target_id = m.reply_to_message.from_user.id
    uid = m.from_user.id
    if target_id == uid:
        return await m.answer("❌ Нельзя грабить себя!")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT balance, last_rob, rob_count FROM users WHERE user_id = ?", (uid,),
        )
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ /start сначала")

        remaining = cd_remaining(row[1], ROB_CD)
        if remaining > 0:
            return await m.answer(f"⏳ КД ограбления: {fmt_seconds(remaining)}")

        tcur = await db.execute("SELECT balance, nickname FROM users WHERE user_id = ?", (target_id,))
        target = await tcur.fetchone()
        if not target:
            return await m.answer("❌ Жертва не зарегистрирована!")
        if target[0] < 100:
            return await m.answer("❌ У жертвы слишком мало монет!")

        success = random.random() < 0.40  # 40% шанс
        if success:
            steal_pct = random.uniform(0.10, 0.30)
            stolen = min(int(target[0] * steal_pct), 5000)
            stolen = max(stolen, 1)
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (stolen, uid))
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (stolen, target_id))
            new_rob_count = (row[2] or 0) + 1
            await db.execute(
                "UPDATE users SET last_rob = ?, rob_count = ? WHERE user_id = ?",
                (datetime.now().isoformat(), new_rob_count, uid),
            )
            lvl_msg = await grant_xp(db, uid, 20)
            if new_rob_count >= 10:
                await try_achievement(db, uid, "rob_master")
            await db.commit()
            text = f"🦹 <b>Успешное ограбление!</b>\n\n💰 Украдено: <b>{stolen:,}</b> у {target[1]}\n✨ +20 XP"
            if lvl_msg:
                text += f"\n{lvl_msg}"
        else:
            fine = min(500, row[0])
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (fine, uid))
            await db.execute(
                "UPDATE users SET last_rob = ? WHERE user_id = ?",
                (datetime.now().isoformat(), uid),
            )
            await db.commit()
            text = f"🚨 <b>Провал!</b>\n\nТебя поймали! Штраф: <b>{fine:,} 💰</b>"

    await m.answer(text, parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════
# ║  GIFT (/gift)                                              ║
# ══════════════════════════════════════════════════════════════

@dp.message(Command("gift"))
async def gift_cmd(m: Message):
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.answer("🎁 Ответь на сообщение: /gift [ID карты]")
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer("🎁 Формат: /gift [ID карты]")
    card_id = parse_positive_int(args[1])
    if not card_id:
        return await m.answer("❌ ID карты — целое число > 0!")
    target_id = m.reply_to_message.from_user.id
    uid = m.from_user.id
    if target_id == uid:
        return await m.answer("❌ Нельзя дарить себе!")

    async with aiosqlite.connect(DB_PATH) as db:
        # Check ownership
        cur = await db.execute(
            "SELECT id FROM user_cards WHERE user_id = ? AND card_id = ? LIMIT 1",
            (uid, card_id),
        )
        uc = await cur.fetchone()
        if not uc:
            return await m.answer("❌ У тебя нет этой карты!")

        tcur = await db.execute("SELECT nickname FROM users WHERE user_id = ?", (target_id,))
        target = await tcur.fetchone()
        if not target:
            return await m.answer("❌ Получатель не зарегистрирован!")

        ccur = await db.execute("SELECT name, rarity FROM cards WHERE card_id = ?", (card_id,))
        card = await ccur.fetchone()

        # Transfer
        await db.execute("UPDATE user_cards SET user_id = ? WHERE id = ?", (target_id, uc[0]))
        await db.commit()

    card_name = card[0] if card else f"#{card_id}"
    card_rarity = RARITY_STARS.get(card[1], "⭐") if card else "⭐"
    await m.answer(
        f"🎁 <b>Подарок!</b>\n\n{card_rarity} <b>{card_name}</b> → <b>{target[0]}</b>",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════
# ║  ACHIEVEMENTS                                              ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_achs")
async def achievements_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT ach_id FROM achievements WHERE user_id = ?", (uid,))
        unlocked = {r[0] for r in await cur.fetchall()}

    lines = []
    for ach_id, (name, desc) in ACHIEVEMENTS.items():
        if ach_id in unlocked:
            lines.append(f"✅ {name} — {desc}")
        else:
            lines.append(f"🔒 {name} — {desc}")

    text = f"🏅 <b>ДОСТИЖЕНИЯ</b> ({len(unlocked)}/{len(ACHIEVEMENTS)})\n\n" + "\n".join(lines)
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  LUCKY WHEEL                                               ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "menu_wheel")
async def wheel_menu_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_wheel FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        remaining = cd_remaining(row[0], WHEEL_CD)

    if remaining > 0:
        text = f"🎡 <b>КОЛЕСО УДАЧИ</b>\n\n⏳ Доступно через: {fmt_seconds(remaining)}"
        await safe_edit(c.message, text, back_menu_kb())
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎡 Крутить!", callback_data="wheel_spin")],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
        ])
        await safe_edit(c.message, "🎡 <b>КОЛЕСО УДАЧИ</b>\n\n🆓 Бесплатный ежедневный спин!", kb)
    await c.answer()


@dp.callback_query(F.data == "wheel_spin")
async def wheel_spin_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_wheel FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        remaining = cd_remaining(row[0], WHEEL_CD)
        if remaining > 0:
            return await c.answer(f"⏳ КД: {fmt_seconds(remaining)}", show_alert=True)

        prize = random.choice(WHEEL_PRIZES)
        ptype, pval, pname = prize
        result_text = ""

        if ptype == "coins":
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (pval, uid))
            result_text = f"💰 <b>+{pval} монет!</b>"
        elif ptype == "bbc":
            await db.execute("UPDATE users SET bbc_balance = bbc_balance + ? WHERE user_id = ?", (pval, uid))
            result_text = f"💵 <b>+{pval} BBC!</b>"
        elif ptype == "xp":
            lvl_msg = await grant_xp(db, uid, pval)
            result_text = f"✨ <b>+{pval} XP!</b>"
            if lvl_msg:
                result_text += f"\n{lvl_msg}"
        else:
            result_text = "💨 <b>Пусто!</b> Повезёт в следующий раз."

        await db.execute(
            "UPDATE users SET last_wheel = ? WHERE user_id = ?",
            (datetime.now().isoformat(), uid),
        )
        await db.commit()

    text = f"🎡 <b>КОЛЕСО УДАЧИ</b>\n\n🎊 Результат: {pname}\n{result_text}"
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  PROMO CODES                                               ║
# ══════════════════════════════════════════════════════════════

@dp.message(Command("promo"))
async def promo_cmd(m: Message):
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer("🎁 Формат: /promo КОД")
    code = args[1].upper()
    uid = m.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
        if not await cur.fetchone():
            return await m.answer("❌ /start сначала")

        pcur = await db.execute(
            "SELECT reward_type, reward_value, uses_left FROM promocodes WHERE code = ?",
            (code,),
        )
        promo = await pcur.fetchone()
        if not promo:
            return await m.answer("❌ Промокод не найден!")
        if promo[2] <= 0:
            return await m.answer("❌ Промокод исчерпан!")

        ucur = await db.execute(
            "SELECT 1 FROM promo_used WHERE user_id = ? AND code = ?", (uid, code),
        )
        if await ucur.fetchone():
            return await m.answer("❌ Ты уже активировал этот промокод!")

        rtype, rval = promo[0], promo[1]
        if rtype == "money":
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (rval, uid))
        elif rtype == "bbc_money":
            await db.execute("UPDATE users SET bbc_balance = bbc_balance + ? WHERE user_id = ?", (rval, uid))

        await db.execute(
            "UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,),
        )
        await db.execute("INSERT INTO promo_used (user_id, code) VALUES (?, ?)", (uid, code))

        # Auto-delete if uses exhausted
        await db.execute("DELETE FROM promocodes WHERE uses_left <= 0")
        await db.commit()

    emoji = "💰" if rtype == "money" else "💵"
    await m.answer(
        f"✅ Промокод <b>{code}</b> активирован!\n{emoji} +{rval}",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════
# ║  ADMIN: ADD CARD, CARDS LIST, RIG                          ║
# ══════════════════════════════════════════════════════════════

@dp.message(Command("addcard"))
async def addcard_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    args = (m.text or "").split()

    # Способ 1: Реплай на пользователя — /addcard [редкость]
    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
        if target.is_bot:
            return await m.answer("❌ Нельзя создать карту из бота!")

        rarity = 1
        if len(args) >= 2:
            rarity = parse_positive_int(args[1])
            if not rarity or rarity > 5:
                return await m.answer("❌ Редкость — число от 1 до 5!\nФормат: /addcard [1-5]")

        # Берём ник
        card_name = target.full_name or f"User {target.id}"

        # Берём аватарку
        image_id = None
        try:
            photos = await m.bot.get_user_profile_photos(target.id, limit=1)
            if photos.total_count > 0:
                image_id = photos.photos[0][-1].file_id
        except Exception:
            pass

        if not image_id:
            return await m.answer(
                f"❌ У пользователя <b>{card_name}</b> нет аватарки!\n"
                f"Без аватарки карту создать нельзя.",
                parse_mode=ParseMode.HTML,
            )

        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO cards (name, rarity, image_id) VALUES (?, ?, ?)",
                (card_name, rarity, image_id),
            )
            card_id = cur.lastrowid
            await db.commit()

        await m.answer(
            f"✅ Карта создана из профиля!\n\n"
            f"🆔 ID: <b>{card_id}</b>\n"
            f"👤 Имя: <b>{card_name}</b>\n"
            f"⭐ Редкость: {RARITY_STARS.get(rarity, '⭐')}\n"
            f"🖼 Аватар: захвачен",
            parse_mode=ParseMode.HTML,
        )
        return

    # Способ 2: Фото + подпись — /addcard Название РЕДКОСТЬ
    if m.photo:
        caption = m.caption or ""
        parts = caption.split()
        if len(parts) < 3 or parts[0].lower() != "/addcard":
            return await m.answer("🃏 Подпись: /addcard Название РЕДКОСТЬ(1-5)")
        rarity = parse_positive_int(parts[-1])
        if not rarity or rarity > 5:
            return await m.answer("❌ Редкость — число от 1 до 5!")
        name = " ".join(parts[1:-1])
        image_id = m.photo[-1].file_id

        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO cards (name, rarity, image_id) VALUES (?, ?, ?)",
                (name, rarity, image_id),
            )
            card_id = cur.lastrowid
            await db.commit()

        await m.answer(
            f"✅ Карта добавлена!\n\n"
            f"🆔 ID: <b>{card_id}</b>\n"
            f"📝 Название: {name}\n"
            f"⭐ Редкость: {RARITY_STARS.get(rarity, '⭐')}",
            parse_mode=ParseMode.HTML,
        )
        return

    # Инструкция
    await m.answer(
        "🃏 <b>Как добавить карту:</b>\n\n"
        "📌 <b>Способ 1 (реплай):</b>\n"
        "Ответь на сообщение пользователя:\n"
        "<code>/addcard 3</code>\n"
        "Бот возьмёт его аватарку и ник.\n\n"
        "📌 <b>Способ 2 (фото):</b>\n"
        "Отправь фото с подписью:\n"
        "<code>/addcard Название 3</code>\n\n"
        "Редкость: 1-5 (⭐ до ⭐⭐⭐⭐⭐)",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("cards"))
async def cards_list_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT card_id, name, rarity FROM cards ORDER BY rarity DESC, card_id")
        cards = await cur.fetchall()
    if not cards:
        return await m.answer("🃏 База карт пуста.")
    lines = [f"<code>#{c[0]}</code> {RARITY_STARS.get(c[2], '⭐')} {c[1]}" for c in cards]
    chunks = [lines[i:i+20] for i in range(0, len(lines), 20)]
    for chunk in chunks:
        await m.answer("🃏 <b>ВСЕ КАРТЫ:</b>\n\n" + "\n".join(chunk), parse_mode=ParseMode.HTML)


@dp.message(Command("rig"))
async def rig_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    global rig_mode, rig_remaining
    args = (m.text or "").split()
    if len(args) < 2:
        status = f"🎯 100% ({rig_remaining} игр)" if rig_mode == "win100" else "⚖️ Выкл"
        return await m.answer(
            f"🎰 Подкрут: {status}\n\n"
            f"Формат: /rig 100 [кол-во игр] или /rig off"
        )
    if args[1].lower() == "off":
        rig_mode = "normal"
        rig_remaining = 0
        return await m.answer("⚖️ Подкрут выключен.")
    if args[1] == "100" and len(args) >= 3:
        count = parse_positive_int(args[2])
        if not count:
            return await m.answer("❌ Количество — целое число > 0!")
        rig_mode = "win100"
        rig_remaining = count
        return await m.answer(f"🎯 Подкрут: 100% побед на {count} игр!")
    await m.answer("❌ Формат: /rig 100 [кол-во] или /rig off")


# ══════════════════════════════════════════════════════════════
# ║  ADMIN PANEL                                               ║
# ══════════════════════════════════════════════════════════════

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm_promo"),
         InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players")],
        [InlineKeyboardButton(text="💰 Экономика", callback_data="adm_econ"),
         InlineKeyboardButton(text="🃏 Карты", callback_data="adm_cards")],
        [InlineKeyboardButton(text="🎰 Подкрутка", callback_data="adm_rig"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="🔍 Просмотр игрока", callback_data="adm_lookup"),
         InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
    ])


@dp.message(Command("admin"))
async def admin_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer("👑 <b>АДМИН-ПАНЕЛЬ</b>", reply_markup=admin_main_kb(), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_back")
async def admin_back_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await safe_edit(c.message, "👑 <b>АДМИН-ПАНЕЛЬ</b>", admin_main_kb())
    await c.answer()


# ── Статистика ───────────────────────────────────────────────

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
        tc = (await (await db.execute("SELECT SUM(balance) FROM users")).fetchone())[0] or 0
        banned = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned = 1"
        )).fetchone())[0]
    rig_status = f"🎯 100% ({rig_remaining} игр)" if rig_mode == "win100" else "⚖️ Выкл"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")]
    ])
    await safe_edit(
        c.message,
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Игроков: {uc}\n"
        f"🚫 Забанено: {banned}\n"
        f"🃏 Карт в базе: {cc}\n"
        f"🎁 Промокодов: {pc}\n"
        f"🏦 Активных вкладов: {bc}\n"
        f"💰 Всего монет в экономике: {tc:,}\n"
        f"🎰 Подкрут: {rig_status}",
        kb,
    )
    await c.answer()


# ── Промокоды ────────────────────────────────────────────────

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
        return await m.answer("❌ Неверный формат.")
    val = parse_positive_int(args[2])
    uses = parse_positive_int(args[3])
    if val is None or uses is None:
        await state.clear()
        return await m.answer("❌ Сумма и кол-во — целые числа > 0!")

    code = args[0].upper()
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO promocodes (code, reward_type, reward_value, uses_left) VALUES (?, ?, ?, ?)",
                (code, args[1], val, uses),
            )
            await db.commit()
        except Exception:
            await state.clear()
            return await m.answer("❌ Промокод уже существует!")

    await state.clear()
    await m.answer(f"✅ Промокод <b>{code}</b> создан! ({args[1]}: {val}, {uses} активаций)", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_promo_list")
async def adm_promo_list_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT code, reward_type, reward_value, uses_left FROM promocodes")
        promos = await cur.fetchall()
    if not promos:
        text = "📋 Промокодов нет."
    else:
        lines = [f"<code>{p[0]}</code> — {p[1]}: {p[2]} (осталось: {p[3]})" for p in promos]
        text = "📋 <b>Промокоды:</b>\n\n" + "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Промокоды", callback_data="adm_promo")]
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "adm_promo_del")
async def adm_promo_del_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_promo_del)
    await safe_edit(c.message, "🗑 Введи код промокода для удаления:")
    await c.answer()


@dp.message(AdminStates.waiting_for_promo_del)
async def process_promo_del(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    code = (m.text or "").strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        await db.commit()
        if cur.rowcount == 0:
            await state.clear()
            return await m.answer("❌ Промокод не найден!")
    await state.clear()
    await m.answer(f"✅ Промокод <b>{code}</b> удалён.", parse_mode=ParseMode.HTML)


# ── Игроки ───────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_players")
async def adm_players_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Бан", callback_data="adm_p_ban"),
         InlineKeyboardButton(text="✅ Разбан", callback_data="adm_p_unban")],
        [InlineKeyboardButton(text="🗑 Вайп", callback_data="adm_p_wipe")],
        [InlineKeyboardButton(text="🔱 Выдать Мифрил", callback_data="adm_p_myth"),
         InlineKeyboardButton(text="⬇️ Снять Мифрил", callback_data="adm_p_demyth")],
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")],
    ])
    await safe_edit(c.message, "👥 <b>Управление игроками</b>", kb)
    await c.answer()


@dp.callback_query(F.data == "adm_p_ban")
async def adm_ban_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_ban_id)
    await safe_edit(c.message, "🚫 Введи ID игрока для бана:")
    await c.answer()


@dp.message(AdminStates.waiting_for_ban_id)
async def process_ban(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🚫 Игрок <code>{uid}</code> забанен.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_unban")
async def adm_unban_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_unban_id)
    await safe_edit(c.message, "✅ Введи ID игрока для разбана:")
    await c.answer()


@dp.message(AdminStates.waiting_for_unban_id)
async def process_unban(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"✅ Игрок <code>{uid}</code> разбанен.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_wipe")
async def adm_wipe_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_wipe_id)
    await safe_edit(c.message, "🗑 Введи ID игрока для аннулирования:")
    await c.answer()


@dp.message(AdminStates.waiting_for_wipe_id)
async def process_wipe(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM user_cards WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM bank_deposits WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM promo_used WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM achievements WHERE user_id = ?", (uid,))
        await db.execute(
            "UPDATE users SET spouse_id = 0, marriage_date = '' WHERE spouse_id = ?", (uid,),
        )
        await db.commit()
    await state.clear()
    await m.answer(f"🗑 Аккаунт <code>{uid}</code> полностью аннулирован.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_myth")
async def adm_myth_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_myth_id)
    await safe_edit(c.message, "🔱 Введи ID игрока для выдачи Мифрила:")
    await c.answer()


@dp.message(AdminStates.waiting_for_myth_id)
async def process_myth(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET rank = 7 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🔱 Игроку <code>{uid}</code> выдан ранг Мифрил.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_demyth")
async def adm_demyth_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_demyth_id)
    await safe_edit(c.message, "⬇️ Введи ID игрока для снятия Мифрила:")
    await c.answer()


@dp.message(AdminStates.waiting_for_demyth_id)
async def process_demyth(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT rank FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            await state.clear()
            return await m.answer("❌ Игрок не найден!")
        if row[0] != 7:
            await state.clear()
            return await m.answer("❌ У игрока нет ранга Мифрил!")
        await db.execute("UPDATE users SET rank = 0 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"⬇️ Ранг Мифрил снят с <code>{uid}</code>.", parse_mode=ParseMode.HTML)


# ── Экономика ────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_econ")
async def adm_econ_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_econ_data)
    await safe_edit(
        c.message,
        "💰 <b>Управление экономикой</b>\n\n"
        "Формат: <code>ТИП ID СУММА</code>\n\n"
        "Типы:\n"
        "• <code>+coins ID СУММА</code> — выдать монеты\n"
        "• <code>-coins ID СУММА</code> — снять монеты\n"
        "• <code>+bbc ID СУММА</code> — выдать BBC\n"
        "• <code>-bbc ID СУММА</code> — снять BBC",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_econ_data)
async def process_econ(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 3:
        await state.clear()
        return await m.answer("❌ Формат: ТИП ID СУММА")

    op = args[0]
    uid = parse_positive_int(args[1])
    val = parse_positive_int(args[2])
    if not uid or not val:
        await state.clear()
        return await m.answer("❌ ID и сумма — целые числа > 0!")

    async with aiosqlite.connect(DB_PATH) as db:
        if op == "+coins":
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (val, uid))
            action = f"+{val:,} монет"
        elif op == "-coins":
            await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (val, uid))
            action = f"-{val:,} монет"
        elif op == "+bbc":
            await db.execute("UPDATE users SET bbc_balance = bbc_balance + ? WHERE user_id = ?", (val, uid))
            action = f"+{val} BBC"
        elif op == "-bbc":
            await db.execute("UPDATE users SET bbc_balance = MAX(0, bbc_balance - ?) WHERE user_id = ?", (val, uid))
            action = f"-{val} BBC"
        else:
            await state.clear()
            return await m.answer("❌ Тип: +coins, -coins, +bbc, -bbc")
        await db.commit()

    await state.clear()
    await m.answer(f"✅ Игрок <code>{uid}</code>: {action}", parse_mode=ParseMode.HTML)


# ── Карты (редкость) ─────────────────────────────────────────

@dp.callback_query(F.data == "adm_cards")
async def adm_cards_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_card_rarity)
    await safe_edit(
        c.message,
        "🃏 <b>Изменение редкости карты</b>\n\n"
        "Формат: <code>ID_КАРТЫ НОВАЯ_РЕДКОСТЬ</code>\n"
        "Пример: <code>5 3</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_card_rarity)
async def process_card_rarity(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 2:
        await state.clear()
        return await m.answer("❌ Формат: ID_КАРТЫ РЕДКОСТЬ")
    cid = parse_positive_int(args[0])
    rarity = parse_positive_int(args[1])
    if not cid or not rarity or rarity > 5:
        await state.clear()
        return await m.answer("❌ ID и редкость (1-5) — целые числа!")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM cards WHERE card_id = ?", (cid,))
        card = await cur.fetchone()
        if not card:
            await state.clear()
            return await m.answer("❌ Карта не найдена!")
        await db.execute("UPDATE cards SET rarity = ? WHERE card_id = ?", (rarity, cid))
        await db.commit()

    await state.clear()
    await m.answer(
        f"✅ Карта <b>{card[0]}</b> (#{cid}): редкость → {RARITY_STARS.get(rarity, '⭐')}",
        parse_mode=ParseMode.HTML,
    )


# ── Подкрутка (админ-панель) ─────────────────────────────────

@dp.callback_query(F.data == "adm_rig")
async def adm_rig_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    status = f"🎯 100% ({rig_remaining} игр)" if rig_mode == "win100" else "⚖️ Выкл"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Включить 100%", callback_data="adm_rig_on")],
        [InlineKeyboardButton(text="⚖️ Выключить", callback_data="adm_rig_off")],
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")],
    ])
    await safe_edit(c.message, f"🎰 <b>Подкрутка</b>\n\nТекущий: {status}", kb)
    await c.answer()


@dp.callback_query(F.data == "adm_rig_on")
async def adm_rig_on_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_rig_count)
    await safe_edit(c.message, "🎯 Введи количество игр с 100% победой:")
    await c.answer()


@dp.message(AdminStates.waiting_for_rig_count)
async def process_rig_count(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    global rig_mode, rig_remaining
    count = parse_positive_int(m.text)
    if not count:
        await state.clear()
        return await m.answer("❌ Число > 0!")
    rig_mode = "win100"
    rig_remaining = count
    await state.clear()
    await m.answer(f"🎯 Подкрут: 100% побед на {count} игр!", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_rig_off")
async def adm_rig_off_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    global rig_mode, rig_remaining
    rig_mode = "normal"
    rig_remaining = 0
    await safe_edit(c.message, "⚖️ Подкрут выключен.", admin_main_kb())
    await c.answer()


# ── Просмотр игрока ──────────────────────────────────────────

@dp.callback_query(F.data == "adm_lookup")
async def adm_lookup_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_lookup_id)
    await safe_edit(c.message, "🔍 Введи ID игрока:")
    await c.answer()


@dp.message(AdminStates.waiting_for_lookup_id)
async def process_lookup(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance, bbc_balance, rank, title, winstreak, "
            "is_banned, xp, level, daily_streak, spouse_id, shield, "
            "coin_multiplier, vip_until FROM users WHERE user_id = ?",
            (uid,),
        )
        u = await cur.fetchone()
        if not u:
            await state.clear()
            return await m.answer("❌ Игрок не найден!")

        ccur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (uid,))
        cards = (await ccur.fetchone())[0]
        acur = await db.execute("SELECT COUNT(*) FROM achievements WHERE user_id = ?", (uid,))
        achs = (await acur.fetchone())[0]

    await state.clear()
    text = (
        f"🔍 <b>Профиль игрока</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 Ник: {u[0]}\n"
        f"💰 Баланс: {u[1]:,}\n"
        f"💵 BBC: {u[2]}\n"
        f"🎖 Ранг: {RANK_NAMES.get(u[3], '?')}\n"
        f"📛 Титул: {u[4] or 'Нет'}\n"
        f"📊 Уровень: {u[8]} ({u[7]} XP)\n"
        f"⚔️ Серия: {u[5]}\n"
        f"🔥 Стрик: {u[9]}\n"
        f"🃏 Карт: {cards}\n"
        f"🏅 Достижений: {achs}\n"
        f"🛡️ Щитов: {u[11]}\n"
        f"💰 Множитель: x{u[12]}\n"
        f"🚫 Бан: {'Да' if u[6] else 'Нет'}\n"
        f"💍 Партнёр: {u[10] or 'Нет'}"
    )
    await m.answer(text, parse_mode=ParseMode.HTML)


# ── Рассылка ─────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await safe_edit(c.message, "📢 Введи текст рассылки (HTML поддерживается):")
    await c.answer()


@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    text = m.text or ""
    if not text:
        await state.clear()
        return await m.answer("❌ Текст пуст!")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = await cur.fetchall()

    sent = 0
    failed = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"📢 <b>Объявление:</b>\n\n{text}", parse_mode=ParseMode.HTML)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # Anti-flood

    await state.clear()
    await m.answer(f"📢 Рассылка: ✅ {sent} | ❌ {failed}")


# ══════════════════════════════════════════════════════════════
# ║  BANK DEPOSIT FSM (intercept from GameStates)              ║
# ══════════════════════════════════════════════════════════════

# The bank deposit uses GameStates.waiting_for_bet with bank_plan in state data
# We need to intercept it. Let's override the handler to check context.

_orig_bet_handler = bet_custom_input


@dp.message(GameStates.waiting_for_bet)
async def smart_bet_input(m: Message, state: FSMContext):
    data = await state.get_data()
    if "bank_plan" in data:
        # Bank deposit flow
        amount = parse_positive_int(m.text)
        if not amount:
            await state.clear()
            return await m.answer("❌ Сумма — целое число > 0!", reply_markup=back_menu_kb())
        plan = data["bank_plan"]
        uid = m.from_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
            row = await cur.fetchone()
            if not row or row[0] < amount:
                await state.clear()
                return await m.answer("❌ Недостаточно монет!", reply_markup=back_menu_kb())

            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, uid))
            now = datetime.now()
            finish = (now + timedelta(hours=plan[2])).isoformat()
            await db.execute(
                "INSERT INTO bank_deposits (user_id, amount, plan, rate, created_at, finish_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (uid, amount, plan[1], plan[3], now.isoformat(), finish),
            )
            await db.commit()

        profit = int(amount * plan[3])
        await state.clear()
        await m.answer(
            f"🏦 <b>Вклад открыт!</b>\n\n"
            f"💰 Сумма: {amount:,}\n"
            f"📋 План: {plan[1]} (+{int(plan[3]*100)}%)\n"
            f"💵 Доход: +{profit:,}\n"
            f"⏰ Готов через: {plan[2]} ч",
            parse_mode=ParseMode.HTML,
            reply_markup=back_menu_kb(),
        )
    else:
        # Game bet flow
        await _orig_bet_handler(m, state)


# ══════════════════════════════════════════════════════════════
# ║  MAIN                                                      ║
# ══════════════════════════════════════════════════════════════

async def main():
    await init_db()
    log.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
