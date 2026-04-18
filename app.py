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
from aiogram.types import ErrorEvent
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

# ── Конфиг ───────────────────────────────────────────────────
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 1548461377
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
RARITY_NAMES = {1: "Обычная", 2: "Необычная", 3: "Редкая", 4: "Эпическая", 5: "Легендарная"}
RARITY_QUOTES = {
    1: "Ну... бывает и так 😅",
    2: "Неплохо! 🙂",
    3: "Оу, это редкость! 🔥",
    4: "ЭПИК!! Тебе повезло! 🎉",
    5: "🌟 ЛЕГЕНДА!! НЕВЕРОЯТНО!! 🌟",
}
CARDS_PER_PAGE = 10

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


class ArenaStates(StatesGroup):
    in_queue = State()
    in_battle = State()


class BlackjackStates(StatesGroup):
    in_game = State()

class RouletteStates(StatesGroup):
    waiting_for_players = State()

class AdminV5States(StatesGroup):
    waiting_for_arena_reset = State()
    waiting_for_quest_reset = State()

# ── Глобальное состояние ─────────────────────────────────────
rig_mode = "normal"
rig_remaining = 0
antispam: dict = {}

# ── Message owner tracking (inline-button protection) ──
_msg_owners: dict[str, int] = {}


def _track_msg(chat_id: int, msg_id: int, user_id: int):
    """Remember who owns a message so only they can tap its buttons."""
    _msg_owners[f"{chat_id}:{msg_id}"] = user_id
    if len(_msg_owners) > 10_000:
        for k in list(_msg_owners)[:5000]:
            del _msg_owners[k]

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
    waiting_for_set_title_id = State()
    waiting_for_set_title_text = State()
    waiting_for_reset_cd_id = State()
    waiting_for_mass_give_data = State()
    waiting_for_del_card_id = State()
    waiting_for_rename_card_data = State()
    waiting_for_give_card_data = State()
    waiting_for_take_card_data = State()
    waiting_for_give_ach_data = State()
    waiting_for_set_level_data = State()
    waiting_for_freeze_id = State()
    waiting_for_unfreeze_id = State()
    waiting_for_set_balance_data = State()
    waiting_for_nickname_data = State()
    waiting_for_db_restore = State()


# ══════════════════════════════════════════════════════════════
# ║  MIDDLEWARE                                                ║
# ══════════════════════════════════════════════════════════════

class BanCheckMiddleware(BaseMiddleware):
    """Полностью игнорирует забаненных пользователей."""

    _ban_cache: dict[int, float] = {}   # uid → timestamp when ban was cached
    _CACHE_TTL = 30                       # seconds

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        uid = user.id
        now = time.time()

        # Fast path: check in-memory cache
        cached_ts = self._ban_cache.get(uid)
        if cached_ts and (now - cached_ts) < self._CACHE_TTL:
            # Known banned user — silently drop
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("🚫 Вы забанены.", show_alert=True)
                except Exception:
                    pass
            return  # ← do NOT call handler

        # Check database
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT is_banned FROM users WHERE user_id = ?", (uid,)
                )
                row = await cur.fetchone()
        except Exception:
            # DB error — block if user was ever in ban cache, otherwise let through
            if uid in self._ban_cache:
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("🚫 Вы забанены.", show_alert=True)
                    except Exception:
                        pass
                return
            return await handler(event, data)

        if row and row[0]:
            self._ban_cache[uid] = now
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("🚫 Вы забанены.", show_alert=True)
                except Exception:
                    pass
            return  # ← do NOT call handler

        # Not banned — remove from cache if was there
        self._ban_cache.pop(uid, None)
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


class OwnerCallbackMiddleware(BaseMiddleware):
    """Only the user who triggered the message can tap its inline buttons."""

    PUBLIC_PREFIXES = (
        "duel_acc_", "duel_dec_", "duel_fire_",
        "marry_acc_", "marry_dec_",

    )

    async def __call__(self, handler, event: CallbackQuery, data):
        cb_data = event.data or ""
        if any(cb_data.startswith(p) for p in self.PUBLIC_PREFIXES):
            return await handler(event, data)
        if event.message:
            owner = _msg_owners.get(f"{event.message.chat.id}:{event.message.message_id}")
            if owner is not None and event.from_user.id != owner:
                await event.answer("❌ Это не твоё меню!", show_alert=True)
                return
        return await handler(event, data)


dp.message.outer_middleware(BanCheckMiddleware())
dp.callback_query.outer_middleware(BanCheckMiddleware())
dp.message.middleware(AntiSpamMiddleware())
dp.callback_query.middleware(AntiSpamMiddleware())
dp.callback_query.middleware(OwnerCallbackMiddleware())


# ══════════════════════════════════════════════════════════════
# ║  ERROR HANDLER                                             ║
# ══════════════════════════════════════════════════════════════

@dp.errors()
async def errors_handler(event: ErrorEvent):
    exc = event.exception
    if isinstance(exc, TelegramBadRequest):
        msg = str(exc)
        if "query is too old" in msg or "message is not modified" in msg:
            return True
    log.exception("Unhandled: %s", exc)
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
            last_wheel TEXT DEFAULT '',
            is_frozen INTEGER DEFAULT 0
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rarity INTEGER DEFAULT 1,
            image_id TEXT DEFAULT '',
            source_user_id INTEGER DEFAULT 0
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
        await db.execute("""CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            ach_id TEXT,
            achieved_at TEXT,
            PRIMARY KEY (user_id, ach_id)
        )""")

        # ── v5.0 Tables ──
        await db.execute("""CREATE TABLE IF NOT EXISTS arena_players (
            user_id INTEGER PRIMARY KEY,
            elo INTEGER DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            league TEXT DEFAULT 'Бронза'
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS fish_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fish_type TEXT,
            count INTEGER DEFAULT 1,
            UNIQUE(user_id, fish_type)
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS daily_quests (
            user_id INTEGER,
            quest_date TEXT,
            q1_type TEXT, q1_target INTEGER, q1_progress INTEGER DEFAULT 0, q1_done INTEGER DEFAULT 0,
            q2_type TEXT, q2_target INTEGER, q2_progress INTEGER DEFAULT 0, q2_done INTEGER DEFAULT 0,
            q3_type TEXT, q3_target INTEGER, q3_progress INTEGER DEFAULT 0, q3_done INTEGER DEFAULT 0,
            all_done_claimed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, quest_date)
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS craft_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_type TEXT,
            count INTEGER DEFAULT 1,
            UNIQUE(user_id, item_type)
        )""")

        # ── Браки / Пары ──
        await db.execute("""CREATE TABLE IF NOT EXISTS marriages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            chat_id INTEGER,
            married_at TEXT DEFAULT '',
            UNIQUE(user1_id, user2_id)
        )""")

        # ── Разрешения /me ──
        await db.execute("""CREATE TABLE IF NOT EXISTS me_permissions (
            user_id INTEGER PRIMARY KEY,
            granted_by INTEGER,
            granted_at TEXT DEFAULT ''
        )""")

        # blackjack_games table removed — game state managed via FSM
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
        "is_frozen": "INTEGER DEFAULT 0",
    }
    for col, td in new.items():
        if col not in cols:
            await db.execute(f"ALTER TABLE users ADD COLUMN {col} {td}")
            log.info("Migrated users.%s", col)
    cur2 = await db.execute("PRAGMA table_info(cards)")
    ccols = {r[1] for r in await cur2.fetchall()}
    if "image_id" not in ccols:
        await db.execute("ALTER TABLE cards ADD COLUMN image_id TEXT DEFAULT ''")
    if "source_user_id" not in ccols:
        await db.execute("ALTER TABLE cards ADD COLUMN source_user_id INTEGER DEFAULT 0")
    await db.execute("""CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER, ach_id TEXT, achieved_at TEXT,
        PRIMARY KEY (user_id, ach_id))""")
    # Defensive: ensure new tables exist on old databases
    await db.execute("""CREATE TABLE IF NOT EXISTS marriages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER,
        user2_id INTEGER,
        chat_id INTEGER,
        married_at TEXT DEFAULT '',
        UNIQUE(user1_id, user2_id)
    )""")
    await db.execute("""CREATE TABLE IF NOT EXISTS me_permissions (
        user_id INTEGER PRIMARY KEY,
        granted_by INTEGER,
        granted_at TEXT DEFAULT ''
    )""")
    await db.commit()


# ══════════════════════════════════════════════════════════════
# ║  HELPERS                                                   ║
# ══════════════════════════════════════════════════════════════

