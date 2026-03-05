import asyncio
import logging
import random
import os
import aiosqlite
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA"
ADMIN_ID = 1548461377 
DB_PATH = "/app/data/gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- КЛАВИАТУРА ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🃏 Получить карту"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🏪 Магазин")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

# --- МЕНЮ КОМАНД ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="promo", description="🎁 Ввести промокод"),
        BotCommand(command="help", description="📖 Инструкция"),
        BotCommand(command="adminhelp", description="🛠 Админ-панель")
    ]
    await bot.set_my_commands(commands)

# --- БАЗА ДАННЫХ ---
async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, bbc_money INTEGER DEFAULT 0, last_draw TEXT, 
            titles TEXT DEFAULT 'Новичок', unlocked_titles TEXT DEFAULT 'Новичок')''')
        
        # Обновление старой таблицы, если нужно
        try:
            await db.execute("ALTER TABLE users ADD COLUMN bbc_money INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE users ADD COLUMN unlocked_titles TEXT DEFAULT 'Новичок'")
        except sqlite3.OperationalError:
            pass # Колонки уже существуют

        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, reward_type TEXT, reward_val INTEGER, uses_left INTEGER, expires_at TEXT)''')
        await db.commit()

# --- ЛОГИКА ШАНСОВ И НАГРАД ---
def get_rarity(rank, titles):
    r = random.uniform(0, 100)
    # Премиум-титулы дают +2% к 5⭐ (Мифик)
    premium_bonus = 2 if any(t in titles for t in ["Элита", "Легенда", "главный кисер"]) else 0
    
    if rank == "Мифрил":
        if r <= (15 + premium_bonus): return 5
        if r <= 35: return 4
        if r <= 60: return 3
        if r <= 90: return 2
        return 1
    
    bonus = 5 if rank == "Серебро" else 0
    if r <= (1 + bonus * 0.25 + premium_bonus): return 5 
    if r <= (4 + bonus * 0.5): return 4
    if r <= (10 + bonus * 1.0): return 3
    if r <= (30 + bonus * 1.5): return 2
    return 1

REWARDS = {
    1: {"new": 100, "dup": 50},
    2: {"new": 150, "dup": 75},
    3: {"new": 250, "dup": 100},
    4: {"new": 500, "dup": 250},
    5: {"new": 1000, "dup": 700}
}

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        default_title = "главный кисер" if m.from_user.id == ADMIN_ID else "Новичок"
        
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank, titles, unlocked_titles) VALUES (?, ?, ?, ?, ?)", 
                         (m.from_user.id, m.from_user.first_name, user_rank, default_title, default_title))
        await db.commit()
    await profile(m, bot)

