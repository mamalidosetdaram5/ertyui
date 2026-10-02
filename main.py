import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = "YOUR_BOT_TOKEN"

# آیدی Owner ها را اینجا قرار بده
OWNER_IDS = {
    111111111,
    222222222,
    333333333,
}

DB_NAME = "diamonds.db"

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

@dp.message(Command("start"))
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

@dp.message(Command("balance"))
async def balance_handler(message: Message):
    register_user(message.from_user)

    balance = get_balance(message.from_user.id)

    await message.answer(
        f"💎 موجودی شما: {balance} الماس"
    )

# =========================================================
# TRANSFER
# =========================================================

@dp.message(Command("give"))
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

    await message.answer(
        f"💎 {amount} الماس با موفقیت منتقل شد.\n"
        f"👤 گیرنده: {receiver.first_name}"
    )

# =========================================================
# OWNER GIVE
# =========================================================

@dp.message(Command("Prgivealmas"))
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

    new_balance = get_balance(target_id)

    await message.answer(
        "✅ الماس با موفقیت اضافه شد.\n\n"
        f"👤 ID: `{target_id}`\n"
        f"💎 مقدار: +{amount}\n"
        f"💰 موجودی جدید: {new_balance}",
        parse_mode="Markdown"
    )

# =========================================================
# OWNER REMOVE
# =========================================================

@dp.message(Command("Prremovealmas"))
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

    new_balance = get_balance(target_id)

    await message.answer(
        "✅ الماس با موفقیت کم شد.\n\n"
        f"👤 ID: `{target_id}`\n"
        f"💎 مقدار: -{amount}\n"
        f"💰 موجودی جدید: {new_balance}",
        parse_mode="Markdown"
    )

# =========================================================
# SET MESSAGE COUNT
# =========================================================

@dp.message(Command("Prsetmessages"))
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

@dp.message(Command("Prsetreward"))
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
# ENABLE / DISABLE AUTO EVENT
# =========================================================

@dp.message(Command("Prgiveevent"))
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

@dp.message(Command("Prsetchat"))
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

@dp.message(Command("Prsettings"))
async def settings_handler(message: Message):
    if not await require_owner(message):
        return

    messages_required = get_setting("messages_required")
    reward_amount = get_setting("reward_amount")
    reward_enabled = get_setting("reward_enabled")
    reward_chat_id = get_setting("reward_chat_id")

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
        f"👥 گروه دراپ: {chat_text}"
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
                    callback_data=f"claim:{chat_id}"
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


@dp.message(Command("Prdrop"))
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
