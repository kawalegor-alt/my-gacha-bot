#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#  GAME BOT v4.0  —  Полная игровая платформа (исправленная)
#  aiogram 3.x  +  aiosqlite  +  Telegram
# =============================================================================

import os
import shutil
import logging
import random
import asyncio
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram import types as aiogram_types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiohttp import web

# =============================================================================
#  Конфигурация
# =============================================================================
# ⚠️  ВСТАВЬ СВОЙ ТОКЕН ПЕРЕД ЗАПУСКОМ
TOKEN = os.environ.get("BOT_TOKEN", "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1548461377"))
DB_PATH = os.environ.get("DB_PATH", "game_bot.db")

# Кулдауны (в секундах)
GACHA_CD = 14400       # 4 часа
DAILY_CD = 86400       # 24 ч
ROB_CD = 7200          # 2 ч
ANTISPAM_CD = 1      # секунд между командами


# Пагинация
CARDS_PER_PAGE = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =============================================================================
#  Константы
# =============================================================================
RANK_NAMES = {
    0: "Нет ранга", 1: "🥉 Бронза", 2: "🥈 Серебро", 3: "🥇 Золото",
    4: "💎 Платина", 5: "💠 Алмаз", 6: "🏅 Мастер", 7: "🔱 Мифрил",
}
RARITY_STARS = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
RARITY_NAMES = {1: "Обычная", 2: "Необычная", 3: "Редкая", 4: "Эпическая", 5: "Легендарная"}
RARITY_QUOTES = {
    1: "Ну... ебать ты лох 😅",
    2: "Пойдет 🙂",
    3: "Не так плохо! 🔥",
    4: "ЭПИК!! Нормас! 🎉",
    5: "🌟 ЛЕГЕНДА!! НИХУЁВА!! 🌟",
}

SHOP_CATALOG = [
    # === Титулы ===
    {"id": "title_podsos", "name": "👑 Титул «Подсос»", "price": 5000, "type": "title", "title": "👑 Подсос"},
    {"id": "title_nonroot", "name": "😈 Титул «Нонрут»", "price": 7500, "type": "title", "title": "😈 Нонрут"},
    {"id": "title_legenda", "name": "🌟 Титул «Легенда»", "price": 15000, "type": "title", "title": "🌟 Легенда"},
    {"id": "title_meow", "name": "🔱 Титул «мяу»", "price": 25000, "type": "title", "title": "🔱 мяу"},
    {"id": "title_cickori", "name": "🏛️ Титул «Цикорий»", "price": 35000, "type": "title", "title": "🏛️ Цикорий"},
    {"id": "title_drochun", "name": "🌑 Титул «дрочун»", "price": 20000, "type": "title", "title": "🌑 дрочун"},
    {"id": "title_angel", "name": "😇 Титул «добри»", "price": 18000, "type": "title", "title": "😇 добри"},
    {"id": "title_furryeb", "name": "🐉 Титул «Фуриеб»", "price": 22000, "type": "title", "title": "🐉 Фуриеб"},
    {"id": "title_vorker", "name": "🥷 Титул «Вокер»", "price": 12000, "type": "title", "title": "🥷 Воркер"},
    {"id": "title_root", "name": "☠️ Титул «root»", "price": 10000, "type": "title", "title": "☠️ root"},
    {"id": "title_pidor", "name": "🐺 Титул «Пидорасик»", "price": 16000, "type": "title", "title": "🐺 Пидорасик"},
    {"id": "title_fire", "name": "🔥 Титул «Друн»", "price": 28000, "type": "title", "title": "🔥 Друн"},
    {"id": "title_pox", "name": "🗿 Титул «Похуист»", "price": 40000, "type": "title", "title": "🗿 Похуист"},
    {"id": "title_nebula", "name": "🌌 Титул «Звездочёт»", "price": 45000, "type": "title", "title": "🌌 Звездочёт"},
    # === VIP ===
    {"id": "vip_24h", "name": "⭐ VIP на 24 часа", "price": 10000, "type": "vip", "hours": 24},
    {"id": "vip_72h", "name": "💫 VIP на 72 часа", "price": 25000, "type": "vip", "hours": 72},
    {"id": "vip_168h", "name": "👑 VIP на неделю", "price": 50000, "type": "vip", "hours": 168},
    # === Множители ===
    {"id": "mult_x2", "name": "💰 Множитель x2 (24ч)", "price": 20000, "type": "multiplier", "mult": 2.0, "hours": 24},
    {"id": "mult_x3", "name": "💰 Множитель x3 (24ч)", "price": 45000, "type": "multiplier", "mult": 3.0, "hours": 24},
    {"id": "mult_x5", "name": "💰 Множитель x5 (12ч)", "price": 80000, "type": "multiplier", "mult": 5.0, "hours": 12},
    # === Ранги ===
    {"id": "rank_bronze", "name": "🥉 Ранг «Бронза» (1)", "price": 1000, "type": "rank", "rank": 1},
    {"id": "rank_silver", "name": "🥈 Ранг «Серебро» (2)", "price": 3000, "type": "rank", "rank": 2},
    {"id": "rank_gold", "name": "🥇 Ранг «Золото» (3)", "price": 8000, "type": "rank", "rank": 3},
    {"id": "rank_platinum", "name": "💎 Ранг «Платина» (4)", "price": 20000, "type": "rank", "rank": 4},
    {"id": "rank_elite", "name": "🎖 Ранг «Элита» (5)", "price": 50000, "type": "rank", "rank": 5},
    {"id": "rank_diamond", "name": "💠 Ранг «Алмаз» (6)", "price": 100000, "type": "rank", "rank": 6},
    {"id": "rank_mithril", "name": "🔱 Ранг «Мифрил» (7)", "price": 250000, "type": "rank", "rank": 7},
    # === BBC ===
    {"id": "bbc_1", "name": "💵 1 BBC", "price": 8000, "type": "bbc", "amount": 1},
    {"id": "bbc_pack", "name": "💵 5 BBC", "price": 30000, "type": "bbc", "amount": 5},
    {"id": "bbc_pack_x10", "name": "💵 10 BBC", "price": 55000, "type": "bbc", "amount": 10},
    {"id": "bbc_pack_x25", "name": "💵 25 BBC", "price": 120000, "type": "bbc", "amount": 25},
    # === Порталы Удачи ===
    {"id": "lucky_gacha_1", "name": "🌀 Портал Удачи x1", "price": 12000, "type": "lucky_gacha", "amount": 1},
    {"id": "lucky_gacha_3", "name": "🌀 Портал Удачи x3", "price": 32000, "type": "lucky_gacha", "amount": 3},
    {"id": "lucky_gacha_5", "name": "🌀 Портал Удачи x5", "price": 50000, "type": "lucky_gacha", "amount": 5},
    # === Сбросы КД ===
    {"id": "reset_gacha", "name": "🔄 Сброс КД гачи", "price": 3000, "type": "reset_cd", "cd_field": "last_gacha"},
    {"id": "reset_daily", "name": "🔄 Сброс КД ежедневки", "price": 8000, "type": "reset_cd", "cd_field": "last_daily"},
    {"id": "reset_rob", "name": "🔄 Сброс КД ограбления", "price": 4000, "type": "reset_cd", "cd_field": "last_rob"},
    {"id": "reset_all", "name": "🔄 Сброс ВСЕХ КД", "price": 20000, "type": "reset_all_cd"},
]

BBC_SHOP_CATALOG = [
    # === Порталы Удачи ===
    {"id": "bbc_lucky", "name": "🌀 Портал Удачи", "desc": "Гарантия 4+⭐ на гачу", "price": 12, "type": "lucky_gacha", "amount": 1},
    {"id": "bbc_lucky_x3", "name": "🌀 Портал Удачи x3", "desc": "Три портала", "price": 30, "type": "lucky_gacha", "amount": 3},
    {"id": "bbc_lucky_x5", "name": "🌀 Портал Удачи x5", "desc": "Пять порталов", "price": 50, "type": "lucky_gacha", "amount": 5},
    # === Конвертеры ===
    {"id": "bbc_convert", "name": "💎 Конвертер BBC→💰", "desc": "1 BBC = 3000 монет", "price": 3, "type": "convert", "coins_per": 3000},
    {"id": "bbc_convert_x5", "name": "💎 Конвертер BBC→💰 x5", "desc": "5 BBC = 15000 монет", "price": 5, "type": "convert", "coins_per": 3000},
    {"id": "bbc_convert_x10", "name": "💎 Конвертер BBC→💰 x10", "desc": "10 BBC = 30000 монет", "price": 10, "type": "convert", "coins_per": 3000},
    # === VIP ===
    {"id": "bbc_vip_24h", "name": "⭐ VIP на 24 часа", "desc": "VIP статус", "price": 8, "type": "vip", "hours": 24},
    {"id": "bbc_vip_72h", "name": "💫 VIP на 72 часа", "desc": "VIP статус", "price": 18, "type": "vip", "hours": 72},
    {"id": "bbc_vip_week", "name": "👑 VIP на неделю", "desc": "VIP статус", "price": 35, "type": "vip", "hours": 168},
    # === Множители ===
    {"id": "bbc_mult_x2", "name": "💰 Множитель x2 (24ч)", "desc": "Удвоение монет", "price": 15, "type": "multiplier", "mult": 2.0, "hours": 24},
    {"id": "bbc_mult_x3", "name": "💰 Множитель x3 (24ч)", "desc": "Утроение монет", "price": 30, "type": "multiplier", "mult": 3.0, "hours": 24},
    # === Ранги ===
    {"id": "bbc_rank_mithril", "name": "🔱 Ранг «Мифрил» (7)", "desc": "Высший ранг", "price": 50, "type": "rank", "rank": 7},
    {"id": "bbc_rank_diamond", "name": "💠 Ранг «Алмаз» (6)", "desc": "Высокий ранг", "price": 35, "type": "rank", "rank": 6},
]

ACHIEVEMENTS = {
    # === Казино ===
    "first_win": ("🏆 Первая победа", "Выиграй в казино"),
    "casino_10": ("🎰 Любитель казино", "Выиграй в казино 10 раз"),
    "casino_50": ("🎰 Азартный", "Выиграй в казино 50 раз"),
    "casino_100": ("🎰 Король казино", "Выиграй в казино 100 раз"),
    "jackpot_slots": ("🌟 Джекпотер", "Выйграй джекпот в слотах (x100)"),
    "crash_x5": ("📈 Краш-мастер", "Забери выигрыш x5+ в краше"),
    "crash_x10": ("📈 Краш-легенда", "Забери выигрыш x10+ в краше"),
    # === Богатство ===
    "rich_10k": ("💰 Богач", "Накопи 10 000 монет"),
    "rich_100k": ("💎 Миллионер", "Накопи 100 000 монет"),
    "rich_1m": ("👑 Мультимиллионер", "Накопи 1 000 000 монет"),
    "rich_10m": ("🌌 Олигарх", "Накопи 10 000 000 монет"),
    "bbc_10": ("💵 BBC Барон", "Накопи 10 BBC"),
    "bbc_50": ("💵 BBC Магнат", "Накопи 50 BBC"),
    "bbc_100": ("💵 BBC Император", "Накопи 100 BBC"),
    # === Карты ===
    "collector_10": ("🃏 Коллекционер", "Собери 10 карт"),
    "collector_50": ("📚 Библиотекарь", "Собери 50 карт"),
    "collector_100": ("📚 Картовед", "Собери 100 карт"),
    "collector_500": ("📚 Энциклопедист", "Собери 500 карт"),
    "legendary_card": ("🌟 Легенда в коллекции", "Получи легендарную карту (5⭐)"),
    "epic_card": ("🟣 Эпический находчик", "Получи эпическую карту (4⭐)"),
    # === Уровни ===
    "level_10": ("📊 Десятка", "Достигни 10 уровня"),
    "level_25": ("🌟 Четвертак", "Достигни 25 уровня"),
    "level_50": ("👑 Пятидесятник", "Достигни 50 уровня"),
    "level_100": ("🔥 Бессмертный", "Достигни 100 уровня"),
    # === Ограбления ===
    "rob_master": ("🦹 Грабитель", "Успешно ограбь 10 раз"),
    "rob_50": ("🦹 Вор", "Успешно ограбь 50 раз"),
    "rob_100": ("🦹 Криминальный авторитет", "Успешно ограбь 100 раз"),
    # === Браки ===
    "married": ("💍 Жених/Невеста", "Вступи в брак"),
    # === Ежедневка ===
    "daily_7": ("📅 Неделька", "7 дней ежедневки подряд"),
    "daily_30": ("📅 Месяц", "30 дней ежедневки подряд"),
    # === Промокоды ===
    "promo_used": ("🎟️ Промо-охотник", "Используй промокод"),
}

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "⭐", "7️⃣"]
SLOT_WEIGHTS = [30, 25, 20, 15, 5, 4, 1]


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

CRASH_STEPS = [
    1.1, 1.2, 1.3, 1.5, 1.7, 2.0, 2.3, 2.6, 3.0, 3.5,
    4.0, 5.0, 6.0, 7.5, 10.0,
]

# =============================================================================
#  Глобальное состояние
# =============================================================================
rig_mode = "normal"
rig_remaining = 0
antispam: dict = {}
_msg_owners: dict[str, int] = {}
_crash_games: dict[int, dict] = {}
_crash_last_click: dict[int, float] = {}
_game_tables_ensured = False

# =============================================================================
#  FSM состояния
# =============================================================================
class ShopStates(StatesGroup):
    waiting_for_quantity = State()

class BbcShopStates(StatesGroup):
    waiting_for_quantity = State()

class GameStates(StatesGroup):
    waiting_for_bet = State()

class BlackjackStates(StatesGroup):
    in_game = State()

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
    waiting_for_reset_cd_id = State()
    waiting_for_set_level_data = State()
    waiting_for_freeze_id = State()
    waiting_for_unfreeze_id = State()
    waiting_for_set_balance_data = State()
    waiting_for_nickname_data = State()
    waiting_for_db_restore = State()


class AdminMeStates(StatesGroup):
    waiting_for_me_grant = State()
    waiting_for_me_revoke = State()