@dp.message(F.text == "👤 Профиль")
@dp.message(Command("profile"))
async def profile(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, bbc_money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
        res = await db.execute("SELECT COUNT(*) FROM cards")
        total = (await res.fetchone())[0]
    
    profile_text = (
        f"<b>✨ ЛИЧНОЕ ДОСЬЕ ✨</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Игрок:</b> {u[0]}\n"
        f"🏅 <b>Ранг:</b> <code>{u[1]}</code>\n"
        f"🏷 <b>Титул:</b> <i>{u[4]}</i>\n"
        f"💰 <b>Монеты:</b> {u[2]}\n"
        f"💎 <b>BBC Валюта:</b> {u[3]}\n"
        f"🎴 <b>Коллекция:</b> {inv_cnt} / {total}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    try:
        photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
        if photos.total_count > 0:
            await m.answer_photo(photos.photos[0][-1].file_id, caption=profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
        else:
            await m.answer(profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
    except:
        await m.answer(profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(F.text == "🎒 Инвентарь")
async def inventory_cmd(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute('''
            SELECT c.name, c.rarity, i.count 
            FROM inventory i JOIN cards c ON i.card_id = c.card_id 
            WHERE i.user_id = ? ORDER BY c.rarity DESC, i.count DESC LIMIT 30
        ''', (m.from_user.id,))
        cards = await res.fetchall()
        
    if not cards:
        return await m.answer("🎒 Твой инвентарь пока пуст. Тяни карты!")
    
    text = "🎒 <b>ТВОИ КАРТЫ:</b>\n━━━━━━━━━━━━━━\n"
    for name, rar, count in cards:
        text += f"{rar}⭐ | {name} (x{count})\n"
    
    if len(cards) == 30: text += "...\n<i>Показаны первые 30 карт.</i>"
    await m.answer(text, parse_mode=ParseMode.HTML)

@dp.message(F.text.lower().in_(["🃏 получить карту", "карта", "карту"]))
async def draw(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        rank, last_draw, titles = u
        cd = timedelta(hours=24) if rank != "Мифрил" else timedelta(seconds=10)
        now = datetime.now()
        
        if last_draw and now < datetime.fromisoformat(last_draw) + cd:
            rem = (datetime.fromisoformat(last_draw) + cd) - now
            return await m.answer(f"⏳ <b>Отдых!</b>\nПодожди ещё: <code>{str(rem).split('.')[0]}</code>", parse_mode=ParseMode.HTML)
        
        rarity = get_rarity(rank, titles)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer("⚠️ База карт нужной редкости пуста!")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        
        is_dup = await res.fetchone()
        reward = REWARDS[rarity]["dup"] if is_dup else REWARDS[rarity]["new"]
        
        if is_dup:
            await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
            cap = (
                f"♻️ <b>ПОВТОРКА!</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"🏷 <b>Название:</b> {c_name}\n"
                f"✨ <b>Редкость:</b> {rarity}⭐\n"
                f"💰 <b>Награда:</b> +{reward} монет"
            )
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, c_id))
            cap = (
                f"🎉 <b>НОВАЯ КАРТА!</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"🏷 <b>Название:</b> {c_name}\n"
                f"✨ <b>Редкость:</b> {rarity}⭐\n"
                f"💰 <b>Бонус за находку:</b> +{reward} монет"
            )
        
        await db.execute("UPDATE users SET money = money + ?, last_draw = ? WHERE user_id = ?", (reward, now.isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap, parse_mode=ParseMode.HTML)

# --- МАГАЗИН И ТОПЫ (ИНЛАЙН) ---

@dp.message(F.text == "🏪 Магазин")
async def shop_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Обычные титулы (Монеты)", callback_data="shop_normal")],
        [InlineKeyboardButton(text="💎 Премиум титулы (BBC)", callback_data="shop_premium")]
    ])
    await m.answer("🏪 <b>Добро пожаловать в магазин!</b>\nВыбери категорию:", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("shop_"))
async def shop_callback(c: CallbackQuery):
    cat = c.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    if cat == "normal":
        text = "🛒 <b>Обычные титулы</b> (Покупка за монеты):\n<i>Обычные титулы созданы для красоты.</i>"
        items = [("Продвинутый", 2000), ("мяу", 3500), ("фембой", 5000)]
        for name, price in items:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"{name} - {price} 💰", callback_data=f"buy_title_{name}_{price}_money")])
    else:
        text = "💎 <b>Премиум титулы</b> (Покупка за BBC):\n<i>Дают +2% шанса на выпадение 5⭐ карт!</i>"
        items = [("Элита", 50), ("Легенда", 150)] # Добавил примеры премиум титулов
        for name, price in items:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"{name} - {price} 💎", callback_data=f"buy_title_{name}_{price}_bbc")])
            
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_main")])
    await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "shop_main")
async def shop_main_callback(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Обычные титулы (Монеты)", callback_data="shop_normal")],
        [InlineKeyboardButton(text="💎 Премиум титулы (BBC)", callback_data="shop_premium")]
    ])
    await c.message.edit_text("🏪 <b>Добро пожаловать в магазин!</b>\nВыбери категорию:", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("buy_title_"))
