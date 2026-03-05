import asyncio
import logging
import random
import os
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
TOKEN = "8666119275:AAEBl4VeUTKGzj-WVrrb8asakNfgIqlqOQA" # Твой токен тут
ADMIN_ID = 1548461377 
DB_PATH = "/app/data/gacha_bot.db"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- КЛАВИАТУРА ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🃏 Получить карту"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

# --- МЕНЮ КОМАНД ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню / Профиль"),
        BotCommand(command="profile", description="👤 Мой профиль"),
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
            money INTEGER DEFAULT 0, last_draw TEXT, titles TEXT DEFAULT 'Новичок')''')
        await db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, PRIMARY KEY (user_id, card_id))''')
        await db.commit()

# --- ЛОГИКА ШАНСОВ ---
def get_rarity(rank):
    r = random.uniform(0, 100)
    if rank == "Мифрил":
        if r <= 15: return 5
        if r <= 35: return 4
        if r <= 60: return 3
        if r <= 90: return 2
        return 1
    bonus = 5 if rank == "Серебро" else 0
    if r <= (1 + bonus * 0.25): return 5 
    if r <= (4 + bonus * 0.5): return 4
    if r <= (10 + bonus * 1.0): return 3
    if r <= (30 + bonus * 1.5): return 2
    return 1

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?, ?, ?)", 
                         (m.from_user.id, m.from_user.first_name, user_rank))
        await db.commit()
    # Сразу вызываем профиль после регистрации
    await profile(m, bot)

@dp.message(F.text == "👤 Профиль")
@dp.message(Command("profile"))
async def profile(m: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
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
        f"🏷 <b>Титул:</b> <i>{u[3]}</i>\n"
        f"💰 <b>Валюта:</b> {u[2]} монеток\n"
        f"🎴 <b>Коллекция:</b> {inv_cnt} / {total}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Используй меню ниже, чтобы собрать все карты!</i>"
    )

    # Получаем фото профиля
    photos = await bot.get_user_profile_photos(m.from_user.id, limit=1)
    if photos.total_count > 0:
        await m.answer_photo(photos.photos[0][-1].file_id, caption=profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
    else:
        await m.answer(profile_text, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(F.text.lower().in_(["🃏 получить карту", "карта", "карту", "нев", "невер"]))
async def draw(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        rank, last_draw = u
        cd = timedelta(hours=24) if rank != "Мифрил" else timedelta(seconds=10)
        now = datetime.now()
        
        if last_draw and now < datetime.fromisoformat(last_draw) + cd:
            rem = (datetime.fromisoformat(last_draw) + cd) - now
            return await m.answer(f"⏳ <b>Отдых!</b>\nПодожди ещё: <code>{str(rem).split('.')[0]}</code>", parse_mode=ParseMode.HTML)
        
        rarity = get_rarity(rank)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer("⚠️ База карт пуста!")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        
        if await res.fetchone():
            bonus = rarity * 20
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bonus, m.from_user.id))
            cap = f"🃏 <b>Повторка:</b> {c_name}\n💎 Редкость: {rarity}⭐\n💰 <b>Компенсация:</b> +{bonus} монет"
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, c_id))
            cap = f"🎉 <b>НОВАЯ КАРТА!</b>\n┃ 🏷 <b>Название:</b> {c_name}\n┃ ✨ <b>Редкость:</b> {rarity}⭐"
        
        await db.execute("UPDATE users SET last_draw = ? WHERE user_id = ?", (now.isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap, parse_mode=ParseMode.HTML)

@dp.message(F.text == "❓ Помощь")
@dp.message(Command("help"))
async def help_cmd(m: Message):
    help_text = (
        "📖 <b>КАК ИГРАТЬ?</b>\n\n"
        "1️⃣ Нажимай кнопку <b>'Получить карту'</b>.\n"
        "2️⃣ Коллекционируй уникальных персонажей.\n"
        "3️⃣ За дубликаты ты получаешь монеты.\n"
        "4️⃣ Ранг 'Серебро' и выше дает бонусы к удаче!\n\n"
        "📌 <i>Все команды доступны через кнопку '/' рядом с клавиатурой.</i>"
    )
    await m.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message(Command("adminhelp"))
async def admin_help(m: Message):
    if m.from_user.id != ADMIN_ID: return
    admin_text = (
        "🛠 <b>ПАНЕЛЬ УПРАВЛЕНИЯ</b>\n\n"
        "🖼 <b>Добавить карту:</b>\n"
        "Отправь фото с подписью:\n"
        "<code>/add_card Название_карты Редкость</code>\n"
        "<i>(Редкость: от 1 до 5)</i>\n\n"
        "👤 <b>Твой статус:</b> Админ (Мифрил)\n"
        "⏱ <b>Кулдаун:</b> 10 секунд"
    )
    await m.answer(admin_text, parse_mode=ParseMode.HTML)

@dp.message(F.photo)
async def add_card_photo(m: Message):
    if m.from_user.id != ADMIN_ID or not m.caption or not m.caption.startswith("/add_card"): return
    try:
        args = m.caption.split()
        rarity = int(args[-1])
        name = " ".join(args[1:-1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?, ?, ?)", (name, rarity, m.photo[-1].file_id))
            await db.commit()
        await m.answer(f"✅ <b>Карта добавлена!</b>\n{name} ({rarity}⭐)", parse_mode=ParseMode.HTML)
    except:
        await m.answer("❌ Ошибка! Формат: <code>/add_card Имя 5</code> + фото")

# --- ЗАПУСК ---
async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    await set_commands(bot) # Добавляет меню команд при нажатии на "/"
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    ]
    await bot.set_my_commands(commands)

# --- СЛОЙ РАБОТЫ С ДАННЫМИ ---
class Database:
    def __init__(self, path):
        self.path = path
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.db = await aiosqlite.connect(self.path)
        await self.db.execute("PRAGMA foreign_keys = ON")
        await self.db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, nickname TEXT, rank TEXT DEFAULT 'Бронза',
            money INTEGER DEFAULT 0, last_draw TEXT, titles TEXT DEFAULT 'Новичок')''')
        await self.db.execute('''CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, rarity INTEGER, file_id TEXT)''')
        await self.db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER, card_id INTEGER, count INTEGER DEFAULT 1, 
            PRIMARY KEY (user_id, card_id),
            FOREIGN KEY (card_id) REFERENCES cards(card_id))''')
        await self.db.commit()