# =============================================================================
#  MIDDLEWARE
# =============================================================================
class BanCheckMiddleware(BaseMiddleware):
    """Полностью игнорирует забаненных пользователей."""
    _ban_cache: dict[int, float] = {}
    _CACHE_TTL = 30

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)
        uid = user.id
        now = time.time()
        cached_ts = self._ban_cache.get(uid)
        if cached_ts and (now - cached_ts) < self._CACHE_TTL:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("🚫 Вы забанены.", show_alert=True)
                except Exception:
                    pass
            return
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT is_banned FROM users WHERE user_id = ?", (uid,))
                row = await cur.fetchone()
        except Exception:
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
            return
        self._ban_cache.pop(uid, None)
        return await handler(event, data)


class AntiSpamMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and user.id != ADMIN_ID and not await is_limited_admin(user.id):
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



_username_seen: set = set()

class UsernameUpdateMiddleware(BaseMiddleware):
    """Saves Telegram username to DB (once per session per user)."""
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and user.username and user.id not in _username_seen:
            _username_seen.add(user.id)
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE users SET username = ? WHERE user_id = ?",
                        (user.username.lower(), user.id)
                    )
                    await db.commit()
            except Exception:
                pass
        return await handler(event, data)

class OwnerCallbackMiddleware(BaseMiddleware):
    """Only the user who triggered the message can tap its inline buttons."""
    PUBLIC_PREFIXES = ("marry_acc_", "marry_dec_")

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
dp.message.outer_middleware(UsernameUpdateMiddleware())

# =============================================================================
#  ERROR HANDLER
# =============================================================================
@dp.errors()
async def errors_handler(event):
    exc = event.exception
    if isinstance(exc, TelegramBadRequest):
        msg = str(exc)
        if "query is too old" in msg or "message is not modified" in msg:
            return True
    log.exception("Unhandled: %s", exc)
    return True

# =============================================================================
#  DATABASE
# =============================================================================
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
            last_gacha TEXT DEFAULT '',
            is_frozen INTEGER DEFAULT 0,
            username TEXT DEFAULT ''
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
        await db.execute("""CREATE TABLE IF NOT EXISTS craft_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_type TEXT,
            count INTEGER DEFAULT 1,
            UNIQUE(user_id, item_type)
        )""")
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
        # === Таблица ограниченных админов ===
        await db.execute("""CREATE TABLE IF NOT EXISTS limited_admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at TEXT DEFAULT '',
            is_full INTEGER DEFAULT 0
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
        "last_gacha": "TEXT DEFAULT ''",
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
    # Миграция limited_admins: добавить is_full если нет
    cur3 = await db.execute("PRAGMA table_info(limited_admins)")
    la_cols = {r[1] for r in await cur3.fetchall()}
    if "is_full" not in la_cols:
        await db.execute("ALTER TABLE limited_admins ADD COLUMN is_full INTEGER DEFAULT 0")
        log.info("Migrated limited_admins.is_full")
    await db.commit()


async def _ensure_game_tables(db):
    """Defensively create all game tables in case DB was created before they were added."""
    global _game_tables_ensured
    if _game_tables_ensured:
        return
    await db.execute("""CREATE TABLE IF NOT EXISTS craft_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_type TEXT,
        count INTEGER DEFAULT 1, UNIQUE(user_id, item_type))""")
    await db.execute("""CREATE TABLE IF NOT EXISTS cards (
        card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
        rarity INTEGER DEFAULT 1, image_id TEXT DEFAULT '', source_user_id INTEGER DEFAULT 0)""")
    await db.execute("""CREATE TABLE IF NOT EXISTS marriages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user1_id INTEGER, user2_id INTEGER,
        chat_id INTEGER, married_at TEXT DEFAULT '', UNIQUE(user1_id, user2_id))""")
    await db.execute("""CREATE TABLE IF NOT EXISTS me_permissions (
        user_id INTEGER PRIMARY KEY, granted_by INTEGER, granted_at TEXT DEFAULT '')""")
    await db.execute("""CREATE TABLE IF NOT EXISTS limited_admins (
        user_id INTEGER PRIMARY KEY, added_by INTEGER, added_at TEXT DEFAULT '', is_full INTEGER DEFAULT 0)""")
    # username column migration
    try:
        await db.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT ''")
        await db.commit()
    except Exception:
        pass
    for col, ctype, default in [("image_id", "TEXT", "''"), ("source_user_id", "INTEGER", "0")]:
        try:
            await db.execute(f"ALTER TABLE cards ADD COLUMN {col} {ctype} DEFAULT {default}")
        except Exception:
            pass
    await db.commit()
    _game_tables_ensured = True


async def _ensure_social_tables(db):
    """Ensure marriages and me_permissions tables exist."""
    await db.execute("""CREATE TABLE IF NOT EXISTS marriages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user1_id INTEGER, user2_id INTEGER,
        chat_id INTEGER, married_at TEXT DEFAULT '', UNIQUE(user1_id, user2_id))""")
    await db.execute("""CREATE TABLE IF NOT EXISTS me_permissions (
        user_id INTEGER PRIMARY KEY, granted_by INTEGER, granted_at TEXT DEFAULT '')""")
    await db.execute("""CREATE TABLE IF NOT EXISTS limited_admins (
        user_id INTEGER PRIMARY KEY, added_by INTEGER, added_at TEXT DEFAULT '', is_full INTEGER DEFAULT 0)""")

# =============================================================================
#  HELPER functions
# =============================================================================


async def resolve_user(m: Message) -> tuple:
    """
    Resolve target user from:
      1. Reply to message (from_user of replied msg)
      2. @username entity (text_mention or mention)
      3. Plain @username text
      4. Numeric user ID

    Returns (user_id: int | None, display_name: str, remaining_text: str).
    On failure: (None, error_message, "").
    """
    text = (m.text or "").strip()

    # 1. Reply
    if m.reply_to_message and m.reply_to_message.from_user:
        ru = m.reply_to_message.from_user
        return ru.id, ru.full_name, text

    # 2. Entities
    if m.entities:
        for ent in m.entities:
            if ent.type == "text_mention" and ent.user:
                rest = text[ent.offset + ent.length:].strip()
                return ent.user.id, ent.user.full_name, rest
            if ent.type == "mention":
                uname = text[ent.offset + 1: ent.offset + ent.length]
                rest = text[ent.offset + ent.length:].strip()
                async with aiosqlite.connect(DB_PATH) as db:
                    cur = await db.execute(
                        "SELECT user_id, nickname FROM users WHERE LOWER(username) = LOWER(?)", (uname,))
                    row = await cur.fetchone()
                if row:
                    return row[0], row[1] or f"@{uname}", rest
                return None, f"❌ Игрок @{uname} не найден в базе!", ""

    # 3. Plain @username
    if text.startswith("@"):
        parts = text.split(maxsplit=1)
        uname = parts[0].lstrip("@")
        rest = parts[1] if len(parts) > 1 else ""
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT user_id, nickname FROM users WHERE LOWER(username) = LOWER(?)", (uname,))
            row = await cur.fetchone()
        if row:
            return row[0], row[1] or f"@{uname}", rest
        return None, f"❌ Игрок @{uname} не найден в базе!", ""

    # 4. Numeric ID
    parts = text.split(maxsplit=1)
    if parts:
        uid = parse_positive_int(parts[0])
        if uid:
            rest = parts[1] if len(parts) > 1 else ""
            return uid, str(uid), rest

    return None, "❌ Укажи пользователя: ответь на сообщение, @юзернейм или ID", ""

async def is_limited_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь ограниченным админом."""
    if user_id == ADMIN_ID:
        return False  # Полный админ — не ограниченный
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute("SELECT user_id FROM limited_admins WHERE user_id = ?", (user_id,))
        return bool(await cur.fetchone())


async def is_full_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь полноценным ограниченным админом (is_full=1)."""
    if user_id == ADMIN_ID:
        return False  # Главный админ — не ограниченный
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT user_id FROM limited_admins WHERE user_id = ? AND is_full = 1", (user_id,)
        )
        return bool(await cur.fetchone())


async def is_any_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь любым админом (полным или ограниченным)."""
    return user_id == ADMIN_ID or await is_limited_admin(user_id)


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


def _track_msg(chat_id: int, msg_id: int, user_id: int):
    _msg_owners[f"{chat_id}:{msg_id}"] = user_id
    if len(_msg_owners) > 10_000:
        for k in list(_msg_owners)[:5000]:
            del _msg_owners[k]


async def try_achievement(db, user_id: int, ach_id: str):
    try:
        await db.execute(
            "INSERT OR IGNORE INTO achievements (user_id, ach_id, achieved_at) VALUES (?, ?, ?)",
            (user_id, ach_id, datetime.now().isoformat()),
        )
    except Exception:
        pass


async def grant_xp(db, user_id: int, amount: int) -> Optional[str]:
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
    if lvl >= 10:
        await try_achievement(db, user_id, "level_10")
    if lvl >= 25:
        await try_achievement(db, user_id, "level_25")
    return msg


async def check_wealth_achievements(db, user_id: int, balance: int):
    if balance >= 10000:
        await try_achievement(db, user_id, "rich_10k")
    if balance >= 100000:
        await try_achievement(db, user_id, "rich_100k")
    if balance >= 1000000:
        await try_achievement(db, user_id, "rich_1m")
    if balance >= 10000000:
        await try_achievement(db, user_id, "rich_10m")
    # Check BBC achievements
    cur = await db.execute("SELECT bbc_balance FROM users WHERE user_id = ?", (user_id,))
    bbc_row = await cur.fetchone()
    if bbc_row:
        bbc = bbc_row[0]
        if bbc >= 10:
            await try_achievement(db, user_id, "bbc_10")
        if bbc >= 50:
            await try_achievement(db, user_id, "bbc_50")
        if bbc >= 100:
            await try_achievement(db, user_id, "bbc_100")


async def check_collection_achievements(db, user_id: int):
    cur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,))
    cnt = (await cur.fetchone())[0]
    if cnt >= 10:
        await try_achievement(db, user_id, "collector_10")
    if cnt >= 50:
        await try_achievement(db, user_id, "collector_50")
    if cnt >= 100:
        await try_achievement(db, user_id, "collector_100")
    if cnt >= 500:
        await try_achievement(db, user_id, "collector_500")
    # Check for legendary/epic cards
    cur2 = await db.execute(
        "SELECT MAX(c.rarity) FROM user_cards uc JOIN cards c ON uc.card_id = c.card_id WHERE uc.user_id = ?", (user_id,))
    max_rarity = (await cur2.fetchone())[0] or 0
    if max_rarity >= 4:
        await try_achievement(db, user_id, "epic_card")
    if max_rarity >= 5:
        await try_achievement(db, user_id, "legendary_card")


# =============================================================================
#  START & MAIN MENU
# =============================================================================
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"),
         InlineKeyboardButton(text="🛒 Магазин", callback_data="menu_shop")],
        [InlineKeyboardButton(text="💎 BBC Магазин", callback_data="menu_bbcshop"),
         InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton(text="🏆 Топы", callback_data="menu_tops"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv")],
        [InlineKeyboardButton(text="📊 Уровень", callback_data="menu_level")],
        [InlineKeyboardButton(text="🏅 Достижения", callback_data="menu_achs"),
         InlineKeyboardButton(text="💰 Ежедневка", callback_data="menu_daily")],
        [InlineKeyboardButton(text="💑 Пары", callback_data="menu_pairs")],
        [InlineKeyboardButton(text="🃏 Карты", callback_data="menu_cards")],
        [InlineKeyboardButton(text="🎟️ Промокод", callback_data="menu_promo")],
    ])


@dp.message(CommandStart())
async def start_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (m.from_user.id,))
        if not await cur.fetchone():
            nick = m.from_user.full_name or f"User{m.from_user.id}"
            await db.execute("INSERT INTO users (user_id, nickname) VALUES (?, ?)", (m.from_user.id, nick))
            await db.commit()
    sent = await m.answer(
        "🎮 <b>Добро пожаловать в Тето пасито:3</b>\n\nВыбери действие:",
        reply_markup=main_menu_kb(), parse_mode=ParseMode.HTML)
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


# =============================================================================
#  PROFILE
# =============================================================================
@dp.callback_query(F.data == "menu_profile")
async def profile_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance, bbc_balance, rank, title, vip_until, "
            "coin_multiplier, xp, level, "
            "daily_streak, shield FROM users WHERE user_id = ?", (uid,))
        u = await cur.fetchone()
        if not u:
            return await c.answer("❌ /start сначала", show_alert=True)
        nick, bal, bbc, rank, title, vip, mult, xp, lvl, streak, shield = u
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
        f"🔥 Дневной стрик: {streak}\n"
        f"{'🛡️ Щит активен!' if shield else ''}\n"
        f"💰 Множитель: x{mult}{vip_str}")
    text = "\n".join(line for line in text.split("\n") if line.strip())
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


@dp.message(Command("profile"))
async def profile_cmd(m: Message):
    uid = m.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance, bbc_balance, rank, title, xp, level "
            "FROM users WHERE user_id = ?", (uid,))
        u = await cur.fetchone()
        if not u:
            return await m.answer("❌ /start сначала")
    xp_need = xp_for_level(u[6])
    await m.answer(
        f"👤 <b>{u[0]}</b>\n💰 {u[1]:,} | 💵 {u[2]} BBC\n"
        f"📊 Ур.{u[6]}\n✨ {u[5]}/{xp_need} XP",
        parse_mode=ParseMode.HTML)


# =============================================================================
#  GACHA
# =============================================================================
async def do_gacha(db, user_id: int, count: int, lucky: bool = False):
    cur = await db.execute(
        "SELECT card_id, name, rarity, image_id FROM cards "
        "WHERE image_id IS NOT NULL AND TRIM(image_id) != '' "
        "AND TRIM(image_id) NOT IN ('None', 'null', '0')")
    all_cards = await cur.fetchall()
    if not all_cards:
        return [], "админ не добавил карты. @gde_DiadSoul работай сука!!!"
    results = []
    for _ in range(count):
        if lucky:
            pool = [c for c in all_cards if c[2] >= 4] or all_cards
            card = random.choice(pool)
        else:
            weights = [max(1, 6 - c[2]) for c in all_cards]
            pool = random.choices(all_cards, weights=weights, k=1)
            card = pool[0]
        await db.execute("INSERT INTO user_cards (user_id, card_id) VALUES (?, ?)", (user_id, card[0]))
        results.append(card)
    return results, None