async def buy_title(c: CallbackQuery):
    _, _, name, price, currency = c.data.split("_")
    price = int(price)
    
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT money, bbc_money, unlocked_titles FROM users WHERE user_id = ?", (c.from_user.id,))
        u = await res.fetchone()
        if not u: return
        money, bbc, unlocked = u
        
        if name in unlocked:
            return await c.answer("У тебя уже есть этот титул!", show_alert=True)
            
        if currency == "money":
            if money < price: return await c.answer("Недостаточно монет!", show_alert=True)
            await db.execute("UPDATE users SET money = money - ?, unlocked_titles = unlocked_titles || ?, titles = ? WHERE user_id = ?", 
                             (price, f", {name}", name, c.from_user.id))
        else:
            if bbc < price: return await c.answer("Недостаточно BBC валюты!", show_alert=True)
            await db.execute("UPDATE users SET bbc_money = bbc_money - ?, unlocked_titles = unlocked_titles || ?, titles = ? WHERE user_id = ?", 
                             (price, f", {name}", name, c.from_user.id))
        await db.commit()
    await c.answer(f"✅ Успешно куплен и установлен титул: {name}", show_alert=True)

@dp.message(F.text == "🏆 Топ")
async def top_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎴 По картам", callback_data="top_cards"),
         InlineKeyboardButton(text="💰 По монетам", callback_data="top_money")],
        [InlineKeyboardButton(text="💎 По BBC", callback_data="top_bbc")]
    ])
    await m.answer("🏆 <b>Выбери таблицу лидеров:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("top_"))
async def top_callback(c: CallbackQuery):
    cat = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        if cat == "cards":
            res = await db.execute('''SELECT u.nickname, COUNT(i.card_id) as cnt 
                                      FROM users u JOIN inventory i ON u.user_id = i.user_id 
                                      GROUP BY u.user_id ORDER BY cnt DESC LIMIT 10''')
            title = "🎴 ТОП ПО КАРТАМ"
            suffix = "карт"
        elif cat == "money":
            res = await db.execute("SELECT nickname, money FROM users ORDER BY money DESC LIMIT 10")
            title = "💰 ТОП ПО МОНЕТАМ"
            suffix = "монет"
        else:
            res = await db.execute("SELECT nickname, bbc_money FROM users ORDER BY bbc_money DESC LIMIT 10")
            title = "💎 ТОП ПО BBC ВАЛЮТЕ"
            suffix = "BBC"
            
        data = await res.fetchall()
        
    text = f"<b>{title}</b>\n━━━━━━━━━━━━━━\n"
    for i, (name, val) in enumerate(data, 1):
        text += f"<b>{i}.</b> {name} — {val} {suffix}\n"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="top_main")]])
    await c.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "top_main")
async def top_main_callback(c: CallbackQuery):
    await top_cmd(c.message)
    await c.message.delete()

# --- ПРОМОКОДЫ ---

@dp.message(Command("promo"))
async def activate_promo(m: Message):
    args = m.text.split()
    if len(args) < 2: return await m.answer("⚠️ Использование: `/promo КОД`", parse_mode=ParseMode.MARKDOWN)
    code = args[1]
    
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT reward_type, reward_val, uses_left, expires_at FROM promocodes WHERE code = ?", (code,))
        promo = await res.fetchone()
        
        if not promo: return await m.answer("❌ Промокод не найден!")
        r_type, r_val, uses, exp = promo
        
        if uses <= 0: return await m.answer("❌ Лимит активаций исчерпан!")
        if datetime.fromisoformat(exp) < datetime.now(): return await m.answer("❌ Срок действия истек!")
        
        if r_type == "cash":
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (r_val, m.from_user.id))
            text = f"✅ Активировано! Получено {r_val} монет."
        elif r_type == "bbc":
            await db.execute("UPDATE users SET bbc_money = bbc_money + ? WHERE user_id = ?", (r_val, m.from_user.id))
            text = f"✅ Активировано! Получено {r_val} BBC."
        elif r_type == "card":
            res = await db.execute("SELECT name FROM cards WHERE card_id = ?", (r_val,))
            card = await res.fetchone()
            if not card: return await m.answer("❌ Ошибка выдачи карты.")
            await db.execute("INSERT OR IGNORE INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, r_val))
            text = f"✅ Активировано! Получена карта: {card[0]}."

        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        await db.commit()
    await m.answer(text)

# --- АДМИН ПАНЕЛЬ ---

@dp.message(Command("adminhelp"))
async def admin_help(m: Message):
    if m.from_user.id != ADMIN_ID: return
    admin_text = (
        "🛠 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "<code>/add_card Имя Редкость</code> - добавить карту (в подписи к фото)\n"
        "<code>/id_card [имя]</code> - узнать ID карты (или всех)\n"
        "<code>/add_cash ID сумма</code> - выдать монеты\n"
        "<code>/add_bbc ID сумма</code> - выдать BBC\n"
        "<code>/give_card ID CardID</code> - выдать карту\n"
        "<code>/create_promo код ТИП знач лимит дни</code>\n"
        "<i>ТИП: cash, bbc, card (знач = ID карты)</i>"
    )
    await m.answer(admin_text, parse_mode=ParseMode.HTML)

@dp.message(Command("id_card"))
async def id_card_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    args = m.text.split(maxsplit=1)
    
    async with aiosqlite.connect(DB_PATH) as db:
        if len(args) > 1:
            name = f"%{args[1]}%"
            res = await db.execute("SELECT card_id, name, rarity FROM cards WHERE name LIKE ?", (name,))
        else:
            res = await db.execute("SELECT card_id, name, rarity FROM cards")
        cards = await res.fetchall()
        
    if not cards: return await m.answer("❌ Карты не найдены.")
    
    text = "🎴 <b>Список карт:</b>\n"
    for c_id, name, rar in cards:
        text += f"ID: <code>{c_id}</code> | {name} ({rar}⭐)\n"
        if len(text) > 3500:
            text += "... (список обрезан)"
            break
    await m.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("add_cash"))