db_manager = Database(DB_PATH)

# --- ЛОГИКА ---
def get_rarity(rank: str) -> int:
    r = random.uniform(0, 100)
    if rank == "Мифрил":
        chances = [(15, 5), (35, 4), (60, 3), (90, 2), (100, 1)]
    else:
        bonus = 5 if rank == "Серебро" else 0
        chances = [(1 + bonus * 0.25, 5), (4 + bonus * 0.5, 4), (10 + bonus * 1.0, 3), (30 + bonus * 1.5, 2), (100, 1)]
    for threshold, rarity in chances:
        if r <= threshold: return rarity
    return 1

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(m: Message, bot: Bot):
    user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
    await db_manager.db.execute(
        "INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?, ?, ?)", 
        (m.from_user.id, m.from_user.first_name, user_rank)
    )
    await db_manager.db.commit()
    # Сразу показываем профиль вместо скучного текста
    await profile(m, bot)

@dp.message(F.text == "👤 Мой профиль")
@dp.message(Command("profile"))
async def profile(m: Message, bot: Bot):
    async with db_manager.db.execute(
        "SELECT nickname, rank, money, titles FROM users WHERE user_id = ?", (m.from_user.id,)
    ) as cursor:
        u = await cursor.fetchone()
    
    if not u:
        return await m.answer("Напиши /start для регистрации!")

    async with db_manager.db.execute(
        "SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,)
    ) as cursor:
        inv_cnt = (await cursor.fetchone())[0]
        
    async with db_manager.db.execute("SELECT COUNT(*) FROM cards") as cursor:
        total = (await cursor.fetchone())[0]
    
    # Красивое форматирование профиля
    text = (
        f"💠 <b>ПРОФИЛЬ ИГРОКА</b> 💠\n\n"
        f"👤 <b>Имя:</b> {u[0]}\n"
        f"🏷 <b>Титул:</b> <i>{u[3]}</i>\n"
        f"🏅 <b>Ранг:</b> <b>{u[1]}</b>\n"
        f"💰 <b>Баланс:</b> {u[2]} монет\n\n"
        f"🎴 <b>Коллекция карт:</b> {inv_cnt} из {total}\n"
        f"<i>Собери их все, чтобы стать легендой!</i>"
    )

    # Пытаемся получить аватарку пользователя
    user_photos = await bot.get_user_profile_photos(m.from_user.id)
    if user_photos.total_count > 0:
        # Берем фото лучшего качества (последнее в массиве первой фотографии)
        photo_id = user_photos.photos[0][-1].file_id
        await m.answer_photo(photo=photo_id, caption=text, parse_mode=ParseMode.HTML, reply_markup=main_kb)
    else:
        # Если у пользователя нет аватарки или она скрыта настройками приватности
        await m.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(F.text.in_(["🃏 Вытянуть карту", "карта", "карту"]))