# =============================================================================
#  DAILY
# =============================================================================
@dp.callback_query(F.data == "menu_daily")
async def daily_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT last_daily, coin_multiplier, daily_streak, last_streak_date FROM users WHERE user_id = ?", (uid,))
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
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last_streak == yesterday:
            streak += 1
        elif last_streak != today:
            streak = 1
        streak_bonus = min(streak * 50, 500)
        total = int(base * mult) + streak_bonus
        await db.execute(
            "UPDATE users SET balance = balance + ?, last_daily = ?, daily_streak = ?, last_streak_date = ? WHERE user_id = ?",
            (total, datetime.now().isoformat(), streak, today, uid))
        lvl_msg = await grant_xp(db, uid, 25)
        # Daily achievements
        if streak >= 7:
            await try_achievement(db, uid, "daily_7")
        if streak >= 30:
            await try_achievement(db, uid, "daily_30")
        cur2 = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
        new_bal = (await cur2.fetchone())[0]
        await check_wealth_achievements(db, uid, new_bal)
        await db.commit()
    text = (f"💰 <b>Ежедневная награда!</b>\n\nБазовая: {base} 💰\nМножитель: x{mult}\n"
            f"🔥 Стрик: {streak} дн. (+{streak_bonus} 💰)\n<b>Итого: +{total} 💰</b>\n✨ +25 XP")
    if lvl_msg:
        text += f"\n{lvl_msg}"
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# =============================================================================
#  PAY
# =============================================================================
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
    await m.answer(f"✅ Перевод <b>{amount:,} 💰</b> → <b>{target[0]}</b>", parse_mode=ParseMode.HTML)


# =============================================================================
#  SHOP (монеты)
# =============================================================================
@dp.callback_query(F.data == "menu_shop")
async def shop_menu_cb(c: CallbackQuery):
    rows = []
    for item in SHOP_CATALOG:
        rows.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']:,}💰", callback_data=f"shop_buy_{item['id']}")])
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
    await safe_edit(c.message, f"🛒 <b>{item['name']}</b>\n💰 Цена: {item['price']:,}\n\nВведи количество:")
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
                reply_markup=back_menu_kb())
        await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (total_cost, uid))
        t = item["type"]
        if t == "title":
            await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (item["title"], uid))
        elif t == "vip":
            until = (datetime.now() + timedelta(hours=item["hours"] * qty)).isoformat()
            await db.execute("UPDATE users SET vip_until = ? WHERE user_id = ?", (until, uid))
        elif t == "multiplier":
            await db.execute("UPDATE users SET coin_multiplier = ? WHERE user_id = ?", (item["mult"], uid))
        elif t == "rank":
            await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (item["rank"], uid))
        elif t == "bbc":
            await db.execute("UPDATE users SET bbc_balance = bbc_balance + ? WHERE user_id = ?", (item["amount"] * qty, uid))
        elif t == "shield":
            amt = item.get("amount", 1) * qty
            await db.execute("UPDATE users SET shield = shield + ? WHERE user_id = ?", (amt, uid))
        elif t == "lucky_gacha":
            amt = item.get("amount", 1) * qty
            await db.execute("UPDATE users SET lucky_gacha = lucky_gacha + ? WHERE user_id = ?", (amt, uid))
        elif t == "reset_cd":
            await db.execute(f"UPDATE users SET {item['cd_field']} = '' WHERE user_id = ?", (uid,))
        elif t == "reset_all_cd":
            await db.execute(
                "UPDATE users SET last_daily='', last_gacha='', last_rob='' WHERE user_id = ?",
                (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"✅ Куплено: <b>{item['name']}</b> x{qty}\n💰 Потрачено: {total_cost:,}",
                   parse_mode=ParseMode.HTML, reply_markup=back_menu_kb())


# =============================================================================
#  BBC SHOP
# =============================================================================
@dp.callback_query(F.data == "menu_bbcshop")
async def bbcshop_menu_cb(c: CallbackQuery):
    rows = []
    for item in BBC_SHOP_CATALOG:
        rows.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']} BBC", callback_data=f"bbcbuy_{item['id']}")])
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
    await safe_edit(c.message, f"💎 <b>{item['name']}</b>\n{item['desc']}\n💵 Цена: {item['price']} BBC\n\nВведи количество:")
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
                reply_markup=back_menu_kb())
        await db.execute("UPDATE users SET bbc_balance = MAX(0, bbc_balance - ?) WHERE user_id = ?", (total_cost, uid))
        t = item["type"]
        result_text = ""
        if t == "title":
            await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (item["title"], uid))
            result_text = f"Титул: {item['title']}"
        elif t == "shield":
            amt = item.get("amount", 1) * qty
            await db.execute("UPDATE users SET shield = shield + ? WHERE user_id = ?", (amt, uid))
            result_text = f"🛡️ Щитов: +{amt}"
        elif t == "lucky_gacha":
            amt = item.get("amount", 1) * qty
            await db.execute("UPDATE users SET lucky_gacha = lucky_gacha + ? WHERE user_id = ?", (amt, uid))
            result_text = f"🌀 Удачных гач: +{amt}"
        elif t == "convert":
            coins = item["coins_per"] * qty
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (coins, uid))
            result_text = f"💰 +{coins:,} монет"
        elif t == "vip":
            until = (datetime.now() + timedelta(hours=item["hours"] * qty)).isoformat()
            await db.execute("UPDATE users SET vip_until = ? WHERE user_id = ?", (until, uid))
            result_text = f"⭐ VIP на {item['hours'] * qty} часов"
        elif t == "multiplier":
            await db.execute("UPDATE users SET coin_multiplier = ? WHERE user_id = ?", (item["mult"], uid))
            result_text = f"💰 Множитель x{item['mult']} на {item['hours']} часов"
        elif t == "rank":
            await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (item["rank"], uid))
            rank_name = RANK_NAMES.get(item["rank"], "???")
            result_text = f"🎖 Ранг: {rank_name}"
        await db.commit()
    await state.clear()
    await m.answer(f"✅ Куплено: <b>{item['name']}</b> x{qty}\n💵 Потрачено: {total_cost} BBC\n{result_text}",
                   parse_mode=ParseMode.HTML, reply_markup=back_menu_kb())


# =============================================================================
#  GAME CENTER
# =============================================================================
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


# =============================================================================
#  BLACKJACK
# =============================================================================
@dp.callback_query(F.data == "game_blackjack")
async def game_blackjack_cb(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(c.message, "🃏 <b>Блэкджек</b>\n\nВыбери ставку:",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="100", callback_data="bjbet_100"),
             InlineKeyboardButton(text="500", callback_data="bjbet_500"),
             InlineKeyboardButton(text="1000", callback_data="bjbet_1000")],
            [InlineKeyboardButton(text="5000", callback_data="bjbet_5000"),
             InlineKeyboardButton(text="ALL-IN", callback_data="bjbet_allin")],
            [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
        ]))
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
        await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid))
        await db.commit()
    deck = new_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    await state.update_data(bet=bet, deck=deck, player_hand=player_hand, dealer_hand=dealer_hand)
    await state.set_state(BlackjackStates.in_game)
    await _show_blackjack(c, player_hand, dealer_hand, bet, state)
    await c.answer()


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


async def _show_blackjack(target, player_hand, dealer_hand, bet, state):
    ptotal = hand_total(player_hand)
    text = (f"🃏 <b>Блэкджек</b> | Ставка: {bet:,}💰\n\n"
            f"🤵 Дилер: {format_hand(dealer_hand, hide_second=True)} (<b>?</b>)\n"
            f"👤 Ты: {format_hand(player_hand)} (<b>{ptotal}</b>)")
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


@dp.message(BlackjackStates.in_game)
async def process_blackjack_text(m: Message, state: FSMContext):
    await m.answer("Используй кнопки ниже!")


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
            await state.clear()
            bj_end_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_blackjack"),
                 InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
            ])
            await c.message.edit_text(
                f"🃏 <b>Блэкджек</b>\n\n👤 Твои карты: {format_hand(player_hand)} (<b>{ptotal}</b>)\n\n"
                f"💥 <b>Перебор! Ты проиграл {bet:,} 💰</b>", parse_mode=ParseMode.HTML, reply_markup=bj_end_kb)
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
            await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid))
            await db.commit()
        bet *= 2
        player_hand.append(deck.pop())
        ptotal_check = hand_total(player_hand)
        if ptotal_check > 21:
            await state.clear()
            bj_end_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_blackjack"),
                 InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
            ])
            await c.message.edit_text(
                f"🃏 <b>Блэкджек</b> | Удвоение\n\n👤 Твои карты: {format_hand(player_hand)} (<b>{ptotal_check}</b>)\n\n"
                f"💥 <b>Перебор при удвоении! -{bet:,} 💰</b>", parse_mode=ParseMode.HTML, reply_markup=bj_end_kb)
            return await c.answer()
        await state.update_data(bet=bet, deck=deck, player_hand=player_hand)
        action = "bj_stand"

    if action == "bj_stand":
        while hand_total(dealer_hand) < 17:
            dealer_hand.append(deck.pop())
        ptotal = hand_total(player_hand)
        dtotal = hand_total(dealer_hand)
        async with aiosqlite.connect(DB_PATH) as db:
            if ptotal <= 21 and (dtotal > 21 or ptotal > dtotal):
                await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bet * 2, uid))
                result = f"🎉 <b>Победа! +{bet:,} 💰</b>"
            elif ptotal == dtotal:
                await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bet, uid))
                result = "🤝 <b>Ничья! Ставка возвращена.</b>"
            else:
                result = f"💸 <b>Проигрыш! -{bet:,} 💰</b>"
            await db.commit()
        await state.clear()
        bj_end_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_blackjack"),
             InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        ])
        await c.message.edit_text(
            f"🃏 <b>Блэкджек</b>\n\n🤵 Дилер: {format_hand(dealer_hand)} (<b>{dtotal}</b>)\n"
            f"👤 Ты: {format_hand(player_hand)} (<b>{ptotal}</b>)\n\n{result}",
            parse_mode=ParseMode.HTML, reply_markup=bj_end_kb)
    await c.answer()


# =============================================================================
#  CRASH GAME
# =============================================================================
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
        await db.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (bet, uid))
        await db.commit()
    crash_point = _generate_crash_point()
    start_mult = 1.0
    _crash_games[uid] = {"bet": bet, "crash_point": crash_point, "current_mult": start_mult, "step_idx": 0}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Дальше!", callback_data="crash_next"),
         InlineKeyboardButton(text=f"💰 Забрать ({bet}💰)", callback_data="crash_cashout")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="crash_cancel")],
    ])
    await safe_edit(c.message, _crash_text(bet, start_mult, 0), kb)
    await c.answer()


def _generate_crash_point() -> float:
    r = random.random()
    if r < 0.35:
        return round(random.uniform(1.0, 1.3), 2)
    elif r < 0.60:
        return round(random.uniform(1.3, 2.0), 2)
    elif r < 0.80:
        return round(random.uniform(2.0, 3.5), 2)
    elif r < 0.92:
        return round(random.uniform(3.5, 5.0), 2)
    elif r < 0.98:
        return round(random.uniform(5.0, 7.5), 2)
    else:
        return round(random.uniform(7.5, 10.0), 2)


def _crash_text(bet: int, current_mult: float, step_idx: int) -> str:
    bar_len = min(step_idx + 1, 15)
    bar = "🟩" * bar_len + "⬛" * (15 - bar_len)
    potential = int(bet * current_mult)
    return (f"📈 <b>КРАШ</b> | Ставка: {bet:,}💰\n\n{bar}\n"
            f"Множитель: <b>x{current_mult}</b>\nПотенциальный выигрыш: <b>{potential:,}💰</b>\n\n"
            f"⚠️ В любой момент может крахнуть!")


@dp.callback_query(F.data == "crash_next")
async def crash_next_cb(c: CallbackQuery):
    uid = c.from_user.id
    import time as _time
    now = _time.time()
    last = _crash_last_click.get(uid, 0)
    if now - last < 1.5:
        return await c.answer("⏳ Подожди 1.5 сек между ходами!", show_alert=False)
    _crash_last_click[uid] = now
    game = _crash_games.get(uid)
    if not game:
        return await c.answer("❌ Нет активной игры!", show_alert=True)
    step_idx = game["step_idx"]
    if step_idx >= len(CRASH_STEPS) - 1:
        game["current_mult"] = CRASH_STEPS[-1]
        return await _crash_cashout(c, uid)
    next_mult = CRASH_STEPS[step_idx]
    crash_point = game["crash_point"]
    if next_mult >= crash_point:
        bet = game["bet"]
        saved_crash_point = crash_point
        del _crash_games[uid]
        text = (f"📈 <b>КРАШ</b> | Ставка: {bet:,}💰\n\n"
                f"💥💥💥 <b>КРАХ на x{saved_crash_point}!</b> 💥💥💥\n\n❌ Ты потерял {bet:,}💰")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="game_crash"),
             InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        ])
        await safe_edit(c.message, text, kb)
        return await c.answer("💥 КРАХ!", show_alert=True)
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
    profit = winnings - bet
    saved_crash_point = game["crash_point"]
    del _crash_games[uid]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (winnings, uid))
        if profit > 0:
            await grant_xp(db, uid, 30)
            await try_achievement(db, uid, "first_win")
        await db.commit()
    if mult <= 1.0:
        result = f"🤝 Ты забрал ставку обратно: {winnings:,}💰 (x{mult})"
    else:
        result = f"✅ <b>Успел забрать на x{mult}! +{profit:,}💰</b>"
    text = (f"📈 <b>КРАШ</b>\n\n💰 {result}\nКрах был бы на: x{saved_crash_point}")
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
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (game["bet"], uid))
            await db.commit()
        del _crash_games[uid]
    await c.answer("Ставка возвращена!")
    await safe_edit(c.message, "📈 Краш отменён. Ставка возвращена.",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        ]))


@dp.callback_query(F.data == "game_crash")
async def game_crash_menu_cb(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100", callback_data="crashbet_100"),
         InlineKeyboardButton(text="500", callback_data="crashbet_500"),
         InlineKeyboardButton(text="1000", callback_data="crashbet_1000")],
        [InlineKeyboardButton(text="5000", callback_data="crashbet_5000"),
         InlineKeyboardButton(text="ALL-IN", callback_data="crashbet_allin")],
        [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
    ])
    await safe_edit(c.message, "<b>📈 Краш</b>\nМножитель растёт. Успей забрать!\n\nВыбери ставку:", kb)
    await c.answer()


# =============================================================================
#  ROULETTE / DICE / COIN
# =============================================================================
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