async def add_cash_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        _, u_id, amount = m.text.split()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (int(amount), int(u_id)))
            await db.commit()
        await m.answer(f"✅ Выдано {amount} монет пользователю {u_id}.")
    except:
        await m.answer("❌ Ошибка! Формат: /add_cash ID сумма")

@dp.message(Command("add_bbc"))
async def add_bbc_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        _, u_id, amount = m.text.split()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET bbc_money = bbc_money + ? WHERE user_id = ?", (int(amount), int(u_id)))
            await db.commit()
        await m.answer(f"✅ Выдано {amount} BBC пользователю {u_id}.")
    except:
        await m.answer("❌ Ошибка! Формат: /add_bbc ID сумма")

@dp.message(Command("give_card"))
async def give_card_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        _, u_id, c_id = m.text.split()
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем есть ли уже
            res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (int(u_id), int(c_id)))
            if await res.fetchone():
                await db.execute("UPDATE inventory SET count = count + 1 WHERE user_id = ? AND card_id = ?", (int(u_id), int(c_id)))
            else:
                await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (int(u_id), int(c_id)))
            await db.commit()
        await m.answer(f"✅ Карта ID {c_id} выдана пользователю {u_id}.")
    except:
        await m.answer("❌ Ошибка! Формат: /give_card ID_юзера ID_карты")

@dp.message(Command("create_promo"))
async def create_promo_cmd(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        args = m.text.split()
        code, r_type, r_val, uses, days = args[1], args[2], int(args[3]), int(args[4]), int(args[5])
        exp_date = (datetime.now() + timedelta(days=days)).isoformat()
        
        if r_type not in ["cash", "bbc", "card"]: raise ValueError
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO promocodes VALUES (?, ?, ?, ?, ?)", 
                             (code, r_type, r_val, uses, exp_date))
            await db.commit()
            await m.answer(f"✅ Карта <b>{name}</b> ({rarity}⭐) добавлена!", parse_mode=ParseMode.HTML)
    except:
        await m.answer("❌ Ошибка! Формат подписи к фото: <code>/add_card Имя 5</code>", parse_mode=ParseMode.HTML)

@dp.message(F.text == "❓ Помощь")
@dp.message(Command("help"))
async def help_cmd(m: Message):
    help_text = (
        "📖 <b>ИНСТРУКЦИЯ</b>\n\n"
        "🃏 <b>Получить карту</b> — тяни карточки (раз в сутки / 10 сек для Админа).\n"
        "🎒 <b>Инвентарь</b> — просмотр всех выбитых карт.\n"
        "🏪 <b>Магазин</b> — покупка титулов за Монеты и BBC (премиум титулы дают +2% к 5⭐).\n"
        "🏆 <b>Топ</b> — соревнуйся с другими игроками.\n\n"
        "🎁 Ввод промокодов: <code>/promo КОД</code>"
    )
    await m.answer(help_text, parse_mode=ParseMode.HTML)

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