async def draw(m: Message):
    async with db_manager.db.execute(
        "SELECT rank, last_draw FROM users WHERE user_id = ?", (m.from_user.id,)
    ) as cursor:
        u = await cursor.fetchone()
    
    if not u: return
    rank, last_draw = u
    cd = timedelta(hours=24) if rank != "Мифрил" else timedelta(seconds=5)
    now = datetime.now()
    
    if last_draw:
        time_passed = now - datetime.fromisoformat(last_draw)
        if time_passed < cd:
            rem = cd - time_passed
            hours, remainder = divmod(rem.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return await m.answer(f"⏳ <b>Кулдаун!</b>\nВозвращайся через: <code>{hours}ч {minutes}м {seconds}с</code>", parse_mode=ParseMode.HTML)
    
    rarity = get_rarity(rank)
    async with db_manager.db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,)) as cursor:
        card = await cursor.fetchone()
    
    if not card: 
        return await m.answer(f"😔 Карт редкости {rarity}⭐ пока нет в базе! Пни админа.")
    
    c_id, c_name, f_id = card
    async with db_manager.db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id)) as cursor:
        is_duplicate = await cursor.fetchone()

    if is_duplicate:
        bonus = rarity * 20
        await db_manager.db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bonus, m.from_user.id))
        cap = f"🃏 <b>Повторка!</b>\n\nТы вытянул: <b>{c_name}</b> ({rarity}⭐)\nОна у тебя уже есть, поэтому ты получаешь компенсацию:\n💰 <b>+{bonus} монет</b>"
    else:
        await db_manager.db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, c_id))
        cap = f"🎉 <b>НОВАЯ КАРТА!</b> 🎉\n\nТы успешно вытянул: <b>{c_name}</b> ({rarity}⭐)\nОна добавлена в твою коллекцию!"
    
    await db_manager.db.execute("UPDATE users SET last_draw = ? WHERE user_id = ?", (now.isoformat(), m.from_user.id))
    await db_manager.db.commit()
    await m.answer_photo(f_id, caption=cap, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(F.text == "❓ Помощь")
@dp.message(Command("help"))
async def bot_help(m: Message):
    text = (
        "📖 <b>Справочник по игре:</b>\n\n"
        "🃏 <b>Как играть?</b>\n"
        "Раз в день (или чаще, зависит от ранга) ты можешь тянуть случайную карту. Твоя цель — собрать всю коллекцию!\n\n"
        "🏆 <b>Редкость карт:</b>\n"
        "1⭐ — Обычная\n"
        "2⭐ — Редкая\n"
        "3⭐ — Эпическая\n"
        "4⭐ — Мифическая\n"
        "5⭐ — Легендарная\n\n"
        "💰 <b>Монеты:</b> Даются за выпадение повторяющихся карт. В будущем их можно будет тратить на покупку титулов или обмен!\n\n"
        "<i>Используй кнопки внизу экрана для управления.</i>"
    )
    await m.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_kb)