@dp.callback_query(F.data.in_({"game_roulette", "game_dice", "game_coin"}))
async def game_select_cb(c: CallbackQuery):
    game = c.data.replace("game_", "")
    names = {"roulette": "🎰 Рулетка", "dice": "🎲 Кости", "coin": "🪙 Монетка"}
    descs = {
        "roulette": "Красное/Чёрное x2, Зелёное x14",
        "dice": "Угадай число 1-6, выигрыш x5",
        "coin": "Орёл или решка, выигрыш x1.9",
    }
    await safe_edit(c.message, f"<b>{names[game]}</b>\n{descs[game]}\n\nВыбери ставку:", bet_keyboard(game))
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
    color = parts[1]
    bet = int(parts[2])
    await play_game(c, "roulette", bet, choice=color)


@dp.callback_query(F.data.regexp(r"^coinpick_(heads|tails)_\d+$"))
async def coin_play_cb(c: CallbackQuery):
    parts = c.data.split("_")
    side = parts[1]
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
        await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ? AND balance >= ?", (bet, uid, bet))
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
            result = player_color if rigged else random.choice(colors)
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
            kb2 = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📈 Краш", callback_data="game_crash")],
                [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
            ])
            if is_message:
                await c.message.answer("📈 Используй кнопку Краш в меню игр!", parse_mode=ParseMode.HTML, reply_markup=kb2)
            else:
                await safe_edit(c.message, "📈 Используй кнопку Краш в меню игр!", kb2)
                await c.answer()
            return
        if won:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (winnings, uid))
            lvl_msg = await grant_xp(db, uid, 30)
            await try_achievement(db, uid, "first_win")
            # Casino achievements - track via incrementing a proxy counter
            await try_achievement(db, uid, "casino_10")
            await try_achievement(db, uid, "casino_50")
            await try_achievement(db, uid, "casino_100")
            cur2 = await db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
            new_bal = (await cur2.fetchone())[0]
            await check_wealth_achievements(db, uid, new_bal)
        else:
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


# =============================================================================
#  INVENTORY
# =============================================================================
@dp.callback_query(F.data == "menu_inv")
async def inventory_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, c.rarity, COUNT(*) FROM user_cards uc "
            "JOIN cards c ON uc.card_id = c.card_id "
            "WHERE uc.user_id = ? GROUP BY c.card_id ORDER BY c.rarity DESC", (uid,))
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


# =============================================================================
#  LEADERBOARDS
# =============================================================================
@dp.callback_query(F.data == "menu_tops")
async def tops_menu_cb(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Монеты", callback_data="top_coins"),
         InlineKeyboardButton(text="🃏 Карты", callback_data="top_cards")],
        [InlineKeyboardButton(text="📊 Уровни", callback_data="top_levels"),
         InlineKeyboardButton(text="💑 Топ пар", callback_data="top_pairs")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, "🏆 <b>ТОПЫ</b>\n\nВыбери рейтинг:", kb)
    await c.answer()


@dp.callback_query(F.data == "top_coins")
async def top_coins_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT nickname, balance FROM users ORDER BY balance DESC LIMIT 10")
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {r[0]}: {r[1]:,} 💰" for i, r in enumerate(rows)]
    await safe_edit(c.message, "💰 <b>ТОП ПО МОНЕТАМ</b>\n\n" + "\n".join(lines), back_menu_kb())
    await c.answer()


@dp.callback_query(F.data == "top_cards")
async def top_cards_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COALESCE(u.nickname, 'User' || u.user_id), SUM(c.rarity) as score, COUNT(*) as cnt "
            "FROM user_cards uc JOIN users u ON uc.user_id = u.user_id "
            "JOIN cards c ON uc.card_id = c.card_id "
            "GROUP BY uc.user_id ORDER BY score DESC LIMIT 10")
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {r[0]}: {r[2]} карт (рейтинг: {r[1]})" for i, r in enumerate(rows)]
    await safe_edit(c.message, "🃏 <b>ТОП ПО КАРТАМ</b>\n\n" + "\n".join(lines or ["Пусто"]), back_menu_kb())
    await c.answer()



@dp.callback_query(F.data == "top_levels")
async def top_levels_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT nickname, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT 10")
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {r[0]}: Ур.{r[1]} ({level_title(r[1])})" for i, r in enumerate(rows)]
    await safe_edit(c.message, "📊 <b>ТОП ПО УРОВНЯМ</b>\n\n" + "\n".join(lines or ["Пусто"]), back_menu_kb())
    await c.answer()


@dp.message(Command("top"))
async def top_cmd(m: Message):
    args = (m.text or "").split()
    valid_types = {
        "coins": ("💰 ТОП ПО МОНЕТАМ", "SELECT nickname, balance FROM users ORDER BY balance DESC LIMIT 10",
                  lambda r: f"{r[0]}: {r[1]:,} 💰"),
        "cards": ("🃏 ТОП ПО КАРТАМ",
                  "SELECT COALESCE(u.nickname, 'User' || u.user_id), SUM(c.rarity) as score, COUNT(*) as cnt FROM user_cards uc JOIN users u ON uc.user_id = u.user_id JOIN cards c ON uc.card_id = c.card_id GROUP BY uc.user_id ORDER BY score DESC LIMIT 10",
                  lambda r: f"{r[0]}: {r[2]} карт (рейтинг: {r[1]})"),
        "levels": ("📊 ТОП ПО УРОВНЯМ",
                   "SELECT nickname, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT 10",
                   lambda r: f"{r[0]}: Ур.{r[1]} ({level_title(r[1])})"),
        "pairs": ("💑 ТОП ПАР",
                  "SELECT m.user1_id, m.user2_id, m.married_at, COALESCE(u1.nickname, 'User' || m.user1_id), COALESCE(u2.nickname, 'User' || m.user2_id) FROM marriages m LEFT JOIN users u1 ON m.user1_id = u1.user_id LEFT JOIN users u2 ON m.user2_id = u2.user_id ORDER BY m.married_at ASC LIMIT 10",
                  lambda r: f"{r[3] or '???'} ❤️ {r[4] or '???'}"),
    }
    top_type = args[1].lower() if len(args) > 1 else "coins"
    if top_type not in valid_types:
        await m.answer(
            "🏆 <b>ТОПЫ</b>\n\nВыбери тип:\n"
            "<code>/top coins</code> — по монетам\n"
            "<code>/top cards</code> — по картам\n"
            "<code>/top levels</code> — по уровням\n"
            "<code>/top pairs</code> — топ пар\n",
            parse_mode=ParseMode.HTML)
        return
    title, query, formatter = valid_types[top_type]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query)
        rows = await cur.fetchall()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    if not rows:
        await m.answer(f"{title}\n\nПока пусто!", parse_mode=ParseMode.HTML)
        return
    lines = [f"{medals[i]} {formatter(r)}" for i, r in enumerate(rows)]
    await m.answer(f"{title}\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


# =============================================================================
#  LEVEL SYSTEM
# =============================================================================
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
    text = (f"📊 <b>УРОВЕНЬ</b>\n\n🎖 Звание: <b>{level_title(lvl)}</b>\n📈 Уровень: <b>{lvl}</b>\n"
            f"✨ XP: {xp}/{need} ({pct}%)\n\n[{bar}]\n\n"
            f"<b>Как получать XP:</b>\n  💰 Ежедневка: +25 XP\n  🔨 Работа: +15 XP\n"
            f"  🎴 Гача: +10 XP/карта\n  🎮 Победа в казино: +30 XP\n"
            f"  🦹 Ограбление: +20 XP")
    await safe_edit(c.message, text, back_menu_kb())
    await c.answer()


# =============================================================================
#  ROB (/rob)
# =============================================================================
@dp.message(Command("rob"))
async def rob_cmd(m: Message):
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.answer("🦹 Ответь на сообщение жертвы: /rob")
    target_id = m.reply_to_message.from_user.id
    uid = m.from_user.id
    if target_id == uid:
        return await m.answer("❌ Нельзя грабить себя!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance, last_rob, rob_count FROM users WHERE user_id = ?", (uid,))
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
        success = random.random() < 0.40
        if success:
            steal_pct = random.uniform(0.10, 0.30)
            stolen = min(int(target[0] * steal_pct), 5000)
            stolen = max(stolen, 1)
            tcur2 = await db.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,))
            target_now = await tcur2.fetchone()
            if target_now and target_now[0] < stolen:
                stolen = max(target_now[0], 0)
            if stolen <= 0:
                await db.execute("UPDATE users SET last_rob = ? WHERE user_id = ?",
                                 (datetime.now().isoformat(), uid))
                await db.commit()
                return await m.answer("🚨 Жертва успела потратить все монеты!")
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (stolen, uid))
            await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (stolen, target_id))
            new_rob_count = (row[2] or 0) + 1
            await db.execute("UPDATE users SET last_rob = ?, rob_count = ? WHERE user_id = ?",
                             (datetime.now().isoformat(), new_rob_count, uid))
            lvl_msg = await grant_xp(db, uid, 20)
            if new_rob_count >= 10:
                await try_achievement(db, uid, "rob_master")
            if new_rob_count >= 50:
                await try_achievement(db, uid, "rob_50")
            if new_rob_count >= 100:
                await try_achievement(db, uid, "rob_100")
            await db.commit()
            text = f"🦹 <b>Успешное ограбление!</b>\n\n💰 Украдено: <b>{stolen:,}</b> у {target[1]}\n✨ +20 XP"
            if lvl_msg:
                text += f"\n{lvl_msg}"
        else:
            fine = min(500, row[0])
            await db.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (fine, uid))
            await db.execute("UPDATE users SET last_rob = ? WHERE user_id = ?",
                             (datetime.now().isoformat(), uid))
            await db.commit()
            text = f"🚨 <b>Провал!</b>\n\nТебя поймали! Штраф: <b>{fine:,} 💰</b>"
    await m.answer(text, parse_mode=ParseMode.HTML)


# =============================================================================
#  ACHIEVEMENTS
# =============================================================================
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



# =============================================================================
#  PROMO CODES
# =============================================================================
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
        pcur = await db.execute("SELECT reward_type, reward_value, uses_left FROM promocodes WHERE code = ?", (code,))
        promo = await pcur.fetchone()
        if not promo:
            return await m.answer("❌ Промокод не найден!")
        if promo[2] <= 0:
            return await m.answer("❌ Промокод исчерпан!")
        ucur = await db.execute("SELECT 1 FROM promo_used WHERE user_id = ? AND code = ?", (uid, code))
        if await ucur.fetchone():
            return await m.answer("❌ Ты уже активировал этот промокод!")
        rtype, rval = promo[0], promo[1]
        if rtype == "money":
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (rval, uid))
        elif rtype == "bbc_money":
            await db.execute("UPDATE users SET bbc_balance = bbc_balance + ? WHERE user_id = ?", (rval, uid))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        await db.execute("INSERT INTO promo_used (user_id, code) VALUES (?, ?)", (uid, code))
        await db.execute("DELETE FROM promocodes WHERE uses_left <= 0")
        await try_achievement(db, uid, "promo_used")
        await db.commit()
    emoji = "💰" if rtype == "money" else "💵"
    await m.answer(f"✅ Промокод <b>{code}</b> активирован!\n{emoji} +{rval}", parse_mode=ParseMode.HTML)