async def is_frozen(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT is_frozen FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return bool(row and row[0])


def parse_positive_int(text) -> Optional[int]:
    try:
        v = int(text)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


async def safe_edit(msg: Message, text: str, kb=None):
    try:
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            pass
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
         InlineKeyboardButton(text="🛒 Магазин", callback_data="menu_shop")],
        [InlineKeyboardButton(text="💎 BBC Магазин", callback_data="menu_bbcshop"),
         InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton(text="🏆 Топы", callback_data="menu_tops"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv")],
        [InlineKeyboardButton(text="📊 Уровень", callback_data="menu_level"),
         InlineKeyboardButton(text="🎡 Колесо", callback_data="menu_wheel")],
        [InlineKeyboardButton(text="🏅 Достижения", callback_data="menu_achs"),
         InlineKeyboardButton(text="💰 Ежедневка", callback_data="menu_daily")],
        [InlineKeyboardButton(text="🔨 Работа", callback_data="menu_work"),
         InlineKeyboardButton(text="🎣 Рыбалка", callback_data="menu_fish")],
        [InlineKeyboardButton(text="⚔️ Арена", callback_data="menu_arena"),
         InlineKeyboardButton(text="💑 Пары", callback_data="menu_pairs")],
        [InlineKeyboardButton(text="📋 Квесты", callback_data="menu_quests"),
         InlineKeyboardButton(text="🃏 Карты", callback_data="menu_cards")],
        [InlineKeyboardButton(text="🎟️ Промокод", callback_data="menu_promo")],
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
    sent = await m.answer(
        "🎮 <b>Добро пожаловать в Game Bot!</b>\n\nВыбери действие:",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    _track_msg(sent.chat.id, sent.message_id, m.from_user.id)


@dp.callback_query(F.data == "menu_back")
async def menu_back_cb(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(c.message, "🎮 <b>Главное меню</b>", main_menu_kb())
    _track_msg(c.message.chat.id, c.message.message_id, c.from_user.id)
    await c.answer()


@dp.message(Command("menu"))
async def menu_cmd(m: Message, state: FSMContext):
    await state.clear()
    sent = await m.answer("🎮 <b>Главное меню</b>", reply_markup=main_menu_kb(), parse_mode=ParseMode.HTML)
    _track_msg(sent.chat.id, sent.message_id, m.from_user.id)


# ── Меню → Арена ─────────────────────────────────────────────
@dp.callback_query(F.data == "menu_arena")
async def menu_arena_cb(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS arena_players (
            user_id INTEGER PRIMARY KEY, elo INTEGER DEFAULT 1000, wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0, league TEXT DEFAULT 'Бронза')""")
        await ensure_arena(db, uid)
        await db.commit()
        cur = await db.execute("SELECT elo, wins, losses, league FROM arena_players WHERE user_id=?", (uid,))
        row = await cur.fetchone()
    elo, wins, losses, league = row
    league = elo_league(elo)

    if any(u == uid for u, _, _ in arena_queue):
        await safe_edit(
            c.message,
            "⏳ <b>Ты уже в очереди!</b> Ожидай соперника...",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="arena_cancel")],
                [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
            ])
        )
    else:
        await safe_edit(
            c.message,
            f"⚔️ <b>Арена</b>\n\n"
            f"🏅 Лига: <b>{league}</b>\n"
            f"📊 ЭЛО: <b>{elo}</b>\n"
            f"✅ Победы: <b>{wins}</b> | ❌ Поражений: <b>{losses}</b>\n\n"
            f"Выбери ставку и найди соперника:",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Найти соперника (100💰)", callback_data="arena_queue:100")],
                [InlineKeyboardButton(text="⚔️ Бой на 500💰", callback_data="arena_queue:500")],
                [InlineKeyboardButton(text="⚔️ Бой на 1000💰", callback_data="arena_queue:1000")],
                [InlineKeyboardButton(text="🏆 Топ арены", callback_data="arena_top")],
                [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
            ])
        )
    await c.answer()


# ── Меню → Кланы ─────────────────────────────────────────────


@dp.callback_query(F.data == "menu_profile")
async def profile_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance, bbc_balance, rank, title, vip_until, "
            "coin_multiplier, winstreak, xp, level, "
            "daily_streak, shield FROM users WHERE user_id = ?",
            (uid,),
        )
        u = await cur.fetchone()
        if not u:
            return await c.answer("❌ /start сначала", show_alert=True)
        nick, bal, bbc, rank, title, vip, mult, ws, xp, lvl, streak, shield = u

        cards_cur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (uid,))
        card_count = (await cards_cur.fetchone())[0]

        ach_cur = await db.execute("SELECT COUNT(*) FROM achievements WHERE user_id = ?", (uid,))
        ach_count = (await ach_cur.fetchone())[0]


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

        await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (amount, m.from_user.id))
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

        await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (total_cost, uid))

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

        await db.execute("UPDATE users SET bbc_balance = MAX(0, bbc_balance - ?) WHERE user_id = ?", (total_cost, uid))

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
        [InlineKeyboardButton(text="🃏 Блэкджек", callback_data="game_blackjack"),
         InlineKeyboardButton(text="🎰 Слоты", callback_data="game_slots")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, "🎮 <b>ИГРОВОЙ ЦЕНТР</b>\n\nВыбери игру:", kb)
    await c.answer()


@dp.callback_query(F.data == "game_blackjack")
async def game_blackjack_cb(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(
        c.message,
        "🃏 <b>Блэкджек</b>\n\nВыбери ставку:",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="100", callback_data="bjbet_100"),
             InlineKeyboardButton(text="500", callback_data="bjbet_500"),
             InlineKeyboardButton(text="1000", callback_data="bjbet_1000")],
            [InlineKeyboardButton(text="5000", callback_data="bjbet_5000"),
             InlineKeyboardButton(text="ALL-IN", callback_data="bjbet_allin")],
            [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
        ])
    )
    await c.answer()


@dp.callback_query(F.data.regexp(r"^bjbet_"))
async def bjbet_cb(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    val = c.data.replace("bjbet_", "")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        await db.commit()
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        balance = row[0] if row else 0
        if val == "allin":
            bet = balance
        else:
            bet = int(val)
        if bet < 50:
            return await c.answer("❌ Минимальная ставка 50!", show_alert=True)
        if balance < bet:
            return await c.answer("❌ Недостаточно монет!", show_alert=True)
        # Deduct bet immediately to prevent negative balance
        await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid))
        await db.commit()
    deck = new_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    await state.update_data(bet=bet, deck=deck, player_hand=player_hand, dealer_hand=dealer_hand)
    await state.set_state(BlackjackStates.in_game)
    await _show_blackjack(c, player_hand, dealer_hand, bet, state)
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  CRASH GAME — Proper turn-based with Cash Out              ║
# ══════════════════════════════════════════════════════════════

# In-memory crash game state: uid -> {bet, crash_point, current_mult, chat_id, msg_id}
_crash_games: dict[int, dict] = {}
_crash_last_click: dict[int, float] = {}   # uid -> timestamp (anti-spam)
CRASH_CLICK_CD = 1.5  # seconds between clicks

CRASH_STEPS = [
    1.1, 1.2, 1.3, 1.5, 1.7, 2.0, 2.3, 2.6, 3.0, 3.5,
    4.0, 5.0, 6.0, 7.5, 10.0
]


def _generate_crash_point() -> float:
    """Generate crash point (weighted towards low values, max x10)."""
    r = random.random()
    if r < 0.35:
        return round(random.uniform(1.0, 1.3), 2)   # 35% — instant crash
    elif r < 0.60:
        return round(random.uniform(1.3, 2.0), 2)    # 25%
    elif r < 0.80:
        return round(random.uniform(2.0, 3.5), 2)    # 20%
    elif r < 0.92:
        return round(random.uniform(3.5, 5.0), 2)    # 12%
    elif r < 0.98:
        return round(random.uniform(5.0, 7.5), 2)    # 6%
    else:
        return round(random.uniform(7.5, 10.0), 2)   # 2%


def _crash_text(bet: int, current_mult: float, step_idx: int) -> str:
    bar_len = min(step_idx + 1, 15)
    bar = "🟩" * bar_len + "⬛" * (15 - bar_len)
    potential = int(bet * current_mult)
    return (
        f"📈 <b>КРАШ</b> | Ставка: {bet:,}💰\n\n"
        f"{bar}\n"
        f"Множитель: <b>x{current_mult}</b>\n"
        f"Потенциальный выигрыш: <b>{potential:,}💰</b>\n\n"
        f"⚠️ В любой момент может крахнуть!"
    )


@dp.callback_query(F.data.regexp(r"^crashbet_"))
async def crashbet_cb(c: CallbackQuery):
    uid = c.from_user.id
    val = c.data.replace("crashbet_", "")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        await db.commit()
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        balance = row[0] if row else 0
        if val == "allin":
            bet = balance
        else:
            bet = int(val)
        if bet < 50:
            return await c.answer("❌ Минимальная ставка 50!", show_alert=True)
        if balance < bet:
            return await c.answer("❌ Недостаточно монет!", show_alert=True)
        # Deduct bet immediately
        await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid))
        await db.commit()

    crash_point = _generate_crash_point()
    start_mult = 1.0
    _crash_games[uid] = {
        "bet": bet,
        "crash_point": crash_point,
        "current_mult": start_mult,
        "step_idx": 0,
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Дальше!", callback_data="crash_next"),
         InlineKeyboardButton(text=f"💰 Забрать ({bet}💰)", callback_data="crash_cashout")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="crash_cancel")],
    ])
    await safe_edit(c.message, _crash_text(bet, start_mult, 0), kb)
    await c.answer()


@dp.callback_query(F.data == "crash_next")
async def crash_next_cb(c: CallbackQuery):
    uid = c.from_user.id
    import time as _time
    now = _time.time()
    last = _crash_last_click.get(uid, 0)
    if now - last < CRASH_CLICK_CD:
        return await c.answer(f"⏳ Подожди {CRASH_CLICK_CD:.0f} сек между ходами!", show_alert=False)
    _crash_last_click[uid] = now

    game = _crash_games.get(uid)
    if not game:
        return await c.answer("❌ Нет активной игры!", show_alert=True)

    step_idx = game["step_idx"]
    if step_idx >= len(CRASH_STEPS) - 1:
        # Max reached — auto cashout
        game["current_mult"] = CRASH_STEPS[-1]
        return await _crash_cashout(c, uid)

    next_mult = CRASH_STEPS[step_idx]
    crash_point = game["crash_point"]

    if next_mult >= crash_point:
        # CRASHED!
        bet = game["bet"]
        del _crash_games[uid]
        text = (
            f"📈 <b>КРАШ</b> | Ставка: {bet:,}💰\n\n"
            f"💥💥💥 <b>КРАХ на x{crash_point}!</b> 💥💥💥\n\n"
            f"❌ Ты потерял {bet:,}💰"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_crash"),
             InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        ])
        await safe_edit(c.message, text, kb)
        return await c.answer("💥 КРАХ!", show_alert=True)

    # Advance
    game["current_mult"] = next_mult
    game["step_idx"] = step_idx + 1
    potential = int(game["bet"] * next_mult)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Дальше!", callback_data="crash_next"),
         InlineKeyboardButton(text=f"💰 Забрать ({potential:,}💰)", callback_data="crash_cashout")],
    ])
    await safe_edit(c.message, _crash_text(game["bet"], next_mult, step_idx + 1), kb)
    await c.answer()


@dp.callback_query(F.data == "crash_cashout")
async def crash_cashout_cb(c: CallbackQuery):
    uid = c.from_user.id
    await _crash_cashout(c, uid)


async def _crash_cashout(c: CallbackQuery, uid: int):
    game = _crash_games.get(uid)
    if not game:
        return await c.answer("❌ Нет активной игры!", show_alert=True)

    bet = game["bet"]
    mult = game["current_mult"]
    winnings = int(bet * mult)
    profit = winnings - bet  # Could be 0 at x1.0
    del _crash_games[uid]

    async with aiosqlite.connect(DB_PATH) as db:
        # Return bet + profit (we already deducted bet)
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (winnings, uid))
        if profit > 0:
            await grant_xp(db, uid, 30)
            await try_achievement(db, uid, "first_win")
        await db.commit()

    if mult <= 1.0:
        result = f"🤝 Ты забрал ставку обратно: {winnings:,}💰 (x{mult})"
    else:
        result = f"✅ <b>Успел забрать на x{mult}! +{profit:,}💰</b>"

    text = (
        f"📈 <b>КРАШ</b>\n\n"
        f"💰 {result}\n"
        f"Крах был бы на: x{game['crash_point']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_crash"),
         InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "crash_cancel")
async def crash_cancel_cb(c: CallbackQuery):
    uid = c.from_user.id
    game = _crash_games.get(uid)
    if game:
        # Return bet
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (game["bet"], uid))
            await db.commit()
        del _crash_games[uid]
    await c.answer("Ставка возвращена!")
    await safe_edit(
        c.message,
        "📈 Краш отменён. Ставка возвращена.",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        ])
    )


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


@dp.callback_query(F.data == "game_crash")
async def game_crash_menu_cb(c: CallbackQuery):
    """Show crash bet selection with its own keyboard."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100", callback_data="crashbet_100"),
         InlineKeyboardButton(text="500", callback_data="crashbet_500"),
         InlineKeyboardButton(text="1000", callback_data="crashbet_1000")],
        [InlineKeyboardButton(text="5000", callback_data="crashbet_5000"),
         InlineKeyboardButton(text="ALL-IN", callback_data="crashbet_allin")],
        [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
    ])
    await safe_edit(
        c.message,
        "<b>📈 Краш</b>\nМножитель растёт. Успей забрать!\n\nВыбери ставку:",
        kb,
    )
    await c.answer()


@dp.callback_query(F.data.in_({"game_roulette", "game_dice", "game_coin"}))
async def game_select_cb(c: CallbackQuery):
    game = c.data.replace("game_", "")
    names = {"roulette": "🎰 Рулетка", "dice": "🎲 Кости", "coin": "🪙 Монетка"}
    descs = {
        "roulette": "Красное/Чёрное x2, Зелёное x14",
        "dice": "Угадай число 1-6, выигрыш x5",
        "coin": "Орёл или решка, выигрыш x1.9",
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
    if game == "roulette":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Красное x2", callback_data=f"rlt_red_{amount}"),
             InlineKeyboardButton(text="⚫ Чёрное x2", callback_data=f"rlt_black_{amount}")],
            [InlineKeyboardButton(text="🟢 Зелёное x14", callback_data=f"rlt_green_{amount}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_roulette")],
        ])
        await safe_edit(c.message, f"🎰 <b>Рулетка</b> | Ставка: {amount:,}💰\n\nВыбери цвет:", kb)
        return await c.answer()
    if game == "coin":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🦅 Орёл", callback_data=f"coinpick_heads_{amount}"),
             InlineKeyboardButton(text="🪙 Решка", callback_data=f"coinpick_tails_{amount}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_coin")],
        ])
        await safe_edit(c.message, f"🪙 <b>Монетка</b> | Ставка: {amount:,}💰\n\nОрёл или решка?", kb)
        return await c.answer()
    await play_game(c, game, amount)


@dp.callback_query(F.data.regexp(r"^bet_\w+_allin$"))
async def bet_allin_cb(c: CallbackQuery):
    game = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (c.from_user.id,))
        row = await cur.fetchone()
        if not row or row[0] <= 0:
            return await c.answer("❌ У тебя 0 монет!", show_alert=True)
        amount = row[0]
    if game == "roulette":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Красное x2", callback_data=f"rlt_red_{amount}"),
             InlineKeyboardButton(text="⚫ Чёрное x2", callback_data=f"rlt_black_{amount}")],
            [InlineKeyboardButton(text="🟢 Зелёное x14", callback_data=f"rlt_green_{amount}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_roulette")],
        ])
        await safe_edit(c.message, f"🎰 <b>Рулетка</b> | ALL-IN: {amount:,}💰\n\nВыбери цвет:", kb)
        return await c.answer()
    if game == "coin":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🦅 Орёл", callback_data=f"coinpick_heads_{amount}"),
             InlineKeyboardButton(text="🪙 Решка", callback_data=f"coinpick_tails_{amount}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_coin")],
        ])
        await safe_edit(c.message, f"🪙 <b>Монетка</b> | ALL-IN: {amount:,}💰\n\nОрёл или решка?", kb)
        return await c.answer()
    await play_game(c, game, amount)


@dp.callback_query(F.data.regexp(r"^bet_\w+_custom$"))
async def bet_custom_cb(c: CallbackQuery, state: FSMContext):
    game = c.data.split("_")[1]
    await state.set_state(GameStates.waiting_for_bet)
    await state.update_data(game_type=game)
    await safe_edit(c.message, "✏️ Введи сумму ставки:")
    await c.answer()


@dp.message(GameStates.waiting_for_bet)
async def bet_custom_input(m: Message, state: FSMContext):
    amount = parse_positive_int(m.text)
    if not amount:
        await state.clear()
        return await m.answer("❌ Ставка — целое число > 0!", reply_markup=back_menu_kb())
    data = await state.get_data()
    game = data.get("game_type", "roulette")
    await state.clear()

    if game == "roulette":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Красное x2", callback_data=f"rlt_red_{amount}"),
             InlineKeyboardButton(text="⚫ Чёрное x2", callback_data=f"rlt_black_{amount}")],
            [InlineKeyboardButton(text="🟢 Зелёное x14", callback_data=f"rlt_green_{amount}")],
            [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
        ])
        return await m.answer(f"🎰 <b>Рулетка</b> | Ставка: {amount:,}💰\n\nВыбери цвет:", reply_markup=kb, parse_mode=ParseMode.HTML)

    if game == "coin":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🦅 Орёл", callback_data=f"coinpick_heads_{amount}"),
             InlineKeyboardButton(text="🪙 Решка", callback_data=f"coinpick_tails_{amount}")],
            [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
        ])
        return await m.answer(f"🪙 <b>Монетка</b> | Ставка: {amount:,}💰\n\nОрёл или решка?", reply_markup=kb, parse_mode=ParseMode.HTML)

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.data = ""
        async def answer(self, *a, **kw):
            pass

    fc = FakeCallback(m, m.from_user)
    await play_game(fc, game, amount, is_message=True)


@dp.callback_query(F.data.regexp(r"^rlt_(red|black|green)_\d+$"))
async def roulette_play_cb(c: CallbackQuery):
    parts = c.data.split("_")
    color = parts[1]  # red, black, green
    bet = int(parts[2])
    await play_game(c, "roulette", bet, choice=color)


@dp.callback_query(F.data.regexp(r"^coinpick_(heads|tails)_\d+$"))
async def coin_play_cb(c: CallbackQuery):
    parts = c.data.split("_")
    side = parts[1]  # heads, tails
    bet = int(parts[2])
    await play_game(c, "coin", bet, choice=side)


async def play_game(c, game: str, bet: int, is_message: bool = False, choice: str = ""):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row or row[0] < bet:
            if is_message:
                return await c.message.answer("❌ Недостаточно монет!", reply_markup=back_menu_kb())
            return await c.answer("❌ Недостаточно монет!", show_alert=True)

        # Deduct bet immediately to prevent negative balance
        await db.execute(
            "UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ? AND balance >= ?",
            (bet, uid, bet),
        )
        await db.commit()

        rigged = game_is_rigged()
        won = False
        winnings = 0
        text = ""

        if game == "roulette":
            color_map = {"red": "🔴", "black": "⚫", "green": "🟢"}
            choice_name = {"red": "Красное", "black": "Чёрное", "green": "Зелёное"}.get(choice, "Красное")
            player_color = color_map.get(choice, "🔴")
            colors = ["🔴"] * 18 + ["⚫"] * 18 + ["🟢"]
            if rigged:
                result = player_color
            else:
                result = random.choice(colors)
            if result == "🟢" and choice == "green":
                won = True
                winnings = bet * 14
                text = f"🎰 Рулетка: {result}\n🎯 Ставка: {choice_name}\n🤑 <b>ЗЕЛЁНОЕ! +{winnings:,} 💰</b>"
            elif result == player_color:
                won = True
                winnings = bet * 2
                text = f"🎰 Рулетка: {result}\n🎯 Ставка: {choice_name}\n✅ <b>Победа! +{winnings:,} 💰</b>"
            else:
                text = f"🎰 Рулетка: {result}\n🎯 Ставка: {choice_name}\n❌ Проигрыш: -{bet:,} 💰"

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
            player_side = "Орёл 🦅" if choice == "heads" else "Решка 🪙"
            if rigged:
                flip = player_side
            else:
                flip = random.choice(["Орёл 🦅", "Решка 🪙"])
            won = (flip == player_side)
            if won:
                winnings = int(bet * 1.9)
                text = f"🪙 Результат: {flip}\n🎯 Твой выбор: {player_side}\n✅ <b>Победа! +{winnings:,} 💰</b>"
            else:
                text = f"🪙 Результат: {flip}\n🎯 Твой выбор: {player_side}\n❌ Проигрыш: -{bet:,} 💰"

        elif game == "crash":
            # Crash is now handled separately via crash_start
            text = "📈 Используй кнопку Краш в меню игр!"
            # Don't process here — redirect
            kb2 = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📈 Краш", callback_data="game_crash")],
                [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
            ])
            if is_message:
                await c.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb2)
            else:
                await safe_edit(c.message, text, kb2)
                await c.answer()
            return

        if won:
            # Bet was already deducted — add full winnings back
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (winnings, uid),
            )
            lvl_msg = await grant_xp(db, uid, 30)
            await try_achievement(db, uid, "first_win")
            cur2 = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
            new_bal = (await cur2.fetchone())[0]
            await check_wealth_achievements(db, uid, new_bal)
        else:
            # Bet already deducted — no further action
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

            # WIPE loser stats (keep user row + marriages!)
            await db.execute(
                "UPDATE users SET balance=0, bbc_balance=0, rank=0, "
                "title='', vip_until='', coin_multiplier=1.0, "
                "winstreak=0, xp=0, level=1, daily_streak=0, "
                "last_streak_date='', rob_count=0, last_rob='', "
                "lucky_gacha=0, shield=0, last_daily='', last_work='', "
                "last_gacha='', last_wheel='' "
                "WHERE user_id = ?", (loser,)
            )
            await db.execute("DELETE FROM user_cards WHERE user_id = ?", (loser,))
            await db.execute("DELETE FROM promo_used WHERE user_id = ?", (loser,))
            await db.execute("DELETE FROM achievements WHERE user_id = ?", (loser,))
            # marriages NOT deleted — брак сохраняется после дуэли

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
        [InlineKeyboardButton(text="💑 Топ пар", callback_data="top_pairs")],
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
            # Re-check victim balance and cap stolen amount to prevent negative balance
            tcur2 = await db.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,))
            target_now = await tcur2.fetchone()
            if target_now and target_now[0] < stolen:
                stolen = max(target_now[0], 0)
            if stolen <= 0:
                # Victim went broke between check and rob
                await db.execute(
                    "UPDATE users SET last_rob = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), uid),
                )
                await db.commit()
                return await m.answer("🚨 Жертва успела потратить все монеты!")
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (stolen, uid))
            await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (stolen, target_id))
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
            await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (fine, uid))
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

