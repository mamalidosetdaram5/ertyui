import asyncio
import csv
import io
import logging
import random
import sqlite3
import uuid

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = "8734473040:AAFghbS5WXw0wOMfdWzEdu4ke8amn0graeY"

# آیدی Owner ها را اینجا قرار بده
OWNER_IDS = {
    8424103847,
    6716559782,
}

DB_NAME = "diamonds.db"

# =========================================================
# پنل اموجی‌های پرمیوم
# =========================================================
# هر اموجی که توی ربات استفاده شده اینجا لیست شده.
# جلوی هرکدوم، آیدی اموجی پرمیوم موردنظرت رو قرار بده.
# اگر برای یک اموجی نمی‌خوای نسخه‌ی پرمیوم نمایش داده بشه،
# مقدارش رو None بذار (همون اموجی معمولی نمایش داده می‌شود).
#
# نکته: این اموجی‌های پرمیوم فقط زمانی نمایش داده می‌شوند که
# اکانت Owner ربات دارای Telegram Premium باشد.
PREMIUM_EMOJIS = {
    "❌": "5416076321442777828",
    "💎": "5399837316384566936", 
    "✅": "5429501538806548545",
    "⚡️": "5780464752744468119",
    "👤": "5470145449983748652",
    "🎁": "5778598452015402915",
    "🏆": "5474546992598264488",
    "💰": "5778407832776871799",
    "📭": "5372930724959624606",
    "🥇": "5832692422647226240",
    "🥈": "5834620746999012948",
    "🥉": "5832346686369832003",
    "🟢": "5778222071146353172",
    "🔴": "5778317805967380891",
    "⚙️": "5843911663203392756",
    "💬": "5778418364036681141",
    "👥": "5391272000545110592",
    "⚠️": "5819051035284479206",
    "🎉": "5474646232112573246",
    "🔁": "5213093310880557054",
    "⚖️": "5217757718378457464",
    "📝": "5386724377502952933",
    "😅": "5348554775510134247",
}

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================================
# BOT
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =========================================================
# EMOJIFY — جایگزینی خودکار اموجی‌ها با نسخه‌ی پرمیوم
# =========================================================
# این تابع هر اموجی موجود در PREMIUM_EMOJIS را که در متن پیدا
# شود، داخل تگ <tg-emoji emoji-id="..."> قرار می‌دهد تا تلگرام
# نسخه‌ی پرمیوم آن را نمایش دهد (نیازمند parse_mode="HTML").
# اموجی‌هایی که مقدارشان None است دست‌نخورده باقی می‌مانند.

def emojify(text):
    if not isinstance(text, str):
        return text

    for emoji_char, emoji_id in PREMIUM_EMOJIS.items():
        if not emoji_id:
            continue

        if emoji_char in text:
            text = text.replace(
                emoji_char,
                f'<tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji>'
            )

    return text


_original_message_answer = Message.answer
_original_message_edit_text = Message.edit_text
_original_bot_send_message = Bot.send_message


async def _patched_message_answer(self, text=None, *args, **kwargs):
    if text is not None:
        text = emojify(text)
        kwargs.setdefault("parse_mode", "HTML")

    return await _original_message_answer(self, text, *args, **kwargs)


async def _patched_message_edit_text(self, text=None, *args, **kwargs):
    if text is not None:
        text = emojify(text)
        kwargs.setdefault("parse_mode", "HTML")

    return await _original_message_edit_text(self, text, *args, **kwargs)


async def _patched_bot_send_message(self, chat_id, text=None, *args, **kwargs):
    if text is not None:
        text = emojify(text)
        kwargs.setdefault("parse_mode", "HTML")

    return await _original_bot_send_message(self, chat_id, text, *args, **kwargs)


Message.answer = _patched_message_answer
Message.edit_text = _patched_message_edit_text
Bot.send_message = _patched_bot_send_message

# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect(DB_NAME, check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT NOT NULL DEFAULT 'User',
    diamonds INTEGER NOT NULL DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS chat_stats (
    chat_id INTEGER PRIMARY KEY,
    message_count INTEGER NOT NULL DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS active_rewards (
    chat_id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    from_id INTEGER,
    to_id INTEGER,
    amount INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
""")

db.commit()

# =========================================================
# DEFAULT SETTINGS
# =========================================================

def set_default_setting(key, value):
    db.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value))
    )
    db.commit()


set_default_setting("messages_required", 500)
set_default_setting("reward_amount", 1)
set_default_setting("reward_enabled", "on")
set_default_setting("reward_chat_id", "0")
set_default_setting("claim_limit_per_day", 3)

# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def get_setting(key):
    row = db.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    ).fetchone()

    if row:
        return row["value"]

    return None


def set_setting(key, value):
    db.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (key, str(value)))

    db.commit()


def register_user(user):
    db.execute("""
        INSERT INTO users (user_id, username, first_name, diamonds)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
    """, (
        user.id,
        user.username,
        user.first_name or "User"
    ))

    db.commit()


def ensure_user_by_id(user_id):
    db.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name, diamonds)
        VALUES (?, NULL, 'User', 0)
    """, (user_id,))

    db.commit()


def get_balance(user_id):
    row = db.execute(
        "SELECT diamonds FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if not row:
        ensure_user_by_id(user_id)
        return 0

    return row["diamonds"]


def add_diamonds(user_id, amount):
    ensure_user_by_id(user_id)

    db.execute("""
        UPDATE users
        SET diamonds = diamonds + ?
        WHERE user_id = ?
    """, (amount, user_id))

    db.commit()


def remove_diamonds(user_id, amount):
    ensure_user_by_id(user_id)

    cur = db.execute("""
        UPDATE users
        SET diamonds = diamonds - ?
        WHERE user_id = ?
        AND diamonds >= ?
    """, (amount, user_id, amount))

    db.commit()

    return cur.rowcount > 0


def transfer_diamonds(sender_id, receiver_id, amount):
    if sender_id == receiver_id:
        return False, "self"

    try:
        db.execute("BEGIN")

        sender = db.execute("""
            SELECT diamonds
            FROM users
            WHERE user_id = ?
        """, (sender_id,)).fetchone()

        if not sender or sender["diamonds"] < amount:
            db.rollback()
            return False, "not_enough"

        ensure_user_by_id(receiver_id)

        db.execute("""
            UPDATE users
            SET diamonds = diamonds - ?
            WHERE user_id = ?
        """, (amount, sender_id))

        db.execute("""
            UPDATE users
            SET diamonds = diamonds + ?
            WHERE user_id = ?
        """, (amount, receiver_id))

        db.commit()

        return True, "ok"

    except Exception:
        db.rollback()
        return False, "error"


def log_transaction(type_, from_id, to_id, amount):
    db.execute("""
        INSERT INTO transactions (type, from_id, to_id, amount)
        VALUES (?, ?, ?, ?)
    """, (type_, from_id, to_id, amount))

    db.commit()


def is_owner(user_id):
    return user_id in OWNER_IDS


async def require_owner(message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ شما دسترسی Owner ندارید.")
        return False

    return True

# =========================================================
# TARGET + AMOUNT PARSER
# =========================================================

def get_target_and_amount(message: Message):
    """
    دو حالت:

    Reply:
    /Prgivealmas 100

    ID:
    /Prgivealmas 123456789 100
    """

    args = message.text.split()

    # حالت Reply
    if message.reply_to_message and message.reply_to_message.from_user:
        if len(args) != 2:
            return None, None, "reply_usage"

        try:
            amount = int(args[1])
        except ValueError:
            return None, None, "invalid_amount"

        target = message.reply_to_message.from_user

        return target.id, amount, "ok"

    # حالت ID عددی
    if len(args) != 3:
        return None, None, "id_usage"

    try:
        target_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        return None, None, "invalid_id_or_amount"

    return target_id, amount, "ok"

# =========================================================
# START
# =========================================================

@dp.message(Command("start", ignore_case=True))
async def start_handler(message: Message):
    register_user(message.from_user)

    await message.answer(
        "💎 به ربات الماس خوش آمدی!\n\n"
        "برای دیدن موجودی:\n"
        "/balance"
    )

# =========================================================
# BALANCE
# =========================================================

@dp.message(Command("balance", ignore_case=True))
async def balance_handler(message: Message):
    register_user(message.from_user)

    balance = get_balance(message.from_user.id)

    await message.answer(
        f"💎 موجودی شما: {balance} الماس"
    )

# =========================================================
# TOP (بیشترین دارندگان الماس)
# =========================================================

@dp.message(Command("top", ignore_case=True))
async def top_handler(message: Message):
    register_user(message.from_user)

    rows = db.execute("""
        SELECT user_id, username, first_name, diamonds
        FROM users
        WHERE diamonds > 0
        ORDER BY diamonds DESC
        LIMIT 10
    """).fetchall()

    if not rows:
        await message.answer("📭 هنوز هیچ کاربری الماس ندارد.")
        return

    medals = ["🥇", "🥈", "🥉"]

    lines = ["🏆 <b>بیشترین دارندگان الماس</b>\n"]

    for i, row in enumerate(rows):
        rank_icon = medals[i] if i < len(medals) else f"{i + 1}."

        name = row["first_name"] or "User"

        lines.append(
            f"{rank_icon} {name} — <b>{row['diamonds']}</b> 💎"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML"
    )

# =========================================================
# HISTORY (تاریخچه‌ی هر کاربر)
# =========================================================

@dp.message(Command("history", ignore_case=True))
async def history_handler(message: Message):
    register_user(message.from_user)

    user_id = message.from_user.id

    rows = db.execute("""
        SELECT type, from_id, to_id, amount, created_at
        FROM transactions
        WHERE from_id = ? OR to_id = ?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id, user_id)).fetchall()

    if not rows:
        await message.answer("📭 هنوز هیچ تراکنشی برات ثبت نشده.")
        return

    labels = {
        "transfer": "🔁 انتقال",
        "owner_add": "✅ افزوده‌شده توسط ادمین",
        "owner_remove": "❌ کسرشده توسط ادمین",
        "reward": "🎁 جایزه‌ی دراپ",
        "bet": "🎲 بت تاسی",
    }

    lines = ["💬 <b>تاریخچه‌ی ۱۰ تراکنش آخر</b>\n"]

    for row in rows:
        label = labels.get(row["type"], row["type"])
        is_incoming = row["to_id"] == user_id
        sign = "+" if is_incoming else "-"

        lines.append(f"{label} — {sign}{row['amount']} 💎 ({row['created_at']})")

    await message.answer("\n".join(lines), parse_mode="HTML")

# =========================================================
# TRANSFER
# =========================================================

@dp.message(Command("give", ignore_case=True))
async def give_handler(message: Message):
    register_user(message.from_user)

    if not message.reply_to_message:
        await message.answer(
            "❌ برای انتقال الماس باید روی پیام شخص Reply بزنی.\n\n"
            "مثال:\n"
            "/give 10"
        )
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/give مقدار"
        )
        return

    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("❌ مقدار الماس باید عدد باشد.")
        return

    if amount <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    receiver = message.reply_to_message.from_user

    if receiver.is_bot:
        await message.answer("❌ نمی‌توانی به ربات الماس بدهی.")
        return

    success, reason = transfer_diamonds(
        message.from_user.id,
        receiver.id,
        amount
    )

    if reason == "self":
        await message.answer("❌ نمی‌توانی به خودت الماس بدهی.")
        return

    if reason == "not_enough":
        await message.answer("❌ موجودی الماس شما کافی نیست.")
        return

    if not success:
        await message.answer("❌ انتقال انجام نشد.")
        return

    log_transaction("transfer", message.from_user.id, receiver.id, amount)

    await message.answer(
        f"💎 {amount} الماس با موفقیت منتقل شد.\n"
        f"👤 گیرنده: {receiver.first_name}"
    )

# =========================================================
# BET (بت تاسی — خود دو نفر با 🎲 واقعی روی پیام بت می‌ندازن)
# =========================================================
# قانون: بعد از قبول‌شدن بت، هر دو طرف باید N بار روی همون پیام بت
# با ایموجی 🎲 تلگرام Reply بزنن. وقتی هر دو کامل شد، جمع تاس‌هاشون
# بر اساس حالت low/high مقایسه می‌شه. در تساوی، هر دو باید از نو
# بندازن.

MAX_BET_DICE = 5

# نوع‌های بازی مجاز برای بت و ایموجی تلگرامی‌شون
# دارت هم مثل تاس بازه‌ی مقدار ۱ تا ۶ داره، پس دقیقاً با همون
# منطق جمع/low/high قابل استفاده‌ست.
GAME_EMOJIS = {
    "dice": "🎲",
    "dart": "🎯",
}

# اسم فارسی هر بازی برای نمایش توی پیام‌ها
GAME_NAMES = {
    "dice": "تاس",
    "dart": "دارت",
}

# بت‌های در انتظار قبول/رد (token -> اطلاعات بت)
pending_bets = {}

# بت‌های قبول‌شده که منتظر انداختن تاس/دارت هستن
# کلید: (chat_id, message_id پیام بت)
active_dice_bets = {}


def format_rolls(rolls):
    return " + ".join(str(r) for r in rolls)


def parse_game_type(raw):
    raw = raw.lower()

    if raw in ("dice", "تاس"):
        return "dice"

    if raw in ("dart", "دارت"):
        return "dart"

    return None


def parse_bet_target(message: Message):
    if not message.reply_to_message:
        return None

    target = message.reply_to_message.from_user

    if target.is_bot or target.id == message.from_user.id:
        return None

    return target


def parse_mode(raw):
    raw = raw.lower()

    if raw in ("low", "کم", "کمترین"):
        return "low"

    if raw in ("high", "زیاد", "بیشترین"):
        return "high"

    return None


@dp.message(Command("bet", ignore_case=True))
async def bet_handler(message: Message):
    register_user(message.from_user)

    target = parse_bet_target(message)

    if not target:
        await message.answer(
            "❌ باید روی پیام کسی که می‌خوای باهاش بت ببندی Reply بزنی.\n\n"
            "مثال:\n"
            "/bet 50 2 low        (۵۰ الماس، ۲ تاس، کمترین جمع برنده‌ست)\n"
            "/bet 50 2 low dart   (همون با دارت 🎯 به‌جای تاس)"
        )
        return

    args = message.text.split()

    if len(args) not in (4, 5):
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/bet مقدار تعداد_پرتاب low|high [dice|dart]\n\n"
            "مثال: /bet 50 2 low\n"
            "مثال با دارت: /bet 50 2 low dart"
        )
        return

    try:
        amount = int(args[1])
        dice_count = int(args[2])
    except ValueError:
        await message.answer("❌ مقدار و تعداد پرتاب باید عدد باشند.")
        return

    mode = parse_mode(args[3])

    if mode is None:
        await message.answer("❌ حالت باید low یا high باشد.")
        return

    game_type = "dice"

    if len(args) == 5:
        game_type = parse_game_type(args[4])

        if game_type is None:
            await message.answer("❌ نوع بازی باید dice یا dart باشد.")
            return

    if amount <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    if not (1 <= dice_count <= MAX_BET_DICE):
        await message.answer(f"❌ تعداد پرتاب باید بین ۱ تا {MAX_BET_DICE} باشد.")
        return

    register_user(target)

    if get_balance(message.from_user.id) < amount:
        await message.answer("❌ موجودی الماس شما کافی نیست.")
        return

    if get_balance(target.id) < amount:
        await message.answer(
            f"❌ موجودی {target.first_name} برای این مقدار بت کافی نیست."
        )
        return

    token = uuid.uuid4().hex

    pending_bets[token] = {
        "type": "diamond",
        "game_type": game_type,
        "challenger_id": message.from_user.id,
        "challenger_name": message.from_user.first_name,
        "target_id": target.id,
        "target_name": target.first_name,
        "amount": amount,
        "dice_count": dice_count,
        "mode": mode,
    }

    mode_text = "کمترین جمع برنده" if mode == "low" else "بیشترین جمع برنده"
    game_emoji = GAME_EMOJIS[game_type]
    game_name = GAME_NAMES[game_type]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ قبول",
            callback_data=f"bet_accept:{token}",
            style="success",
        ),
        InlineKeyboardButton(
            text="❌ رد",
            callback_data=f"bet_decline:{token}",
            style="danger",
        ),
    ]])

    await message.answer(
        f"{game_emoji} {message.from_user.first_name} به {target.first_name} پیشنهاد بت داد:\n\n"
        f"💎 مقدار: {amount} الماس\n"
        f"{game_emoji} نوع: {game_name} | تعداد پرتاب: {dice_count}\n"
        f"⚖️ قانون: {mode_text}\n\n"
        f"{target.first_name}, قبول می‌کنی؟",
        reply_markup=keyboard
    )


@dp.message(Command("custombet", ignore_case=True))
async def custom_bet_handler(message: Message):
    register_user(message.from_user)

    target = parse_bet_target(message)

    if not target:
        await message.answer(
            "❌ باید روی پیام کسی که می‌خوای باهاش بت ببندی Reply بزنی.\n\n"
            "مثال:\n"
            "/custombet 2 high بازنده باید ۱۰۰ تا پوش‌آپ بزنه\n"
            "/custombet 2 high dart بازنده باید ۱۰۰ تا پوش‌آپ بزنه"
        )
        return

    args = message.text.split(maxsplit=3)

    if len(args) != 4:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/custombet تعداد_پرتاب low|high [dice|dart] شرط\n\n"
            "مثال: /custombet 2 high بازنده باید ۱۰۰ تا پوش‌آپ بزنه\n"
            "مثال با دارت: /custombet 2 high dart بازنده باید ۱۰۰ تا پوش‌آپ بزنه"
        )
        return

    try:
        dice_count = int(args[1])
    except ValueError:
        await message.answer("❌ تعداد پرتاب باید عدد باشد.")
        return

    mode = parse_mode(args[2])

    if mode is None:
        await message.answer("❌ حالت باید low یا high باشد.")
        return

    if not (1 <= dice_count <= MAX_BET_DICE):
        await message.answer(f"❌ تعداد پرتاب باید بین ۱ تا {MAX_BET_DICE} باشد.")
        return

    # بخش متن شرط، خودش ممکنه با "dice" یا "dart" شروع بشه که یعنی
    # نوع بازی هم مشخص شده؛ وگرنه پیش‌فرض همون تاس می‌مونه.
    rest = args[3]
    rest_parts = rest.split(maxsplit=1)

    game_type = "dice"
    bet_text = rest

    if rest_parts and parse_game_type(rest_parts[0]) is not None:
        if len(rest_parts) < 2 or not rest_parts[1].strip():
            await message.answer("❌ متن شرط را هم بنویس.")
            return

        game_type = parse_game_type(rest_parts[0])
        bet_text = rest_parts[1]

    register_user(target)

    token = uuid.uuid4().hex

    pending_bets[token] = {
        "type": "custom",
        "game_type": game_type,
        "challenger_id": message.from_user.id,
        "challenger_name": message.from_user.first_name,
        "target_id": target.id,
        "target_name": target.first_name,
        "bet_text": bet_text,
        "dice_count": dice_count,
        "mode": mode,
    }

    mode_text = "کمترین جمع برنده" if mode == "low" else "بیشترین جمع برنده"
    game_emoji = GAME_EMOJIS[game_type]
    game_name = GAME_NAMES[game_type]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ قبول",
            callback_data=f"bet_accept:{token}",
            style="success",
        ),
        InlineKeyboardButton(
            text="❌ رد",
            callback_data=f"bet_decline:{token}",
            style="danger",
        ),
    ]])

    await message.answer(
        f"{game_emoji} {message.from_user.first_name} به {target.first_name} پیشنهاد بت داد:\n\n"
        f"📝 شرط: {bet_text}\n"
        f"{game_emoji} نوع: {game_name} | تعداد پرتاب: {dice_count}\n"
        f"⚖️ قانون: {mode_text}\n\n"
        f"{target.first_name}, قبول می‌کنی؟",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("bet_decline:"))
async def bet_decline_handler(callback: CallbackQuery):
    token = callback.data.split(":", 1)[1]
    bet = pending_bets.get(token)

    if not bet:
        await callback.answer("❌ این بت دیگر معتبر نیست.", show_alert=True)
        return

    if callback.from_user.id != bet["target_id"]:
        await callback.answer("❌ این دکمه مال تو نیست.", show_alert=True)
        return

    pending_bets.pop(token, None)

    await callback.message.edit_text("❌ بت رد شد.")
    await callback.answer()


@dp.callback_query(F.data.startswith("bet_accept:"))
async def bet_accept_handler(callback: CallbackQuery):
    token = callback.data.split(":", 1)[1]
    bet = pending_bets.get(token)

    if not bet:
        await callback.answer("❌ این بت دیگر معتبر نیست.", show_alert=True)
        return

    if callback.from_user.id != bet["target_id"]:
        await callback.answer("❌ این دکمه مال تو نیست.", show_alert=True)
        return

    pending_bets.pop(token, None)

    if bet["type"] in ("diamond", "slot"):
        amount = bet["amount"]

        # موجودی هر دو طرف دوباره چک می‌شود (ممکن است از زمان پیشنهاد تغییر کرده باشد)
        if get_balance(bet["challenger_id"]) < amount or get_balance(bet["target_id"]) < amount:
            await callback.message.edit_text(
                "❌ بت لغو شد؛ موجودی یکی از طرفین دیگر کافی نیست."
            )
            await callback.answer()
            return

    key = (callback.message.chat.id, callback.message.message_id)

    if bet["type"] in ("slot", "custom_slot"):
        bet_text_line = (
            f"📝 شرط: {bet['bet_text']}\n" if bet["type"] == "custom_slot" else ""
        )

        await callback.message.edit_text(
            "✅ بت قبول شد!\n\n"
            f"{bet_text_line}"
            f"{SLOT_EMOJI} {bet['challenger_name']} و {bet['target_name']}، هرکدوم یک بار "
            f"روی همین پیام با ایموجی {SLOT_EMOJI} Reply بزنید.\n"
            f"⚖️ قانون: هرکی عدد بزرگ‌تر آورد برنده‌ست"
        )

        active_slot_bets[key] = {
            "type": bet["type"],
            "amount": bet.get("amount"),
            "bet_text": bet.get("bet_text"),
            "challenger_id": bet["challenger_id"],
            "challenger_name": bet["challenger_name"],
            "target_id": bet["target_id"],
            "target_name": bet["target_name"],
            "challenger_roll": None,
            "target_roll": None,
        }

        await callback.answer()
        return

    dice_count = bet["dice_count"]
    mode_text = "کمترین جمع برنده" if bet["mode"] == "low" else "بیشترین جمع برنده"
    game_type = bet.get("game_type", "dice")
    game_emoji = GAME_EMOJIS[game_type]
    game_name = GAME_NAMES[game_type]

    await callback.message.edit_text(
        "✅ بت قبول شد!\n\n"
        f"{game_emoji} {bet['challenger_name']} و {bet['target_name']}، هرکدوم {dice_count} بار "
        f"روی همین پیام با ایموجی {game_emoji} ({game_name}) Reply بزنید.\n"
        f"⚖️ قانون: {mode_text}"
    )

    active_dice_bets[key] = {
        "type": bet["type"],
        "game_type": game_type,
        "mode": bet["mode"],
        "dice_count": dice_count,
        "amount": bet.get("amount"),
        "bet_text": bet.get("bet_text"),
        "challenger_id": bet["challenger_id"],
        "challenger_name": bet["challenger_name"],
        "target_id": bet["target_id"],
        "target_name": bet["target_name"],
        "challenger_rolls": [],
        "target_rolls": [],
    }

    await callback.answer()


async def finish_dice_bet(message: Message, key, bet):
    challenger_rolls = bet["challenger_rolls"]
    target_rolls = bet["target_rolls"]
    challenger_sum = sum(challenger_rolls)
    target_sum = sum(target_rolls)
    game_emoji = GAME_EMOJIS[bet.get("game_type", "dice")]
    game_name = GAME_NAMES[bet.get("game_type", "dice")]

    if challenger_sum == target_sum:
        # تساوی؛ هر دو باید از نو بندازن
        bet["challenger_rolls"] = []
        bet["target_rolls"] = []

        await bot.send_message(
            key[0],
            f"{game_emoji} مساوی شد! هر دو نفر باید دوباره از اول {game_name} بندازید.",
            reply_to_message_id=key[1]
        )
        return

    if bet["mode"] == "low":
        challenger_wins = challenger_sum < target_sum
    else:
        challenger_wins = challenger_sum > target_sum

    if challenger_wins:
        winner_id, winner_name = bet["challenger_id"], bet["challenger_name"]
        loser_id, loser_name = bet["target_id"], bet["target_name"]
        winner_sum, loser_sum = challenger_sum, target_sum
    else:
        winner_id, winner_name = bet["target_id"], bet["target_name"]
        loser_id, loser_name = bet["challenger_id"], bet["challenger_name"]
        winner_sum, loser_sum = target_sum, challenger_sum

    result_text = (
        f"{game_emoji} {bet['challenger_name']}: {format_rolls(challenger_rolls)} = {challenger_sum}\n"
        f"{game_emoji} {bet['target_name']}: {format_rolls(target_rolls)} = {target_sum}\n\n"
        f"🏆 برنده: {winner_name} ({winner_sum} در مقابل {loser_sum})"
    )

    active_dice_bets.pop(key, None)

    if bet["type"] == "diamond":
        amount = bet["amount"]

        if get_balance(loser_id) < amount:
            await bot.send_message(
                key[0],
                f"{result_text}\n\n❌ انتقال انجام نشد؛ موجودی بازنده دیگر کافی نیست.",
                reply_to_message_id=key[1]
            )
            return

        try:
            db.execute("BEGIN")

            cur = db.execute("""
                UPDATE users
                SET diamonds = diamonds - ?
                WHERE user_id = ? AND diamonds >= ?
            """, (amount, loser_id, amount))

            if cur.rowcount == 0:
                db.rollback()
                await bot.send_message(
                    key[0],
                    f"{result_text}\n\n❌ انتقال انجام نشد؛ موجودی بازنده دیگر کافی نیست.",
                    reply_to_message_id=key[1]
                )
                return

            db.execute("""
                UPDATE users
                SET diamonds = diamonds + ?
                WHERE user_id = ?
            """, (amount, winner_id))

            db.commit()
        except Exception:
            db.rollback()
            await bot.send_message(
                key[0],
                f"{result_text}\n\n❌ خطایی در پردازش بت رخ داد.",
                reply_to_message_id=key[1]
            )
            return

        log_transaction("bet", loser_id, winner_id, amount)

        await bot.send_message(
            key[0],
            f"{result_text}\n\n💎 {amount} الماس به {winner_name} منتقل شد.",
            reply_to_message_id=key[1]
        )
    else:
        await bot.send_message(
            key[0],
            f"{result_text}\n\n"
            f"📝 شرط: {bet['bet_text']}\n"
            f"😅 {loser_name} بازنده شد و باید به شرط عمل کنه.",
            reply_to_message_id=key[1]
        )


@dp.message(F.dice.emoji.in_((GAME_EMOJIS["dice"], GAME_EMOJIS["dart"])))
async def dice_roll_handler(message: Message):
    if not message.reply_to_message:
        return

    key = (message.chat.id, message.reply_to_message.message_id)
    bet = active_dice_bets.get(key)

    if not bet:
        return

    expected_emoji = GAME_EMOJIS[bet.get("game_type", "dice")]

    if message.dice.emoji != expected_emoji:
        # این بت با ایموجی دیگه‌ای تعریف شده (مثلاً بت دارت است ولی کاربر تاس فرستاده)
        await message.reply(
            f"❌ این بت با {expected_emoji} انجام می‌شه، نه {message.dice.emoji}."
        )
        return

    user_id = message.from_user.id

    if user_id == bet["challenger_id"]:
        side = "challenger_rolls"
    elif user_id == bet["target_id"]:
        side = "target_rolls"
    else:
        return

    if len(bet[side]) >= bet["dice_count"]:
        return

    bet[side].append(message.dice.value)

    remaining = bet["dice_count"] - len(bet[side])
    game_name = GAME_NAMES[bet.get("game_type", "dice")]

    if remaining > 0:
        await message.reply(f"{expected_emoji} {remaining} {game_name} دیگه مونده.")
        return

    if len(bet["challenger_rolls"]) < bet["dice_count"] or len(bet["target_rolls"]) < bet["dice_count"]:
        await message.reply("✅ نوبت تو کامل شد، منتظر طرف مقابل بمون.")
        return

    await finish_dice_bet(message, key, bet)

# =========================================================
# بت اسلات (کازینو) — حالت High-roll
# =========================================================
# قانون: بر خلاف تاس/دارت که چند بار پرتاب و جمع می‌شن، اسلات فقط
# یک‌بار پرتاب می‌شه. تلگرام برای اسلات عددی بین ۱ تا ۶۴ برمی‌گردونه؛
# عدد ۶۴ یعنی جکپات (سه‌تا ۷۷۷). هرکی عدد بزرگ‌تر بیاره برنده است.
# در تساوی، هر دو باید دوباره بندازن.

SLOT_EMOJI = "🎰"
SLOT_JACKPOT_VALUE = 64

# بت‌های اسلات قبول‌شده که منتظر پرتاب هستن
# کلید: (chat_id, message_id پیام بت)
active_slot_bets = {}


@dp.message(Command("betslot", ignore_case=True))
async def slot_bet_handler(message: Message):
    register_user(message.from_user)

    target = parse_bet_target(message)

    if not target:
        await message.answer(
            "❌ باید روی پیام کسی که می‌خوای باهاش بت ببندی Reply بزنی.\n\n"
            "مثال:\n"
            "/betslot 50   (۵۰ الماس؛ هرکی عدد اسلاتش بزرگ‌تر بود برنده‌ست)"
        )
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/betslot مقدار\n\n"
            "مثال: /betslot 50"
        )
        return

    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("❌ مقدار باید عدد باشد.")
        return

    if amount <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    register_user(target)

    if get_balance(message.from_user.id) < amount:
        await message.answer("❌ موجودی الماس شما کافی نیست.")
        return

    if get_balance(target.id) < amount:
        await message.answer(
            f"❌ موجودی {target.first_name} برای این مقدار بت کافی نیست."
        )
        return

    token = uuid.uuid4().hex

    pending_bets[token] = {
        "type": "slot",
        "challenger_id": message.from_user.id,
        "challenger_name": message.from_user.first_name,
        "target_id": target.id,
        "target_name": target.first_name,
        "amount": amount,
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ قبول",
            callback_data=f"bet_accept:{token}",
            style="success",
        ),
        InlineKeyboardButton(
            text="❌ رد",
            callback_data=f"bet_decline:{token}",
            style="danger",
        ),
    ]])

    await message.answer(
        f"{SLOT_EMOJI} {message.from_user.first_name} به {target.first_name} پیشنهاد بت کازینو (اسلات) داد:\n\n"
        f"💎 مقدار: {amount} الماس\n"
        f"{SLOT_EMOJI} قانون: هرکی عدد اسلاتش بزرگ‌تر بود برنده‌ست (۱ تا ۶۴)\n\n"
        f"{target.first_name}, قبول می‌کنی؟",
        reply_markup=keyboard
    )


@dp.message(Command("customslot", ignore_case=True))
async def custom_slot_bet_handler(message: Message):
    register_user(message.from_user)

    target = parse_bet_target(message)

    if not target:
        await message.answer(
            "❌ باید روی پیام کسی که می‌خوای باهاش بت ببندی Reply بزنی.\n\n"
            "مثال:\n"
            "/customslot بازنده باید ۱۰۰ تا پوش‌آپ بزنه"
        )
        return

    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/customslot شرط\n\n"
            "مثال: /customslot بازنده باید ۱۰۰ تا پوش‌آپ بزنه"
        )
        return

    bet_text = args[1]

    register_user(target)

    token = uuid.uuid4().hex

    pending_bets[token] = {
        "type": "custom_slot",
        "challenger_id": message.from_user.id,
        "challenger_name": message.from_user.first_name,
        "target_id": target.id,
        "target_name": target.first_name,
        "bet_text": bet_text,
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ قبول",
            callback_data=f"bet_accept:{token}",
            style="success",
        ),
        InlineKeyboardButton(
            text="❌ رد",
            callback_data=f"bet_decline:{token}",
            style="danger",
        ),
    ]])

    await message.answer(
        f"{SLOT_EMOJI} {message.from_user.first_name} به {target.first_name} پیشنهاد بت کازینو (اسلات) داد:\n\n"
        f"📝 شرط: {bet_text}\n"
        f"{SLOT_EMOJI} قانون: هرکی عدد اسلاتش بزرگ‌تر بود برنده‌ست (۱ تا ۶۴)\n\n"
        f"{target.first_name}, قبول می‌کنی؟",
        reply_markup=keyboard
    )


async def finish_slot_bet(key, bet):
    challenger_value = bet["challenger_roll"]
    target_value = bet["target_roll"]

    if challenger_value == target_value:
        # تساوی؛ هر دو باید دوباره بندازن
        bet["challenger_roll"] = None
        bet["target_roll"] = None

        await bot.send_message(
            key[0],
            f"{SLOT_EMOJI} مساوی شد ({challenger_value} = {challenger_value})! "
            "هر دو نفر باید دوباره اسلات بندازید.",
            reply_to_message_id=key[1]
        )
        return

    if challenger_value > target_value:
        winner_id, winner_name = bet["challenger_id"], bet["challenger_name"]
        loser_id, loser_name = bet["target_id"], bet["target_name"]
        winner_value, loser_value = challenger_value, target_value
    else:
        winner_id, winner_name = bet["target_id"], bet["target_name"]
        loser_id, loser_name = bet["challenger_id"], bet["challenger_name"]
        winner_value, loser_value = target_value, challenger_value

    jackpot_text = "\n🎉 جکپات! (۷۷۷)" if winner_value == SLOT_JACKPOT_VALUE else ""

    result_text = (
        f"{SLOT_EMOJI} {bet['challenger_name']}: {challenger_value}\n"
        f"{SLOT_EMOJI} {bet['target_name']}: {target_value}\n\n"
        f"🏆 برنده: {winner_name} ({winner_value} در مقابل {loser_value}){jackpot_text}"
    )

    active_slot_bets.pop(key, None)

    if bet["type"] == "custom_slot":
        await bot.send_message(
            key[0],
            f"{result_text}\n\n"
            f"📝 شرط: {bet['bet_text']}\n"
            f"😅 {loser_name} بازنده شد و باید به شرط عمل کنه.",
            reply_to_message_id=key[1]
        )
        return

    amount = bet["amount"]

    if get_balance(loser_id) < amount:
        await bot.send_message(
            key[0],
            f"{result_text}\n\n❌ انتقال انجام نشد؛ موجودی بازنده دیگر کافی نیست.",
            reply_to_message_id=key[1]
        )
        return

    try:
        db.execute("BEGIN")

        cur = db.execute("""
            UPDATE users
            SET diamonds = diamonds - ?
            WHERE user_id = ? AND diamonds >= ?
        """, (amount, loser_id, amount))

        if cur.rowcount == 0:
            db.rollback()
            await bot.send_message(
                key[0],
                f"{result_text}\n\n❌ انتقال انجام نشد؛ موجودی بازنده دیگر کافی نیست.",
                reply_to_message_id=key[1]
            )
            return

        db.execute("""
            UPDATE users
            SET diamonds = diamonds + ?
            WHERE user_id = ?
        """, (amount, winner_id))

        db.commit()
    except Exception:
        db.rollback()
        await bot.send_message(
            key[0],
            f"{result_text}\n\n❌ خطایی در پردازش بت رخ داد.",
            reply_to_message_id=key[1]
        )
        return

    log_transaction("bet", loser_id, winner_id, amount)

    await bot.send_message(
        key[0],
        f"{result_text}\n\n💎 {amount} الماس به {winner_name} منتقل شد.",
        reply_to_message_id=key[1]
    )


@dp.message(F.dice.emoji == SLOT_EMOJI)
async def slot_roll_handler(message: Message):
    if not message.reply_to_message:
        return

    key = (message.chat.id, message.reply_to_message.message_id)
    bet = active_slot_bets.get(key)

    if not bet:
        return

    user_id = message.from_user.id

    if user_id == bet["challenger_id"]:
        side = "challenger_roll"
    elif user_id == bet["target_id"]:
        side = "target_roll"
    else:
        return

    if bet[side] is not None:
        return

    bet[side] = message.dice.value

    if bet["challenger_roll"] is None or bet["target_roll"] is None:
        await message.reply("✅ پرتاب تو ثبت شد، منتظر طرف مقابل بمون.")
        return

    await finish_slot_bet(key, bet)

# =========================================================
# OWNER GIVE
# =========================================================

@dp.message(Command("Prgivealmas", ignore_case=True))
async def owner_give_handler(message: Message):
    if not await require_owner(message):
        return

    target_id, amount, status = get_target_and_amount(message)

    if status == "reply_usage":
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/Prgivealmas 100"
        )
        return

    if status == "id_usage":
        await message.answer(
            "❌ فرمت صحیح:\n\n"
            "با Reply:\n"
            "/Prgivealmas 100\n\n"
            "با ID عددی:\n"
            "/Prgivealmas 123456789 100"
        )
        return

    if status == "invalid_amount":
        await message.answer("❌ مقدار الماس باید عدد باشد.")
        return

    if status == "invalid_id_or_amount":
        await message.answer(
            "❌ ID و مقدار الماس باید عدد باشند."
        )
        return

    if amount <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    add_diamonds(target_id, amount)
    log_transaction("owner_add", None, target_id, amount)

    new_balance = get_balance(target_id)

    await message.answer(
        "✅ الماس با موفقیت اضافه شد.\n\n"
        f"👤 ID: <code>{target_id}</code>\n"
        f"💎 مقدار: +{amount}\n"
        f"💰 موجودی جدید: {new_balance}",
        parse_mode="HTML"
    )

# =========================================================
# OWNER REMOVE
# =========================================================

@dp.message(Command("Prremovealmas", ignore_case=True))
async def owner_remove_handler(message: Message):
    if not await require_owner(message):
        return

    target_id, amount, status = get_target_and_amount(message)

    if status == "reply_usage":
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/Prremovealmas 100"
        )
        return

    if status == "id_usage":
        await message.answer(
            "❌ فرمت صحیح:\n\n"
            "با Reply:\n"
            "/Prremovealmas 100\n\n"
            "با ID عددی:\n"
            "/Prremovealmas 123456789 100"
        )
        return

    if status == "invalid_amount":
        await message.answer("❌ مقدار الماس باید عدد باشد.")
        return

    if status == "invalid_id_or_amount":
        await message.answer(
            "❌ ID و مقدار الماس باید عدد باشند."
        )
        return

    if amount <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    success = remove_diamonds(target_id, amount)

    if not success:
        await message.answer(
            "❌ موجودی این کاربر برای کم کردن این مقدار کافی نیست."
        )
        return

    log_transaction("owner_remove", target_id, None, amount)

    new_balance = get_balance(target_id)

    await message.answer(
        "✅ الماس با موفقیت کم شد.\n\n"
        f"👤 ID: <code>{target_id}</code>\n"
        f"💎 مقدار: -{amount}\n"
        f"💰 موجودی جدید: {new_balance}",
        parse_mode="HTML"
    )

# =========================================================
# SET MESSAGE COUNT
# =========================================================

@dp.message(Command("Prsetmessages", ignore_case=True))
async def set_messages_handler(message: Message):
    if not await require_owner(message):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/Prsetmessages 500"
        )
        return

    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("❌ مقدار باید عدد باشد.")
        return

    if amount <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    set_setting("messages_required", amount)

    await message.answer(
        f"✅ تعداد پیام برای دراپ بعدی روی {amount} تنظیم شد."
    )

# =========================================================
# SET REWARD
# =========================================================

@dp.message(Command("Prsetreward", ignore_case=True))
async def set_reward_handler(message: Message):
    if not await require_owner(message):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/Prsetreward 10"
        )
        return

    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("❌ مقدار باید عدد باشد.")
        return

    if amount <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    set_setting("reward_amount", amount)

    await message.answer(
        f"✅ مقدار جایزه روی {amount} الماس تنظیم شد."
    )

# =========================================================
# SET CLAIM LIMIT (محدودیت گرفتن جایزه در روز)
# =========================================================

@dp.message(Command("Prsetclaimlimit", ignore_case=True))
async def set_claim_limit_handler(message: Message):
    if not await require_owner(message):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/Prsetclaimlimit 3\n\n"
            "(تعداد دفعاتی که هر کاربر می‌تواند در روز روی دکمه‌ی جایزه بزند)"
        )
        return

    try:
        limit = int(args[1])
    except ValueError:
        await message.answer("❌ مقدار باید عدد باشد.")
        return

    if limit <= 0:
        await message.answer("❌ مقدار باید بیشتر از صفر باشد.")
        return

    set_setting("claim_limit_per_day", limit)

    await message.answer(
        f"✅ محدودیت گرفتن جایزه روی {limit} بار در روز تنظیم شد."
    )

# =========================================================
# ENABLE / DISABLE AUTO EVENT
# =========================================================

@dp.message(Command("Prgiveevent", ignore_case=True))
async def give_event_handler(message: Message):
    if not await require_owner(message):
        return

    args = message.text.split()

    if len(args) != 2 or args[1].lower() not in ("on", "off"):
        await message.answer(
            "❌ فرمت صحیح:\n\n"
            "/Prgiveevent on\n"
            "/Prgiveevent off"
        )
        return

    value = args[1].lower()

    set_setting("reward_enabled", value)

    if value == "on":
        await message.answer("🟢 دراپ خودکار فعال شد.")
    else:
        await message.answer("🔴 دراپ خودکار غیرفعال شد.")

# =========================================================
# SET REWARD CHAT
# =========================================================

@dp.message(Command("Prsetchat", ignore_case=True))
async def set_chat_handler(message: Message):
    if not await require_owner(message):
        return

    if message.chat.type not in ("group", "supergroup"):
        await message.answer(
            "❌ این دستور را داخل گروه موردنظر اجرا کن."
        )
        return

    set_setting("reward_chat_id", message.chat.id)

    await message.answer(
        "✅ این گروه به عنوان گروه دراپ تنظیم شد."
    )

# =========================================================
# SETTINGS
# =========================================================

@dp.message(Command("Prsettings", ignore_case=True))
async def settings_handler(message: Message):
    if not await require_owner(message):
        return

    messages_required = get_setting("messages_required")
    reward_amount = get_setting("reward_amount")
    reward_enabled = get_setting("reward_enabled")
    reward_chat_id = get_setting("reward_chat_id")
    claim_limit = get_setting("claim_limit_per_day")

    chat_text = (
        str(reward_chat_id)
        if reward_chat_id != "0"
        else "تنظیم نشده"
    )

    await message.answer(
        "⚙️ تنظیمات ربات\n\n"
        f"💬 تعداد پیام: {messages_required}\n"
        f"💎 مقدار جایزه: {reward_amount}\n"
        f"🎁 دراپ خودکار: {reward_enabled}\n"
        f"👥 گروه دراپ: {chat_text}\n"
        f"⚡ محدودیت گرفتن جایزه: {claim_limit} بار در روز"
    )

# =========================================================
# STATS (آمار کلی ربات)
# =========================================================

@dp.message(Command("Prstats", ignore_case=True))
async def stats_handler(message: Message):
    if not await require_owner(message):
        return

    total_users = db.execute(
        "SELECT COUNT(*) AS c FROM users"
    ).fetchone()["c"]

    total_diamonds = db.execute(
        "SELECT COALESCE(SUM(diamonds), 0) AS s FROM users"
    ).fetchone()["s"]

    total_transactions = db.execute(
        "SELECT COUNT(*) AS c FROM transactions"
    ).fetchone()["c"]

    today_transactions = db.execute("""
        SELECT COUNT(*) AS c
        FROM transactions
        WHERE date(created_at) = date('now')
    """).fetchone()["c"]

    today_rewards = db.execute("""
        SELECT COUNT(*) AS c
        FROM transactions
        WHERE type = 'reward'
        AND date(created_at) = date('now')
    """).fetchone()["c"]

    top_user = db.execute("""
        SELECT first_name, diamonds
        FROM users
        ORDER BY diamonds DESC
        LIMIT 1
    """).fetchone()

    top_text = (
        f"{top_user['first_name']} ({top_user['diamonds']} 💎)"
        if top_user
        else "—"
    )

    await message.answer(
        "🏆 <b>آمار کلی ربات</b>\n\n"
        f"👥 تعداد کاربران: {total_users}\n"
        f"💎 مجموع الماس در گردش: {total_diamonds}\n"
        f"💬 کل تراکنش‌ها: {total_transactions}\n"
        f"⚡ تراکنش‌های امروز: {today_transactions}\n"
        f"🎁 جایزه‌های گرفته‌شده امروز: {today_rewards}\n"
        f"🥇 بیشترین دارنده: {top_text}",
        parse_mode="HTML"
    )

# =========================================================
# IMMEDIATE DROP
# =========================================================

async def create_reward(chat_id):
    # اگر جایزه فعالی وجود دارد، جایزه جدید نساز
    active = db.execute("""
        SELECT message_id
        FROM active_rewards
        WHERE chat_id = ?
    """, (chat_id,)).fetchone()

    if active:
        return False, "active"

    reward_amount = int(get_setting("reward_amount"))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💎 دریافت {reward_amount} الماس",
                    callback_data=f"claim:{chat_id}",
                    style="success",
                    icon_custom_emoji_id=PREMIUM_EMOJIS["💎"],
                )
            ]
        ]
    )

    msg = await bot.send_message(
        chat_id,
        "🎁 <b>دراپ الماس!</b>\n\n"
        f"💎 جایزه: <b>{reward_amount} الماس</b>\n"
        "⚡ اولین نفری که دکمه را بزند، جایزه را دریافت می‌کند!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    db.execute("""
        INSERT INTO active_rewards (chat_id, message_id)
        VALUES (?, ?)
    """, (chat_id, msg.message_id))

    db.commit()

    return True, "ok"


@dp.message(Command("Prdrop", ignore_case=True))
async def immediate_drop_handler(message: Message):
    if not await require_owner(message):
        return

    if message.chat.type not in ("group", "supergroup"):
        await message.answer(
            "❌ این دستور را داخل گروه دراپ اجرا کن."
        )
        return

    configured_chat = int(get_setting("reward_chat_id"))

    if configured_chat == 0:
        await message.answer(
            "❌ هنوز گروه دراپ تنظیم نشده.\n"
            "ابتدا داخل گروه موردنظر بزن:\n"
            "/Prsetchat"
        )
        return

    if message.chat.id != configured_chat:
        await message.answer(
            "❌ این گروه، گروه دراپ نیست."
        )
        return

    success, reason = await create_reward(message.chat.id)

    if not success and reason == "active":
        await message.answer(
            "⚠️ در حال حاضر یک جایزه فعال وجود دارد."
        )

# =========================================================
# BROADCAST (پیام همگانی)
# =========================================================

# پیام‌های در انتظار تایید (owner_id -> متن پیام)
pending_broadcasts = {}


async def run_broadcast(broadcast_text):
    users = db.execute("SELECT user_id FROM users").fetchall()

    sent = 0
    failed = 0

    for row in users:
        try:
            await bot.send_message(row["user_id"], broadcast_text)
            sent += 1
        except Exception:
            failed += 1

        await asyncio.sleep(0.05)

    return len(users), sent, failed


@dp.message(Command("Prbroadcast", ignore_case=True))
async def broadcast_handler(message: Message):
    if not await require_owner(message):
        return

    text = message.text.split(maxsplit=1)

    if len(text) != 2:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/Prbroadcast متن پیام"
        )
        return

    broadcast_text = text[1]

    user_count = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]

    pending_broadcasts[message.from_user.id] = broadcast_text

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ تایید ارسال",
            callback_data="broadcast_confirm",
            style="success",
        ),
        InlineKeyboardButton(
            text="❌ لغو",
            callback_data="broadcast_cancel",
            style="danger",
        ),
    ]])

    await message.answer(
        f"⚠️ این پیام به {user_count} کاربر ارسال می‌شود:\n\n"
        f"{broadcast_text}\n\n"
        "آیا مطمئنی؟",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm_handler(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ شما دسترسی ندارید.", show_alert=True)
        return

    broadcast_text = pending_broadcasts.pop(callback.from_user.id, None)

    if not broadcast_text:
        await callback.answer(
            "❌ این درخواست دیگر معتبر نیست.",
            show_alert=True
        )
        return

    await callback.answer("⚡ ارسال شروع شد...")

    await callback.message.edit_text("⚡ در حال ارسال پیام...")

    total, sent, failed = await run_broadcast(broadcast_text)

    await callback.message.edit_text(
        "✅ ارسال همگانی تمام شد.\n\n"
        f"✅ موفق: {sent}\n"
        f"❌ ناموفق: {failed}"
    )


@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel_handler(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ شما دسترسی ندارید.", show_alert=True)
        return

    pending_broadcasts.pop(callback.from_user.id, None)

    await callback.message.edit_text("❌ ارسال پیام همگانی لغو شد.")
    await callback.answer()

# =========================================================
# EXPORT (خروجی CSV)
# =========================================================

@dp.message(Command("Prexport", ignore_case=True))
async def export_handler(message: Message):
    if not await require_owner(message):
        return

    rows = db.execute("""
        SELECT user_id, username, first_name, diamonds
        FROM users
        ORDER BY diamonds DESC
    """).fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["user_id", "username", "first_name", "diamonds"])

    for row in rows:
        writer.writerow([
            row["user_id"],
            row["username"] or "",
            row["first_name"],
            row["diamonds"],
        ])

    file_bytes = buffer.getvalue().encode("utf-8-sig")

    await message.answer_document(
        BufferedInputFile(file_bytes, filename="users_export.csv"),
        caption=f"📭 خروجی {len(rows)} کاربر."
    )

# =========================================================
# CLAIM REWARD
# =========================================================

@dp.callback_query(F.data.startswith("claim:"))
async def claim_reward_handler(callback: CallbackQuery):
    try:
        chat_id = int(callback.data.split(":")[1])
    except Exception:
        await callback.answer(
            "❌ خطا در جایزه.",
            show_alert=True
        )
        return

    if not callback.message:
        await callback.answer(
            "❌ پیام جایزه پیدا نشد.",
            show_alert=True
        )
        return

    message_id = callback.message.message_id

    active = db.execute("""
        SELECT message_id
        FROM active_rewards
        WHERE chat_id = ?
    """, (chat_id,)).fetchone()

    if not active or active["message_id"] != message_id:
        await callback.answer(
            "⚡ دیر رسیدی! جایزه قبلاً گرفته شده.",
            show_alert=True
        )
        return

    claim_limit = int(get_setting("claim_limit_per_day"))

    claims_today = db.execute("""
        SELECT COUNT(*) AS c
        FROM transactions
        WHERE type = 'reward'
        AND to_id = ?
        AND date(created_at) = date('now')
    """, (callback.from_user.id,)).fetchone()["c"]

    if claims_today >= claim_limit:
        await callback.answer(
            f"⚠️ تو امروز {claim_limit} بار جایزه گرفتی، فردا دوباره امتحان کن.",
            show_alert=True
        )
        return

    reward_amount = int(get_setting("reward_amount"))

    try:
        db.execute("BEGIN")

        cur = db.execute("""
            DELETE FROM active_rewards
            WHERE chat_id = ?
            AND message_id = ?
        """, (chat_id, message_id))

        if cur.rowcount == 0:
            db.rollback()

            await callback.answer(
                "⚡ دیر رسیدی! یکی دیگه جایزه رو گرفت.",
                show_alert=True
            )
            return

        ensure_user_by_id(callback.from_user.id)

        db.execute("""
            UPDATE users
            SET diamonds = diamonds + ?
            WHERE user_id = ?
        """, (reward_amount, callback.from_user.id))

        db.commit()

    except Exception:
        db.rollback()

        await callback.answer(
            "❌ خطایی رخ داد.",
            show_alert=True
        )
        return

    log_transaction("reward", None, callback.from_user.id, reward_amount)

    await callback.answer(
        f"🎉 {reward_amount} الماس گرفتی!",
        show_alert=True
    )

    try:
        await callback.message.edit_text(
            "🎁 <b>دراپ دریافت شد!</b>\n\n"
            f"🏆 برنده: <b>{callback.from_user.first_name}</b>\n"
            f"💎 جایزه: <b>{reward_amount} الماس</b>\n\n"
            "⚡ دراپ بعدی در راه است...",
            parse_mode="HTML"
        )
    except Exception:
        pass

# =========================================================
# MESSAGE COUNTER
# =========================================================

async def count_group_message(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    if message.from_user and message.from_user.is_bot:
        return

    configured_chat = int(get_setting("reward_chat_id"))

    if configured_chat == 0:
        return

    if message.chat.id != configured_chat:
        return

    if get_setting("reward_enabled") != "on":
        return

    # اگر جایزه فعالی وجود دارد، شمارش متوقف می‌شود
    active = db.execute("""
        SELECT message_id
        FROM active_rewards
        WHERE chat_id = ?
    """, (message.chat.id,)).fetchone()

    if active:
        return

    row = db.execute("""
        SELECT message_count
        FROM chat_stats
        WHERE chat_id = ?
    """, (message.chat.id,)).fetchone()

    if row:
        count = row["message_count"] + 1

        db.execute("""
            UPDATE chat_stats
            SET message_count = ?
            WHERE chat_id = ?
        """, (count, message.chat.id))

    else:
        count = 1

        db.execute("""
            INSERT INTO chat_stats (chat_id, message_count)
            VALUES (?, ?)
        """, (message.chat.id, count))

    db.commit()

    required = int(get_setting("messages_required"))

    if count >= required:

        # ریست شمارنده
        db.execute("""
            UPDATE chat_stats
            SET message_count = 0
            WHERE chat_id = ?
        """, (message.chat.id,))

        db.commit()

        await create_reward(message.chat.id)

# =========================================================
# GENERAL MESSAGE HANDLER
# =========================================================

@dp.message()
async def all_messages_handler(message: Message):
    if message.from_user:
        register_user(message.from_user)

    await count_group_message(message)

# =========================================================
# MAIN
# =========================================================

async def main():
    logging.info("Bot started.")

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