# =============================================================================
#  CARDS WORD TRIGGER
# =============================================================================
@dp.message(F.text.regexp(r'^[^/]'), StateFilter(None))
async def word_trigger_card(m: Message):
    text = (m.text or "").lower().strip()
    if "карта" not in text:
        return
    uid = m.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_gacha, lucky_gacha, is_frozen, rank FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ Сначала нажми /start!")
        if row[2]:
            return await m.answer("🥶 Твой аккаунт заморожен!")
        user_rank = row[3] or 0
        if user_rank != 7:
            remaining = cd_remaining(row[0], GACHA_CD)
            if remaining > 0:
                return await m.answer(f"⏳ Гача на КД: {fmt_seconds(remaining)}")
        lucky = bool(row[1])
        results, err = await do_gacha(db, uid, 1, lucky)
        if err:
            return await m.answer(err)
        if lucky:
            await db.execute("UPDATE users SET lucky_gacha = 0 WHERE user_id = ?", (uid,))
        await db.execute("UPDATE users SET last_gacha = ? WHERE user_id = ?", (datetime.now().isoformat(), uid))
        lvl_msg = await grant_xp(db, uid, 10)
        await check_collection_achievements(db, uid)
        await db.commit()
    async with aiosqlite.connect(DB_PATH) as db2:
        total_cur = await db2.execute("SELECT COUNT(*) FROM cards")
        total_in_db = (await total_cur.fetchone())[0]
        owned_cur = await db2.execute("SELECT COUNT(DISTINCT card_id) FROM user_cards WHERE user_id = ?", (uid,))
        owned_unique = (await owned_cur.fetchone())[0]
    card = results[0]
    r = card[2]
    rname = RARITY_NAMES.get(r, "???")
    quote = RARITY_QUOTES.get(r, "")
    text_out = (f"🎴 <b>НОВАЯ КАРТА!</b>\n\n{RARITY_STARS.get(r, '⭐')} <b>{card[1]}</b>\n"
                f"├ Редкость: {rname} ({r}/5)\n└ {quote}\n\n📊 Коллекция: {owned_unique}/{total_in_db} уникальных")
    if lucky:
        text_out += "\n🌀 <i>Портал Удачи использован!</i>"
    if lvl_msg:
        text_out += f"\n{lvl_msg}"
    text_out += "\n✨ +10 XP"
    if card[3]:
        try:
            await m.reply_photo(card[3], caption=text_out, parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            log.warning(f"reply_photo failed for card {card[0]} (image_id={card[3]!r}): {e}")
    await m.answer(text_out, parse_mode=ParseMode.HTML)


# =============================================================================
#  ADD CARD (/addcard)
# =============================================================================
def _is_addcard_cmd(m: Message) -> bool:
    t = (m.text or m.caption or "").strip().lower()
    if not t.startswith("/addcard"):
        return False
    rest = t[8:]
    return not rest or rest[0] in (" ", "@", "\n")


@dp.message(_is_addcard_cmd)
async def addcard_cmd(m: Message):
    if not await is_any_admin(m.from_user.id):
        return
    raw = (m.text or m.caption or "").strip()
    args = raw.split()
    # Способ 1: Реплай на пользователя
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
        async with aiosqlite.connect(DB_PATH) as db:
            await _ensure_game_tables(db)
            dup_cur = await db.execute("SELECT card_id, name FROM cards WHERE source_user_id = ?", (target.id,))
            existing = await dup_cur.fetchone()
        if existing:
            return await m.answer(
                f"❌ Карта этого юзера уже существует!\n\n🆔 ID: <b>{existing[0]}</b>\n"
                f"👤 Имя: <b>{existing[1]}</b>\n\nИспользуй <code>/delcard {existing[0]}</code> чтобы удалить старую.",
                parse_mode=ParseMode.HTML)
        image_id = None
        try:
            photos = await m.bot.get_user_profile_photos(target.id, limit=1)
            if photos.total_count > 0:
                raw_file_id = photos.photos[0][-1].file_id
                # Аватарные file_id (от get_user_profile_photos) нельзя отправить повторно.
                # Пересылаем фото боту/админу, чтобы получить нормальный переиспользуемый file_id.
                try:
                    sent_msg = await m.bot.send_photo(ADMIN_ID, raw_file_id)
                    image_id = sent_msg.photo[-1].file_id
                    await sent_msg.delete()
                except Exception as e2:
                    logging.warning(f"ADDCARD re-upload error: {e2}")
                    image_id = raw_file_id  # запасной вариант
        except Exception as e:
            logging.warning(f"ADDCARD avatar error: {e}")
        if not image_id:
            return await m.answer(f"❌ У <b>{card_name}</b> нет аватарки! Карту без фото создать нельзя.", parse_mode=ParseMode.HTML)
        async with aiosqlite.connect(DB_PATH) as db:
            await _ensure_game_tables(db)
            cur = await db.execute(
                "INSERT INTO cards (name, rarity, image_id, source_user_id) VALUES (?, ?, ?, ?)",
                (card_name, rarity, image_id, target.id))
            card_id = cur.lastrowid
            await db.commit()
        await m.answer(
            f"✅ Карта создана из профиля!\n\n🆔 ID: <b>{card_id}</b>\n👤 Имя: <b>{card_name}</b>\n"
            f"⭐ Редкость: {RARITY_STARS.get(rarity, '⭐')}\n🖼 Аватар: захвачен",
            parse_mode=ParseMode.HTML)
        return
    # Способ 2: Фото + подпись
    if m.photo:
        parts = raw.split()
        if len(parts) < 3:
            return await m.answer("🃏 Подпись: /addcard Название РЕДКОСТЬ(1-5)")
        rarity = parse_positive_int(parts[-1])
        if not rarity or rarity > 5:
            return await m.answer("❌ Редкость — число от 1 до 5!")
        name = " ".join(parts[1:-1])
        image_id = m.photo[-1].file_id
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("INSERT INTO cards (name, rarity, image_id) VALUES (?, ?, ?)", (name, rarity, image_id))
            card_id = cur.lastrowid
            await db.commit()
        await m.answer(
            f"✅ Карта добавлена!\n\n🆔 ID: <b>{card_id}</b>\n📝 Название: {name}\n"
            f"⭐ Редкость: {RARITY_STARS.get(rarity, '⭐')}", parse_mode=ParseMode.HTML)
        return
    # Инструкция
    await m.answer(
        "🃏 <b>Как добавить карту:</b>\n\n📌 <b>Способ 1 (реплай):</b>\nОтветь на сообщение пользователя:\n"
        "<code>/addcard 3</code>\nБот возьмёт его аватарку и ник автоматически.\n\n"
        "📌 <b>Способ 2 (фото):</b>\nОтправь фото с подписью:\n<code>/addcard Название 3</code>\n\n"
        "⭐ Редкость: 1-5", parse_mode=ParseMode.HTML)


# =============================================================================
#  CARDS LIST (/cards)
# =============================================================================
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


# =============================================================================
#  RIG (/rig)
# =============================================================================
@dp.message(Command("rig"))
async def rig_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    global rig_mode, rig_remaining
    args = (m.text or "").split()
    if len(args) < 2:
        status = f"🎯 100% ({rig_remaining} игр)" if rig_mode == "win100" else "⚖️ Выкл"
        return await m.answer(f"🎰 Подкрут: {status}\n\nФормат: /rig 100 [кол-во игр] или /rig off")
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


# =============================================================================
#  SSS RESET CD (/Sss) — быстрый сброс всех КД, только для админа
# =============================================================================
@dp.message(Command("Sss"))
async def sss_reset_cd_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    # Определяем цель: реплай, @username или ID в аргументе
    uid, name, _ = await resolve_user(m)
    if not uid:
        await m.answer(
            "❓ Укажи цель:\n"
            "• <b>Реплай</b> на сообщение игрока\n"
            "• <code>/Sss @username</code>\n"
            "• <code>/Sss 123456789</code>",
            parse_mode=ParseMode.HTML)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_daily='', last_gacha='', last_rob='' WHERE user_id = ?",
            (uid,))
        await db.commit()
    await m.answer(
        f"✅ Все КД сброшены для <b>{name}</b> (<code>{uid}</code>).",
        parse_mode=ParseMode.HTML)


# =============================================================================
#  FIX CARDS (/fixcards) — починка file_id аватарок в БД
# =============================================================================
@dp.message(Command("fixcards"))
async def fixcards_cmd(m: Message):
    """Перезаливает все аватарные file_id (profile-photo тип) через send→delete,
       чтобы получить нормальные переиспользуемые file_id."""
    if m.from_user.id != ADMIN_ID:
        return
    status_msg = await m.answer("🔧 Начинаю починку карт... это может занять время.")
    fixed = 0
    failed = 0
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT card_id, name, image_id FROM cards WHERE image_id IS NOT NULL AND TRIM(image_id) != ''")
        cards = await cur.fetchall()
        for card_id, name, image_id in cards:
            # Аватарные file_id от get_user_profile_photos начинаются с AgACAgIAAxUAA
            # Обычные фото из сообщений — AgACAgIAAxkB
            # Пробуем переслать каждую, у которой prefix не xkB (т.е. подозрительная)
            if "AxUAA" in image_id or "AxkBAAI" not in image_id:
                try:
                    sent_msg = await m.bot.send_photo(ADMIN_ID, image_id)
                    new_file_id = sent_msg.photo[-1].file_id
                    await sent_msg.delete()
                    await db.execute("UPDATE cards SET image_id = ? WHERE card_id = ?", (new_file_id, card_id))
                    fixed += 1
                    await asyncio.sleep(0.3)  # не спамим API
                except Exception as e:
                    log.warning(f"fixcards: card {card_id} ({name}) failed: {e}")
                    failed += 1
        await db.commit()
    await status_msg.edit_text(
        f"✅ <b>Починка карт завершена!</b>\n\n"
        f"✔️ Исправлено: <b>{fixed}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>",
        parse_mode=ParseMode.HTML)


# =============================================================================
#  DEL CARD (/delcard) — админ
# =============================================================================
@dp.message(Command("delcard"))
async def delcard_cmd(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer(
            "🗑 <b>Удаление карты</b>\n\nФормат: <code>/delcard CARD_ID</code>\nУдалит карту из базы и у всех игроков.",
            parse_mode=ParseMode.HTML)
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
        f"🗑 <b>Карта удалена!</b>\n\n🆔 ID: <b>{cid}</b>\n📝 Имя: <b>{card[0]}</b>\n"
        f"⭐ Редкость: {RARITY_STARS.get(card[1], '⭐')}\n👥 Убрана у {cnt} игроков.",
        parse_mode=ParseMode.HTML)


# =============================================================================
#  DROP CARD (/dropcard) — игрок
# =============================================================================
@dp.message(Command("dropcard"))
async def dropcard_cmd(m: Message):
    uid = m.from_user.id
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer(
            "🗑 <b>Удалить карту</b>\n\nФормат: <code>/dropcard CARD_ID</code> — удалить 1 шт.\n"
            "<code>/dropcard CARD_ID 3</code> — удалить 3 шт.\n"
            "<code>/dropcard CARD_ID all</code> — удалить все копии.",
            parse_mode=ParseMode.HTML)
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
        cnt_cur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND card_id = ?", (uid, cid))
        owned = (await cnt_cur.fetchone())[0]
        if owned == 0:
            return await m.answer("❌ У тебя нет этой карты!")
        to_delete = owned if drop_all else min(amount, owned)
        ids_cur = await db.execute("SELECT id FROM user_cards WHERE user_id = ? AND card_id = ? LIMIT ?", (uid, cid, to_delete))
        ids = [r[0] for r in await ids_cur.fetchall()]
        if ids:
            placeholders = ",".join("?" * len(ids))
            await db.execute(f"DELETE FROM user_cards WHERE id IN ({placeholders})", ids)
            await db.commit()
    remaining = owned - to_delete
    rarity_star = RARITY_STARS.get(card_info[1], "⭐")
    await m.answer(
        f"🗑 <b>Карта удалена из коллекции!</b>\n\n{rarity_star} <b>{card_info[0]}</b>\n"
        f"Удалено: {to_delete} шт.\nОсталось: {remaining} шт.", parse_mode=ParseMode.HTML)


# =============================================================================
#  CLEAN CARDS (/cleancards) — удалить карты без картинки
# =============================================================================
@dp.message(Command("cleancards"))
async def cleancards_cmd(m: Message):
    """Удалить все карты из БД у которых нет картинки (image_id пустой)."""
    if m.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT card_id, name, rarity, image_id FROM cards")
        all_cards = await cur.fetchall()
        removed = []
        for card in all_cards:
            card_id, name, rarity, image_id = card
            if not image_id or str(image_id).strip() in ("", "None", "null", "0"):
                # Удаляем карту из базы и у всех игроков
                await db.execute("DELETE FROM user_cards WHERE card_id = ?", (card_id,))
                await db.execute("DELETE FROM cards WHERE card_id = ?", (card_id,))
                removed.append((card_id, name, rarity))
        await db.commit()
    if not removed:
        await m.answer("✅ Все карты имеют картинки. Удалять нечего.")
    else:
        lines = [f"<code>#{c[0]}</code> {RARITY_STARS.get(c[2], '⭐')} <b>{c[1]}</b>" for c in removed]
        await m.answer(
            f"🧹 <b>Очистка карт без картинки</b>\n\nУдалено карт: <b>{len(removed)}</b>\n\n" + "\n".join(lines),
            parse_mode=ParseMode.HTML)


# =============================================================================
#  LIMITED ADMIN SYSTEM
# =============================================================================
@dp.message(Command("addadmin"))
async def addadmin_cmd(m: Message):
    """Добавить ограниченного админа. Доступно только полному админу."""
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer(
            "👤 <b>Добавить ограниченного админа</b>\n\n"
            "Формат: <code>/addadmin USER_ID</code>\n\n"
            "⚠️ Ограниченный админ НЕ имеет доступа к:\n"
            "  • Бэкап/Откат/Восстановление БД\n"
            "  • Подкрутка казино\n"
            "  • Удаление/переименование карт в базе\n"
            "  • Изменение редкости карт\n"
            "  • Сброс арены\n"
            "  • Управление /me разрешениями\n"
            "  • Добавление других админов\n"
            "  • Очистка карт без картинки",
            parse_mode=ParseMode.HTML)
    uid = parse_positive_int(args[1])
    if not uid:
        return await m.answer("❌ ID — целое число > 0!")
    if uid == ADMIN_ID:
        return await m.answer("❌ Нельзя добавить себя как ограниченного админа!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT nickname FROM users WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await m.answer("❌ Игрок не найден! Сначала /start.")
        # Проверяем не является ли уже админом
        acur = await db.execute("SELECT user_id FROM limited_admins WHERE user_id = ?", (uid,))
        if await acur.fetchone():
            return await m.answer(f"⚠️ Игрок <code>{uid}</code> уже является ограниченным админом.", parse_mode=ParseMode.HTML)
        await db.execute("INSERT INTO limited_admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
                         (uid, ADMIN_ID, datetime.now().isoformat()))
        await db.commit()
    await m.answer(f"✅ Игрок <b>{row[0]}</b> (<code>{uid}</code>) добавлен как ограниченный админ!", parse_mode=ParseMode.HTML)


@dp.message(Command("removeadmin"))
async def removeadmin_cmd(m: Message):
    """Удалить ограниченного админа. Доступно только полному админу."""
    if m.from_user.id != ADMIN_ID:
        return
    args = (m.text or "").split()
    if len(args) < 2:
        return await m.answer("👤 <b>Удалить ограниченного админа</b>\n\nФормат: <code>/removeadmin USER_ID</code>", parse_mode=ParseMode.HTML)
    uid = parse_positive_int(args[1])
    if not uid:
        return await m.answer("❌ ID — целое число > 0!")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM limited_admins WHERE user_id = ?", (uid,))
        await db.commit()
        if cur.rowcount == 0:
            return await m.answer(f"❌ Игрок <code>{uid}</code> не является ограниченным админом.", parse_mode=ParseMode.HTML)
    await m.answer(f"✅ Игрок <code>{uid}</code> больше не является ограниченным админом.", parse_mode=ParseMode.HTML)


@dp.message(Command("listadmins"))
async def listadmins_cmd(m: Message):
    """Список ограниченных админов. Доступно только полному админу."""
    if m.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT la.user_id, u.nickname, la.added_at FROM limited_admins la "
            "LEFT JOIN users u ON la.user_id = u.user_id")
        rows = await cur.fetchall()
    if not rows:
        return await m.answer("📋 <b>Список ограниченных админов</b>\n\nПусто.", parse_mode=ParseMode.HTML)
    lines = []
    for r in rows:
        name = r[1] or "???"
        added_at = r[2] or "?"
        lines.append(f"  • <b>{name}</b> (<code>{r[0]}</code>) — добавлен: {added_at}")
    await m.answer("📋 <b>Ограниченные админы:</b>\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN PANEL
# =============================================================================
def limited_admin_kb() -> InlineKeyboardMarkup:
    """Меню для ограниченных админов."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players")],
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm_promo"),
         InlineKeyboardButton(text="🃏 Карты (добавить)", callback_data="adm_cards_limited")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="🔍 Просмотр игрока", callback_data="adm_lookup"),
         InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="✏️ Сменить ник", callback_data="adm_set_nickname")],
    ])


def full_admin_kb() -> InlineKeyboardMarkup:
    """Меню для полноценных ограниченных админов (все права кроме управления админами)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players")],
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm_promo"),
         InlineKeyboardButton(text="🃏 Карты", callback_data="adm_cards")],
        [InlineKeyboardButton(text="🎰 Игры & Подкрутка", callback_data="adm_games"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="💬 /me разрешения", callback_data="adm_me_perms")],
        [InlineKeyboardButton(text="🔍 Просмотр игрока", callback_data="adm_lookup"),
         InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="✏️ Сменить ник", callback_data="adm_set_nickname")],
        [InlineKeyboardButton(text="📦 Бэкап БД", callback_data="adm_backup"),
         InlineKeyboardButton(text="🔄 Откат БД", callback_data="adm_rollback")],
        [InlineKeyboardButton(text="📥 Восстановить БД", callback_data="adm_restore")],
    ])