def _is_addcard_cmd(m: Message) -> bool:
    """Custom filter: ловит /addcard в text И в caption (фото)."""
    t = (m.text or m.caption or "").strip().lower()
    if not t.startswith("/addcard"):
        return False
    rest = t[8:]  # len("/addcard") == 8
    return not rest or rest[0] in (" ", "@", "\n")


@dp.message(_is_addcard_cmd)
async def addcard_cmd(m: Message):
    logging.info(
        f"ADDCARD HIT: user={m.from_user.id}, text={m.text!r}, "
        f"caption={m.caption!r}, has_photo={bool(m.photo)}, "
        f"reply={bool(m.reply_to_message)}"
    )
    if m.from_user.id != ADMIN_ID:
        return

    raw = (m.text or m.caption or "").strip()
    args = raw.split()

    # ── Способ 1: Реплай на пользователя — /addcard [редкость] ──
    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
        if target.is_bot:
            return await m.answer("❌ Нельзя создать карту из бота!")

        rarity = 1
        if len(args) >= 2:
            r = parse_positive_int(args[1])
            if r and 1 <= r <= 5:
                rarity = r
            else:
                return await m.answer("❌ Редкость — число от 1 до 5!\nФормат: /addcard [1-5]")

        card_name = target.full_name or f"User {target.id}"

        # ── Проверка: нельзя создать 2 карты одного юзера ──
        async with aiosqlite.connect(DB_PATH) as db:
            await _ensure_game_tables(db)
            dup_cur = await db.execute(
                "SELECT card_id, name FROM cards WHERE source_user_id = ?",
                (target.id,),
            )
            existing = await dup_cur.fetchone()
        if existing:
            return await m.answer(
                f"❌ Карта этого юзера уже существует!\n\n"
                f"🆔 ID: <b>{existing[0]}</b>\n"
                f"👤 Имя: <b>{existing[1]}</b>\n\n"
                f"Используй <code>/delcard {existing[0]}</code> чтобы удалить старую.",
                parse_mode=ParseMode.HTML,
            )

        # Берём аватарку
        image_id = None
        try:
            photos = await m.bot.get_user_profile_photos(target.id, limit=1)
            if photos.total_count > 0:
                image_id = photos.photos[0][-1].file_id
        except Exception as e:
            logging.warning(f"ADDCARD avatar error: {e}")

        if not image_id:
            return await m.answer(
                f"❌ У <b>{card_name}</b> нет аватарки! Карту без фото создать нельзя.",
                parse_mode=ParseMode.HTML,
            )

        async with aiosqlite.connect(DB_PATH) as db:
            await _ensure_game_tables(db)
            cur = await db.execute(
                "INSERT INTO cards (name, rarity, image_id, source_user_id) VALUES (?, ?, ?, ?)",
                (card_name, rarity, image_id, target.id),
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

    # ── Способ 2: Фото + подпись — /addcard Название РЕДКОСТЬ ──
    if m.photo:
        parts = raw.split()
        if len(parts) < 3:
            return await m.answer("🃏 Подпись: /addcard Название РЕДКОСТЬ(1-5)")
        rarity = parse_positive_int(parts[-1])
        if not rarity or rarity > 5:
            return await m.answer("❌ Редкость — число от 1 до 5!")
        # Убираем /addcard и редкость, остаётся название
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

    # ── Инструкция ──
    await m.answer(
        "🃏 <b>Как добавить карту:</b>\n\n"
        "📌 <b>Способ 1 (реплай):</b>\n"
        "Ответь на сообщение пользователя:\n"
        "<code>/addcard 3</code>\n"
        "Бот возьмёт его аватарку и ник автоматически.\n\n"
        "📌 <b>Способ 2 (фото):</b>\n"
        "Отправь фото с подписью:\n"
        "<code>/addcard Название 3</code>\n\n"
        "⭐ Редкость: 1-5",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("cards"))
async def cards_list_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT card_id, name, rarity FROM cards ORDER BY rarity DESC, card_id")
        cards = await cur.fetchall()
    if not cards:
        return await m.answer("🃏 База карт пуста.")
    total = len(cards)
    total_pages = (total + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
    page_cards = cards[:CARDS_PER_PAGE]
    lines = [f"<code>#{c[0]}</code> {RARITY_STARS.get(c[2], '⭐')} <b>{c[1]}</b> ({RARITY_NAMES.get(c[2], '?')})" for c in page_cards]
    text = f"🃏 <b>ВСЕ КАРТЫ</b> (стр. 1/{total_pages}, всего: {total})\n\n" + "\n".join(lines)
    buttons = []
    if total_pages > 1:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data="cards_page_1"))
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])
    await m.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@dp.callback_query(F.data.startswith("cards_page_"))
async def cards_page_cb(c: CallbackQuery):
    page = int(c.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT card_id, name, rarity FROM cards ORDER BY rarity DESC, card_id")
        cards = await cur.fetchall()
    if not cards:
        return await c.answer("🃏 База карт пуста.", show_alert=True)
    total = len(cards)
    total_pages = (total + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
    page = max(0, min(page, total_pages - 1))
    start = page * CARDS_PER_PAGE
    page_cards = cards[start:start + CARDS_PER_PAGE]
    lines = [f"<code>#{c[0]}</code> {RARITY_STARS.get(c[2], '⭐')} <b>{c[1]}</b> ({RARITY_NAMES.get(c[2], '?')})" for c in page_cards]
    text = f"🃏 <b>ВСЕ КАРТЫ</b> (стр. {page+1}/{total_pages}, всего: {total})\n\n" + "\n".join(lines)
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"cards_page_{page-1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"cards_page_{page+1}"))
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])
    await safe_edit(c.message, text, kb)
    await c.answer()


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


@dp.message(Command("delcard"))
async def delcard_cmd(m: Message):
    """Админ удаляет карту из базы: /delcard CARD_ID"""
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer(
            "🗑 <b>Удаление карты</b>\n\n"
            "Формат: <code>/delcard CARD_ID</code>\n"
            "Удалит карту из базы и у всех игроков.",
            parse_mode=ParseMode.HTML,
        )
    cid = parse_positive_int(args[1])
    if not cid:
        return await m.answer("❌ ID карты — целое число > 0!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name, rarity FROM cards WHERE card_id = ?", (cid,))
        card = await cur.fetchone()
        if not card:
            return await m.answer(f"❌ Карта #{cid} не найдена в базе!")
        cnt_cur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE card_id = ?", (cid,))
        cnt = (await cnt_cur.fetchone())[0]
        await db.execute("DELETE FROM cards WHERE card_id = ?", (cid,))
        await db.execute("DELETE FROM user_cards WHERE card_id = ?", (cid,))
        await db.commit()
    await m.answer(
        f"🗑 <b>Карта удалена!</b>\n\n"
        f"🆔 ID: <b>{cid}</b>\n"
        f"📝 Имя: <b>{card[0]}</b>\n"
        f"⭐ Редкость: {RARITY_STARS.get(card[1], '⭐')}\n"
        f"👥 Убрана у {cnt} игроков.",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("dropcard"))
async def dropcard_cmd(m: Message):
    """Игрок удаляет свою карту: /dropcard CARD_ID [кол-во|all]"""
    uid = m.from_user.id
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer(
            "🗑 <b>Удалить карту</b>\n\n"
            "Формат: <code>/dropcard CARD_ID</code> — удалить 1 шт.\n"
            "<code>/dropcard CARD_ID 3</code> — удалить 3 шт.\n"
            "<code>/dropcard CARD_ID all</code> — удалить все копии.\n\n"
            "Посмотри свои карты в профиле 🃏",
            parse_mode=ParseMode.HTML,
        )
    cid = parse_positive_int(args[1])
    if not cid:
        return await m.answer("❌ ID карты — целое число > 0!")

    amount_str = args[2].lower() if len(args) >= 3 else "1"
    drop_all = amount_str == "all"
    amount = 0 if drop_all else parse_positive_int(amount_str)
    if not drop_all and not amount:
        return await m.answer("❌ Количество — число > 0 или 'all'!")

    async with aiosqlite.connect(DB_PATH) as db:
        ccur = await db.execute("SELECT name, rarity FROM cards WHERE card_id = ?", (cid,))
        card_info = await ccur.fetchone()
        if not card_info:
            return await m.answer(f"❌ Карта #{cid} не существует!")
        cnt_cur = await db.execute(
            "SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND card_id = ?",
            (uid, cid),
        )
        owned = (await cnt_cur.fetchone())[0]
        if owned == 0:
            return await m.answer("❌ У тебя нет этой карты!")
        to_delete = owned if drop_all else min(amount, owned)
        ids_cur = await db.execute(
            "SELECT id FROM user_cards WHERE user_id = ? AND card_id = ? LIMIT ?",
            (uid, cid, to_delete),
        )
        ids = [r[0] for r in await ids_cur.fetchall()]
        if ids:
            placeholders = ",".join("?" * len(ids))
            await db.execute(f"DELETE FROM user_cards WHERE id IN ({placeholders})", ids)
            await db.commit()

    remaining = owned - to_delete
    rarity_star = RARITY_STARS.get(card_info[1], "⭐")
    await m.answer(
        f"🗑 <b>Карта удалена из коллекции!</b>\n\n"
        f"{rarity_star} <b>{card_info[0]}</b>\n"
        f"Удалено: {to_delete} шт.\n"
        f"Осталось: {remaining} шт.",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════
# ║  ADMIN PANEL                                               ║
# ══════════════════════════════════════════════════════════════

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players"),
         InlineKeyboardButton(text="📦 Выдача", callback_data="adm_give_panel")],
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm_promo"),
         InlineKeyboardButton(text="🃏 Карты", callback_data="adm_cards")],
        [InlineKeyboardButton(text="🎰 Игры & Подкрутка", callback_data="adm_games"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="⚔️ Арена", callback_data="adm_arena_panel")],
        [InlineKeyboardButton(text="💬 /me разрешения", callback_data="adm_me_perms")],
        [InlineKeyboardButton(text="🔍 Просмотр игрока", callback_data="adm_lookup"),
         InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="✏️ Сменить ник", callback_data="adm_set_nickname")],
        [InlineKeyboardButton(text="📦 Бэкап БД", callback_data="adm_backup")],
        [InlineKeyboardButton(text="🔄 Откат БД", callback_data="adm_rollback"),
         InlineKeyboardButton(text="📥 Восстановить БД", callback_data="adm_restore")],
    ])