@dp.message(Command("adminhelp"))
async def admin_help(m: Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔️ Эта команда доступна только администратору.")
    
    text = (
        "🛠 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b> 🛠\n\n"
        "<b>Как добавить новую карту?</b>\n"
        "1. Отправь картинку (фото) боту.\n"
        "2. В поле «Подпись» (Caption) напиши команду в формате:\n"
        "<code>/add_card Название карты 5</code>\n"
        "<i>(Где 5 — это редкость от 1 до 5)</i>\n\n"
        "<b>Пример:</b>\n"
        "<code>/add_card Огненный Дракон 4</code>\n\n"
        "<b>Особенности админа:</b>\n"
        "- У тебя ранг «Мифрил»\n"
        "- Кулдаун на карты всего 5 секунд\n"
        "- Повышенный шанс на Легендарки"
    )
    await m.answer(text, parse_mode=ParseMode.HTML)

@dp.message(F.photo)
async def add_card_photo(m: Message):
    if m.from_user.id != ADMIN_ID or not m.caption or not m.caption.startswith("/add_card"):
        return
    
    try:
        parts = m.caption.split()
        rarity = int(parts[-1])
        name = " ".join(parts[1:-1])
        
        await db_manager.db.execute(
            "INSERT INTO cards (name, rarity, file_id) VALUES (?, ?, ?)", 
            (name, rarity, m.photo[-1].file_id)
        )
        await db_manager.db.commit()
        await m.answer(f"✅ Успешно добавлено!\n<b>Имя:</b> {name}\n<b>Редкость:</b> {rarity}⭐", parse_mode=ParseMode.HTML)
    except (ValueError, IndexError):
        await m.answer("❌ <b>Ошибка формата!</b>\nИспользуй: <code>/add_card Название 5</code> в подписи к фото.", parse_mode=ParseMode.HTML)

# --- ЗАПУСК ---
async def main():
    await db_manager.connect()
    bot = Bot(token=TOKEN)
    await setup_bot_commands(bot) # Устанавливаем меню команд
    print("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await db_manager.db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
# --- ЛОГИКА ШАНСОВ ---
def get_rarity(rank):
    r = random.uniform(0, 100)
    if rank == "Мифрил":
        if r <= 15: return 5
        if r <= 35: return 4
        if r <= 60: return 3
        if r <= 90: return 2
        return 1
    bonus = 5 if rank == "Серебро" else 0
    if r <= (1 + bonus * 0.25): return 5 
    if r <= (4 + bonus * 0.5): return 4
    if r <= (10 + bonus * 1.0): return 3
    if r <= (30 + bonus * 1.5): return 2
    return 1

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        user_rank = "Мифрил" if m.from_user.id == ADMIN_ID else "Бронза"
        await db.execute("INSERT OR IGNORE INTO users (user_id, nickname, rank) VALUES (?, ?, ?)", 
                         (m.from_user.id, m.from_user.first_name, user_rank))
        await db.commit()
    await m.answer("👋 Бот запущен на Railway! Напиши 'карта' или /profile")

@dp.message(F.text.lower().in_(["карта", "карту", "нев", "невер"]))
async def draw(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT rank, last_draw FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        if not u: return
        rank, last_draw = u
        cd = timedelta(hours=24) if rank != "Мифрил" else timedelta(seconds=10)
        now = datetime.now()
        if last_draw and now < datetime.fromisoformat(last_draw) + cd:
            rem = (datetime.fromisoformat(last_draw) + cd) - now
            return await m.answer(f"⏳ Кулдаун! Осталось: {str(rem).split('.')[0]}")
        
        rarity = get_rarity(rank)
        res = await db.execute("SELECT card_id, name, file_id FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))
        card = await res.fetchone()
        if not card: return await m.answer("Карт пока нет в базе!")
        
        c_id, c_name, f_id = card
        res = await db.execute("SELECT count FROM inventory WHERE user_id = ? AND card_id = ?", (m.from_user.id, c_id))
        if await res.fetchone():
            bonus = rarity * 20
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (bonus, m.from_user.id))
            cap = f"🃏 Повторка: {c_name} ({rarity}⭐)\n💰 +{bonus} мошенников"
        else:
            await db.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (m.from_user.id, c_id))
            cap = f"🎉 НОВАЯ: {c_name} ({rarity}⭐)"
        
        await db.execute("UPDATE users SET last_draw = ? WHERE user_id = ?", (now.isoformat(), m.from_user.id))
        await db.commit()
        await m.answer_photo(f_id, caption=cap)

@dp.message(Command("profile"))
async def profile(m: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        res = await db.execute("SELECT nickname, rank, money, titles FROM users WHERE user_id = ?", (m.from_user.id,))
        u = await res.fetchone()
        res = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (m.from_user.id,))
        inv_cnt = (await res.fetchone())[0]
        res = await db.execute("SELECT COUNT(*) FROM cards")
        total = (await res.fetchone())[0]
    
    text = (f"👤 {u[0]} | Титул: {u[3]}\n🏅 Ранг: {u[1]}\n💰 Мошенники: {u[2]}\n🎴 Карты: {inv_cnt}/{total}")
    await m.answer(text)

@dp.message(F.photo)
async def add_card_photo(m: Message, bot: Bot):
    if m.from_user.id != ADMIN_ID or not m.caption or not m.caption.startswith("/add_card"): return
    try:
        args = m.caption.split()
        rarity = int(args[-1])
        name = " ".join(args[1:-1])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO cards (name, rarity, file_id) VALUES (?, ?, ?)", (name, rarity, m.photo[-1].file_id))
            await db.commit()
        await m.answer(f"✅ Добавлено: {name} ({rarity}⭐)")
    except:
        await m.answer("Ошибка! Формат: /add_card Имя 5 (и прикрепи фото)")

# --- ЗАПУСК ---
async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