def admin_main_kb() -> InlineKeyboardMarkup:
    """Меню главного админа (все права + управление админами)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Игроки", callback_data="adm_players")],
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm_promo"),
         InlineKeyboardButton(text="🃏 Карты", callback_data="adm_cards")],
        [InlineKeyboardButton(text="🎰 Игры & Подкрутка", callback_data="adm_games"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="💬 /me разрешения", callback_data="adm_me_perms")],
        [InlineKeyboardButton(text="🔍 Просмотр игрока", callback_data="adm_lookup"),
         InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="✏️ Сменить ник", callback_data="adm_set_nickname")],
        [InlineKeyboardButton(text="📦 Бэкап БД", callback_data="adm_backup"),
         InlineKeyboardButton(text="🔄 Откат БД", callback_data="adm_rollback")],
        [InlineKeyboardButton(text="📥 Восстановить БД", callback_data="adm_restore")],
        [InlineKeyboardButton(text="👤 Управление админами", callback_data="adm_manage_admins")],
    ])


def admin_games_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Подкрутка казино", callback_data="adm_rig")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")],
    ])


@dp.message(Command("admin"))
async def admin_cmd(m: Message):
    uid = m.from_user.id
    if uid == ADMIN_ID:
        kb = admin_main_kb()
        title = "👑 <b>АДМИН-ПАНЕЛЬ</b>"
    elif await is_full_admin(uid):
        kb = full_admin_kb()
        title = "👑 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>"
    elif await is_limited_admin(uid):
        kb = limited_admin_kb()
        title = "🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>"
    else:
        return
    await m.answer(title, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_back")
async def admin_back_cb(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    if uid == ADMIN_ID:
        kb = admin_main_kb()
        title = "👑 <b>АДМИН-ПАНЕЛЬ</b>"
    elif await is_full_admin(uid):
        kb = full_admin_kb()
        title = "👑 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>"
    elif await is_limited_admin(uid):
        kb = limited_admin_kb()
        title = "🔧 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>"
    else:
        return
    await state.clear()
    await safe_edit(c.message, title, kb)
    await c.answer()


# =============================================================================
#  ADMIN: Statistics
# =============================================================================
@dp.callback_query(F.data == "adm_stats")
async def adm_stats_cb(c: CallbackQuery):
    if not await is_any_admin(c.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Админ", callback_data="adm_back")]])
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            uc = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            cc = (await (await db.execute("SELECT COUNT(*) FROM cards")).fetchone())[0]
            pc = (await (await db.execute("SELECT COUNT(*) FROM promocodes")).fetchone())[0]
            tc = (await (await db.execute("SELECT SUM(balance) FROM users")).fetchone())[0] or 0
            banned = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")).fetchone())[0]
            limited = (await (await db.execute("SELECT COUNT(*) FROM limited_admins")).fetchone())[0]
        rig_status = f"🎯 100% ({rig_remaining} игр)" if rig_mode == "win100" else "⚖️ Выкл"
        await safe_edit(c.message,
            f"📊 <b>Статистика</b>\n\n👥 Игроков: {uc}\n🚫 Забанено: {banned}\n"
            f"👤 Ограниченных админов: {limited}\n🃏 Карт в базе: {cc}\n"
            f"🎁 Промокодов: {pc}\n💰 Всего монет в экономике: {tc:,}\n🎰 Подкрут: {rig_status}", kb)
    except Exception as e:
        await safe_edit(c.message, f"📊 <b>Статистика</b>\n\n⚠️ Ошибка: <code>{e}</code>", kb)
    await c.answer()


# =============================================================================
#  ADMIN: Promocodes
# =============================================================================
@dp.callback_query(F.data == "adm_promo")
async def adm_promo_cb(c: CallbackQuery):
    if not await is_any_admin(c.from_user.id):
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
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_promo_data)
    await safe_edit(c.message, "Введи данные промокода:\n<code>КОД ТИП(money/bbc_money) СУММА АКТИВАЦИИ</code>\n\nПример: <code>NEWYEAR money 1000 50</code>")
    await c.answer()


@dp.message(AdminStates.waiting_for_promo_data)
async def process_promo_data(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
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
                (code, args[1], val, uses))
            await db.commit()
        except Exception:
            await state.clear()
            return await m.answer("❌ Промокод уже существует!")
    await state.clear()
    await m.answer(f"✅ Промокод <b>{code}</b> создан! ({args[1]}: {val}, {uses} активаций)", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_promo_list")
async def adm_promo_list_cb(c: CallbackQuery):
    if not await is_any_admin(c.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Промокоды", callback_data="adm_promo")]])
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT code, reward_type, reward_value, uses_left FROM promocodes")
            promos = await cur.fetchall()
        text = "📋 <b>Промокоды:</b>\n\n" + "\n".join(
            f"<code>{p[0]}</code> — {p[1]}: {p[2]} (осталось: {p[3]})" for p in promos) if promos else "📋 Промокодов нет."
    except Exception as e:
        text = f"📋 <b>Промокоды</b>\n\n⚠️ Ошибка: <code>{e}</code>"
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "adm_promo_del")
async def adm_promo_del_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_promo_del)
    await safe_edit(c.message, "🗑 Введи код промокода для удаления:")
    await c.answer()


@dp.message(AdminStates.waiting_for_promo_del)
async def process_promo_del(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
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


# =============================================================================
#  ADMIN: Players (ban/unban/wipe)
# =============================================================================
@dp.callback_query(F.data == "adm_players")
async def adm_players_cb(c: CallbackQuery):
    if not await is_any_admin(c.from_user.id):
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
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_ban_id)
    await safe_edit(c.message, "🚫 Ответь на сообщение игрока, или напиши @юзернейм / ID для бана:")
    await c.answer()


@dp.message(AdminStates.waiting_for_ban_id)
async def process_ban(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (uid,))
        await db.commit()
    BanCheckMiddleware._ban_cache[uid] = time.time()
    await state.clear()
    await m.answer(f"🚫 Игрок <b>{name}</b> (<code>{uid}</code>) забанен.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_unban")
async def adm_unban_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_unban_id)
    await safe_edit(c.message, "✅ Ответь на сообщение игрока, или напиши @юзернейм / ID для разбана:")
    await c.answer()


@dp.message(AdminStates.waiting_for_unban_id)
async def process_unban(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (uid,))
        await db.commit()
    BanCheckMiddleware._ban_cache.pop(uid, None)
    await state.clear()
    await m.answer(f"✅ Игрок <b>{name}</b> (<code>{uid}</code>) разбанен.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_wipe")
async def adm_wipe_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_wipe_id)
    await safe_edit(c.message, "🗑 Ответь на сообщение игрока, или напиши @юзернейм / ID для аннулирования:")
    await c.answer()


@dp.message(AdminStates.waiting_for_wipe_id)
async def process_wipe(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance=0, bbc_balance=0, rank=0, title='', vip_until='', coin_multiplier=1.0, "
            "winstreak=0, xp=0, level=1, daily_streak=0, last_streak_date='', rob_count=0, last_rob='', "
            "lucky_gacha=0, shield=0, last_daily='', last_gacha='' "
            "WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM user_cards WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM promo_used WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM achievements WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🗑 Аккаунт <b>{name}</b> (<code>{uid}</code>) полностью аннулирован.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_myth")
async def adm_myth_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_myth_id)
    await safe_edit(c.message, "🔱 Ответь на сообщение игрока, или напиши @юзернейм / ID для выдачи Мифрила:")
    await c.answer()


@dp.message(AdminStates.waiting_for_myth_id)
async def process_myth(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET rank = 7 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🔱 Игроку <b>{name}</b> (<code>{uid}</code>) выдан ранг Мифрил.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_p_demyth")
async def adm_demyth_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_demyth_id)
    await safe_edit(c.message, "⬇️ Ответь на сообщение игрока, или напиши @юзернейм / ID для снятия Мифрила:")
    await c.answer()


@dp.message(AdminStates.waiting_for_demyth_id)
async def process_demyth(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
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
    await m.answer(f"⬇️ Ранг Мифрил снят с <b>{name}</b> (<code>{uid}</code>).", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Economy
# =============================================================================
@dp.callback_query(F.data == "adm_econ")
async def adm_econ_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_econ_data)
    await safe_edit(c.message,
        "💰 <b>Управление экономикой</b>\n\n"
        "Ответь на сообщение: <code>+coins 500</code>\n"
        "Или: <code>+coins @юзер 500</code> / <code>+coins ID 500</code>\n\n"
        "Типы: <code>+coins</code> <code>-coins</code> <code>+bbc</code> <code>-bbc</code>")
    await c.answer()


@dp.message(AdminStates.waiting_for_econ_data)
async def process_econ(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    text = (m.text or "").strip()
    args = text.split()
    # Determine op (always first word)
    if not args or args[0] not in ("+coins", "-coins", "+bbc", "-bbc"):
        await state.clear()
        return await m.answer("❌ Начни с типа: +coins / -coins / +bbc / -bbc")
    op = args[0]
    rest_after_op = text[len(op):].strip()
    # If reply: rest_after_op = "AMOUNT"
    if m.reply_to_message and m.reply_to_message.from_user:
        ru = m.reply_to_message.from_user
        uid, name = ru.id, ru.full_name
        val = parse_positive_int(rest_after_op.split()[0] if rest_after_op.split() else "")
    else:
        # Parse user from rest_after_op
        # Create a fake context to reuse resolve_user logic inline
        inner_parts = rest_after_op.split(maxsplit=1)
        if not inner_parts:
            await state.clear()
            return await m.answer("❌ Укажи пользователя и сумму")
        # Check for @username or numeric ID
        token = inner_parts[0]
        amount_str = inner_parts[1] if len(inner_parts) > 1 else ""
        if token.startswith("@"):
            uname = token.lstrip("@")
            async with aiosqlite.connect(DB_PATH) as db2:
                cur2 = await db2.execute(
                    "SELECT user_id, nickname FROM users WHERE LOWER(username) = LOWER(?)", (uname,))
                row2 = await cur2.fetchone()
            if not row2:
                await state.clear()
                return await m.answer(f"❌ Игрок @{uname} не найден в базе!")
            uid, name = row2[0], row2[1] or f"@{uname}"
        else:
            uid = parse_positive_int(token)
            name = str(uid) if uid else None
            if not uid:
                await state.clear()
                return await m.answer("❌ Укажи @юзернейм или ID после типа операции")
        val = parse_positive_int(amount_str.split()[0] if amount_str.split() else "")
    if not val:
        await state.clear()
        return await m.answer("❌ Сумма — целое число > 0!")
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
        await db.commit()
    await state.clear()
    await m.answer(f"✅ <b>{name}</b> (<code>{uid}</code>): {action}", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Card rarity
# =============================================================================
@dp.callback_query(F.data == "adm_cards")
async def adm_cards_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только полный админ может изменять редкость карт!", show_alert=True)
    await state.set_state(AdminStates.waiting_for_card_rarity)
    await safe_edit(c.message, "🃏 <b>Изменение редкости карты</b>\n\nФормат: <code>ID_КАРТЫ НОВАЯ_РЕДКОСТЬ</code>\nПример: <code>5 3</code>")
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
    await m.answer(f"✅ Карта <b>{card[0]}</b> (#{cid}): редкость → {RARITY_STARS.get(rarity, '⭐')}", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Rig (full admin only)
# =============================================================================
@dp.callback_query(F.data == "adm_cards_limited")
async def adm_cards_limited_cb(c: CallbackQuery):
    if not await is_limited_admin(c.from_user.id):
        return await c.answer("❌ Нет доступа!", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить карту", callback_data="adm_card_add")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")],
    ])
    await safe_edit(c.message, "🃏 <b>Карты</b>\n\nДоступные действия:", kb)
    await c.answer()


@dp.callback_query(F.data == "adm_games")
async def adm_games_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только полный админ!", show_alert=True)
    await safe_edit(c.message, "🎰 <b>Игры & Управление</b>", admin_games_kb())
    await c.answer()


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


# =============================================================================
#  ADMIN: Lookup
# =============================================================================
@dp.callback_query(F.data == "adm_lookup")
async def adm_lookup_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_lookup_id)
    await safe_edit(c.message, "🔍 Ответь на сообщение игрока, или напиши @юзернейм / ID:")
    await c.answer()


@dp.message(AdminStates.waiting_for_lookup_id)
async def process_lookup(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT nickname, balance, bbc_balance, rank, title, "
            "is_banned, xp, level, daily_streak, shield, coin_multiplier, vip_until FROM users WHERE user_id = ?", (uid,))
        u = await cur.fetchone()
        if not u:
            await state.clear()
            return await m.answer("❌ Игрок не найден!")
        ccur = await db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (uid,))
        cards = (await ccur.fetchone())[0]
        acur = await db.execute("SELECT COUNT(*) FROM achievements WHERE user_id = ?", (uid,))
        achs = (await acur.fetchone())[0]
    await state.clear()
    text = (f"🔍 <b>Профиль игрока</b>\n\n🆔 ID: <code>{uid}</code>\n👤 Ник: {u[0]}\n"
            f"💰 Баланс: {u[1]:,}\n💵 BBC: {u[2]}\n🎖 Ранг: {RANK_NAMES.get(u[3], '?')}\n"
            f"📛 Титул: {u[4] or 'Нет'}\n📊 Уровень: {u[7]} ({u[6]} XP)\n"
            f"🔥 Стрик: {u[8]}\n🃏 Карт: {cards}\n"
            f"🏅 Достижений: {achs}\n🛡️ Щитов: {u[9]}\n💰 Множитель: x{u[10]}\n"
            f"🚫 Бан: {'Да' if u[5] else 'Нет'}")
    await m.answer(text, parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Broadcast
# =============================================================================
@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await safe_edit(c.message, "📢 Введи текст рассылки (HTML поддерживается):")
    await c.answer()


@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
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
        await asyncio.sleep(0.05)
    await state.clear()
    await m.answer(f"📢 Рассылка: ✅ {sent} | ❌ {failed}")


# =============================================================================
#  ADMIN: Set title
# =============================================================================
@dp.callback_query(F.data == "adm_set_title")
async def adm_set_title_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_set_title_id)
    await safe_edit(c.message,
        "📝 <b>Задать титул</b>\n\nФорматы:\n"
        "• Ответь на сообщение игрока + напиши <code>ТИТУЛ</code>\n"
        "• <code>@юзернейм ТИТУЛ</code>\n"
        "• <code>ID ТИТУЛ</code>\n"
        "Для удаления: <code>-</code> вместо титула")
    await c.answer()


@dp.message(AdminStates.waiting_for_set_title_id)
async def process_set_title(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, rest = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    if not rest:
        await state.clear()
        return await m.answer("❌ Укажи титул после пользователя (или - для удаления)")
    title = "" if rest.strip() == "-" else rest.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (title, uid))
        await db.commit()
    await state.clear()
    res = f"📝 Титул <b>{name}</b> → <b>{title}</b>" if title else f"📝 Титул <b>{name}</b> убран"
    await m.answer(res, parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Reset CD
# =============================================================================
@dp.callback_query(F.data == "adm_reset_cd")
async def adm_reset_cd_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_reset_cd_id)
    await safe_edit(c.message, "🔄 Ответь на сообщение игрока, или напиши @юзернейм / ID для сброса КД:")
    await c.answer()


@dp.message(AdminStates.waiting_for_reset_cd_id)
async def process_reset_cd(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_daily='', last_gacha='', last_rob='' WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🔄 Все КД сброшены для <b>{name}</b> (<code>{uid}</code>).", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Set level
# =============================================================================
@dp.callback_query(F.data == "adm_set_level")
async def adm_set_level_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_set_level_data)
    await safe_edit(c.message, "⚡ <b>Задать уровень</b>\n\nФорматы:\n"
        "• Ответь на сообщение игрока + <code>УРОВЕНЬ</code>\n"
        "• <code>@юзернейм УРОВЕНЬ</code>\n"
        "• <code>ID УРОВЕНЬ</code>")
    await c.answer()


@dp.message(AdminStates.waiting_for_set_level_data)
async def process_set_level(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, rest = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    lvl = parse_positive_int(rest.split()[0] if rest.split() else "")
    if not lvl:
        await state.clear()
        return await m.answer("❌ Укажи уровень (число > 0)")
    xp_needed = sum(xp_for_level(i) for i in range(1, lvl))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET level = ?, xp = ? WHERE user_id = ?", (lvl, xp_needed, uid))
        await db.commit()
    await state.clear()
    await m.answer(f"⚡ <b>{name}</b> (<code>{uid}</code>): уровень → {lvl} (XP: {xp_needed:,})", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Freeze / Unfreeze
# =============================================================================
@dp.callback_query(F.data == "adm_freeze")
async def adm_freeze_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_freeze_id)
    await safe_edit(c.message, "🥶 Ответь на сообщение игрока, или напиши @юзернейм / ID для заморозки:")
    await c.answer()


@dp.message(AdminStates.waiting_for_freeze_id)
async def process_freeze(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_frozen = 1 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"🥶 Игрок <b>{name}</b> (<code>{uid}</code>) заморожен.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_unfreeze")
async def adm_unfreeze_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_unfreeze_id)
    await safe_edit(c.message, "☀️ Ответь на сообщение игрока, или напиши @юзернейм / ID для разморозки:")
    await c.answer()


@dp.message(AdminStates.waiting_for_unfreeze_id)
async def process_unfreeze(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_frozen = 0 WHERE user_id = ?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"☀️ Игрок <b>{name}</b> (<code>{uid}</code>) разморожен.", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Set balance
# =============================================================================
@dp.callback_query(F.data == "adm_set_balance")
async def adm_set_balance_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_set_balance_data)
    await safe_edit(c.message,
        "💰 <b>Задать точный баланс</b>\n\nФорматы:\n"
        "• Ответь на сообщение + <code>coins/bbc СУММА</code>\n"
        "• <code>@юзернейм coins СУММА</code>\n"
        "• <code>ID coins СУММА</code>")
    await c.answer()


@dp.message(AdminStates.waiting_for_set_balance_data)
async def process_set_balance(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, rest = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    rargs = rest.split()
    if len(rargs) != 2 or rargs[0] not in ("coins", "bbc"):
        await state.clear()
        return await m.answer("❌ После пользователя укажи: <code>coins/bbc СУММА</code>", parse_mode=ParseMode.HTML)
    val = parse_positive_int(rargs[1])
    if val is None:
        await state.clear()
        return await m.answer("❌ Сумма — число > 0!")
    col = "balance" if rargs[0] == "coins" else "bbc_balance"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {col} = ? WHERE user_id = ?", (val, uid))
        await db.commit()
    await state.clear()
    await m.answer(f"💰 Баланс <b>{name}</b>: {rargs[0]} = {val:,}", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: Set nickname
# =============================================================================
@dp.callback_query(F.data == "adm_set_nickname")
async def adm_set_nickname_cb(c: CallbackQuery, state: FSMContext):
    if not await is_any_admin(c.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_nickname_data)
    await safe_edit(c.message, "✏️ <b>Сменить ник</b>\n\nФорматы:\n"
        "• Ответь на сообщение + новый ник\n"
        "• <code>@юзернейм НИК</code>\n"
        "• <code>ID НИК</code>")
    await c.answer()


@dp.message(AdminStates.waiting_for_nickname_data)
async def process_set_nickname(m: Message, state: FSMContext):
    if not await is_any_admin(m.from_user.id):
        return
    uid, name, rest = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    if not rest.strip():
        await state.clear()
        return await m.answer("❌ Укажи новый ник после пользователя")
    nick = rest.strip()[:50]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET nickname = ? WHERE user_id = ?", (nick, uid))
        await db.commit()
    await state.clear()
    await m.answer(f"✏️ Ник <b>{name}</b> (<code>{uid}</code>) → <b>{nick}</b>", parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: DB Backup / Rollback / Restore (FULL ADMIN ONLY)
# =============================================================================
DB_BACKUP_DIR = "db_backups"

def _ensure_backup_dir():
    os.makedirs(DB_BACKUP_DIR, exist_ok=True)

def _create_auto_backup(tag: str = "auto") -> str:
    import shutil
    _ensure_backup_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(DB_BACKUP_DIR, f"{ts}_{tag}.db")
    shutil.copy2(DB_PATH, backup_path)
    backups = sorted([f for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".db")], reverse=True)
    for old in backups[10:]:
        try:
            os.remove(os.path.join(DB_BACKUP_DIR, old))
        except OSError:
            pass
    return backup_path

def _get_latest_backup() -> str | None:
    _ensure_backup_dir()
    backups = sorted([f for f in os.listdir(DB_BACKUP_DIR) if f.endswith(".db")], reverse=True)
    return os.path.join(DB_BACKUP_DIR, backups[0]) if backups else None


@dp.callback_query(F.data == "adm_backup")
async def adm_backup_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только полный админ!", show_alert=True)
    backup_path = _create_auto_backup("manual")
    try:
        await bot.send_document(
            c.from_user.id,
            FSInputFile(backup_path, filename="bot_database.db"),
            caption=f"📦 Бэкап БД\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n💾 Сохранено бэкапов: {len(os.listdir(DB_BACKUP_DIR))}")
        await c.answer("📦 Бэкап отправлен в ЛС!", show_alert=True)
    except Exception as e:
        await c.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data == "adm_rollback")
async def adm_rollback_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только полный админ!", show_alert=True)
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
        f"🔄 <b>Откат БД</b>\n\nПоследний бэкап: <code>{backup_name}</code>\n\n"
        f"⚠️ Текущая БД будет заменена на бэкап.\nПеред откатом будет создана резервная копия текущей БД.\n\nВы уверены?",
        parse_mode=ParseMode.HTML, reply_markup=kb)


@dp.callback_query(F.data == "adm_rollback_confirm")
async def adm_rollback_confirm_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    latest = _get_latest_backup()
    if not latest:
        await c.answer("❌ Нет бэкапов!", show_alert=True)
        return
    _create_auto_backup("pre_rollback")
    shutil.copy2(latest, DB_PATH)
    await c.message.edit_text(
        f"✅ <b>БД успешно откачена!</b>\n\n📁 Восстановлено из: <code>{os.path.basename(latest)}</code>\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n💡 Перед откатом была создана резервная копия.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="adm_back")],
        ]))


@dp.callback_query(F.data == "adm_restore")
async def adm_restore_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только полный админ!", show_alert=True)
    await state.set_state(AdminStates.waiting_for_db_restore)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")]])
    await c.message.edit_text(
        "📥 <b>Восстановление БД</b>\n\nОтправьте мне файл базы данных <code>.db</code>\n\n"
        "⚠️ Текущая БД будет заменена на загруженный файл.\nПеред заменой будет создана автоматическая резервная копия.",
        parse_mode=ParseMode.HTML, reply_markup=kb)


@dp.message(AdminStates.waiting_for_db_restore, F.document)
async def adm_restore_file_handler(m: aiogram_types.Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    doc = m.document
    fname = doc.file_name or ""
    if not fname.endswith(".db"):
        await m.answer("❌ Файл должен иметь расширение <code>.db</code>\nОтправьте корректный файл базы данных.", parse_mode=ParseMode.HTML)
        return
    _create_auto_backup("pre_restore")
    tmp_path = DB_PATH + ".tmp_restore"
    try:
        await bot.download(doc, destination=tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.execute("SELECT name FROM sqlite_master LIMIT 1")
        conn.close()
    except Exception as e:
        await m.answer(f"❌ Файл повреждён или не является базой данных SQLite!\nОшибка: <code>{e}</code>", parse_mode=ParseMode.HTML)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return
    shutil.move(tmp_path, DB_PATH)
    await state.clear()
    await m.answer(
        f"✅ <b>БД успешно восстановлена!</b>\n\n📁 Загружен файл: <code>{fname}</code>\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n💾 Размер: {doc.file_size / 1024:.1f} КБ\n\n"
        f"💡 Резервная копия старой БД сохранена автоматически.", parse_mode=ParseMode.HTML)


@dp.message(AdminStates.waiting_for_db_restore)
async def adm_restore_not_file(m: aiogram_types.Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer("📥 Жду файл <code>.db</code>!\nОтправьте документ с базой данных, или нажмите Отмена.", parse_mode=ParseMode.HTML)


# =============================================================================
#  MARRY / PAIRS / DIVORCE
# =============================================================================
@dp.message(Command("marry"))
async def marry_cmd(m: Message):
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.answer("💍 Ответь на сообщение человека, которому хочешь предложить брак!")
    target = m.reply_to_message.from_user
    if target.id == m.from_user.id:
        return await m.answer("❌ Нельзя жениться на себе!")
    if target.is_bot:
        return await m.answer("❌ Нельзя жениться на боте!")
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        c1 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (m.from_user.id,))
        c2 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (target.id,))
        u1 = await c1.fetchone()
        u2 = await c2.fetchone()
        if not u1 or not u2:
            return await m.answer("❌ Оба должны быть зарегистрированы (/start)!")
        cur = await db.execute(
            "SELECT id FROM marriages WHERE (user1_id=? OR user2_id=? OR user1_id=? OR user2_id=?)",
            (m.from_user.id, m.from_user.id, target.id, target.id))
        if await cur.fetchone():
            return await m.answer("❌ Один из вас уже в браке! Сначала /divorce")
    p1, p2 = m.from_user.id, target.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💍 Принять", callback_data=f"marry_acc_{p1}_{p2}")],
        [InlineKeyboardButton(text="💔 Отклонить", callback_data=f"marry_dec_{p1}_{p2}")],
    ])
    await m.answer(
        f"💍 <b>{u1[0]}</b> предлагает <b>{u2[0]}</b> вступить в брак!\n\nТолько вызванный может ответить.",
        parse_mode=ParseMode.HTML, reply_markup=kb)


@dp.callback_query(F.data.startswith("marry_acc_"))
async def marry_accept_cb(c: CallbackQuery):
    parts = c.data.split("_")
    p1, p2 = int(parts[2]), int(parts[3])
    if c.from_user.id != p2:
        return await c.answer("❌ Это не тебе!", show_alert=True)
    chat_id = c.message.chat.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT id FROM marriages WHERE (user1_id=? OR user2_id=? OR user1_id=? OR user2_id=?)",
            (p1, p1, p2, p2))
        if await cur.fetchone():
            return await c.answer("❌ Кто-то из вас уже в браке!", show_alert=True)
        now_str = datetime.now().isoformat()
        pair = (min(p1, p2), max(p1, p2))
        await db.execute(
            "INSERT OR IGNORE INTO marriages (user1_id, user2_id, chat_id, married_at) VALUES (?,?,?,?)",
            (pair[0], pair[1], chat_id, now_str))
        await db.commit()
        c1 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (p1,))
        c2 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (p2,))
        n1 = (await c1.fetchone() or ("???",))[0]
        n2 = (await c2.fetchone() or ("???",))[0]
    await safe_edit(c.message, f"💍💒 <b>{n1}</b> и <b>{n2}</b> теперь в браке! 💕\n\nСовет да любовь! 🥂")
    async with aiosqlite.connect(DB_PATH) as db:
        await try_achievement(db, p1, "married")
        await try_achievement(db, p2, "married")
        await db.commit()
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
    uid = m.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute("SELECT id, user1_id, user2_id FROM marriages WHERE user1_id=? OR user2_id=?", (uid, uid))
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
    await m.answer(f"💔 <b>{my_name}</b> развёлся с <b>{partner_name}</b>.", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "menu_pairs")
async def menu_pairs_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute("SELECT user1_id, user2_id, married_at FROM marriages WHERE user1_id=? OR user2_id=?", (uid, uid))
        row = await cur.fetchone()
    if not row:
        text = "💑 <b>Пары</b>\n\nТы пока не в браке.\nИспользуй /marry (ответом на сообщение) чтобы предложить брак!"
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
    text = f"💑 <b>Твой брак</b>\n\n💍 <b>{my_name}</b> ❤️ <b>{partner_name}</b>\n📅 Вместе: <b>{duration}</b>\n\nЧтобы развестись: /divorce"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💑 Топ пар", callback_data="top_pairs")],
        [InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data == "top_pairs")
async def top_pairs_cb(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT m.user1_id, m.user2_id, m.married_at, COALESCE(u1.nickname, 'User' || m.user1_id), COALESCE(u2.nickname, 'User' || m.user2_id) FROM marriages m "
            "LEFT JOIN users u1 ON m.user1_id = u1.user_id LEFT JOIN users u2 ON m.user2_id = u2.user_id "
            "ORDER BY m.married_at ASC LIMIT 10")
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
    await safe_edit(c.message, "💑 <b>ТОП ПАР</b>\n\n" + "\n".join(lines_out), back_menu_kb())
    await c.answer()


# =============================================================================
#  ME ACTIONS (авто-определение)
# =============================================================================
async def _has_me_permission(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute("SELECT user_id FROM me_permissions WHERE user_id=?", (user_id,))
        return bool(await cur.fetchone())


@dp.message(lambda m: m.text and m.text.strip().lower() in ME_ACTIONS)
async def me_auto_cmd(m: Message):
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return
    if not await _has_me_permission(m.from_user.id):
        return
    target = m.reply_to_message.from_user
    if target.id == m.from_user.id:
        return
    matched_action = m.text.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        c1 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (m.from_user.id,))
        c2 = await db.execute("SELECT nickname FROM users WHERE user_id=?", (target.id,))
        n1 = (await c1.fetchone() or (m.from_user.full_name,))[0]
        n2 = (await c2.fetchone() or (target.full_name,))[0]
    link1 = f'<a href="tg://user?id={m.from_user.id}">{n1}</a>'
    link2 = f'<a href="tg://user?id={target.id}">{n2}</a>'
    action_text = ME_ACTIONS[matched_action]
    emoji = ME_ACTIONS_EMOJI.get(matched_action, "✨")
    if matched_action == "посмеялся":
        result = f"{emoji} {link1} посмеялся с {link2}"
    elif matched_action == "принудил":
        result = f"{emoji} {link1} принудил к интиму {link2}"
    else:
        result = f"{emoji} {link1} {action_text} {link2}"
    await m.answer(result, parse_mode=ParseMode.HTML)


# =============================================================================
#  ADMIN: /me permissions (full admin only)
# =============================================================================
@dp.callback_query(F.data == "adm_me_perms")
async def adm_me_perms_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только полный админ!", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        await db.execute("""CREATE TABLE IF NOT EXISTS me_permissions (
            user_id INTEGER PRIMARY KEY, granted_by INTEGER, granted_at TEXT DEFAULT '')""")
        await db.commit()
        cur = await db.execute(
            "SELECT mp.user_id, u.nickname FROM me_permissions mp LEFT JOIN users u ON mp.user_id = u.user_id")
        rows = await cur.fetchall()
    perm_list = "\n".join(f"  • {r[1] or '???'} (<code>{r[0]}</code>)" for r in rows) if rows else "  Нет разрешений"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выдать разрешение", callback_data="adm_me_grant")],
        [InlineKeyboardButton(text="❌ Забрать разрешение", callback_data="adm_me_revoke")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")],
    ])
    await safe_edit(c.message, f"💬 <b>/me Разрешения</b>\n\nПользователи с доступом к /me:\n{perm_list}", kb)
    await c.answer()


@dp.callback_query(F.data == "adm_me_grant")
async def adm_me_grant_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminMeStates.waiting_for_me_grant)
    await safe_edit(c.message, "✅ Ответь на сообщение, или напиши @юзернейм / ID для выдачи /me:")
    await c.answer()


@dp.message(AdminMeStates.waiting_for_me_grant)
async def process_me_grant(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT nickname FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row:
            await state.clear()
            return await m.answer("❌ Игрок не найден в базе!")
        await db.execute("INSERT OR REPLACE INTO me_permissions (user_id, granted_by, granted_at) VALUES (?,?,?)",
                         (uid, ADMIN_ID, datetime.now().isoformat()))
        await db.commit()
    await state.clear()
    await m.answer(f"✅ Разрешение /me выдано игроку <b>{name}</b> (<code>{uid}</code>)", parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "adm_me_revoke")
async def adm_me_revoke_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminMeStates.waiting_for_me_revoke)
    await safe_edit(c.message, "❌ Ответь на сообщение, или напиши @юзернейм / ID для отзыва /me:")
    await c.answer()


@dp.message(AdminMeStates.waiting_for_me_revoke)
async def process_me_revoke(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    uid, name, _ = await resolve_user(m)
    if not uid:
        await state.clear()
        return await m.answer(name)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM me_permissions WHERE user_id=?", (uid,))
        if not await cur.fetchone():
            await state.clear()
            return await m.answer("❌ У этого игрока нет разрешения /me!")
        await db.execute("DELETE FROM me_permissions WHERE user_id=?", (uid,))
        await db.commit()
    await state.clear()
    await m.answer(f"❌ Разрешение /me отозвано у <b>{name}</b> (<code>{uid}</code>)", parse_mode=ParseMode.HTML)


# =============================================================================
#  CARDS MENU
# =============================================================================
@dp.callback_query(F.data == "menu_cards")
async def menu_cards_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, c.rarity, COUNT(*) FROM user_cards uc "
            "JOIN cards c ON uc.card_id = c.card_id "
            "WHERE uc.user_id = ? GROUP BY c.card_id ORDER BY c.rarity DESC LIMIT 30", (uid,))
        cards = await cur.fetchall()
    if not cards:
        text = "🃏 <b>Твоя коллекция</b>\n\n😕 У тебя пока нет карт.\nИспользуй 🎴 Гачу чтобы получить!"
    else:
        text = "🃏 <b>Твоя коллекция</b>\n\n"
        for name, rarity, cnt in cards:
            text += f"{RARITY_STARS.get(rarity, '⭐')} <b>{name}</b> x{cnt}\n"
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
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT card_id, name, rarity FROM cards ORDER BY rarity DESC, card_id")
        cards = await cur.fetchall()
    if not cards:
        await safe_edit(c.message, "🃏 База карт пуста.", back_menu_kb())
        return await c.answer()
    total = len(cards)
    per_page = CARDS_PER_PAGE
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


# =============================================================================
#  PROMO MENU
# =============================================================================
@dp.callback_query(F.data == "menu_promo")
async def menu_promo_cb(c: CallbackQuery):
    text = ("🎟️ <b>Промокод</b>\n\nЧтобы активировать промокод, напиши:\n<code>/promo КОД</code>\n\n"
            "💡 <i>Промокоды раздаются в группе и каналах!</i>")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Меню", callback_data="menu_back")]])
    await safe_edit(c.message, text, kb)
    await c.answer()


# =============================================================================
#  SLOTS
# =============================================================================
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


@dp.callback_query(F.data == "game_slots")
async def game_slots_cb(c: CallbackQuery):
    uid = c.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if not row:
            return await c.answer("❌ /start", show_alert=True)
        balance = row[0]
    text = f"🎰 <b>Слоты</b>\n\n💰 Баланс: <b>{balance:,}</b>\n\nВыбери ставку:"
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
                await try_achievement(db, uid, "jackpot_slots")
            else:
                result = f"🎉 <b>Выигрыш x{mult}! +{profit:,} 💰</b>"
        else:
            result = f"💸 <b>Проигрыш! -{bet:,} 💰</b>"
        await db.commit()
        cur2 = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        new_bal = (await cur2.fetchone())[0]
    reel_str = " │ ".join(reels)
    text = (f"🎰 <b>Слоты</b> | Ставка: {bet:,}💰\n\n┌─────────────┐\n│  {reel_str}  │\n└─────────────┘\n\n"
            f"{result}\n💰 Баланс: <b>{new_bal:,}</b>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔄 Ещё ({bet:,})", callback_data=f"slots_bet:{bet_str}")],
        [InlineKeyboardButton(text="💰 Сменить ставку", callback_data="game_slots")],
        [InlineKeyboardButton(text="🔙 Игры", callback_data="menu_games")],
    ])
    await safe_edit(c.message, text, kb)
    await c.answer()


# =============================================================================
#  MAIN
# =============================================================================
async def health_server():
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

    # Автоматически удаляем карты без картинок при запуске
    async with aiosqlite.connect(DB_PATH) as _db:
        _cur = await _db.execute(
            "SELECT card_id FROM cards WHERE image_id IS NULL OR TRIM(image_id) = '' "
            "OR TRIM(image_id) IN ('None', 'null', '0')")
        _bad = await _cur.fetchall()
        if _bad:
            _ids = [r[0] for r in _bad]
            await _db.execute(f"DELETE FROM user_cards WHERE card_id IN ({','.join('?'*len(_ids))})", _ids)
            await _db.execute(f"DELETE FROM cards WHERE card_id IN ({','.join('?'*len(_ids))})", _ids)
            await _db.commit()
            log.info(f"🧹 Автоочистка: удалено {len(_ids)} карт без картинки")

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot started!")
    await asyncio.gather(health_server(), dp.start_polling(bot))



# =============================================================================
#  УПРАВЛЕНИЕ АДМИНАМИ (только ADMIN_ID)
# =============================================================================

@dp.callback_query(F.data == "adm_manage_admins")
async def adm_manage_admins_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только главный админ!", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute(
            "SELECT la.user_id, u.nickname, la.is_full FROM limited_admins la "
            "LEFT JOIN users u ON la.user_id = u.user_id ORDER BY la.is_full DESC, u.nickname"
        )
        admins = await cur.fetchall()
    if not admins:
        text = "👤 <b>Управление Админами</b>\n\nАдминов пока нет."
    else:
        lines = []
        for uid, nick, is_full in admins:
            badge = "⭐ Полный" if is_full else "🔧 Ограниченный"
            lines.append(f"  {badge} | {nick or '???'} (<code>{uid}</code>)")
        text = "👤 <b>Управление Админами</b>\n\n" + "\n".join(lines) + "\n\n<i>⬆️ — повысить до полного | ⬇️ — снизить | 🗑 — удалить</i>"

    buttons = []
    for uid, nick, is_full in (admins or []):
        name = nick or str(uid)
        row_top = []
        if is_full:
            row_top.append(InlineKeyboardButton(
                text=f"⬇️ Понизить {name}",
                callback_data=f"adm_demote_{uid}"
            ))
        else:
            row_top.append(InlineKeyboardButton(
                text=f"⬆️ Повысить {name}",
                callback_data=f"adm_promote_{uid}"
            ))
        row_top.append(InlineKeyboardButton(
            text=f"🗑 Снять {name}",
            callback_data=f"adm_remove_admin_{uid}"
        ))
        buttons.append(row_top)
    buttons.append([InlineKeyboardButton(text="➕ Добавить админа", callback_data="adm_add_admin_start")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await safe_edit(c.message, text, kb)
    await c.answer()


@dp.callback_query(F.data.startswith("adm_promote_"))
async def adm_promote_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только главный админ!", show_alert=True)
    try:
        target_id = int(c.data.split("_")[2])
    except (IndexError, ValueError):
        return await c.answer("❌ Ошибка!", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        await db.execute("UPDATE limited_admins SET is_full = 1 WHERE user_id = ?", (target_id,))
        await db.commit()
    await c.answer("✅ Повышен до полного админа!", show_alert=True)
    await adm_manage_admins_cb(c)


@dp.callback_query(F.data.startswith("adm_demote_"))
async def adm_demote_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только главный админ!", show_alert=True)
    try:
        target_id = int(c.data.split("_")[2])
    except (IndexError, ValueError):
        return await c.answer("❌ Ошибка!", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        await db.execute("UPDATE limited_admins SET is_full = 0 WHERE user_id = ?", (target_id,))
        await db.commit()
    await c.answer("✅ Понижен до ограниченного!", show_alert=True)
    await adm_manage_admins_cb(c)


@dp.callback_query(F.data.startswith("adm_remove_admin_"))
async def adm_remove_admin_cb(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только главный админ!", show_alert=True)
    try:
        target_id = int(c.data.split("_")[3])
    except (IndexError, ValueError):
        return await c.answer("❌ Ошибка при разборе ID!", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        # Получаем ник перед удалением
        nick_cur = await db.execute(
            "SELECT u.nickname FROM limited_admins la LEFT JOIN users u ON la.user_id = u.user_id WHERE la.user_id = ?",
            (target_id,)
        )
        nick_row = await nick_cur.fetchone()
        nick = nick_row[0] if nick_row and nick_row[0] else str(target_id)
        cur = await db.execute("DELETE FROM limited_admins WHERE user_id = ?", (target_id,))
        await db.commit()
        deleted = cur.rowcount
    if deleted:
        await c.answer(f"✅ {nick} снят с должности админа!", show_alert=True)
    else:
        await c.answer("❌ Такой админ не найден!", show_alert=True)
    await adm_manage_admins_cb(c)


class AdminManageStates(StatesGroup):
    waiting_for_add_admin_id = State()


@dp.callback_query(F.data == "adm_add_admin_start")
async def adm_add_admin_start_cb(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("❌ Только главный админ!", show_alert=True)
    await state.set_state(AdminManageStates.waiting_for_add_admin_id)
    await safe_edit(c.message, "➕ <b>Добавить ограниченного админа</b>\n\nОтветь на сообщение игрока, или напиши @юзернейм / ID:")
    await c.answer()


@dp.message(AdminManageStates.waiting_for_add_admin_id)
async def process_add_admin_id(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return
    await state.clear()
    uid, name, _ = await resolve_user(m)
    if not uid:
        return await m.answer(name)
    if uid == ADMIN_ID:
        return await m.answer("❌ Ты и так главный админ!")
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_social_tables(db)
        cur = await db.execute("SELECT user_id FROM limited_admins WHERE user_id = ?", (uid,))
        if await cur.fetchone():
            return await m.answer(f"⚠️ <b>{name}</b> (<code>{uid}</code>) уже является ограниченным админом.", parse_mode=ParseMode.HTML)
        await db.execute(
            "INSERT INTO limited_admins (user_id, added_by, added_at, is_full) VALUES (?, ?, ?, 0)",
            (uid, ADMIN_ID, datetime.now().isoformat())
        )
        await db.commit()
    await m.answer(f"✅ <b>{name}</b> (<code>{uid}</code>) добавлен как ограниченный админ.", parse_mode=ParseMode.HTML)

if __name__ == "__main__":
    asyncio.run(main())