def admin_give_kb() -> InlineKeyboardMarkup:
    """Клавиатура со всеми функциями выдачи"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Экономика (+/-)", callback_data="adm_econ"),
         InlineKeyboardButton(text="💰 Задать баланс", callback_data="adm_set_balance")],
        [InlineKeyboardButton(text="🎁 Раздача всем", callback_data="adm_mass_give"),
         InlineKeyboardButton(text="📝 Задать титул", callback_data="adm_set_title")],
        [InlineKeyboardButton(text="⚡ Задать уровень", callback_data="adm_set_level"),
         InlineKeyboardButton(text="🔄 Сброс КД", callback_data="adm_reset_cd")],
        [InlineKeyboardButton(text="🔱 Выдать Мифрил", callback_data="adm_p_myth"),
         InlineKeyboardButton(text="⬇️ Снять Мифрил", callback_data="adm_p_demyth")],
        [InlineKeyboardButton(text="🎴 Дать карту", callback_data="adm_give_card"),
         InlineKeyboardButton(text="🗑 Забрать карту", callback_data="adm_take_card")],
        [InlineKeyboardButton(text="🏅 Дать ачивку", callback_data="adm_give_ach")],
        [InlineKeyboardButton(text="🥶 Заморозить", callback_data="adm_freeze"),
         InlineKeyboardButton(text="☀️ Разморозить", callback_data="adm_unfreeze")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")],
    ])


def admin_games_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Подкрутка казино", callback_data="adm_rig")],
        [InlineKeyboardButton(text="🗑 Удалить карту", callback_data="adm_del_card"),
         InlineKeyboardButton(text="✏️ Переименовать карту", callback_data="adm_rename_card")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")],
    ])


def admin_arena_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сброс ЭЛО игрока", callback_data="adm_arena_reset")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")],
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")]
    ])
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            uc = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            cc = (await (await db.execute("SELECT COUNT(*) FROM cards")).fetchone())[0]
            pc = (await (await db.execute("SELECT COUNT(*) FROM promocodes")).fetchone())[0]
            tc = (await (await db.execute("SELECT SUM(balance) FROM users")).fetchone())[0] or 0
            banned = (await (await db.execute(
                "SELECT COUNT(*) FROM users WHERE is_banned = 1"
            )).fetchone())[0]
        rig_status = f"🎯 100% ({rig_remaining} игр)" if rig_mode == "win100" else "⚖️ Выкл"
        await safe_edit(
            c.message,
            f"📊 <b>Статистика</b>\n\n"
            f"👥 Игроков: {uc}\n"
            f"🚫 Забанено: {banned}\n"
            f"🃏 Карт в базе: {cc}\n"
            f"🎁 Промокодов: {pc}\n"
            f"💰 Всего монет в экономике: {tc:,}\n"
            f"🎰 Подкрут: {rig_status}",
            kb,
        )
    except Exception as e:
        await safe_edit(c.message, f"📊 <b>Статистика</b>\n\n⚠️ Ошибка: <code>{e}</code>", kb)
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Промокоды", callback_data="adm_promo")]
    ])
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT code, reward_type, reward_value, uses_left FROM promocodes")
            promos = await cur.fetchall()
        if not promos:
            text = "📋 Промокодов нет."
        else:
            lines = [f"<code>{p[0]}</code> — {p[1]}: {p[2]} (осталось: {p[3]})" for p in promos]
            text = "📋 <b>Промокоды:</b>\n\n" + "\n".join(lines)
    except Exception as e:
        text = f"📋 <b>Промокоды</b>\n\n⚠️ Ошибка: <code>{e}</code>"
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
        [InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")],
    ])
    await safe_edit(c.message, "👥 <b>Управление игроками</b>\n\n💡 Выдача мифрила, заморозка — в разделе 📦 Выдача", kb)
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
        # Ensure user exists before banning
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (uid,))
        await db.commit()
    # Immediately add to ban cache so middleware blocks them right away
    BanCheckMiddleware._ban_cache[uid] = time.time()
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
    # Clear ban cache immediately
    BanCheckMiddleware._ban_cache.pop(uid, None)
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
        await db.execute(
            "UPDATE users SET balance=0, bbc_balance=0, rank=0, "
            "title='', vip_until='', coin_multiplier=1.0, "
            "winstreak=0, xp=0, level=1, daily_streak=0, "
            "last_streak_date='', rob_count=0, last_rob='', "
            "lucky_gacha=0, shield=0, last_daily='', last_work='', "
            "last_gacha='', last_wheel='' "
            "WHERE user_id = ?", (uid,)
        )
        await db.execute("DELETE FROM user_cards WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM promo_used WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM achievements WHERE user_id = ?", (uid,))
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
            "is_banned, xp, level, daily_streak, shield, "
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
        f"🛡️ Щитов: {u[10]}\n"
        f"💰 Множитель: x{u[11]}\n"
        f"🚫 Бан: {'Да' if u[6] else 'Нет'}"
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
# ║  WORD TRIGGER: "карта" → gacha                             ║
# ══════════════════════════════════════════════════════════════

@dp.message(F.text.regexp(r'^[^/]'), StateFilter(None))
async def word_trigger_card(m: Message):
    text = (m.text or "").lower().strip()
    if "карта" not in text:
        return  # Not our trigger
    uid = m.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT last_gacha, lucky_gacha, is_frozen, rank FROM users WHERE user_id = ?", (uid,)
        )
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ Сначала нажми /start!")
        if row[2]:
            return await m.answer("🥶 Твой аккаунт заморожен!")
        user_rank = row[3] or 0
        if user_rank != 7:  # 🔱 Мифрил — КД 0 сек
            remaining = cd_remaining(row[0], GACHA_CD)
            if remaining > 0:
                return await m.answer(f"⏳ Гача на КД: {fmt_seconds(remaining)}")

        lucky = bool(row[1])
        results, err = await do_gacha(db, uid, 1, lucky)
        if err:
            return await m.answer(err)

        if lucky:
            await db.execute("UPDATE users SET lucky_gacha = 0 WHERE user_id = ?", (uid,))
        await db.execute(
            "UPDATE users SET last_gacha = ? WHERE user_id = ?",
            (datetime.now().isoformat(), uid),
        )
        lvl_msg = await grant_xp(db, uid, 10)
        await check_collection_achievements(db, uid)
        await db.commit()

    # Build rich output
    async with aiosqlite.connect(DB_PATH) as db2:
        total_cur = await db2.execute("SELECT COUNT(*) FROM cards")
        total_in_db = (await total_cur.fetchone())[0]
        owned_cur = await db2.execute(
            "SELECT COUNT(DISTINCT card_id) FROM user_cards WHERE user_id = ?", (uid,)
        )
        owned_unique = (await owned_cur.fetchone())[0]

    card = results[0]
    r = card[2]
    rname = RARITY_NAMES.get(r, "???")
    quote = RARITY_QUOTES.get(r, "")
    text_out = (
        f"🎴 <b>НОВАЯ КАРТА!</b>\n\n"
        f"{RARITY_STARS.get(r, '⭐')} <b>{card[1]}</b>\n"
        f"├ Редкость: {rname} ({r}/5)\n"
        f"└ {quote}\n\n"
        f"📊 Коллекция: {owned_unique}/{total_in_db} уникальных"
    )
    if lucky:
        text_out += "\n🌀 <i>Портал Удачи использован!</i>"
    if lvl_msg:
        text_out += f"\n{lvl_msg}"
    text_out += "\n✨ +10 XP"

    if card[3]:
        try:
            await bot.send_photo(
                m.chat.id, card[3], caption=text_out,
                parse_mode=ParseMode.HTML, reply_to_message_id=m.message_id,
            )
            return
        except Exception:
            pass
    await m.answer(text_out, parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════
# ║  ADMIN: EXTENDED COMMANDS                                  ║
# ══════════════════════════════════════════════════════════════

# ── Задать титул ──────────────────────────────────────────────

@dp.callback_query(F.data == "adm_set_title")
async def adm_set_title_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_set_title_id)
    await safe_edit(
        c.message,
        "📝 <b>Задать титул</b>\n\nВведи: <code>ID ТИТУЛ</code>\n"
        "Пример: <code>123456 🔥 Огненный</code>\n"
        "Для удаления: <code>ID -</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_set_title_id)
async def process_set_title(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await state.clear()
        return await m.answer("❌ Формат: ID ТИТУЛ")
    uid = parse_positive_int(parts[0])
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    title = "" if parts[1].strip() == "-" else parts[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (title, uid))
        await db.commit()
    await state.clear()
    res = f"📝 Титул <code>{uid}</code> → <b>{title}</b>" if title else f"📝 Титул <code>{uid}</code> убран"
    await m.answer(res, parse_mode=ParseMode.HTML)


# ── Сброс КД ─────────────────────────────────────────────────

@dp.callback_query(F.data == "adm_reset_cd")
async def adm_reset_cd_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_reset_cd_id)
    await safe_edit(c.message, "🔄 Введи ID игрока для полного сброса всех КД:")
    await c.answer()


@dp.message(AdminStates.waiting_for_reset_cd_id)
async def process_reset_cd(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_daily='', last_work='', last_gacha='', "
            "last_wheel='', last_rob='' WHERE user_id = ?", (uid,)
        )
        await db.commit()
    await state.clear()
    await m.answer(f"🔄 Все КД сброшены для <code>{uid}</code>.", parse_mode=ParseMode.HTML)


# ── Раздача всем ─────────────────────────────────────────────

@dp.callback_query(F.data == "adm_mass_give")
async def adm_mass_give_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_mass_give_data)
    await safe_edit(
        c.message,
        "🎁 <b>Раздача всем</b>\n\n"
        "Формат: <code>ТИП СУММА</code>\n"
        "• <code>coins 1000</code>\n"
        "• <code>bbc 5</code>\n"
        "• <code>xp 100</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_mass_give_data)
async def process_mass_give(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 2 or args[0] not in ("coins", "bbc", "xp"):
        await state.clear()
        return await m.answer("❌ Формат: coins/bbc/xp СУММА")
    val = parse_positive_int(args[1])
    if not val:
        await state.clear()
        return await m.answer("❌ Сумма — число > 0!")
    col_map = {"coins": "balance", "bbc": "bbc_balance", "xp": "xp"}
    col = col_map[args[0]]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {col} = {col} + ? WHERE is_banned = 0", (val,))
        cnt = (await (await db.execute("SELECT changes()")).fetchone())[0]
        await db.commit()
    await state.clear()
    await m.answer(f"🎁 Выдано +{val:,} {args[0]} всем ({cnt} игроков)!", parse_mode=ParseMode.HTML)


# ── Удалить карту из базы ─────────────────────────────────────

@dp.callback_query(F.data == "adm_del_card")
async def adm_del_card_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_del_card_id)
    await safe_edit(c.message, "🗑 Введи ID карты для удаления из базы:")
    await c.answer()


@dp.message(AdminStates.waiting_for_del_card_id)
async def process_del_card(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    cid = parse_positive_int(m.text)
    if not cid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM cards WHERE card_id = ?", (cid,))
        card = await cur.fetchone()
        if not card:
            await state.clear()
            return await m.answer("❌ Карта не найдена!")
        await db.execute("DELETE FROM cards WHERE card_id = ?", (cid,))
        await db.execute("DELETE FROM user_cards WHERE card_id = ?", (cid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🗑 Карта <b>{card[0]}</b> (#{cid}) удалена из базы и у всех игроков.", parse_mode=ParseMode.HTML)


# ── Переименовать карту ───────────────────────────────────────

@dp.callback_query(F.data == "adm_rename_card")
async def adm_rename_card_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_rename_card_data)
    await safe_edit(
        c.message,
        "✏️ <b>Переименовать карту</b>\n\n"
        "Формат: <code>ID НОВОЕ_ИМЯ</code>\n"
        "Пример: <code>5 Огненный Дракон</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_rename_card_data)
async def process_rename_card(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await state.clear()
        return await m.answer("❌ Формат: ID НОВОЕ_ИМЯ")
    cid = parse_positive_int(parts[0])
    if not cid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    name = parts[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM cards WHERE card_id = ?", (cid,))
        card = await cur.fetchone()
        if not card:
            await state.clear()
            return await m.answer("❌ Карта не найдена!")
        await db.execute("UPDATE cards SET name = ? WHERE card_id = ?", (name, cid))
        await db.commit()
    await state.clear()
    await m.answer(f"✏️ Карта #{cid}: <b>{card[0]}</b> → <b>{name}</b>", parse_mode=ParseMode.HTML)


# ── Дать карту игроку ─────────────────────────────────────────

@dp.callback_query(F.data == "adm_give_card")
async def adm_give_card_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_give_card_data)
    await safe_edit(
        c.message,
        "🎴 <b>Дать карту</b>\n\n"
        "Формат: <code>USER_ID CARD_ID</code>\n"
        "Пример: <code>123456 5</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_give_card_data)
async def process_give_card(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 2:
        await state.clear()
        return await m.answer("❌ Формат: USER_ID CARD_ID")
    uid = parse_positive_int(args[0])
    cid = parse_positive_int(args[1])
    if not uid or not cid:
        await state.clear()
        return await m.answer("❌ Оба — числа > 0!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM cards WHERE card_id = ?", (cid,))
        card = await cur.fetchone()
        if not card:
            await state.clear()
            return await m.answer("❌ Карта не найдена!")
        await db.execute("INSERT INTO user_cards (user_id, card_id) VALUES (?, ?)", (uid, cid))
        await db.commit()
    await state.clear()
    await m.answer(f"🎴 Карта <b>{card[0]}</b> (#{cid}) выдана игроку <code>{uid}</code>.", parse_mode=ParseMode.HTML)


# ── Забрать карту ─────────────────────────────────────────────

@dp.callback_query(F.data == "adm_take_card")
async def adm_take_card_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_take_card_data)
    await safe_edit(
        c.message,
        "🗑 <b>Забрать карту</b>\n\n"
        "Формат: <code>USER_ID CARD_ID</code>\n"
        "Удалит 1 экземпляр карты из инвентаря.",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_take_card_data)
async def process_take_card(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 2:
        await state.clear()
        return await m.answer("❌ Формат: USER_ID CARD_ID")
    uid = parse_positive_int(args[0])
    cid = parse_positive_int(args[1])
    if not uid or not cid:
        await state.clear()
        return await m.answer("❌ Оба — числа > 0!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM user_cards WHERE user_id = ? AND card_id = ? LIMIT 1",
            (uid, cid),
        )
        row = await cur.fetchone()
        if not row:
            await state.clear()
            return await m.answer("❌ У игрока нет этой карты!")
        await db.execute("DELETE FROM user_cards WHERE id = ?", (row[0],))
        await db.commit()
    await state.clear()
    await m.answer(f"🗑 Карта #{cid} забрана у <code>{uid}</code>.", parse_mode=ParseMode.HTML)


# ── Дать ачивку ───────────────────────────────────────────────

@dp.callback_query(F.data == "adm_give_ach")
async def adm_give_ach_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    ach_list = "\n".join(f"• <code>{k}</code> — {v[0]}" for k, v in ACHIEVEMENTS.items())
    await state.set_state(AdminStates.waiting_for_give_ach_data)
    await safe_edit(
        c.message,
        f"🏅 <b>Дать ачивку</b>\n\n"
        f"Формат: <code>USER_ID ACH_ID</code>\n\n"
        f"Доступные:\n{ach_list}",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_give_ach_data)
async def process_give_ach(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 2:
        await state.clear()
        return await m.answer("❌ Формат: USER_ID ACH_ID")
    uid = parse_positive_int(args[0])
    ach_id = args[1].strip()
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    if ach_id not in ACHIEVEMENTS:
        await state.clear()
        return await m.answer("❌ Ачивка не найдена!")
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO achievements (user_id, ach_id, achieved_at) VALUES (?, ?, ?)",
                (uid, ach_id, datetime.now().isoformat()),
            )
            await db.commit()
        except Exception:
            await state.clear()
            return await m.answer("❌ Ачивка уже есть!")
    await state.clear()
    name = ACHIEVEMENTS[ach_id][0]
    await m.answer(f"🏅 Ачивка <b>{name}</b> выдана <code>{uid}</code>.", parse_mode=ParseMode.HTML)


# ── Задать уровень ────────────────────────────────────────────

@dp.callback_query(F.data == "adm_set_level")
async def adm_set_level_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_set_level_data)
    await safe_edit(
        c.message,
        "⚡ <b>Задать уровень</b>\n\n"
        "Формат: <code>USER_ID УРОВЕНЬ</code>\n"
        "XP пересчитается автоматически.",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_set_level_data)
async def process_set_level(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 2:
        await state.clear()
        return await m.answer("❌ Формат: USER_ID УРОВЕНЬ")
    uid = parse_positive_int(args[0])
    lvl = parse_positive_int(args[1])
    if not uid or not lvl:
        await state.clear()
        return await m.answer("❌ Оба — числа > 0!")
    xp_needed = sum(100 * i for i in range(1, lvl))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET level = ?, xp = ? WHERE user_id = ?", (lvl, xp_needed, uid)
        )
        await db.commit()
    await state.clear()
    await m.answer(
        f"⚡ Игрок <code>{uid}</code>: уровень → {lvl} (XP: {xp_needed:,})",
        parse_mode=ParseMode.HTML,
    )


# ── Заморозка / Разморозка ────────────────────────────────────

@dp.callback_query(F.data == "adm_freeze")
async def adm_freeze_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_freeze_id)
    await safe_edit(c.message, "🥶 Введи ID игрока для заморозки (не сможет играть):")
    await c.answer()


@dp.message(AdminStates.waiting_for_freeze_id)
async def process_freeze(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_frozen = 1 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🥶 Игрок <code>{uid}</code> заморожен.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_unfreeze")
async def adm_unfreeze_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_unfreeze_id)
    await safe_edit(c.message, "☀️ Введи ID игрока для разморозки:")
    await c.answer()


@dp.message(AdminStates.waiting_for_unfreeze_id)
async def process_unfreeze(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_frozen = 0 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"☀️ Игрок <code>{uid}</code> разморожен.", parse_mode=ParseMode.HTML)


# ── Задать баланс ─────────────────────────────────────────────

@dp.callback_query(F.data == "adm_set_balance")
async def adm_set_balance_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_set_balance_data)
    await safe_edit(
        c.message,
        "💰 <b>Задать точный баланс</b>\n\n"
        "Формат: <code>USER_ID ТИП СУММА</code>\n"
        "Типы: coins, bbc\n"
        "Пример: <code>123456 coins 50000</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_set_balance_data)
async def process_set_balance(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) != 3 or args[1] not in ("coins", "bbc"):
        await state.clear()
        return await m.answer("❌ Формат: USER_ID coins/bbc СУММА")
    uid = parse_positive_int(args[0])
    val = parse_positive_int(args[2])
    if not uid or val is None:
        await state.clear()
        return await m.answer("❌ ID и сумма — числа > 0!")
    col = "balance" if args[1] == "coins" else "bbc_balance"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {col} = ? WHERE user_id = ?", (val, uid))
        await db.commit()
    await state.clear()
    await m.answer(
        f"💰 Баланс <code>{uid}</code>: {args[1]} = {val:,}",
        parse_mode=ParseMode.HTML,
    )


# ── Сменить ник ───────────────────────────────────────────────

@dp.callback_query(F.data == "adm_set_nickname")
async def adm_set_nickname_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_nickname_data)
    await safe_edit(
        c.message,
        "✏️ <b>Сменить ник</b>\n\n"
        "Формат: <code>USER_ID НОВЫЙ_НИК</code>",
    )
    await c.answer()


@dp.message(AdminStates.waiting_for_nickname_data)
async def process_set_nickname(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await state.clear()
        return await m.answer("❌ Формат: USER_ID НИК")
    uid = parse_positive_int(parts[0])
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — число!")
    nick = parts[1].strip()[:50]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET nickname = ? WHERE user_id = ?", (nick, uid))
        await db.commit()
    await state.clear()
    await m.answer(f"✏️ Ник <code>{uid}</code> → <b>{nick}</b>", parse_mode=ParseMode.HTML)


# ── Бэкап / Откат / Восстановление БД ────────────────────────

DB_BACKUP_DIR = "db_backups"

def _ensure_backup_dir():
    os.makedirs(DB_BACKUP_DIR, exist_ok=True)

def _create_auto_backup(tag: str = "auto") -> str:
    """Создаёт автоматический бэкап БД с меткой времени. Возвращает путь."""
    import shutil
    _ensure_backup_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(DB_BACKUP_DIR, f"{ts}_{tag}.db")
    shutil.copy2(DB_PATH, backup_path)
    # Храним макс 10 бэкапов, удаляем старые
    backups = sorted(
        [f for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".db")],
        reverse=True,
    )
    for old in backups[10:]:
        try:
            os.remove(os.path.join(DB_BACKUP_DIR, old))
        except OSError:
            pass
    return backup_path

def _get_latest_backup() -> str | None:
    """Возвращает путь к последнему бэкапу или None."""
    _ensure_backup_dir()
    backups = sorted(
        [f for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".db")],
        reverse=True,
    )
    return os.path.join(DB_BACKUP_DIR, backups[0]) if backups else None

@dp.callback_query(F.data == "adm_backup")
async def adm_backup_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    backup_path = _create_auto_backup("manual")
    try:
        await bot.send_document(
            c.from_user.id,
            types.FSInputFile(backup_path, filename="bot_database.db"),
            caption=(
                f"📦 Бэкап БД\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"💾 Сохранено бэкапов: {len(os.listdir(DB_BACKUP_DIR))}"
            ),
        )
        await c.answer("📦 Бэкап отправлен в ЛС!", show_alert=True)
    except Exception as e:
        await c.answer(f"❌ {e}", show_alert=True)


# ── 🔄 Откат БД ──────────────────────────────────────────────

@dp.callback_query(F.data == "adm_rollback")
async def adm_rollback_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    latest = _get_latest_backup()
    if not latest:
        await c.answer("❌ Нет бэкапов для отката!", show_alert=True)
        return
    backup_name = os.path.basename(latest)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, откатить!", callback_data="adm_rollback_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")],
    ])
    await c.message.edit_text(
        f"🔄 <b>Откат БД</b>\n\n"
        f"Последний бэкап: <code>{backup_name}</code>\n\n"
        f"⚠️ Текущая БД будет заменена на бэкап.\n"
        f"Перед откатом будет создана резервная копия текущей БД.\n\n"
        f"Вы уверены?",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )

@dp.callback_query(F.data == "adm_rollback_confirm")
async def adm_rollback_confirm_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    import shutil
    latest = _get_latest_backup()
    if not latest:
        await c.answer("❌ Нет бэкапов!", show_alert=True)
        return
    # Сохраняем текущую БД перед откатом
    _create_auto_backup("pre_rollback")
    # Заменяем БД
    shutil.copy2(latest, DB_PATH)
    await c.message.edit_text(
        f"✅ <b>БД успешно откачена!</b>\n\n"
        f"📁 Восстановлено из: <code>{os.path.basename(latest)}</code>\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"💡 Перед откатом была создана резервная копия.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="adm_back")],
        ]),
    )


# ── 📥 Восстановить БД (загрузка файла) ──────────────────────

@dp.callback_query(F.data == "adm_restore")
async def adm_restore_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_db_restore)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")],
    ])
    await c.message.edit_text(
        "📥 <b>Восстановление БД</b>\n\n"
        "Отправьте мне файл базы данных <code>.db</code>\n\n"
        "⚠️ Текущая БД будет заменена на загруженный файл.\n"
        "Перед заменой будет создана автоматическая резервная копия.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )

@dp.message(AdminStates.waiting_for_db_restore, F.document)
async def adm_restore_file_handler(m: types.Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    doc = m.document
    # Проверяем что это файл БД
    fname = doc.file_name or ""
    if not fname.endswith(".db"):
        await m.answer(
            "❌ Файл должен иметь расширение <code>.db</code>\n"
            "Отправьте корректный файл базы данных.",
            parse_mode=ParseMode.HTML,
        )
        return
    # Сохраняем текущую БД перед заменой
    _create_auto_backup("pre_restore")
    # Скачиваем новый файл
    tmp_path = DB_PATH + ".tmp_restore"
    try:
        await bot.download(doc, destination=tmp_path)
        # Проверяем что файл — валидная SQLite БД
        import sqlite3
        conn = sqlite3.connect(tmp_path)
        conn.execute("SELECT name FROM sqlite_master LIMIT 1")
        conn.close()
    except Exception as e:
        await m.answer(
            f"❌ Файл повреждён или не является базой данных SQLite!\n"
            f"Ошибка: <code>{e}</code>",
            parse_mode=ParseMode.HTML,
        )
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return
    # Заменяем БД
    import shutil
    shutil.move(tmp_path, DB_PATH)
    await state.clear()
    await m.answer(
        f"✅ <b>БД успешно восстановлена!</b>\n\n"
        f"📁 Загружен файл: <code>{fname}</code>\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"💾 Размер: {doc.file_size / 1024:.1f} КБ\n\n"
        f"💡 Резервная копия старой БД сохранена автоматически.",
        parse_mode=ParseMode.HTML,
    )

@dp.message(AdminStates.waiting_for_db_restore)
async def adm_restore_not_file(m: types.Message, state: FSMContext):
    """Если админ отправил не файл в режиме ожидания"""
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer(
        "📥 Жду файл <code>.db</code>!\n"
        "Отправьте документ с базой данных, или нажмите Отмена.",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════
# ║  v5.0 — КОНСТАНТЫ НОВЫХ СИСТЕМ                            ║
# ══════════════════════════════════════════════════════════════

FISH_CD = 600   # 10 мин

FISH_TABLE = [
    ("🐟 Карась",    "common",    0.40, 50,   10),
    ("🐠 Окунь",     "common",    0.30, 80,   15),
    ("🦈 Щука",      "uncommon",  0.15, 200,  30),
    ("🐡 Сом",       "rare",      0.08, 500,  50),
    ("🦑 Кальмар",   "epic",      0.05, 1500, 100),
    ("🐙 Осьминог",  "legendary", 0.02, 5000, 200),
]

QUEST_TYPES = [
    ("win_casino",   3,  500,   "🎰 Выиграй в казино {t} раз"),
    ("earn_coins",   500, 300,  "💰 Заработай {t} монет"),
    ("fish_catch",   3,  350,   "🎣 Поймай {t} рыбы"),
    ("win_duel",     1,  600,   "⚔️ Выиграй {t} дуэль"),
]




ELO_LEAGUES = [
    (0,    "🥉 Бронза"),
    (1200, "🥈 Серебро"),
    (1400, "🥇 Золото"),
    (1600, "💎 Платина"),
    (1800, "💠 Алмаз"),
    (2000, "🏅 Легенда"),
]

arena_queue: list = []  # [(user_id, bet, message)]


# ── Утилиты новых систем ──────────────────────────────────────

def elo_league(elo: int) -> str:
    league = ELO_LEAGUES[0][1]
    for threshold, name in ELO_LEAGUES:
        if elo >= threshold:
            league = name
    return league


async def ensure_arena(db, user_id: int):
    await db.execute(
        "INSERT OR IGNORE INTO arena_players (user_id) VALUES (?)", (user_id,)
    )


async def update_quest_progress(db, user_id: int, quest_type: str, amount: int = 1):
    """Update daily quest progress for a given type."""
    await _ensure_game_tables(db)
    today = datetime.now().strftime("%Y-%m-%d")
    cur = await db.execute(
        "SELECT q1_type,q1_target,q1_progress,q1_done, q2_type,q2_target,q2_progress,q2_done, q3_type,q3_target,q3_progress,q3_done "
        "FROM daily_quests WHERE user_id=? AND quest_date=?", (user_id, today)
    )
    row = await cur.fetchone()
    if not row:
        return
    updates = []
    for i, col_prefix in enumerate(["q1", "q2", "q3"]):
        qtype, qtarget, qprogress, qdone = row[i*4], row[i*4+1], row[i*4+2], row[i*4+3]
        if qtype == quest_type and not qdone:
            new_progress = min(qprogress + amount, qtarget)
            new_done = 1 if new_progress >= qtarget else 0
            updates.append((col_prefix, new_progress, new_done))
    for col_prefix, np, nd in updates:
        await db.execute(
            f"UPDATE daily_quests SET {col_prefix}_progress=?, {col_prefix}_done=? WHERE user_id=? AND quest_date=?",
            (np, nd, user_id, today)
        )
    await db.commit()



# ══════════════════════════════════════════════════════════════
# ║  v5.0 — ПИТОМЦЫ                                           ║
# ══════════════════════════════════════════════════════════════


@dp.message(Command("arena"))
async def cmd_arena(m: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await ensure_arena(db, m.from_user.id)
        await db.commit()
        cur = await db.execute("SELECT elo, wins, losses, league FROM arena_players WHERE user_id=?", (m.from_user.id,))
        row = await cur.fetchone()
    elo, wins, losses, league = row
    league = elo_league(elo)

    # Check if already in queue
    if any(uid == m.from_user.id for uid, _, _ in arena_queue):
        return await m.answer("⏳ Ты уже в очереди! Ожидай соперника...")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Найти соперника (100💰 ставка)", callback_data="arena_queue:100")],
        [InlineKeyboardButton(text="⚔️ Бой на 500💰", callback_data="arena_queue:500")],
        [InlineKeyboardButton(text="⚔️ Бой на 1000💰", callback_data="arena_queue:1000")],
        [InlineKeyboardButton(text="🏆 Топ арены", callback_data="arena_top")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await m.answer(
        f"⚔️ <b>Арена</b>\n\n"
        f"🏅 Лига: <b>{league}</b>\n"
        f"📊 ЭЛО: <b>{elo}</b>\n"
        f"✅ Победы: <b>{wins}</b> | ❌ Поражений: <b>{losses}</b>\n\n"
        f"Выбери ставку и найди соперника:",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("arena_queue:"))
async def cb_arena_queue(c: CallbackQuery):
    bet = int(c.data.split(":")[1])
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row or row[0] < bet:
            return await c.answer(f"❌ Нужно {bet:,} монет!", show_alert=True)

    # Check if already in queue
    if any(u == uid for u, _, _ in arena_queue):
        return await c.answer("⏳ Ты уже в очереди!")

    # Look for opponent
    opponent = None
    for i, (opp_uid, opp_bet, opp_msg) in enumerate(arena_queue):
        if opp_bet == bet and opp_uid != uid:
            opponent = (opp_uid, opp_msg)
            arena_queue.pop(i)
            break

    if opponent:
        opp_uid, opp_msg = opponent
        await _run_arena_battle(c, uid, opp_uid, bet)
    else:
        arena_queue.append((uid, bet, c.message))
        await c.message.edit_text(
            f"⏳ <b>Ищем соперника...</b>\n\nСтавка: {bet:,} 💰\nОчередь: {len(arena_queue)} чел.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="arena_cancel")]
            ]),
            parse_mode=ParseMode.HTML
        )
    await c.answer()


async def _run_arena_battle(c: CallbackQuery, uid1: int, uid2: int, bet: int):
    try:
        u1 = await bot.get_chat(uid1)
        u2 = await bot.get_chat(uid2)
    except Exception:
        return

    # Simple battle: random rolls with ELO influence
    async with aiosqlite.connect(DB_PATH) as db:
        cur1 = await db.execute("SELECT elo FROM arena_players WHERE user_id=?", (uid1,))
        cur2 = await db.execute("SELECT elo FROM arena_players WHERE user_id=?", (uid2,))
        r1 = await cur1.fetchone()
        r2 = await cur2.fetchone()
        elo1 = r1[0] if r1 else 1000
        elo2 = r2[0] if r2 else 1000

    # ELO-based win probability
    prob1 = 1 / (1 + 10 ** ((elo2 - elo1) / 400))
    winner_uid = uid1 if random.random() < prob1 else uid2
    loser_uid = uid2 if winner_uid == uid1 else uid1

    # ELO update
    k = 32
    if winner_uid == uid1:
        delta = int(k * (1 - prob1))
    else:
        delta = int(k * prob1)
    delta = max(10, delta)

    async with aiosqlite.connect(DB_PATH) as db:
        # Balance update
        await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid1))
        await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid2))
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bet * 2, winner_uid))
        # ELO update
        await db.execute("UPDATE arena_players SET elo=elo+?, wins=wins+1, league=? WHERE user_id=?",
                         (delta, elo_league(elo1 + delta if winner_uid == uid1 else elo1 - delta), winner_uid))
        await db.execute("UPDATE arena_players SET elo=MAX(0,elo-?), losses=losses+1 WHERE user_id=?",
                         (delta, loser_uid))
        await db.commit()

    winner_name = u1.first_name if winner_uid == uid1 else u2.first_name
    loser_name = u2.first_name if winner_uid == uid1 else u1.first_name

    result_text = (
        f"⚔️ <b>Бой на арене!</b>\n\n"
        f"🥊 {u1.first_name} vs {u2.first_name}\n"
        f"Ставка: {bet:,} 💰 каждый\n\n"
        f"🏆 Победитель: <b>{winner_name}</b>\n"
        f"💰 Выигрыш: <b>{bet * 2:,} монет</b>\n"
        f"📊 ЭЛО: ±{delta}"
    )
    try:
        await c.message.edit_text(result_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    try:
        await bot.send_message(loser_uid, result_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass


@dp.callback_query(F.data == "arena_cancel")
async def cb_arena_cancel(c: CallbackQuery):
    uid = c.from_user.id
    for i, (u, b, msg) in enumerate(arena_queue):
        if u == uid:
            arena_queue.pop(i)
            break
    await c.message.edit_text("❌ Ты вышел из очереди.")
    await c.answer()


@dp.callback_query(F.data == "arena_top")
async def cb_arena_top(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT a.user_id, a.elo, a.wins, u.nickname FROM arena_players a "
            "LEFT JOIN users u ON a.user_id=u.user_id "
            "ORDER BY a.elo DESC LIMIT 10"
        )
        rows = await cur.fetchall()
    text = "🏆 <b>Топ-10 Арены</b>\n\n"
    medals = ["🥇","🥈","🥉"] + ["🏅"]*7
    for i, (uid, elo, wins, nick) in enumerate(rows):
        name = nick or f"id{uid}"
        text += f"{medals[i]} {name} — ЭЛО: {elo} | ✅{wins}\n"
    await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")]
    ]), parse_mode=ParseMode.HTML)
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  v5.0 — РЫБАЛКА                                           ║
# ══════════════════════════════════════════════════════════════

# /fish command removed — use inline version via fish menu


@dp.callback_query(F.data == "fish_sell_all")
async def cb_fish_sell_all(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_game_tables(db)
        cur = await db.execute("SELECT fish_type, count FROM fish_inventory WHERE user_id=?", (c.from_user.id,))
        rows = await cur.fetchall()
        if not rows:
            return await c.answer("🐟 Нет рыбы для продажи!", show_alert=True)

        total = 0
        for fish_name, count in rows:
            for fish in FISH_TABLE:
                if fish[0] == fish_name:
                    total += fish[3] * count
                    break

        await db.execute("DELETE FROM fish_inventory WHERE user_id=?", (c.from_user.id,))
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (total, c.from_user.id))
        await update_quest_progress(db, c.from_user.id, "earn_coins", total)
        await db.commit()

    await c.message.edit_text(
        f"💰 <b>Улов продан!</b>\n\nПолучено: <b>{total:,} монет</b>",
        parse_mode=ParseMode.HTML
    )
    await c.answer()


@dp.callback_query(F.data == "fish_inventory")
async def cb_fish_inventory(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_game_tables(db)
        cur = await db.execute("SELECT fish_type, count FROM fish_inventory WHERE user_id=?", (c.from_user.id,))
        rows = await cur.fetchall()
    if not rows:
        return await c.answer("🐟 Нет рыбы в инвентаре!", show_alert=True)
    text = "🐟 <b>Инвентарь рыбы</b>\n\n"
    total_val = 0
    for fish_name, count in rows:
        sell = next((f[3] for f in FISH_TABLE if f[0] == fish_name), 0)
        total_val += sell * count
        text += f"{fish_name} x{count} (💰{sell * count:,})\n"
    text += f"\n💰 Итого: <b>{total_val:,} монет</b>"
    await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Продать всё", callback_data="fish_sell_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")],
    ]), parse_mode=ParseMode.HTML)
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  v5.0 — ЕЖЕДНЕВНЫЕ КВЕСТЫ                                 ║
# ══════════════════════════════════════════════════════════════

def random_quests() -> list:
    """Generate 3 random quests for today."""
    chosen = random.sample(QUEST_TYPES, 3)
    return [(q[0], q[1], q[3].format(t=q[1])) for q in chosen]


@dp.message(Command("quests"))
async def cmd_quests(m: Message):
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_game_tables(db)
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.from_user.id,))
        cur = await db.execute(
            "SELECT q1_type,q1_target,q1_progress,q1_done, q2_type,q2_target,q2_progress,q2_done, "
            "q3_type,q3_target,q3_progress,q3_done, all_done_claimed "
            "FROM daily_quests WHERE user_id=? AND quest_date=?",
            (m.from_user.id, today)
        )
        row = await cur.fetchone()
        if not row:
            quests = random_quests()
            await db.execute(
                "INSERT INTO daily_quests (user_id, quest_date, q1_type,q1_target, q2_type,q2_target, q3_type,q3_target) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (m.from_user.id, today, quests[0][0], quests[0][1], quests[1][0], quests[1][1], quests[2][0], quests[2][1])
            )
            await db.commit()
            cur = await db.execute(
                "SELECT q1_type,q1_target,q1_progress,q1_done, q2_type,q2_target,q2_progress,q2_done, "
                "q3_type,q3_target,q3_progress,q3_done, all_done_claimed "
                "FROM daily_quests WHERE user_id=? AND quest_date=?",
                (m.from_user.id, today)
            )
            row = await cur.fetchone()

    quest_reward_by_type = {q[0]: q[2] for q in QUEST_TYPES}
    quest_desc_by_type = {q[0]: q[3] for q in QUEST_TYPES}

    def quest_bar(prog, target):
        pct = min(prog, target)
        filled = int((pct / max(target, 1)) * 5)
        return "🟩" * filled + "⬛" * (5 - filled)

    text = f"📜 <b>Квесты на сегодня</b> ({today})\n\n"
    for i, col_prefix in enumerate([(0,1,2,3), (4,5,6,7), (8,9,10,11)]):
        qi = col_prefix
        qtype = row[qi[0]]
        qtarget = row[qi[1]]
        qprog = row[qi[2]]
        qdone = row[qi[3]]
        desc = quest_desc_by_type.get(qtype, qtype).format(t=qtarget)
        reward = quest_reward_by_type.get(qtype, 300)
        status = "✅" if qdone else quest_bar(qprog, qtarget)
        text += f"{'✅' if qdone else '📌'} <b>Квест {i+1}:</b> {desc}\n"
        text += f"   Прогресс: {qprog}/{qtarget} {status}\n"
        text += f"   Награда: {reward} 💰\n\n"

    all_done = row[3] >= 1 and row[7] >= 1 and row[11] >= 1
    all_claimed = row[12]
    if all_done and not all_claimed:
        text += "🎉 <b>Все квесты выполнены! Забери бонус!</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Забрать бонус (1000💰)", callback_data="quest_claim_all")],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
        ])
    elif all_claimed:
        text += "✅ Бонус за все квесты уже получен!"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")]
        ])
    else:
        # Claim individual done quests
        kb_rows = []
        for i, (done_idx, done_val, coin_val) in enumerate([
            (3, row[3], quest_reward_by_type.get(row[0], 300)),
            (7, row[7], quest_reward_by_type.get(row[4], 300)),
            (11, row[11], quest_reward_by_type.get(row[8], 300)),
        ]):
            if done_val == 1:
                kb_rows.append([InlineKeyboardButton(
                    text=f"🎁 Забрать квест {i+1} ({coin_val}💰)",
                    callback_data=f"quest_claim:{i+1}:{coin_val}"
                )])
        kb_rows.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    await m.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("quest_claim:"))
async def cb_quest_claim(c: CallbackQuery):
    parts = c.data.split(":")
    q_num = int(parts[1])
    reward = int(parts[2])
    today = datetime.now().strftime("%Y-%m-%d")
    col_map = {1: ("q1_done", "q1_claimed"), 2: ("q2_done", "q2_claimed"), 3: ("q3_done", "q3_claimed")}
    done_col = f"q{q_num}_done"
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_game_tables(db)
        cur = await db.execute(
            f"SELECT {done_col} FROM daily_quests WHERE user_id=? AND quest_date=?",
            (c.from_user.id, today)
        )
        row = await cur.fetchone()
        if not row or row[0] != 1:
            return await c.answer("❌ Квест не выполнен или уже забран!", show_alert=True)
        # Mark as 2 (claimed)
        await db.execute(
            f"UPDATE daily_quests SET {done_col}=2 WHERE user_id=? AND quest_date=?",
            (c.from_user.id, today)
        )
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (reward, c.from_user.id))
        await db.commit()
    await c.answer(f"✅ Получено {reward} монет!", show_alert=True)


@dp.callback_query(F.data == "quest_claim_all")
async def cb_quest_claim_all(c: CallbackQuery):
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_game_tables(db)
        cur = await db.execute(
            "SELECT all_done_claimed FROM daily_quests WHERE user_id=? AND quest_date=?",
            (c.from_user.id, today)
        )
        row = await cur.fetchone()
        if not row or row[0]:
            return await c.answer("❌ Бонус уже получен!", show_alert=True)
        await db.execute(
            "UPDATE daily_quests SET all_done_claimed=1 WHERE user_id=? AND quest_date=?",
            (c.from_user.id, today)
        )
        await db.execute("UPDATE users SET balance=balance+1000 WHERE user_id=?", (c.from_user.id,))
        await db.commit()
    await c.answer("🎉 Получено 1000 монет за все квесты!", show_alert=True)


# ══════════════════════════════════════════════════════════════
# ║  v5.0 — НОВЫЕ ИГРЫ: БЛЭКДЖЕК                              ║
# ══════════════════════════════════════════════════════════════

def new_deck() -> list:
    suits = ["♠", "♥", "♦", "♣"]
    values = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
    deck = [f"{v}{s}" for v in values for s in suits]
    random.shuffle(deck)
    return deck


def card_value(card: str) -> int:
    val = card[:-1]
    if val in ("J", "Q", "K"):
        return 10
    if val == "A":
        return 11
    return int(val)


def hand_total(hand: list) -> int:
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def format_hand(hand: list, hide_second: bool = False) -> str:
    if hide_second and len(hand) > 1:
        return f"{hand[0]} 🂠"
    return " ".join(hand)


# /blackjack command removed — use inline version via game menu
@dp.message(BlackjackStates.in_game)
async def process_blackjack_text(m: Message, state: FSMContext):
    """Handle stray text messages during blackjack — redirect to buttons."""
    await m.answer("Используй кнопки ниже!")


async def _show_blackjack(target, player_hand, dealer_hand, bet, state):
    ptotal = hand_total(player_hand)
    text = (
        f"🃏 <b>Блэкджек</b> | Ставка: {bet:,}💰\n\n"
        f"🤵 Дилер: {format_hand(dealer_hand, hide_second=True)} (<b>?</b>)\n"
        f"👤 Ты: {format_hand(player_hand)} (<b>{ptotal}</b>)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👊 Ещё карту", callback_data="bj_hit"),
         InlineKeyboardButton(text="✋ Стоп", callback_data="bj_stand")],
        [InlineKeyboardButton(text="💰 Удвоить", callback_data="bj_double")],
    ])
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            await target.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.in_({"bj_hit", "bj_stand", "bj_double"}))
async def cb_blackjack(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "bet" not in data:
        return await c.answer("❌ Нет активной игры!")
    bet = data["bet"]
    deck = data["deck"]
    player_hand = data["player_hand"]
    dealer_hand = data["dealer_hand"]
    uid = c.from_user.id
    action = c.data

    if action == "bj_hit":
        player_hand.append(deck.pop())
        ptotal = hand_total(player_hand)
        if ptotal > 21:
            # Bust — bet already deducted at start
            await state.clear()
            bj_end_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_blackjack"),
                 InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
            ])
            await c.message.edit_text(
                f"🃏 <b>Блэкджек</b>\n\n"
                f"👤 Твои карты: {format_hand(player_hand)} (<b>{ptotal}</b>)\n\n"
                f"💥 <b>Перебор! Ты проиграл {bet:,} 💰</b>",
                parse_mode=ParseMode.HTML, reply_markup=bj_end_kb
            )
            return await c.answer()
        await state.update_data(deck=deck, player_hand=player_hand)
        await _show_blackjack(c, player_hand, dealer_hand, bet, state)
        return await c.answer()

    if action == "bj_double":
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if not row or row[0] < bet:
                return await c.answer("❌ Недостаточно монет для удвоения!", show_alert=True)
            # Deduct additional bet for doubling (original bet already deducted at start)
            await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid))
            await db.commit()
        bet *= 2
        player_hand.append(deck.pop())
        ptotal_check = hand_total(player_hand)
        if ptotal_check > 21:
            # Bust on double — already fully deducted
            await state.clear()
            bj_end_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_blackjack"),
                 InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
            ])
            await c.message.edit_text(
                f"🃏 <b>Блэкджек</b> | Удвоение\n\n"
                f"👤 Твои карты: {format_hand(player_hand)} (<b>{ptotal_check}</b>)\n\n"
                f"💥 <b>Перебор при удвоении! -{bet:,} 💰</b>",
                parse_mode=ParseMode.HTML, reply_markup=bj_end_kb
            )
            return await c.answer()
        await state.update_data(bet=bet, deck=deck, player_hand=player_hand)
        action = "bj_stand"  # Fall through to stand logic

    if action == "bj_stand":
        # Dealer draws
        while hand_total(dealer_hand) < 17:
            dealer_hand.append(deck.pop())
        ptotal = hand_total(player_hand)
        dtotal = hand_total(dealer_hand)

        async with aiosqlite.connect(DB_PATH) as db:
            if ptotal <= 21 and (dtotal > 21 or ptotal > dtotal):
                # Player wins — return bet + profit (bet already deducted at start)
                await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bet * 2, uid))
                result = f"🎉 <b>Победа! +{bet:,} 💰</b>"
                await update_quest_progress(db, uid, "win_casino")
            elif ptotal == dtotal:
                # Draw — return bet
                await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bet, uid))
                result = "🤝 <b>Ничья! Ставка возвращена.</b>"
            else:
                # Player loses — bet already deducted at start
                result = f"💸 <b>Проигрыш! -{bet:,} 💰</b>"
            await db.commit()
        await state.clear()
        bj_end_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_blackjack"),
             InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        ])
        await c.message.edit_text(
            f"🃏 <b>Блэкджек</b>\n\n"
            f"🤵 Дилер: {format_hand(dealer_hand)} (<b>{dtotal}</b>)\n"
            f"👤 Ты: {format_hand(player_hand)} (<b>{ptotal}</b>)\n\n"
            f"{result}",
            parse_mode=ParseMode.HTML, reply_markup=bj_end_kb
        )
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  v5.0 — СЛОТЫ                                             ║
# ══════════════════════════════════════════════════════════════

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "⭐", "7️⃣"]
SLOT_WEIGHTS = [30, 25, 20, 15, 5, 4, 1]


def roll_slots() -> tuple[list, int, int]:
    reels = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    if reels[0] == reels[1] == reels[2]:
        sym = reels[0]
        if sym == "7️⃣":
            mult = 100
        elif sym == "💎":
            mult = 50
        elif sym == "⭐":
            mult = 20
        else:
            mult = 5
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        mult = 2
    else:
        mult = 0
    return reels, mult, 0


# /slots command removed — use inline version via game menu


# ══════════════════════════════════════════════════════════════
# ║  v5.0 — РУССКАЯ РУЛЕТКА                                   ║
# ══════════════════════════════════════════════════════════════

roulette_sessions: dict = {}  # chat_id -> {players, bet, status}


@dp.message(Command("roulette"))
async def cmd_roulette(m: Message):
    chat_id = m.chat.id
    uid = m.from_user.id
    parts = (m.text or "").split()
    bet = parse_positive_int(parts[1]) if len(parts) > 1 else 200

    if chat_id in roulette_sessions and roulette_sessions[chat_id]["status"] == "waiting":
        sess = roulette_sessions[chat_id]
        if any(p["uid"] == uid for p in sess["players"]):
            return await m.answer("⏳ Ты уже в игре!")
        if bet != sess["bet"]:
            return await m.answer(f"❌ Ставка в этой игре: {sess['bet']:,}💰")
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if not row or row[0] < bet:
                return await m.answer(f"❌ Нужно {bet:,} монет!")
            # Deduct bet immediately on join
            await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=? AND balance>=?", (bet, uid, bet))
            await db.commit()
        sess["players"].append({"uid": uid, "name": m.from_user.first_name})
        player_names = ", ".join(p["name"] for p in sess["players"])
        if len(sess["players"]) >= 2:
            # Start game
            await _resolve_roulette(m, chat_id)
        else:
            await m.answer(
                f"🔫 <b>Русская рулетка</b>\n\nИграки: {player_names}\nСтавка: {bet:,}💰\n\nЖдём ещё игроков...",
                parse_mode=ParseMode.HTML
            )
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if not row or row[0] < bet:
                return await m.answer(f"❌ Нужно {bet:,} монет!")
            # Deduct bet immediately on session creation
            await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=? AND balance>=?", (bet, uid, bet))
            await db.commit()
        roulette_sessions[chat_id] = {
            "players": [{"uid": uid, "name": m.from_user.first_name}],
            "bet": bet,
            "status": "waiting"
        }
        await m.answer(
            f"🔫 <b>Русская рулетка</b>\n\n"
            f"🎯 {m.from_user.first_name} открыл игру!\n"
            f"💰 Ставка: {bet:,} монет\n\n"
            f"Присоединись: <code>/roulette {bet}</code>",
            parse_mode=ParseMode.HTML
        )
        # Auto-cancel after 60s
        asyncio.create_task(_roulette_timeout(chat_id, 60))


async def _roulette_timeout(chat_id: int, seconds: int):
    await asyncio.sleep(seconds)
    if chat_id in roulette_sessions and roulette_sessions[chat_id]["status"] == "waiting":
        sess = roulette_sessions.pop(chat_id)
        # Refund bets to all players since game was cancelled
        bet = sess["bet"]
        async with aiosqlite.connect(DB_PATH) as db:
            for p in sess["players"]:
                await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bet, p["uid"]))
            await db.commit()
        try:
            await bot.send_message(chat_id, "🔫 Рулетка отменена — никто не присоединился. Ставки возвращены.")
        except Exception:
            pass


async def _resolve_roulette(m: Message, chat_id: int):
    sess = roulette_sessions.pop(chat_id, None)
    if not sess:
        return
    players = sess["players"]
    bet = sess["bet"]
    loser = random.choice(players)
    winners = [p for p in players if p["uid"] != loser["uid"]]
    prize = bet * len(players) // max(len(winners), 1)
    async with aiosqlite.connect(DB_PATH) as db:
        # Bets already deducted on join — just award prizes to winners
        for w in winners:
            await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (prize, w["uid"]))
        await db.commit()
    winner_names = ", ".join(p["name"] for p in winners)
    await m.answer(
        f"🔫 <b>Русская рулетка — Результат!</b>\n\n"
        f"💀 Проиграл: <b>{loser['name']}</b> (-{bet:,}💰)\n"
        f"🏆 Победители: <b>{winner_names}</b> (+{prize:,}💰 каждый)",
        parse_mode=ParseMode.HTML
    )


# ══════════════════════════════════════════════════════════════
# ║  v5.0 — КЛАНЫ                                             ║
# ══════════════════════════════════════════════════════════════


_game_tables_ensured = False

async def _ensure_game_tables(db):
    """Defensively create all game tables in case DB was created before they were added."""
    global _game_tables_ensured
    if _game_tables_ensured:
        return
    await db.execute("""CREATE TABLE IF NOT EXISTS craft_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_type TEXT,
        count INTEGER DEFAULT 1,
        UNIQUE(user_id, item_type)
    )""")
    await db.execute("""CREATE TABLE IF NOT EXISTS fish_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        fish_type TEXT,
        count INTEGER DEFAULT 1,
        UNIQUE(user_id, fish_type)
    )""")
    await db.execute("""CREATE TABLE IF NOT EXISTS daily_quests (
        user_id INTEGER,
        quest_date TEXT,
        q1_type TEXT, q1_target INTEGER, q1_progress INTEGER DEFAULT 0, q1_done INTEGER DEFAULT 0,
        q2_type TEXT, q2_target INTEGER, q2_progress INTEGER DEFAULT 0, q2_done INTEGER DEFAULT 0,
        q3_type TEXT, q3_target INTEGER, q3_progress INTEGER DEFAULT 0, q3_done INTEGER DEFAULT 0,
        all_done_claimed INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, quest_date)
    )""")
    # Ensure cards table has all columns (for old DBs)
    await db.execute("""CREATE TABLE IF NOT EXISTS cards (
        card_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        rarity INTEGER DEFAULT 1,
        image_id TEXT DEFAULT '',
        source_user_id INTEGER DEFAULT 0
    )""")
    for col, ctype, default in [("image_id", "TEXT", "''"), ("source_user_id", "INTEGER", "0")]:
        try:
            await db.execute(f"ALTER TABLE cards ADD COLUMN {col} {ctype} DEFAULT {default}")
        except Exception:
            pass
    await db.commit()
    _game_tables_ensured = True


@dp.callback_query(F.data == "menu_fish")
async def menu_fish_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_game_tables(db)
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        await db.execute(
            "INSERT OR IGNORE INTO craft_items (user_id, item_type, count) VALUES (?, '_last_fish', 0)",
            (uid,),
        )
        await db.commit()
        cur = await db.execute(
            "SELECT count FROM craft_items WHERE user_id=? AND item_type='_last_fish'",
            (uid,),
        )
        lf_row = await cur.fetchone()
        last_fish_ts = lf_row[0] if lf_row else 0
        now_ts = int(time.time())

        if now_ts - last_fish_ts < FISH_CD:
            remaining = FISH_CD - (now_ts - last_fish_ts)
            mins, secs = remaining // 60, remaining % 60
            await safe_edit(
                c.message,
                f"🎣 <b>Рыба не клюёт!</b>\n⏳ Подожди ещё <b>{mins}м {secs}с</b>",
                InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🐟 Инвентарь рыбы", callback_data="fish_inventory")],
                    [InlineKeyboardButton(text="💰 Продать улов", callback_data="fish_sell_all")],
                    [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
                ]),
            )
            return await c.answer()

        roll = random.random()
        cumulative = 0.0
        caught = FISH_TABLE[0]
        for fish in FISH_TABLE:
            cumulative += fish[2]
            if roll < cumulative:
                caught = fish
                break
        fish_name, rarity, _, sell_price, xp_reward = caught

        await db.execute(
            "INSERT INTO fish_inventory (user_id, fish_type, count) VALUES (?,?,1) "
            "ON CONFLICT(user_id, fish_type) DO UPDATE SET count=count+1",
            (uid, fish_name),
        )
        await db.execute(
            "UPDATE craft_items SET count=? WHERE user_id=? AND item_type='_last_fish'",
            (now_ts, uid),
        )
        lvl_msg = await grant_xp(db, uid, xp_reward)
        await update_quest_progress(db, uid, "fish_catch")
        await db.commit()

    rarity_emoji = {"common": "⬜", "uncommon": "🟩", "rare": "🟦", "epic": "🟪", "legendary": "🟨"}
    text = (
        f"🎣 <b>Поймал рыбу!</b>\n\n"
        f"{rarity_emoji.get(rarity, '⬜')} <b>{fish_name}</b>\n"
        f"💰 Цена продажи: {sell_price:,} монет\n"
        f"✨ XP: +{xp_reward}"
    )
    if lvl_msg:
        text += f"\n\n{lvl_msg}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎣 Ловить ещё", callback_data="menu_fish")],
        [InlineKeyboardButton(text="🐟 Инвентарь рыбы", callback_data="fish_inventory")],
        [InlineKeyboardButton(text="💰 Продать улов", callback_data="fish_sell_all")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "menu_quests")
async def menu_quests_cb(c: CallbackQuery):
    uid = c.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_game_tables(db)
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        cur = await db.execute(
            "SELECT q1_type,q1_target,q1_progress,q1_done, q2_type,q2_target,q2_progress,q2_done, "
            "q3_type,q3_target,q3_progress,q3_done, all_done_claimed "
            "FROM daily_quests WHERE user_id=? AND quest_date=?",
            (uid, today),
        )
        row = await cur.fetchone()
        if not row:
            quests = random_quests()
            await db.execute(
                "INSERT INTO daily_quests (user_id, quest_date, q1_type,q1_target, q2_type,q2_target, q3_type,q3_target) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (uid, today, quests[0][0], quests[0][1], quests[1][0], quests[1][1], quests[2][0], quests[2][1]),
            )
            await db.commit()
            cur = await db.execute(
                "SELECT q1_type,q1_target,q1_progress,q1_done, q2_type,q2_target,q2_progress,q2_done, "
                "q3_type,q3_target,q3_progress,q3_done, all_done_claimed "
                "FROM daily_quests WHERE user_id=? AND quest_date=?",
                (uid, today),
            )
            row = await cur.fetchone()

    quest_reward_by_type = {q[0]: q[2] for q in QUEST_TYPES}
    quest_desc_by_type = {q[0]: q[3] for q in QUEST_TYPES}

    def quest_bar(prog, target):
        pct = min(prog, target)
        filled = int((pct / max(target, 1)) * 5)
        return "🟩" * filled + "⬛" * (5 - filled)

    text = f"📜 <b>Квесты на сегодня</b> ({today})\n\n"
    for i, qi in enumerate([(0,1,2,3), (4,5,6,7), (8,9,10,11)]):
        qtype, qtarget, qprog, qdone = row[qi[0]], row[qi[1]], row[qi[2]], row[qi[3]]
        desc = quest_desc_by_type.get(qtype, qtype).format(t=qtarget)
        reward = quest_reward_by_type.get(qtype, 300)
        status = "✅" if qdone else quest_bar(qprog, qtarget)
        text += f"{'✅' if qdone else '📌'} <b>Квест {i+1}:</b> {desc}\n"
        text += f"   Прогресс: {qprog}/{qtarget} {status}\n"
        text += f"   Награда: {reward} 💰\n\n"

    all_done = row[3] >= 1 and row[7] >= 1 and row[11] >= 1
    all_claimed = row[12]
    if all_done and not all_claimed:
        text += "🎉 <b>Все квесты выполнены! Забери бонус!</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Забрать бонус (1000💰)", callback_data="quest_claim_all")],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
        ])
    elif all_claimed:
        text += "✅ Бонус за все квесты уже получен!"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
        ])
    else:
        kb_rows = []
        for i, (done_idx, qtype_idx) in enumerate([(3, 0), (7, 4), (11, 8)]):
            if row[done_idx]:
                reward = quest_reward_by_type.get(row[qtype_idx], 300)
                kb_rows.append([InlineKeyboardButton(
                    text=f"🎁 Забрать квест {i+1} ({reward}💰)",
                    callback_data=f"quest_claim:{i+1}",
                )])
        kb_rows.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "menu_cards")
async def menu_cards_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, c.rarity, COUNT(*) FROM user_cards uc "
            "JOIN cards c ON uc.card_id = c.card_id "
            "WHERE uc.user_id = ? GROUP BY c.card_id ORDER BY c.rarity DESC LIMIT 30",
            (uid,),
        )
        cards = await cur.fetchall()

    if not cards:
        text = "🃏 <b>Твоя коллекция</b>\n\n😕 У тебя пока нет карт.\nИспользуй 🎴 Гачу чтобы получить!"
    else:
        text = "🃏 <b>Твоя коллекция</b>\n\n"
        for name, rarity, cnt in cards:
            stars = RARITY_STARS.get(rarity, "⭐")
            text += f"{stars} <b>{name}</b> x{cnt}\n"
        if len(cards) >= 30:
            text += "\n<i>...показаны первые 30</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Все карты в игре", callback_data="menu_all_cards")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "menu_all_cards")
async def menu_all_cards_cb(c: CallbackQuery):
    """Показать все карты в игре (первая страница)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT card_id, name, rarity FROM cards ORDER BY rarity DESC, card_id")
        cards = await cur.fetchall()
    if not cards:
        await safe_edit(c.message, "🃏 База карт пуста.", back_menu_kb())
        return await c.answer()
    total = len(cards)
    per_page = CARDS_PER_PAGE if 'CARDS_PER_PAGE' in dir() else 15
    total_pages = (total + per_page - 1) // per_page
    page_cards = cards[:per_page]
    lines = [f"<code>#{c[0]}</code> {RARITY_STARS.get(c[2], '⭐')} <b>{c[1]}</b>" for c in page_cards]
    text = f"🃏 <b>ВСЕ КАРТЫ</b> (стр. 1/{total_pages}, всего: {total})\n\n" + "\n".join(lines)
    buttons = []
    if total_pages > 1:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data="cards_page_1"))
    buttons_row = [buttons] if buttons else []
    buttons_row.append([InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")])
    await safe_edit(c.message, text, InlineKeyboardMarkup(inline_keyboard=buttons_row))
    await c.answer()


@dp.callback_query(F.data == "menu_promo")
async def menu_promo_cb(c: CallbackQuery):
    text = (
        "🎟️ <b>Промокод</b>\n\n"
        "Чтобы активировать промокод, напиши:\n"
        "<code>/promo КОД</code>\n\n"
        "💡 <i>Промокоды раздаются в группе и каналах!</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "game_slots")
async def game_slots_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        balance = row[0]
    text = (
        f"🎰 <b>Слоты</b>\n\n"
        f"💰 Баланс: <b>{balance:,}</b>\n\n"
        f"Выбери ставку:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100", callback_data="slots_bet:100"),
         InlineKeyboardButton(text="500", callback_data="slots_bet:500")],
        [InlineKeyboardButton(text="1000", callback_data="slots_bet:1000"),
         InlineKeyboardButton(text="5000", callback_data="slots_bet:5000")],
        [InlineKeyboardButton(text="♾ Всё", callback_data="slots_bet:allin")],
        [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("slots_bet:"))
async def slots_bet_cb(c: CallbackQuery):
    uid = c.from_user.id
    bet_str = c.data.split(":")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        balance = row[0]
        if bet_str == "allin":
            bet = balance
        else:
            bet = int(bet_str)
        if bet < 10 or balance < bet:
            return await c.answer("❌ Недостаточно монет!", show_alert=True)

        reels, mult, _ = roll_slots()
        await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid))
        if mult > 0:
            winnings = bet * mult
            await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (winnings, uid))
            profit = winnings - bet
            if mult == 100:
                result = f"🌟🌟🌟 <b>ДЖЕКПОТ! +{profit:,} 💰</b> 🌟🌟🌟"
            else:
                result = f"🎉 <b>Выигрыш x{mult}! +{profit:,} 💰</b>"
            await update_quest_progress(db, uid, "win_casino")
        else:
            result = f"💸 <b>Проигрыш! -{bet:,} 💰</b>"
        await db.commit()
        cur2 = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        new_bal = (await cur2.fetchone())[0]

    reel_str = " │ ".join(reels)
    text = (
        f"🎰 <b>Слоты</b> | Ставка: {bet:,}💰\n\n"
        f"┌─────────────┐\n"
        f"│  {reel_str}  │\n"
        f"└─────────────┘\n\n"
        f"{result}\n"
        f"💰 Баланс: <b>{new_bal:,}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔄 Ещё ({bet:,})", callback_data=f"slots_bet:{bet_str}")],
        [InlineKeyboardButton(text="💰 Сменить ставку", callback_data="game_slots")],
        [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()



# ══════════════════════════════════════════════════════════════
# ║  v5.0 — НОВЫЕ КНОПКИ АДМИН-ПАНЕЛИ                        ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "adm_games")
async def adm_games_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    await safe_edit(c.message, "🎰 <b>Игры & Управление</b>", admin_games_kb())
    await c.answer()


@dp.callback_query(F.data == "adm_arena_panel")
async def adm_arena_panel_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS arena_players (
                user_id INTEGER PRIMARY KEY, elo INTEGER DEFAULT 1000, wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0, league TEXT DEFAULT 'Бронза')""")
        await db.commit()
        cur = await db.execute("SELECT COUNT(*) FROM arena_players")
        total = (await cur.fetchone())[0]
        cur2 = await db.execute("SELECT user_id, elo FROM arena_players ORDER BY elo DESC LIMIT 5")
        top = await cur2.fetchall()
    top_text = "\n".join(f"id{r[0]}: {r[1]} ЭЛО" for r in top) if top else "Пусто"
    await safe_edit(
        c.message,
        f"⚔️ <b>Арена</b>\n\nЗарегистрировано: <b>{total}</b>\n\nТоп-5:\n{top_text}",
        admin_arena_kb()
    )
    await c.answer()



@dp.callback_query(F.data == "adm_arena_reset")
async def adm_arena_reset_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM arena_players")
        await db.commit()
    await safe_edit(c.message, "⚔️ Арена сброшена!", admin_arena_kb())
    await c.answer()
@dp.message(AdminV5States.waiting_for_arena_reset)
async def process_arena_reset(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ Нужно число!")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE arena_players SET elo=1000, league='Бронза' WHERE user_id=?", (uid,)
        )
        await db.commit()
    await state.clear()
    await m.answer(f"✅ ЭЛО игрока {uid} сброшено до 1000.")



# ══════════════════════════════════════════════════════════════
# ║  📦 ВЫДАЧА — АДМИН ПАНЕЛЬ                                  ║
# ══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "adm_give_panel")
async def adm_give_panel_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    await safe_edit(
        c.message,
        "📦 <b>Выдача & Управление</b>\n\n"
        "Здесь собраны все функции выдачи,\n"
        "настройки баланса, уровней и ресурсов.",
        admin_give_kb()
    )
    await c.answer()






# ══════════════════════════════════════════════════════════════
# ║  💑 БРАКИ / ПАРЫ                                           ║
# ══════════════════════════════════════════════════════════════

@dp.message(Command("marry"))
async def marry_cmd(m: Message):
    """Предложить брак — ответом на сообщение."""
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.answer("💍 Ответь на сообщение человека, которому хочешь предложить брак!")
    target = m.reply_to_message.from_user
    if target.id == m.from_user.id:
        return await m.answer("❌ Нельзя жениться на себе!")
    if target.is_bot:
        return await m.answer("❌ Нельзя жениться на боте!")
    chat_id = m.chat.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        # Check both registered
        c1 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (m.from_user.id,))
        c2 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (target.id,))
        u1 = await c1.fetchone()
        u2 = await c2.fetchone()
        if not u1 or not u2:
            return await m.answer("❌ Оба должны быть зарегистрированы (/start)!")
        # Check not already married
        cur = await db.execute(
            "SELECT id FROM marriages WHERE "
            "(user1_id=? OR user2_id=? OR user1_id=? OR user2_id=?)",
            (m.from_user.id, m.from_user.id, target.id, target.id),
        )
        if await cur.fetchone():
            return await m.answer("❌ Один из вас уже в браке! Сначала /divorce")
    p1, p2 = m.from_user.id, target.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_acc_{p1}_{p2}")],
        [InlineKeyboardButton(text="💔 Отклонить", callback_data=f"marry_dec_{p1}_{p2}")],
    ])
    await m.answer(
        f"💍 <b>{u1[0]}</b> предлагает <b>{u2[0]}</b> вступить в брак!\n\n"
        f"Только вызванный может ответить.",
        parse_mode=ParseMode.HTML, reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("marry_acc_"))
async def marry_accept_cb(c: CallbackQuery):
    parts = c.data.split("_")
    p1, p2 = int(parts[2]), int(parts[3])
    if c.from_user.id != p2:
        return await c.answer("❌ Это не тебе!", show_alert=True)
    chat_id = c.message.chat.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        # Double check nobody married
        cur = await db.execute(
            "SELECT id FROM marriages WHERE "
            "(user1_id=? OR user2_id=? OR user1_id=? OR user2_id=?)",
            (p1, p1, p2, p2),
        )
        if await cur.fetchone():
            return await c.answer("❌ Кто-то из вас уже в браке!", show_alert=True)
        now_str = datetime.now().isoformat()
        pair = (min(p1, p2), max(p1, p2))
        await db.execute(
            "INSERT OR IGNORE INTO marriages (user1_id, user2_id, chat_id, married_at) VALUES (?,?,?,?)",
            (pair[0], pair[1], chat_id, now_str),
        )
        await db.commit()
        c1 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (p1,))
        c2 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (p2,))
        n1 = (await c1.fetchone() or ("???",))[0]
        n2 = (await c2.fetchone() or ("???",))[0]
    await safe_edit(
        c.message,
        f"💍💒 <b>{n1}</b> и <b>{n2}</b> теперь в браке! 💕\n\n"
        f"Совет да любовь! 🥂",
    )
    await c.answer("💍 Поздравляем!", show_alert=True)


@dp.callback_query(F.data.startswith("marry_dec_"))
async def marry_decline_cb(c: CallbackQuery):
    parts = c.data.split("_")
    p2 = int(parts[3])
    if c.from_user.id != p2:
        return await c.answer("❌ Это не тебе!", show_alert=True)
    await safe_edit(c.message, "💔 Предложение отклонено.", back_menu_kb())
    await c.answer()


@dp.message(Command("divorce"))
async def divorce_cmd(m: Message):
    """Развод — разрывает текущий брак."""
    uid = m.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT id, user1_id, user2_id FROM marriages WHERE user1_id=? OR user2_id=?",
            (uid, uid),
        )
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ Ты не в браке!")
        partner_id = row[2] if row[1] == uid else row[1]
        await db.execute("DELETE FROM marriages WHERE id=?", (row[0],))
        await db.commit()
        pc = await db.execute("SELECT nickname FROM users WHERE user_id=?", (partner_id,))
        prow = await pc.fetchone()
        partner_name = prow[0] if prow else "???"
        mc = await db.execute("SELECT nickname FROM users WHERE user_id=?", (uid,))
        mrow = await mc.fetchone()
        my_name = mrow[0] if mrow else "???"
    await m.answer(
        f"💔 <b>{my_name}</b> развёлся с <b>{partner_name}</b>.",
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "menu_pairs")
async def menu_pairs_cb(c: CallbackQuery):
    """Показать текущий брак пользователя."""
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT user1_id, user2_id, married_at FROM marriages WHERE user1_id=? OR user2_id=?",
            (uid, uid),
        )
        row = await cur.fetchone()
    if not row:
        text = (
            "💑 <b>Пары</b>\n\n"
            "Ты пока не в браке.\n"
            "Используй /marry (ответом на сообщение) чтобы предложить брак!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💑 Топ пар", callback_data="top_pairs")],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
        ])
        await safe_edit(c.message, text, kb)
        return await c.answer()

    partner_id = row[1] if row[0] == uid else row[0]
    married_at = row[2]
    async with aiosqlite.connect(DB_PATH) as db:
        pc = await db.execute("SELECT nickname FROM users WHERE user_id=?", (partner_id,))
        prow = await pc.fetchone()
        partner_name = prow[0] if prow else "???"
        mc = await db.execute("SELECT nickname FROM users WHERE user_id=?", (uid,))
        mrow = await mc.fetchone()
        my_name = mrow[0] if mrow else "???"

    try:
        dt = datetime.fromisoformat(married_at)
        delta = datetime.now() - dt
        days = delta.days
        hours = delta.seconds // 3600
        duration = f"{days} дн. {hours} ч."
    except Exception:
        duration = "неизвестно"

    text = (
        f"💑 <b>Твой брак</b>\n\n"
        f"💍 <b>{my_name}</b> ❤️ <b>{partner_name}</b>\n"
        f"📅 Вместе: <b>{duration}</b>\n\n"
        f"Чтобы развестись: /divorce"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💑 Топ пар", callback_data="top_pairs")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "top_pairs")
async def top_pairs_cb(c: CallbackQuery):
    """Топ пар по длительности брака."""
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT m.user1_id, m.user2_id, m.married_at, "
            "u1.nickname, u2.nickname "
            "FROM marriages m "
            "LEFT JOIN users u1 ON m.user1_id = u1.user_id "
            "LEFT JOIN users u2 ON m.user2_id = u2.user_id "
            "ORDER BY m.married_at ASC LIMIT 10"
        )
        rows = await cur.fetchall()

    if not rows:
        await safe_edit(c.message, "💑 <b>ТОП ПАР</b>\n\nПока нет ни одной пары!", back_menu_kb())
        return await c.answer()

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines_out = []
    for i, r in enumerate(rows):
        n1 = r[3] or "???"
        n2 = r[4] or "???"
        try:
            dt = datetime.fromisoformat(r[2])
            delta = datetime.now() - dt
            days = delta.days
            hours = delta.seconds // 3600
            duration = f"{days} дн. {hours} ч."
        except Exception:
            duration = "?"
        lines_out.append(f"{medals[i]} {n1} ❤️ {n2} — {duration}")

    text = "💑 <b>ТОП ПАР</b>\n\n" + "\n".join(lines_out)
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# ══════════════════════════════════════════════════════════════
# ║  💬 /me — ДЕЙСТВИЯ (Обнял, поцеловал и т.д.)              ║
# ══════════════════════════════════════════════════════════════

ME_ACTIONS = {
    "обнял": "обнял",
    "поцеловал": "поцеловал",
    "шлепнул": "шлепнул",
    "ударил": "ударил",
    "посмеялся": "посмеялся с",
    "принудил": "принудил к интиму",
    "трахнул": "трахнул",
}

ME_ACTIONS_EMOJI = {
    "обнял": "🤗",
    "поцеловал": "💋",
    "шлепнул": "👋",
    "ударил": "👊",
    "посмеялся": "😂",
    "принудил": "😈",
    "трахнул": "🔥",
}


async def _ensure_social_tables(db):
    """Ensure marriages and me_permissions tables exist."""
    await db.execute("""CREATE TABLE IF NOT EXISTS marriages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER, user2_id INTEGER,
        chat_id INTEGER, married_at TEXT DEFAULT '',
        UNIQUE(user1_id, user2_id))""")
    await db.execute("""CREATE TABLE IF NOT EXISTS me_permissions (
        user_id INTEGER PRIMARY KEY,
        granted_by INTEGER, granted_at TEXT DEFAULT '')""")


async def _has_me_permission(user_id: int) -> bool:
    """Check if user is admin or has /me permission."""
    if user_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute("SELECT user_id FROM me_permissions WHERE user_id=?", (user_id,))
        return bool(await cur.fetchone())


@dp.message(Command("me"))
async def me_cmd(m: Message):
    """
    /me <действие> — в ответ на сообщение.
    Доступно админу и пользователям с разрешением.
    Действия: обнял, поцеловал, шлепнул, ударил, посмеялся, принудил, трахнул
    """
    if not await _has_me_permission(m.from_user.id):
        return await m.answer("❌ У тебя нет разрешения на /me команды!")
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.answer(
            "💬 <b>Использование:</b> ответь на сообщение и напиши:\n"
            "<code>/me обнял</code>\n<code>/me поцеловал</code>\n"
            "<code>/me шлепнул</code>\n<code>/me ударил</code>\n"
            "<code>/me посмеялся</code>\n<code>/me принудил</code>\n"
            "<code>/me трахнул</code>",
            parse_mode=ParseMode.HTML,
        )
    target = m.reply_to_message.from_user
    if target.id == m.from_user.id:
        return await m.answer("❌ Нельзя применить к себе!")
    args = (m.text or "").split(maxsplit=1)
    if len(args) < 2:
        return await m.answer("❌ Укажи действие: /me <действие>")
    action_raw = args[1].strip().lower()
    # Find matching action
    matched_action = None
    for key in ME_ACTIONS:
        if action_raw.startswith(key):
            matched_action = key
            break
    if not matched_action:
        actions_list = ", ".join(ME_ACTIONS.keys())
        return await m.answer(f"❌ Неизвестное действие!\nДоступно: {actions_list}")

    async with aiosqlite.connect(DB_PATH) as db:
        c1 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (m.from_user.id,))
        c2 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (target.id,))
        n1 = (await c1.fetchone() or (m.from_user.full_name,))[0]
        n2 = (await c2.fetchone() or (target.full_name,))[0]

    # Clickable mentions — blue links to Telegram profiles
    link1 = f'<a href="tg://user?id={m.from_user.id}">{n1}</a>'
    link2 = f'<a href="tg://user?id={target.id}">{n2}</a>'

    action_text = ME_ACTIONS[matched_action]
    emoji = ME_ACTIONS_EMOJI.get(matched_action, "✨")

    if matched_action == "посмеялся":
        result = f"{emoji} {link1} посмеялся с {link2}"
    elif matched_action == "принудил":
        result = f"{emoji} {link1} принудил к интиму {link2}"
    elif matched_action == "ударил":
        result = f"{emoji} {link1} ударил {link2}"
    else:
        result = f"{emoji} {link1} {action_text} {link2}"

    await m.answer(result, parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════
# ║  💬 АДМИН: /me РАЗРЕШЕНИЯ                                 ║
# ══════════════════════════════════════════════════════════════

class AdminMeStates(StatesGroup):
    waiting_for_me_grant = State()
    waiting_for_me_revoke = State()


@dp.callback_query(F.data == "adm_me_perms")
async def adm_me_perms_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        await db.execute("""CREATE TABLE IF NOT EXISTS me_permissions (
            user_id INTEGER PRIMARY KEY, granted_by INTEGER, granted_at TEXT DEFAULT '')""")
        await db.commit()
        cur = await db.execute(
            "SELECT mp.user_id, u.nickname FROM me_permissions mp "
            "LEFT JOIN users u ON mp.user_id = u.user_id"
        )
        rows = await cur.fetchall()
    if rows:
        perm_list = "\n".join(f"  • {r[1] or '???'} (<code>{r[0]}</code>)" for r in rows)
    else:
        perm_list = "  Нет разрешений"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выдать разрешение", callback_data="adm_me_grant")],
        [InlineKeyboardButton(text="❌ Забрать разрешение", callback_data="adm_me_revoke")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")],
    ])
    await safe_edit(
        c.message,
        f"💬 <b>/me Разрешения</b>\n\n"
        f"Пользователи с доступом к /me:\n{perm_list}",
        kb,
    )
    await c.answer()


@dp.callback_query(F.data == "adm_me_grant")
async def adm_me_grant_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminMeStates.waiting_for_me_grant)
    await safe_edit(c.message, "✅ Введи ID пользователя для выдачи разрешения /me:")
    await c.answer()


@dp.message(AdminMeStates.waiting_for_me_grant)
async def process_me_grant(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT nickname FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row:
            await state.clear()
            return await m.answer("❌ Игрок не найден!")
        await db.execute(
            "INSERT OR REPLACE INTO me_permissions (user_id, granted_by, granted_at) VALUES (?,?,?)",
            (uid, ADMIN_ID, datetime.now().isoformat()),
        )
        await db.commit()
    await state.clear()
    await m.answer(
        f"✅ Разрешение /me выдано игроку <b>{row[0]}</b> (<code>{uid}</code>)",
        parse_mode=ParseMode.HTML,
    )


@dp.callback_query(F.data == "adm_me_revoke")
async def adm_me_revoke_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminMeStates.waiting_for_me_revoke)
    await safe_edit(c.message, "❌ Введи ID пользователя для отзыва разрешения /me:")
    await c.answer()


@dp.message(AdminMeStates.waiting_for_me_revoke)
async def process_me_revoke(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid = parse_positive_int(m.text)
    if not uid:
        await state.clear()
        return await m.answer("❌ ID — целое число!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM me_permissions WHERE user_id=?", (uid,))
        if not await cur.fetchone():
            await state.clear()
            return await m.answer("❌ У этого игрока нет разрешения /me!")
        await db.execute("DELETE FROM me_permissions WHERE user_id=?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"❌ Разрешение /me отозвано у <code>{uid}</code>", parse_mode=ParseMode.HTML)


async def health_server():
    """Minimal HTTP health-check server for platform probes."""
    from aiohttp import web

    async def handle(request):
        return web.Response(text="ok")

    app_http = web.Application()
    app_http.router.add_get("/", handle)
    app_http.router.add_get("/health", handle)
    runner = web.AppRunner(app_http)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log.info("Health server started on :8080")


async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot started!")
    await asyncio.gather(
        health_server(),
        dp.start_polling(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
