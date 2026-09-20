# ============================================================
#  نسخه تک‌منبع (Single-File) ربات WAIFU & HUSBANDO CATCHER
#  همراه با سیستم پروفایل پیشرفته (/profile) و اقتصاد کامل
# ============================================================
import io
import os
import re
import json
import html
import time
import math
import random
import secrets
import sqlite3
import asyncio
import textwrap
import traceback
from html import escape
from itertools import groupby
from contextlib import redirect_stdout

import aiosqlite
from cachetools import TTLCache

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedVideo,
    InlineQueryResultCachedMpeg4Gif,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters as tg_filters,
)

# ============================================================
#  بخش ۱: ثبت لاگ
# ============================================================
import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)
logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("pyrate_limiter").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

# ============================================================
#  بخش ۲: تنظیمات و کانفیگ ریرتی‌ها و اقتصاد
# ============================================================
TOKEN = "8834212485:AAHa9_kk9Ak6KU8-L_Ma80CCp_JFDoayrVw"
api_id = 26626068
api_hash = "bf423698bcbe33cfd58b11c78c42caa2"
OWNER_ID = "6716559782"
sudo_users = ("8853202353", "6716559782", "8424103847", "7276858003", "8415158653", "7644152678", "8886156118")

def is_owner_or_sudo(user_id) -> bool:
    """
    True برای اونر یا هر کاربری که داخل sudo_users هست.
    اینجوری حتی اگه یه روز OWNER_ID عوض بشه یا از لیست sudo_users در بیاد،
    اونر همیشه به همه‌ی دستورات سطح سودو دسترسی داره.
    """
    uid = str(user_id)
    return uid == str(OWNER_ID) or uid in sudo_users
GROUP_ID = -1004395930099
PHOTO_URL = [
    "https://telegra.ph/file/b925c3985f0f325e62e17.jpg",
    "https://telegra.ph/file/4211fb191383d895dab9d.jpg",
]
SUPPORT_CHAT = "Guesser_official_group"
UPDATE_CHAT = "Guesser_official_group"
BOT_USERNAME = "Guesser_Character_Bot"
CHARA_CHANNEL_ID = "-1003917559114"

DEV_LIST = [6716559782]
# مسیر دیتابیس از محیط خونده میشه؛ روی Railway یه Volume با mount path مثلاً
# /data بزن و متغیر DB_PATH=/data/db.sqlite3 رو در Environment تنظیم کن.
# اگه این متغیر ست نباشه (local یا بدون volume) از همون پوشه‌ی جاری استفاده میشه.
DB_PATH = os.environ.get("DB_PATH", "db.sqlite3")

# آیدی‌های ایموجی سفارشی (پرمیوم) برای دکمه‌های اینلاین.
# فقط وقتی رندر می‌شن که اکانت مالک بات Telegram Premium داشته باشه.
EMOJI_IDS = {
    "add": "5210956306952758910",
    "support": "5253742260054409879",
    "updates": "5388632425314140043",
    "help": "5452069934089641166",
    "back": "5416117059207572332",
    "harem": "5222444124698853913",
    "collection": "5467538555158943525",
    "prev": "5447183459602669338",
    "next": "5449683594425410231",
    "confirm": "5206607081334906820",
    "cancel": "5210952531676504517",
    "coin": "5834605246462039136",
}

RARITY_CONFIG = {
    1: {
        "name": "⚪ Common",
        "emoji": "⚪",
        "sell_coin": 15,
        "guess_reward": 5,
        "gacha_weight": 58.0,
        "can_sell_to_bot": True,
        "in_gacha": True,
    },
    2: {
        "name": "🟢 Medium",
        "emoji": "🟢",
        "sell_coin": 30,
        "guess_reward": 10,
        "gacha_weight": 28.0,
        "can_sell_to_bot": True,
        "in_gacha": True,
    },
    3: {
        "name": "🟣 Rare",
        "emoji": "🟣",
        "sell_coin": 50,
        "guess_reward": 20,
        "gacha_weight": 10.0,
        "can_sell_to_bot": True,
        "in_gacha": True,
    },
    4: {
        "name": "🟡 Legendary",
        "emoji": "🟡",
        "sell_coin": 70,
        "guess_reward": 30,
        "gacha_weight": 4.0,
        "can_sell_to_bot": True,
        "in_gacha": True,
    },
    5: {
        "name": "🪼 Elemental",
        "emoji": "🪼",
        "sell_coin": 0,
        "guess_reward": 50,
        "gacha_weight": 0.0,
        "can_sell_to_bot": False,
        "in_gacha": False,
    },
    6: {
        "name": "⛩️ Mastery",
        "emoji": "⛩️",
        "sell_coin": 0,
        "guess_reward": 75,
        "gacha_weight": 0.0,
        "can_sell_to_bot": False,
        "in_gacha": False,
    },

    7: {
        "name": "🎗 Celestial",
        "emoji": "🎗",
        "sell_coin": 15,
        "guess_reward": 100,
        "gacha_weight": 10.0,
        "can_sell_to_bot": False,
        "in_gacha": False,
    },
    8: {
        "name": "🎭 Asteral",
        "emoji": "🎭",
        "sell_coin": 20,
        "guess_reward": 200,
        "gacha_weight": 4.0,
        "can_sell_to_bot": False,
        "in_gacha": False,
    },
}

RARITY_MAP = {k: v["name"] for k, v in RARITY_CONFIG.items()}
RARITY_EMOJI = {v["name"]: v["emoji"] for v in RARITY_CONFIG.values()}

GACHA_COST = 350
DAILY_REWARD = 50
MARKET_TAX_PERCENT = 5

DEFAULT_EVENTS = {
    "Winter": "❄️",
    "Summer": "🏖️",
    "Neko": "🐾",
    "Nude": "🔞",
    "School": "🎒",
    "Maid": "🧹",
    "Bunny": "🐰",
    "Police": "👮",
    "Egypt": "🏜️",
    "Manga": "📔",
    "Baby": "🍼",
    "Bikini": "👙",
    "Cowboy": "🤠",
    "Angle": "🪽",
    "Demon": "🩸",
    "Christmas": "🎄",
    "Halloween": "🎃",
    "Nurse": "💉",
    "Married": "💍",
    "Valentine": "💝",
}

DEFAULT_EVENTS_LOWER = {k.lower(): k for k in DEFAULT_EVENTS}

def get_event_emoji(event_name: str) -> str:
    """
    اموجی متناظر با یه اسم ایونت رو برمی‌گردونه؛ مقایسه case-insensitive
    هست تا فرقی نکنه ایونت توی دیتابیس با چه حروفی ذخیره شده (بزرگ/کوچیک).
    اگه ایونت توی DEFAULT_EVENTS نبود، یه اموجی خنثی برمی‌گردونه.
    """
    if not event_name:
        return ""
    return DEFAULT_EVENTS.get(event_name) or next(
        (emoji for name, emoji in DEFAULT_EVENTS.items() if name.lower() == event_name.lower()),
        "🎉",
    )

# ============================================================
#  بخش ۳: لایه دیتابیس SQLite
# ============================================================
_write_lock = asyncio.Lock()

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS characters(
            id TEXT PRIMARY KEY,
            img_url TEXT,
            name TEXT,
            anime TEXT,
            rarity TEXT,
            message_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            coins INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS user_characters(
            user_id INTEGER,
            character_id TEXT,
            character_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_uc ON user_characters(character_id);

        CREATE TABLE IF NOT EXISTS user_favorites(
            user_id INTEGER,
            character_id TEXT
        );

        CREATE TABLE IF NOT EXISTS user_totals(
            chat_id TEXT PRIMARY KEY,
            message_frequency INTEGER
        );

        CREATE TABLE IF NOT EXISTS group_user_totals(
            user_id INTEGER,
            group_id INTEGER,
            username TEXT,
            first_name TEXT,
            count INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_gut ON group_user_totals(group_id);

        CREATE TABLE IF NOT EXISTS top_global_groups(
            group_id INTEGER PRIMARY KEY,
            group_name TEXT,
            count INTEGER
        );

        CREATE TABLE IF NOT EXISTS pm_users(
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT
        );

        CREATE TABLE IF NOT EXISTS sequences(
            id TEXT PRIMARY KEY,
            sequence_value INTEGER
        );

        CREATE TABLE IF NOT EXISTS event_settings(
            id INTEGER PRIMARY KEY CHECK (id = 1),
            event_name TEXT
        );

        CREATE TABLE IF NOT EXISTS rarity_settings(
            rarity TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            weight REAL
        );

        CREATE TABLE IF NOT EXISTS market_listings(
            listing_id TEXT PRIMARY KEY,
            seller_id INTEGER,
            seller_name TEXT,
            character_id TEXT,
            character_json TEXT,
            price INTEGER,
            created_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS banned_users(
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            banned_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS bot_settings(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()

    for query in [
        "ALTER TABLE characters ADD COLUMN event TEXT",
        "ALTER TABLE characters ADD COLUMN type TEXT DEFAULT 'photo'",
        "ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN last_daily INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(query)
            conn.commit()
        except sqlite3.OperationalError:
            pass

    conn.close()

async def db_execute(fetch: str, sql: str, params=(), write: bool = False):
    if write:
        async with _write_lock:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(sql, params)
                await db.commit()
                return None
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(sql, params)
            if fetch == "one":
                row = await cur.fetchone()
                await cur.close()
                return row
            if fetch == "all":
                rows = await cur.fetchall()
                await cur.close()
                return rows
            await cur.close()
            return None

async def characters_all():
    rows = await db_execute("all", "SELECT * FROM characters")
    return [dict(r) for r in rows]

async def character_by_id(cid):
    row = await db_execute("one", "SELECT * FROM characters WHERE id=?", (cid,))
    return dict(row) if row else None

async def characters_count_all():
    row = await db_execute("one", "SELECT COUNT(*) AS c FROM characters")
    return row["c"] if row else 0

async def characters_count_by_anime(anime):
    row = await db_execute("one", "SELECT COUNT(*) AS c FROM characters WHERE anime=?", (anime,))
    return row["c"] if row else 0

async def characters_search(query):
    if not query:
        return await characters_all()
    pattern = "%" + query + "%"
    rows = await db_execute(
        "all",
        "SELECT * FROM characters WHERE LOWER(name) LIKE LOWER(?) OR LOWER(anime) LIKE LOWER(?)",
        (pattern, pattern),
    )
    return [dict(r) for r in rows]

async def get_user(user_id):
    row = await db_execute("one", "SELECT id, username, first_name, coins, last_daily FROM users WHERE id=?", (user_id,))
    if row is None:
        return None
    chars_rows = await db_execute("all", "SELECT character_json FROM user_characters WHERE user_id=?", (user_id,))
    chars = [json.loads(r["character_json"]) for r in chars_rows]
    fav_row = await db_execute("one", "SELECT character_id FROM user_favorites WHERE user_id=?", (user_id,))
    favs = [fav_row["character_id"]] if fav_row else []
    return {
        "id": user_id,
        "username": row["username"],
        "first_name": row["first_name"],
        "coins": row["coins"] or 0,
        "last_daily": row["last_daily"] or 0,
        "characters": chars,
        "favorites": favs,
    }

async def upsert_user(user_id, username, first_name):
    existing = await db_execute("one", "SELECT username, first_name FROM users WHERE id=?", (user_id,))
    if existing is None:
        await db_execute("none", "INSERT INTO users(id, username, first_name, coins, last_daily) VALUES(?,?,?,0,0)",
                         (user_id, username, first_name), write=True)
    elif existing["username"] != username or existing["first_name"] != first_name:
        await db_execute("none", "UPDATE users SET username=?, first_name=? WHERE id=?",
                         (username, first_name, user_id), write=True)

async def add_user_coins(user_id, amount):
    await db_execute("none", "UPDATE users SET coins=MAX(0, COALESCE(coins, 0) + ?) WHERE id=?", (amount, user_id), write=True)

async def reset_user_coins(user_id):
    await db_execute("none", "UPDATE users SET coins=0 WHERE id=?", (user_id,), write=True)

async def wipe_user_harem(user_id):
    await db_execute("none", "DELETE FROM user_characters WHERE user_id=?", (user_id,), write=True)
    await db_execute("none", "DELETE FROM user_favorites WHERE user_id=?", (user_id,), write=True)
    await db_execute("none", "DELETE FROM market_listings WHERE seller_id=?", (user_id,), write=True)

async def set_user_daily(user_id, timestamp):
    await db_execute("none", "UPDATE users SET last_daily=? WHERE id=?", (timestamp, user_id), write=True)

async def add_user_character(user_id, character):
    await db_execute("none",
                     "INSERT INTO user_characters(user_id, character_id, character_json) VALUES(?,?,?)",
                     (user_id, character["id"], json.dumps(character)), write=True)

async def remove_user_single_character(user_id, character_id):
    row = await db_execute("one", "SELECT rowid, character_json FROM user_characters WHERE user_id=? AND character_id=? LIMIT 1",
                           (user_id, character_id))
    if row:
        await db_execute("none", "DELETE FROM user_characters WHERE rowid=?", (row["rowid"],), write=True)
        return json.loads(row["character_json"])
    return None

async def set_user_characters(user_id, chars):
    await db_execute("none", "DELETE FROM user_characters WHERE user_id=?", (user_id,), write=True)
    for c in chars:
        await db_execute("none",
                         "INSERT INTO user_characters(user_id, character_id, character_json) VALUES(?,?,?)",
                         (user_id, c["id"], json.dumps(c)), write=True)

async def set_favorite(user_id, character_id):
    await db_execute("none", "DELETE FROM user_favorites WHERE user_id=?", (user_id,), write=True)
    await db_execute("none", "INSERT INTO user_favorites(user_id, character_id) VALUES(?,?)",
                     (user_id, character_id), write=True)

async def user_character_count(user_id):
    row = await db_execute("one", "SELECT COUNT(*) AS c FROM user_characters WHERE user_id=?", (user_id,))
    return row["c"] if row else 0

async def character_global_count(cid):
    row = await db_execute("one", "SELECT COUNT(*) AS c FROM user_characters WHERE character_id=?", (cid,))
    return row["c"] if row else 0

async def top_owners_of_character(cid, n=10):
    """۱۰ کاربر برتری که بیشترین تعداد از یک کارت مشخص رو دارن"""
    return await db_execute(
        "all",
        "SELECT uc.user_id, COUNT(*) AS cnt, u.username, u.first_name "
        "FROM user_characters uc "
        "LEFT JOIN users u ON u.id = uc.user_id "
        "WHERE uc.character_id=? "
        "GROUP BY uc.user_id "
        "ORDER BY cnt DESC LIMIT ?",
        (cid, n),
    )

async def get_user_global_rank(user_id: int) -> int:
    """محاسبه رتبه کاربر بر اساس تعداد کل کارت‌ها"""
    query = """
        SELECT COUNT(*) + 1 AS rank
        FROM (
            SELECT user_id, COUNT(*) AS card_count
            FROM user_characters
            GROUP BY user_id
            HAVING card_count > (
                SELECT COUNT(*) FROM user_characters WHERE user_id = ?
            )
        )
    """
    row = await db_execute("one", query, (user_id,))
    return row["rank"] if row else 1

async def get_user_totals(chat_id):
    return await db_execute("one", "SELECT message_frequency FROM user_totals WHERE chat_id=?", (chat_id,))

async def set_frequency(chat_id, freq):
    await db_execute(
        "none",
        "INSERT INTO user_totals(chat_id, message_frequency) VALUES(?,?) "
        "ON CONFLICT(chat_id) DO UPDATE SET message_frequency=excluded.message_frequency",
        (chat_id, freq), write=True,
    )

async def upsert_group_user(user_id, group_id, username, first_name):
    row = await db_execute("one",
                           "SELECT username, first_name FROM group_user_totals WHERE user_id=? AND group_id=?",
                           (user_id, group_id))
    if row is None:
        await db_execute("none",
                         "INSERT INTO group_user_totals(user_id, group_id, username, first_name, count) VALUES(?,?,?,?,1)",
                         (user_id, group_id, username, first_name), write=True)
    else:
        if row["username"] != username or row["first_name"] != first_name:
            await db_execute("none",
                             "UPDATE group_user_totals SET username=?, first_name=? WHERE user_id=? AND group_id=?",
                             (username, first_name, user_id, group_id), write=True)
        await db_execute("none", "UPDATE group_user_totals SET count=count+1 WHERE user_id=? AND group_id=?",
                         (user_id, group_id), write=True)

async def upsert_top_group(group_id, group_name):
    row = await db_execute("one", "SELECT group_name FROM top_global_groups WHERE group_id=?", (group_id,))
    if row is None:
        await db_execute("none", "INSERT INTO top_global_groups(group_id, group_name, count) VALUES(?,?,1)",
                         (group_id, group_name), write=True)
    else:
        if row["group_name"] != group_name:
            await db_execute("none", "UPDATE top_global_groups SET group_name=? WHERE group_id=?",
                             (group_name, group_id), write=True)
        await db_execute("none", "UPDATE top_global_groups SET count=count+1 WHERE group_id=?",
                         (group_id,), write=True)

async def distinct_group_ids():
    rows = await db_execute("all", "SELECT DISTINCT group_id FROM group_user_totals")
    return [r["group_id"] for r in rows]

async def distinct_top_group_ids():
    rows = await db_execute("all", "SELECT group_id FROM top_global_groups")
    return [r["group_id"] for r in rows]

async def distinct_pm_user_ids():
    rows = await db_execute("all", "SELECT id FROM pm_users")
    return [r["id"] for r in rows]

async def insert_pm_user(user_id, first_name, username):
    row = await db_execute("one", "SELECT id FROM pm_users WHERE id=?", (user_id,))
    if row is None:
        await db_execute("none", "INSERT INTO pm_users(id, first_name, username) VALUES(?,?,?)",
                         (user_id, first_name, username), write=True)

async def get_pm_user(user_id):
    return await db_execute("one", "SELECT id FROM pm_users WHERE id=?", (user_id,))

async def next_sequence(name):
    row = await db_execute("one", "SELECT sequence_value FROM sequences WHERE id=?", (name,))
    if row is None:
        await db_execute("none", "INSERT INTO sequences(id, sequence_value) VALUES(?,0)", (name,), write=True)
        return 0
    new_val = row["sequence_value"] + 1
    await db_execute("none", "UPDATE sequences SET sequence_value=? WHERE id=?", (new_val, name), write=True)
    return new_val

async def all_pm_users():
    return await db_execute("all", "SELECT first_name FROM pm_users")

async def all_top_groups():
    return await db_execute("all", "SELECT group_name FROM top_global_groups")

async def top_groups_limited(n=10):
    return await db_execute("all", "SELECT group_name, count FROM top_global_groups ORDER BY count DESC LIMIT ?", (n,))

async def top_users_in_group(chat_id, n=10):
    return await db_execute(
        "all",
        "SELECT username, first_name, count FROM group_user_totals WHERE group_id=? ORDER BY count DESC LIMIT ?",
        (chat_id, n),
    )

async def top_users_global(n=10):
    return await db_execute(
        "all",
        "SELECT u.id, u.username, u.first_name, "
        " (SELECT COUNT(*) FROM user_characters WHERE user_id=u.id) AS cnt "
        " FROM users u ORDER BY cnt DESC LIMIT ?",
        (n,),
    )

async def count_users():
    row = await db_execute("one", "SELECT COUNT(*) AS c FROM users")
    return row["c"] if row else 0

async def insert_character(c):
    await db_execute(
        "none",
        "INSERT INTO characters(id, img_url, name, anime, rarity, message_id, event, type) VALUES(?,?,?,?,?,?,?,?)",
        (c["id"], c["img_url"], c["name"], c["anime"], c["rarity"], c.get("message_id"), c.get("event"), c.get("type", "photo")), write=True
    )

async def delete_character(cid):
    await db_execute("none", "DELETE FROM characters WHERE id=?", (cid,), write=True)
    # حذف کارت از حرم‌سرای همه‌ی کاربرانی که اون رو دارن
    await db_execute("none", "DELETE FROM user_characters WHERE character_id=?", (cid,), write=True)
    # حذف از لیست علاقه‌مندی‌ها هم همینطور
    await db_execute("none", "DELETE FROM user_favorites WHERE character_id=?", (cid,), write=True)
    # پاک کردن کش‌هایی که کارت‌های حذف‌شده رو نگه می‌دارن (اینلاین و حرم)
    all_characters_cache.clear()
    user_collection_cache.clear()

async def update_character(cid, field, value):
    await db_execute("none", f"UPDATE characters SET {field}=? WHERE id=?", (value, cid), write=True)
    owned = await db_execute("all", "SELECT user_id, character_json FROM user_characters WHERE character_id=?", (cid,))
    for row in owned:
        data = json.loads(row["character_json"])
        data[field] = value
        await db_execute(
            "none",
            "UPDATE user_characters SET character_json=? WHERE user_id=? AND character_id=?",
            (json.dumps(data), row["user_id"], cid), write=True,
        )

_bot_settings_table_ready = False

async def _ensure_bot_settings_table():
    """
    ایجاد تضمینی جدول bot_settings از طریق همون مسیر و همون درایور (aiosqlite)
    که db_execute در زمان اجرا واقعاً ازش استفاده می‌کنه — به‌جای تکیه کردن
    روی init_db() که با sqlite3 همگام‌ساز جدا اجرا می‌شه و ممکنه (بسته به
    مسیر نسبی DB_PATH و working directory در لحظه‌ی استارت) به فایل فیزیکی
    متفاوتی نسبت به کوئری‌های زمان اجرا ختم بشه.
    """
    global _bot_settings_table_ready
    if _bot_settings_table_ready:
        return
    async with _write_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS bot_settings(key TEXT PRIMARY KEY, value TEXT)"
            )
            await db.commit()
    _bot_settings_table_ready = True

async def get_setting(key: str, default: str = None):
    await _ensure_bot_settings_table()
    row = await db_execute("one", "SELECT value FROM bot_settings WHERE key=?", (key,))
    if row is None or row["value"] is None:
        return default
    return row["value"]

async def set_setting(key: str, value: str):
    await _ensure_bot_settings_table()
    await db_execute(
        "none",
        "INSERT INTO bot_settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value), write=True,
    )

async def is_event_system_enabled() -> bool:
    val = await get_setting("events_enabled", "1")
    return val == "1"

async def set_event_system_enabled(enabled: bool):
    await set_setting("events_enabled", "1" if enabled else "0")

async def is_rarity_system_enabled() -> bool:
    val = await get_setting("rarities_enabled", "1")
    return val == "1"

async def set_rarity_system_enabled(enabled: bool):
    await set_setting("rarities_enabled", "1" if enabled else "0")

async def get_active_event():
    row = await db_execute("one", "SELECT event_name FROM event_settings WHERE id=1")
    return row["event_name"] if row and row["event_name"] else None

async def set_active_event(name):
    # اسم ایونت رو استاندارد می‌کنیم: حرف اول بزرگ (Title Case) تا "neko" و
    # "Neko" یه چیز واحد حساب بشن و همیشه با حرف بزرگ ذخیره/نمایش داده بشن.
    if name:
        name = name.strip()
        name = DEFAULT_EVENTS_LOWER.get(name.lower(), name[:1].upper() + name[1:])
    await db_execute(
        "none",
        "INSERT INTO event_settings(id, event_name) VALUES(1, ?) "
        "ON CONFLICT(id) DO UPDATE SET event_name=excluded.event_name",
        (name,), write=True,
    )

async def normalize_existing_event_names():
    """
    مهاجرت یک‌باره: اسم‌های ایونت قدیمی روی کاراکترها که با حرف کوچیک
    ذخیره شده بودن (مثل "neko") رو با نسخه‌ی استاندارد (Title Case، مثل
    "Neko") جایگزین می‌کنه؛ هم روی جدول characters هم روی event_settings.
    این تابع idempotent هست، هر بار اجرا بشه مشکلی پیش نمیاد.
    """
    rows = await db_execute("all", "SELECT DISTINCT event FROM characters WHERE event IS NOT NULL AND event != ''")
    for r in rows:
        old_name = r["event"]
        new_name = DEFAULT_EVENTS_LOWER.get(old_name.lower(), old_name[:1].upper() + old_name[1:])
        if new_name != old_name:
            await db_execute(
                "none", "UPDATE characters SET event=? WHERE event=?",
                (new_name, old_name), write=True,
            )
    active = await get_active_event()
    if active:
        fixed = DEFAULT_EVENTS_LOWER.get(active.lower(), active[:1].upper() + active[1:])
        if fixed != active:
            await set_active_event(fixed)

async def clear_active_event():
    await db_execute(
        "none",
        "INSERT INTO event_settings(id, event_name) VALUES(1, NULL) "
        "ON CONFLICT(id) DO UPDATE SET event_name=NULL",
        (), write=True,
    )

async def characters_by_event(event_name):
    rows = await db_execute("all", "SELECT * FROM characters WHERE event=?", (event_name,))
    return [dict(r) for r in rows]

async def characters_spawnable(ignore_restrictions: bool = False):
    if ignore_restrictions or not await is_event_system_enabled():
        # سیستم ایونت خاموشه (یا نادیده گرفته شده): همه کاراکترها بدون توجه
        # به ایونت فعال، قابل اسپان هستن.
        rows = await db_execute("all", "SELECT * FROM characters")
        return [dict(r) for r in rows]

    active_event = await get_active_event()
    rows = await db_execute(
        "all",
        "SELECT * FROM characters WHERE (event IS NULL OR event='') OR event=?",
        (active_event or "",),
    )
    return [dict(r) for r in rows]

async def is_rarity_enabled(rarity):
    row = await db_execute("one", "SELECT enabled FROM rarity_settings WHERE rarity=?", (rarity,))
    if row is None:
        return True
    return bool(row["enabled"])

async def set_rarity_enabled(rarity, enabled: bool):
    await db_execute(
        "none",
        "INSERT INTO rarity_settings(rarity, enabled) VALUES(?,?) "
        "ON CONFLICT(rarity) DO UPDATE SET enabled=excluded.enabled",
        (rarity, int(enabled)), write=True,
    )

async def get_disabled_rarities():
    rows = await db_execute("all", "SELECT rarity FROM rarity_settings WHERE enabled=0")
    return [r["rarity"] for r in rows]

async def get_rarity_weight(rarity):
    row = await db_execute("one", "SELECT weight FROM rarity_settings WHERE rarity=?", (rarity,))
    if row and row["weight"] is not None:
        return row["weight"]
    for cfg in RARITY_CONFIG.values():
        if cfg["name"] == rarity:
            return cfg.get("gacha_weight", 1.0)
    return 1.0

async def set_rarity_weight(rarity, weight: float):
    await db_execute(
        "none",
        "INSERT INTO rarity_settings(rarity, weight) VALUES(?,?) "
        "ON CONFLICT(rarity) DO UPDATE SET weight=excluded.weight",
        (rarity, weight), write=True,
    )

async def is_user_banned(user_id) -> bool:
    row = await db_execute("one", "SELECT user_id FROM banned_users WHERE user_id=?", (user_id,))
    return bool(row)

async def ban_user(user_id, reason="Admin Ban"):
    await db_execute(
        "none",
        "INSERT INTO banned_users(user_id, reason, banned_at) VALUES(?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason",
        (user_id, reason, int(time.time())), write=True
    )

async def unban_user(user_id):
    await db_execute("none", "DELETE FROM banned_users WHERE user_id=?", (user_id,), write=True)

async def all_banned_users():
    return await db_execute("all", "SELECT * FROM banned_users")

async def market_add_listing(listing_id, seller_id, seller_name, character_id, character, price):
    await db_execute(
        "none",
        "INSERT INTO market_listings(listing_id, seller_id, seller_name, character_id, character_json, price, created_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (listing_id, seller_id, seller_name, character_id, json.dumps(character), price, int(time.time())),
        write=True,
    )

async def market_get_listing(listing_id):
    row = await db_execute("one", "SELECT * FROM market_listings WHERE listing_id=?", (listing_id,))
    if not row:
        return None
    data = dict(row)
    data["character"] = json.loads(data["character_json"])
    return data

async def market_delete_listing(listing_id):
    await db_execute("none", "DELETE FROM market_listings WHERE listing_id=?", (listing_id,), write=True)

async def market_all_listings():
    rows = await db_execute("all", "SELECT * FROM market_listings ORDER BY created_at DESC")
    results = []
    for r in rows:
        d = dict(r)
        d["character"] = json.loads(d["character_json"])
        results.append(d)
    return results

async def market_user_listings(seller_id):
    rows = await db_execute("all", "SELECT * FROM market_listings WHERE seller_id=? ORDER BY created_at DESC", (seller_id,))
    results = []
    for r in rows:
        d = dict(r)
        d["character"] = json.loads(d["character_json"])
        results.append(d)
    return results

# ============================================================
#  بخش ۴: کلاینت ربات و توابع کمکی مدیا
# ============================================================
application = Application.builder().token(TOKEN).build()

locks = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}
namespaces = {}
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

async def send_media_safe(bot, chat_id, media_id, media_type="photo", caption=None, reply_markup=None, parse_mode="HTML"):
    try:
        if media_type == "video":
            return await bot.send_video(chat_id=chat_id, video=media_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode, read_timeout=20, write_timeout=20)
        elif media_type == "animation":
            return await bot.send_animation(chat_id=chat_id, animation=media_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode, read_timeout=20, write_timeout=20)
        else:
            return await bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode, read_timeout=20, write_timeout=20)
    except Exception as e:
        LOGGER.error(f"Error sending media via main route (media_id={media_id}, type={media_type}): {e}")
        try: return await bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e2: LOGGER.error(f"send_media_safe fallback send_photo failed: {e2}")
        try: return await bot.send_video(chat_id=chat_id, video=media_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode, read_timeout=20)
        except Exception as e3: LOGGER.error(f"send_media_safe fallback send_video failed: {e3}")
        try: return await bot.send_animation(chat_id=chat_id, animation=media_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e4:
            LOGGER.error(f"send_media_safe fallback send_animation failed: {e4}")
            raise

def extract_target_user(update: Update, context: CallbackContext) -> tuple[int | None, list[str]]:
    message = update.effective_message
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, context.args or []
    if context.args:
        first_arg = context.args[0]
        if first_arg.isdigit() or (first_arg.startswith("-") and first_arg[1:].isdigit()):
            return int(first_arg), context.args[1:]
    return None, context.args or []

def make_progress_bar(percent: float, length: int = 10) -> str:
    filled = int(round((percent / 100.0) * length))
    filled = max(0, min(length, filled))
    return "▰" * filled + "▱" * (length - filled)

# ============================================================
#  بخش ۵: دستورات مدیریتی و نظارتی (Sudo/Admin)
# ============================================================
async def ban_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, extra_args = extract_target_user(update, context)
    if not target_id:
        await update.message.reply_text("Usage: <code>/ban User_ID [Reason]</code> or reply to user with <code>/ban</code>", parse_mode="HTML")
        return

    if is_owner_or_sudo(target_id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> You cannot ban a Sudo/Owner!", parse_mode="HTML")
        return

    reason = " ".join(extra_args) if extra_args else "Banned by Admin"
    await ban_user(target_id, reason)
    await update.message.reply_text(f"🔨 User <code>{target_id}</code> has been <b>BANNED</b> from using the bot.\nReason: {escape(reason)}", parse_mode="HTML")

async def unban_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, _ = extract_target_user(update, context)
    if not target_id:
        await update.message.reply_text("Usage: <code>/unban User_ID</code> or reply to user with <code>/unban</code>", parse_mode="HTML")
        return

    await unban_user(target_id)
    await update.message.reply_text(f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> User <code>{target_id}</code> has been <b>UNBANNED</b>.", parse_mode="HTML")

async def banned_list_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    banned = await all_banned_users()
    if not banned:
        await update.message.reply_text("<tg-emoji emoji-id=\"5337039345419317958\">🕊</tg-emoji> No users are currently banned.", parse_mode="HTML")
        return

    text = f"<tg-emoji emoji-id=\"5240241223632954241\">🚫</tg-emoji> <b>Banned Users ({len(banned)}):</b>\n\n"
    for r in banned:
        text += f"• <code>{r['user_id']}</code> | Reason: {escape(r['reason'] or 'N/A')}\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def wipe_harem_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, _ = extract_target_user(update, context)
    if not target_id:
        await update.message.reply_text("Usage: <code>/wipeharem User_ID</code> or reply to user with <code>/wipeharem</code>", parse_mode="HTML")
        return

    user = await get_user(target_id)
    char_count = len(user["characters"]) if user else 0

    await wipe_user_harem(target_id)
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5445267414562389170\">🗑</tg-emoji> <b>Harem Wiped!</b>\n\nAll <b>{char_count}</b> characters belonging to user <code>{target_id}</code> have been removed.",
        parse_mode="HTML"
    )

async def wipe_coins_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, _ = extract_target_user(update, context)
    if not target_id:
        await update.message.reply_text("Usage: <code>/wipecoins User_ID</code> or reply to user with <code>/wipecoins</code>", parse_mode="HTML")
        return

    await reset_user_coins(target_id)
    await update.message.reply_text(f"<tg-emoji emoji-id=\"5339568737559278051\">💸</tg-emoji> User <code>{target_id}</code>'s coin balance has been reset to <b>0</b>.", parse_mode="HTML")

async def give_char_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, extra_args = extract_target_user(update, context)
    if not target_id or not extra_args:
        await update.message.reply_text("Usage:\n• Reply: <code>/givechar Character_ID</code>\n• Direct: <code>/givechar User_ID Character_ID</code>", parse_mode="HTML")
        return

    cid = extra_args[0]
    character = await character_by_id(cid)
    if not character:
        await update.message.reply_text(f"<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Character ID <code>{cid}</code> does not exist in database.", parse_mode="HTML")
        return

    target_user = await get_user(target_id)
    if not target_user:
        await upsert_user(target_id, None, f"User_{target_id}")

    await add_user_character(target_id, character)
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5337265647246144613\">🎁</tg-emoji> Added <b>{escape(character['name'])}</b> (<code>{cid}</code>) to user <code>{target_id}</code>'s harem!",
        parse_mode="HTML"
    )

async def take_char_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, extra_args = extract_target_user(update, context)
    if not target_id or not extra_args:
        await update.message.reply_text("Usage:\n• Reply: <code>/takechar Character_ID</code>\n• Direct: <code>/takechar User_ID Character_ID</code>", parse_mode="HTML")
        return

    cid = extra_args[0]
    target_user = await get_user(target_id)
    if not target_user or not any(c["id"] == cid for c in target_user["characters"]):
        await update.message.reply_text(f"<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> User <code>{target_id}</code> does not have character <code>{cid}</code>.", parse_mode="HTML")
        return

    removed = await remove_user_single_character(target_id, cid)
    if removed:
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"5406745015365943482\">🔻</tg-emoji> Removed <b>{escape(removed['name'])}</b> (<code>{cid}</code>) from user <code>{target_id}</code>'s harem!",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("Failed to remove character.")

async def give_coins_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, extra_args = extract_target_user(update, context)
    if not target_id or not extra_args:
        await update.message.reply_text("Usage:\n• Reply: <code>/givecoins Amount</code>\n• Direct: <code>/givecoins User_ID Amount</code>", parse_mode="HTML")
        return

    try:
        amount = int(extra_args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Amount must be a positive number.", parse_mode="HTML")
        return

    target_user = await get_user(target_id)
    if not target_user:
        await upsert_user(target_id, None, f"User_{target_id}")

    await add_user_coins(target_id, amount)
    user_now = await get_user(target_id)
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> Gave <b>+{amount:,} Coins</b> to user <code>{target_id}</code>!\nNew Balance: <code>{user_now['coins']:,}</code> Coins.",
        parse_mode="HTML"
    )

async def take_coins_command(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Only for Sudo/Owner users.", parse_mode="HTML")
        return

    target_id, extra_args = extract_target_user(update, context)
    if not target_id or not extra_args:
        await update.message.reply_text("Usage:\n• Reply: <code>/takecoins Amount</code>\n• Direct: <code>/takecoins User_ID Amount</code>", parse_mode="HTML")
        return

    try:
        amount = int(extra_args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Amount must be a positive number.", parse_mode="HTML")
        return

    await add_user_coins(target_id, -amount)
    user_now = await get_user(target_id)
    new_bal = user_now["coins"] if user_now else 0
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5406745015365943482\">🔻</tg-emoji> Deducted <b>{amount:,} Coins</b> from user <code>{target_id}</code>!\nNew Balance: <code>{new_bal:,}</code> Coins.",
        parse_mode="HTML"
    )

# ============================================================
#  بخش ۶: شمارنده پیام و اسپان / حدس کاراکتر
# ============================================================
async def message_counter(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.effective_chat:
        return
    user_id = update.effective_user.id
    if await is_user_banned(user_id):
        return

    chat_id = str(update.effective_chat.id)

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    async with locks[chat_id]:
        freq_row = await get_user_totals(chat_id)
        message_frequency = freq_row["message_frequency"] if freq_row else 100

        if chat_id in last_user and last_user[chat_id]["user_id"] == user_id:
            last_user[chat_id]["count"] += 1
            if last_user[chat_id]["count"] >= 10:
                # اگه هنوز داخل بازه‌ی ۱۰ دقیقه‌ای هشدار هستیم، پیام رو نادیده بگیر
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                # بازه‌ی ۱۰ دقیقه تموم شده (یا هشدار قبلی نبوده): شمارنده رو ریست کن
                # تا کاربر دوباره بتونه باعث اسپان کارت بشه، وگرنه این چت برای همیشه
                # قفل می‌مونه تا یه کاربر دیگه پیام بده.
                last_user[chat_id] = {"user_id": user_id, "count": 1}
                if user_id not in warned_users:
                    await update.message.reply_text(
                        f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Don't Spam {update.effective_user.first_name}...\n"
                        "Your Messages Will be ignored for 10 Minutes..."
                    , parse_mode="HTML")
                    warned_users[user_id] = time.time()
                    return
        else:
            last_user[chat_id] = {"user_id": user_id, "count": 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        if message_counts[chat_id] >= message_frequency:
            await send_image(update, context)
            message_counts[chat_id] = 0

async def send_image(update: Update, context: CallbackContext, notify_empty: bool = False, ignore_restrictions: bool = False) -> bool:
    chat_id = update.effective_chat.id
    pool = await characters_spawnable(ignore_restrictions=ignore_restrictions)

    if not ignore_restrictions and await is_rarity_system_enabled():
        disabled_rarities = await get_disabled_rarities()
        if disabled_rarities:
            pool = [c for c in pool if c["rarity"] not in disabled_rarities]

    if not pool:
        if notify_empty:
            await update.effective_message.reply_text(
                "<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> No characters available to drop right now "
                "(database is empty or every rarity is currently disabled).",
                parse_mode="HTML",
            )
        return False

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []
    if len(sent_characters[chat_id]) == len(pool):
        sent_characters[chat_id] = []

    available = [c for c in pool if c["id"] not in sent_characters[chat_id]]
    rarities = sorted({c["rarity"] for c in available})
    weights = [await get_rarity_weight(r) for r in rarities]
    if sum(weights) <= 0:
        character = random.choice(available)
    else:
        chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
        character = random.choice([c for c in available if c["rarity"] == chosen_rarity])
    sent_characters[chat_id].append(character["id"])
    last_characters[chat_id] = character
    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    event_tag = f"<tg-emoji emoji-id=\"5339183745280798256\">🎉</tg-emoji> <b>EVENT:</b> {get_event_emoji(character['event'])}\n" if character.get("event") else ""

    try:
        await send_media_safe(
            bot=context.bot,
            chat_id=chat_id,
            media_id=character["img_url"],
            media_type=character.get("type", "photo"),
            caption=f"{event_tag}<tg-emoji emoji-id=\"5339265538637983729\">🌟</tg-emoji> <b>A wild {escape(character['rarity'])} character appeared!</b>\n\n<tg-emoji emoji-id=\"5339055695125837138\">🎯</tg-emoji> /guess character name to claim it for your Harem",
            parse_mode="HTML"
        )
    except Exception as e:
        LOGGER.error(f"send_image: failed to deliver character {character.get('id')} to chat {chat_id}: {e}")
        # روی خطای غیرمنتظره، کاراکتر رو از لیست "قبلا فرستاده شده" پاک می‌کنیم
        # تا دفعه بعد دوباره امتحان بشه، و اگه فراخوانی دستی بوده به کاربر خبر بدیم.
        if character["id"] in sent_characters.get(chat_id, []):
            sent_characters[chat_id].remove(character["id"])
        if notify_empty:
            await update.effective_message.reply_text(
                "<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Failed to send the character media "
                "(invalid file_id/URL or the bot lacks permission to post media here). Check log.txt for details.",
                parse_mode="HTML",
            )
        return False
    return True

async def force_drop(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("This command only works in groups.")
        return

    user_id = str(update.effective_user.id)
    if not is_owner_or_sudo(user_id):
        try:
            member = await context.bot.get_chat_member(chat_id, update.effective_user.id)
            if member.status not in ("administrator", "creator"):
                await update.message.reply_text("You must be an admin to use this command.")
                return
        except Exception as e:
            LOGGER.error(f"force_drop: get_chat_member failed for chat={chat_id} user={user_id}: {e}")
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Couldn't verify your admin status "
                "(the bot may be missing permissions in this group). Please try again or check the bot's rights.",
                parse_mode="HTML",
            )
            return

    await send_image(update, context, notify_empty=True)
    message_counts[chat_id] = 0

async def guess(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return
    if chat_id in first_correct_guesses:
        await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>️ Already Guessed By Someone.. Try Next Time Bruhh ", parse_mode="HTML")
        return

    guess_text = " ".join(context.args).lower() if context.args else ""
    if "()" in guess_text or "&" in guess_text.lower():
        await update.message.reply_text("Nahh You Can't use This Types of words in your guess..<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>️", parse_mode="HTML")
        return

    name_parts = last_characters[chat_id]["name"].lower().split()
    if sorted(name_parts) == sorted(guess_text.split()) or any(part == guess_text for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        character = last_characters[chat_id]

        await upsert_user(user_id, update.effective_user.username, update.effective_user.first_name)
        await add_user_character(user_id, character)

        reward_coins = 20
        for cfg in RARITY_CONFIG.values():
            if cfg["name"] == character.get("rarity"):
                reward_coins = cfg.get("guess_reward", 20)
                break
        await add_user_coins(user_id, reward_coins)

        await upsert_group_user(user_id, chat_id, update.effective_user.username, update.effective_user.first_name)
        await upsert_top_group(chat_id, update.effective_chat.title)

        keyboard = [[InlineKeyboardButton("Sᴇᴇ Hᴀʀᴇᴍ", switch_inline_query_current_chat=f"collection.{user_id}", style="success", icon_custom_emoji_id=EMOJI_IDS["harem"])]]
        event_line = f'<tg-emoji emoji-id=\"5339183745280798256\">🎉</tg-emoji> <b>Event:</b> {get_event_emoji(character["event"])} \n' if character.get("event") else ""
        await update.message.reply_text(
            f'<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> caught a new character!\n\n'
            f'<tg-emoji emoji-id=\"5337327602149389705\">🌸</tg-emoji> <b>Name:</b> {escape(character["name"])} \n'
            f'<tg-emoji emoji-id=\"5339079278791258832\">📺</tg-emoji> <b>Anime:</b> {escape(character["anime"])} \n'
            f'<tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji> <b>Rarity:</b> {escape(character["rarity"])}\n'
            f'{event_line}'
            f'<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> <b>Reward:</b> +{reward_coins} Coins\n\n'
            "<i>Added to your Harem — use /harem to view your collection.</i>",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> <b>Wrong guess!</b> Try again. <tg-emoji emoji-id=\"5386367538735104399\">🔎</tg-emoji>", parse_mode="HTML")

async def fav(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please provide Character id...")
        return
    character_id = context.args[0]

    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("You have not Guessed any characters yet....")
        return
    if not any(c["id"] == character_id for c in user["characters"]):
        await update.message.reply_text("This Character is Not In your collection")
        return

    await set_favorite(user_id, character_id)
    character = next((c for c in user["characters"] if c["id"] == character_id))
    await update.message.reply_text(f'Character {character["name"]} has been added to your favorite...')

async def pin_character(update: Update, context: CallbackContext) -> None:
    """
    /pin <character_id>
    همون منطق /fav رو انجام می‌ده (چون هارم از قبل favorite رو به‌عنوان عکس
    اصلی هارم نشون می‌ده) ولی با پیام مخصوص «پین شد» تا کاربر گیج نشه.
    """
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "<b>Usage:</b> <code>/pin &lt;character_id&gt;</code>\n"
            "آیدی کاراکتر رو از /harem می‌تونی ببینی.",
            parse_mode="HTML",
        )
        return
    character_id = context.args[0]

    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("هنوز هیچ کاراکتری نگرفتی.")
        return
    if not any(c["id"] == character_id for c in user["characters"]):
        await update.message.reply_text("این کاراکتر توی کالکشن تو نیست.")
        return

    await set_favorite(user_id, character_id)
    character = next((c for c in user["characters"] if c["id"] == character_id))
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>{escape(character['name'])}</b> "
        "پین شد و از الان به‌عنوان عکس هارم تو نشون داده می‌شه.\n"
        "برای برداشتن پین: <code>/unpin</code>",
        parse_mode="HTML",
    )

async def unpin_character(update: Update, context: CallbackContext) -> None:
    """/unpin - پاک کردن کاراکتر پین‌شده؛ هارم دوباره یه کاراکتر تصادفی نشون می‌ده."""
    if await is_user_banned(update.effective_user.id):
        return
    user_id = update.effective_user.id
    await db_execute("none", "DELETE FROM user_favorites WHERE user_id=?", (user_id,), write=True)
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> پین برداشته شد.",
        parse_mode="HTML",
    )

# ============================================================
#  بخش ۷: اقتصاد و فروشگاه
# ============================================================
async def balance(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    await upsert_user(user_id, update.effective_user.username, update.effective_user.first_name)
    user = await get_user(user_id)
    coins = user["coins"] if user else 0
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5814670671153730702\">💎</tg-emoji> <b>{escape(update.effective_user.first_name)}'s Wallet</b>\n\n"
        f"<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> <b>Balance:</b> <code>{coins:,}</code> Coins",
        parse_mode="HTML"
    )

async def daily(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    await upsert_user(user_id, update.effective_user.username, update.effective_user.first_name)
    user = await get_user(user_id)

    last_daily = user.get("last_daily", 0) if user else 0
    now = int(time.time())
    cooldown = 86400

    if now - last_daily < cooldown:
        rem = cooldown - (now - last_daily)
        hours = rem // 3600
        mins = (rem % 3600) // 60
        await update.message.reply_text(f"⏳ <b>Daily reward already claimed!</b>\nCome back in <b>{hours}h {mins}m</b>. ⏰", parse_mode="HTML")
        return

    await add_user_coins(user_id, DAILY_REWARD)
    await set_user_daily(user_id, now)
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5337265647246144613\">🎁</tg-emoji> <b>Daily Reward Claimed!</b> <tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji>\n\n"
        f"<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> You received <b>+{DAILY_REWARD} Coins</b>!",
        parse_mode="HTML"
    )

async def sell_character(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: <code>/sell Character_ID</code>\nExample: <code>/sell 01</code>", parse_mode="HTML")
        return

    cid = context.args[0]
    user = await get_user(user_id)
    if not user or not user["characters"]:
        await update.message.reply_text("Your collection is empty!")
        return

    char_match = next((c for c in user["characters"] if c["id"] == cid), None)
    if not char_match:
        await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> You don't have this character in your collection!", parse_mode="HTML")
        return

    rarity_conf = None
    for cfg in RARITY_CONFIG.values():
        if cfg["name"] == char_match.get("rarity"):
            rarity_conf = cfg
            break

    if not rarity_conf or not rarity_conf.get("can_sell_to_bot", False):
        await update.message.reply_text("<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> This character is Special/Mythical and cannot be sold to the bot! You can sell it in the /market to other players instead.", parse_mode="HTML")
        return

    sell_price = rarity_conf["sell_coin"]
    removed_char = await remove_user_single_character(user_id, cid)
    if removed_char:
        await add_user_coins(user_id, sell_price)
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"5339475193171569528\">💰</tg-emoji> <b>Sold!</b>\n\n{escape(removed_char['name'])} ({removed_char['rarity']}) → <b>+{sell_price} Coins</b> <tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("Failed to sell character.")

async def gacha_pull(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    await upsert_user(user_id, update.effective_user.username, update.effective_user.first_name)
    user = await get_user(user_id)

    if not user or user.get("coins", 0) < GACHA_COST:
        await update.message.reply_text(f"<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> You need at least <b>{GACHA_COST} Coins</b> to roll the Gacha!\nCheck your balance with /bal.", parse_mode="HTML")
        return

    allowed_rarities = [cfg["name"] for cfg in RARITY_CONFIG.values() if cfg.get("in_gacha", False)]
    all_chars = await characters_all()
    gacha_pool = [c for c in all_chars if c.get("rarity") in allowed_rarities]

    if not gacha_pool:
        await update.message.reply_text("No characters available in the Gacha pool right now!")
        return

    await add_user_coins(user_id, -GACHA_COST)

    weights = []
    for c in gacha_pool:
        w = 1.0
        for cfg in RARITY_CONFIG.values():
            if cfg["name"] == c.get("rarity"):
                w = cfg.get("gacha_weight", 1.0)
                break
        weights.append(w)

    chosen_char = random.choices(gacha_pool, weights=weights, k=1)[0]
    await add_user_character(user_id, chosen_char)

    caption = (
        f"<tg-emoji emoji-id=\"5336942274863462411\">🎰</tg-emoji> <b>GACHA SUMMON!</b>\n\n"
        f"<tg-emoji emoji-id=\"5339183745280798256\">🎉</tg-emoji> Congratulations <b>{escape(update.effective_user.first_name)}</b>!\n"
        f"You pulled:\n\n"
        f"<tg-emoji emoji-id=\"5337327602149389705\">🌸</tg-emoji> <b>{escape(chosen_char['name'])}</b>\n"
        f"🏖️ <b>Anime:</b> {escape(chosen_char['anime'])}\n"
        f"<tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji> <b>Rarity:</b> {escape(chosen_char['rarity'])}\n"
        f"🆔 <b>ID:</b> <code>{chosen_char['id']}</code>\n\n"
        f"<i>Added to your Harem!</i>"
    )

    await send_media_safe(
        bot=context.bot,
        chat_id=update.effective_chat.id,
        media_id=chosen_char["img_url"],
        media_type=chosen_char.get("type", "photo"),
        caption=caption,
        parse_mode="HTML"
    )

# ============================================================
#  بخش ۸: بازارچه بین پلیرها (Marketplace)
# ============================================================
def generate_listing_token() -> str:
    return secrets.token_hex(8)

async def market_command(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    args = context.args
    user_id = update.effective_user.id
    await upsert_user(user_id, update.effective_user.username, update.effective_user.first_name)

    if args and args[0].lower() == "sell":
        if len(args) < 3:
            await update.message.reply_text("Usage: <code>/market sell Character_ID Price</code>\nExample: <code>/market sell 01 1500</code>", parse_mode="HTML")
            return
        cid = args[1]
        try:
            price = int(args[2])
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Price must be a positive number.", parse_mode="HTML")
            return

        user = await get_user(user_id)
        if not user or not user["characters"]:
            await update.message.reply_text("You don't have any characters to sell.")
            return

        char_to_sell = next((c for c in user["characters"] if c["id"] == cid), None)
        if not char_to_sell:
            await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> You don't have this character in your collection!", parse_mode="HTML")
            return

        removed = await remove_user_single_character(user_id, cid)
        if not removed:
            await update.message.reply_text("Error removing character from harem.")
            return

        token = generate_listing_token()
        await market_add_listing(
            listing_id=token,
            seller_id=user_id,
            seller_name=update.effective_user.first_name or "Trader",
            character_id=cid,
            character=removed,
            price=price,
        )

        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"5339468076410759828\">🛒</tg-emoji> <b>Character Listed in Market!</b>\n\n"
            f"<tg-emoji emoji-id=\"5337327602149389705\">🌸</tg-emoji> <b>Name:</b> {escape(removed['name'])}\n"
            f"<tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji> <b>Rarity:</b> {escape(removed['rarity'])}\n"
            f"<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> <b>Price:</b> <code>{price:,}</code> Coins\n"
            f"<tg-emoji emoji-id=\"5337025214976915709\">🔑</tg-emoji> <b>Listing Token:</b> <code>{token}</code>\n\n"
            f"Others can buy it using:\n<code>/market buy {token}</code>",
            parse_mode="HTML"
        )
        return

    elif args and args[0].lower() == "buy":
        if len(args) < 2:
            await update.message.reply_text("Usage: <code>/market buy Listing_Token</code>", parse_mode="HTML")
            return
        token = args[1]
        listing = await market_get_listing(token)
        if not listing:
            await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Listing not found or already sold.", parse_mode="HTML")
            return

        buyer_id = user_id
        if listing["seller_id"] == buyer_id:
            await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> You cannot buy your own listing! Use <code>/market cancel</code> to take it back.", parse_mode="HTML")
            return

        buyer = await get_user(buyer_id)
        if not buyer or buyer.get("coins", 0) < listing["price"]:
            await update.message.reply_text(f"<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> You don't have enough coins! Price is <b>{listing['price']:,} Coins</b>.", parse_mode="HTML")
            return

        total_price = listing["price"]
        tax = int(total_price * (MARKET_TAX_PERCENT / 100.0))
        seller_receives = total_price - tax

        await add_user_coins(buyer_id, -total_price)
        await add_user_coins(listing["seller_id"], seller_receives)

        await add_user_character(buyer_id, listing["character"])
        await market_delete_listing(token)

        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"5339183745280798256\">🎉</tg-emoji> <b>Purchase Successful!</b>\n\n"
            f"You bought <b>{escape(listing['character']['name'])}</b> for <b>{total_price:,} Coins</b>!\n"
            f"<i>Added to your Harem!</i>",
            parse_mode="HTML"
        )
        try:
            await context.bot.send_message(
                chat_id=listing["seller_id"],
                text=f"<tg-emoji emoji-id=\"5339475193171569528\">💰</tg-emoji> <b>Your Market Item was Sold!</b>\n\n<b>{escape(listing['character']['name'])}</b> was bought for <b>{total_price:,} Coins</b> (You received <b>{seller_receives:,}</b> after {MARKET_TAX_PERCENT}% tax).",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    elif args and args[0].lower() == "cancel":
        if len(args) < 2:
            await update.message.reply_text("Usage: <code>/market cancel Listing_Token</code>", parse_mode="HTML")
            return
        token = args[1]
        listing = await market_get_listing(token)
        if not listing:
            await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Listing not found.", parse_mode="HTML")
            return

        if listing["seller_id"] != user_id and not is_owner_or_sudo(user_id):
            await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> You can only cancel your own listings.", parse_mode="HTML")
            return

        await add_user_character(listing["seller_id"], listing["character"])
        await market_delete_listing(token)

        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Listing <code>{token}</code> cancelled. <b>{escape(listing['character']['name'])}</b> has been returned to your Harem.",
            parse_mode="HTML"
        )
        return

    await show_market_page(update, context, page=0)

async def show_market_page(update: Update, context: CallbackContext, page: int = 0) -> None:
    listings = await market_all_listings()
    if not listings:
        msg = "<tg-emoji emoji-id=\"5337157684653226101\">🏬</tg-emoji> <b>Marketplace is currently empty!</b>\n\nUse <code>/market sell ID Price</code> to list your characters."
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="HTML")
        return

    per_page = 8
    total_pages = math.ceil(len(listings) / per_page)
    page = max(0, min(page, total_pages - 1))

    current_items = listings[page * per_page : (page + 1) * per_page]

    text = f"<tg-emoji emoji-id=\"5337157684653226101\">🏬</tg-emoji> <b>GLOBAL CHARACTER MARKETPLACE</b> (Page {page+1}/{total_pages})\n\n"
    for item in current_items:
        c = item["character"]
        rarity_emoji = RARITY_EMOJI.get(c.get("rarity"), "⚪")
        text += (
            f"{rarity_emoji} <b>{escape(c['name'])}</b> | <i>{escape(c['anime'])}</i>\n"
            f"<tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji> Rarity: <b>{escape(c['rarity'])}</b>\n"
            f"<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> Price: <b>{item['price']:,} Coins</b>\n"
            f"<tg-emoji emoji-id=\"5339160183090212029\">👤</tg-emoji> Seller: {escape(item['seller_name'])}\n"
            f"<tg-emoji emoji-id=\"5337025214976915709\">🔑</tg-emoji> Token: <code>{item['listing_id']}</code>\n"
            f"<tg-emoji emoji-id=\"5339468076410759828\">🛒</tg-emoji> Buy: <code>/market buy {item['listing_id']}</code>\n"
            f"──────────────────\n"
        )

    keyboard = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("Pʀᴇᴠ", callback_data=f"market_page:{page-1}", style="primary", icon_custom_emoji_id=EMOJI_IDS["prev"]))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Nᴇxᴛ", callback_data=f"market_page:{page+1}", style="primary", icon_custom_emoji_id=EMOJI_IDS["next"]))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def market_page_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    await show_market_page(update, context, page)

async def my_market_listings(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    listings = await market_user_listings(user_id)

    if not listings:
        await update.message.reply_text(
            "<tg-emoji emoji-id=\"5339368158291587586\">📦</tg-emoji> <b>You don't have any characters listed in the market.</b>\n\n"
            "To sell a character, use:\n<code>/market sell Character_ID Price</code>",
            parse_mode="HTML"
        )
        return

    text = f"<tg-emoji emoji-id=\"5339368158291587586\">📦</tg-emoji> <b>Your Active Market Listings ({len(listings)}):</b>\n\n"
    for item in listings:
        c = item["character"]
        rarity_emoji = RARITY_EMOJI.get(c.get("rarity"), "⚪")
        text += (
            f"{rarity_emoji} <b>{escape(c['name'])}</b> ({escape(c['anime'])})\n"
            f"<tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji> Rarity: <b>{escape(c['rarity'])}</b>\n"
            f"<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> Price: <b>{item['price']:,} Coins</b>\n"
            f"<tg-emoji emoji-id=\"5337025214976915709\">🔑</tg-emoji> Listing Token: <code>{item['listing_id']}</code>\n"
            f"<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Cancel: <code>/market cancel {item['listing_id']}</code>\n"
            f"──────────────────\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")

# ============================================================
#  بخش ۹: هارم و پروفایل کاربر
# ============================================================
async def harem(update: Update, context: CallbackContext, page=0) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        if update.message:
            await update.message.reply_text("<tg-emoji emoji-id=\"5339353834575654382\">📭</tg-emoji> You haven't caught any characters yet!", parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text("<tg-emoji emoji-id=\"5339353834575654382\">📭</tg-emoji> You haven't caught any characters yet!", parse_mode="HTML")
        return

    characters = sorted(user["characters"], key=lambda x: (x["anime"], x["id"]))
    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x["id"])}
    unique_characters = list({c["id"]: c for c in characters}.values())

    total_pages = math.ceil(len(unique_characters) / 15)
    if total_pages == 0:
        total_pages = 1
    if page < 0 or page >= total_pages:
        page = 0

    harem_message = f"<tg-emoji emoji-id=\"5339174987842482774\">📖</tg-emoji> <b>{escape(update.effective_user.first_name)}'s Harem</b> — Page {page+1}/{total_pages}\n"
    current_characters = unique_characters[page * 15:(page + 1) * 15]
    current_grouped = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x["anime"])}

    for anime, chars in current_grouped.items():
        ac = await characters_count_by_anime(anime)
        harem_message += f"\n<b>{escape(anime)} {len(chars)}/{ac}</b>\n"
        for character in chars:
            count = character_counts[character["id"]]
            rarity_emoji = RARITY_EMOJI.get(character.get("rarity"), "⚪")
            event_mark = f" {get_event_emoji(character['event'])}" if character.get("event") else ""
            
            harem_message += f"<code>{character['id']}</code> | {rarity_emoji} | {escape(character['name'])}{event_mark} (x{count})\n"

    total_count = len(user["characters"])
    keyboard = [[InlineKeyboardButton(f"Sᴇᴇ Fᴜʟʟ Cᴏʟʟᴇᴄᴛɪᴏɴ ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}", style="success", icon_custom_emoji_id=EMOJI_IDS["collection"])]]
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("Pʀᴇᴠ", callback_data=f"harem:{page-1}:{user_id}", style="primary", icon_custom_emoji_id=EMOJI_IDS["prev"]))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Nᴇxᴛ", callback_data=f"harem:{page+1}:{user_id}", style="primary", icon_custom_emoji_id=EMOJI_IDS["next"]))
        keyboard.append(nav)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if user["favorites"]:
        fav_id = user["favorites"][0]
        fav_character = next((c for c in user["characters"] if c["id"] == fav_id), None)
        image_url = fav_character["img_url"] if fav_character and "img_url" in fav_character else None
        m_type = fav_character.get("type", "photo") if fav_character else "photo"
    else:
        image_url = None
        m_type = "photo"
        if user["characters"]:
            rc = random.choice(user["characters"])
            image_url = rc["img_url"] if "img_url" in rc else None
            m_type = rc.get("type", "photo")

    if image_url:
        if update.message:
            await send_media_safe(
                bot=context.bot, chat_id=update.effective_chat.id, media_id=image_url, 
                media_type=m_type, caption=harem_message, reply_markup=reply_markup, parse_mode="HTML"
            )
        elif update.callback_query.message.caption != harem_message:
            await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode="HTML")
    else:
        if not user["characters"] and update.message:
            await update.message.reply_text("<tg-emoji emoji-id=\"5339353834575654382\">📭</tg-emoji> Your Harem is empty — go catch some characters!", parse_mode="HTML")
        elif update.message:
            await update.message.reply_text(harem_message, parse_mode="HTML", reply_markup=reply_markup)
        elif update.callback_query.message.text != harem_message:
            await update.callback_query.edit_message_text(harem_message, parse_mode="HTML", reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, page, user_id = query.data.split(":")
    page, user_id = int(page), int(user_id)
    if query.from_user.id != user_id:
        await query.answer("its Not Your Harem", show_alert=True)
        return
    await harem(update, context, page)

async def profile_command(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    target_id, _ = extract_target_user(update, context)
    if not target_id:
        target_id = update.effective_user.id
        target_name = update.effective_user.first_name
        target_username = update.effective_user.username
    else:
        user_row = await get_user(target_id)
        target_name = user_row["first_name"] if user_row else f"User_{target_id}"
        target_username = user_row["username"] if user_row else None

    await upsert_user(target_id, target_username, target_name)
    user = await get_user(target_id)
    
    characters = user["characters"] if user else []
    total_cards = len(characters)
    unique_ids = set(c["id"] for c in characters)
    unique_cards = len(unique_ids)

    total_db_chars = await characters_count_all()
    if total_db_chars == 0:
        harem_percent = 0.0
    else:
        harem_percent = (unique_cards / total_db_chars) * 100

    exp_level = (total_cards // 30) + 1
    current_level_base = (exp_level - 1) * 30
    progress_in_level = total_cards - current_level_base
    progress_pct = (progress_in_level / 30.0) * 100
    p_bar = make_progress_bar(progress_pct, 10)

    rarity_stats = {}
    for r_num in sorted(RARITY_CONFIG.keys(), reverse=True):
        r_info = RARITY_CONFIG[r_num]
        rarity_stats[r_info["name"]] = {"emoji": r_info["emoji"], "unique_ids": set(), "total": 0}

    for c in characters:
        r_name = c.get("rarity")
        if r_name in rarity_stats:
            rarity_stats[r_name]["total"] += 1
            rarity_stats[r_name]["unique_ids"].add(c["id"])

    global_rank = await get_user_global_rank(target_id)

    clean_name = escape(target_name or "Collector")
    text = (
        f"<tg-emoji emoji-id=\"5339382185654775714\">🎗️</tg-emoji> <b>CATCHER PROFILE</b>\n\n"
        f"<tg-emoji emoji-id=\"5339160183090212029\">👤</tg-emoji> <b>{clean_name}</b>\n"
        f"<tg-emoji emoji-id=\"5336964320930591180\">ℹ️</tg-emoji> <code>{target_id}</code>\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"<tg-emoji emoji-id=\"5337263018726159342\">📈</tg-emoji> <b>Collection Overview</b>\n"
        f"▸ <tg-emoji emoji-id=\"5395444514028529554\">🎴</tg-emoji> Characters: <b>{total_cards:,}</b>  (unique <b>{unique_cards:,}</b>)\n"
        f"▸ <tg-emoji emoji-id=\"5339382185654775714\">🎗️</tg-emoji> Harem Coverage: <b>{harem_percent:.2f}%</b>  ({unique_cards:,}/{total_db_chars:,})\n"
        f"▸ <tg-emoji emoji-id=\"5336964320930591180\">ℹ️</tg-emoji> Experience Level: <b>{exp_level}</b>\n"
        f"▸ <tg-emoji emoji-id=\"5337263018726159342\">📈</tg-emoji> Progress: {p_bar}\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"<tg-emoji emoji-id=\"5395444514028529554\">🎴</tg-emoji> <b>Rarity Breakdown</b>\n"
    )

    for r_name, data in rarity_stats.items():
        pure_name = r_name.split(" ", 1)[-1] if " " in r_name else r_name
        u_cnt = len(data["unique_ids"])
        t_cnt = data["total"]
        emoji = data["emoji"]
        text += f"▸ {emoji} {pure_name}: <b>{u_cnt}</b> ({t_cnt})\n"

    text += (
        f"\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"<tg-emoji emoji-id=\"5447410659077661506\">🌍</tg-emoji> Global Position: <b>#{global_rank:,}</b>"
    )

    media_url = None
    media_type = "photo"
    if user and user.get("favorites"):
        fav_id = user["favorites"][0]
        fav_char = next((c for c in characters if c["id"] == fav_id), None)
        if fav_char:
            media_url = fav_char.get("img_url")
            media_type = fav_char.get("type", "photo")

    if not media_url and characters:
        rand_c = random.choice(characters)
        media_url = rand_c.get("img_url")
        media_type = rand_c.get("type", "photo")

    if not media_url:
        media_url = random.choice(PHOTO_URL)
        media_type = "photo"

    try:
        await send_media_safe(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            media_id=media_url,
            media_type=media_type,
            caption=text,
            parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text(text, parse_mode="HTML")

# ============================================================
#  بخش ۱۰: لیدربورد و آمار
# ============================================================
async def global_leaderboard(update: Update, context: CallbackContext) -> None:
    rows = await top_groups_limited(10)
    msg = "<b>TOP 10 GROUPS WHO GUESSED MOST CHARACTERS</b>\n\n"
    for i, g in enumerate(rows, 1):
        name = html.escape(g["group_name"] or "Unknown")
        if len(name) > 10:
            name = name[:15] + "..."
        msg += f'{i}. <b>{name}</b> ➾ <b>{g["count"]}</b>\n'
    await update.message.reply_photo(photo=random.choice(PHOTO_URL), caption=msg, parse_mode="HTML")

async def ctop(update: Update, context: CallbackContext) -> None:
    rows = await top_users_in_group(update.effective_chat.id, 10)
    msg = "<b>TOP 10 USERS WHO GUESSED CHARACTERS MOST TIME IN THIS GROUP..</b>\n\n"
    for i, u in enumerate(rows, 1):
        uname = u["username"] or "Unknown"
        fname = html.escape(u["first_name"] or "Unknown")
        if len(fname) > 10:
            fname = fname[:15] + "..."
        msg += f'{i}. <a href="https://t.me/{uname}"><b>{fname}</b></a> ➾ <b>{u["count"]}</b>\n'
    await update.message.reply_photo(photo=random.choice(PHOTO_URL), caption=msg, parse_mode="HTML")

async def leaderboard(update: Update, context: CallbackContext) -> None:
    rows = await top_users_global(10)
    msg = "<b>TOP 10 USERS WITH MOST CHARACTERS</b>\n\n"
    for i, u in enumerate(rows, 1):
        uname = u["username"] or "Unknown"
        fname = html.escape(u["first_name"] or "Unknown")
        if len(fname) > 10:
            fname = fname[:15] + "..."
        msg += f'{i}. <a href="https://t.me/{uname}"><b>{fname}</b></a> ➾ <b>{u["cnt"]}</b>\n'
    await update.message.reply_photo(photo=random.choice(PHOTO_URL), caption=msg, parse_mode="HTML")

async def character_info(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /cinfo <character_id>")
        return

    cid = context.args[0]
    character = await character_by_id(cid)
    if not character:
        await update.message.reply_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Character not found.", parse_mode="HTML")
        return

    global_count = await character_global_count(cid)
    owners = await top_owners_of_character(cid, 10)

    event_line = f'<tg-emoji emoji-id="5339183745280798256">🎉</tg-emoji> <b>Event:</b> {get_event_emoji(character["event"])}\n' if character.get("event") else ""

    caption = (
        f'<tg-emoji emoji-id="5337327602149389705">🌸</tg-emoji> <b>Name:</b> {escape(character["name"])}\n'
        f'<tg-emoji emoji-id="5339079278791258832">📺</tg-emoji> <b>Anime:</b> {escape(character["anime"])}\n'
        f'<tg-emoji emoji-id="5336969552200758497">✨</tg-emoji> <b>Rarity:</b> {escape(character["rarity"])}\n'
        f'{event_line}'
        f'<tg-emoji emoji-id="5834605246462039136">🪙</tg-emoji> <b>ID:</b> <code>{escape(cid)}</code>\n'
        f'<tg-emoji emoji-id="5395444514028529554">📦</tg-emoji> <b>Total owned globally:</b> {global_count}\n\n'
        f'<b>🏆 Top 10 owners:</b>\n'
    )

    if owners:
        for i, row in enumerate(owners, 1):
            uname = row["username"]
            fname = escape(row["first_name"] or "Unknown")
            if len(fname) > 15:
                fname = fname[:15] + "..."
            name_display = f'<a href="https://t.me/{uname}">{fname}</a>' if uname else fname
            caption += f'{i}. {name_display} ➾ <b>{row["cnt"]}</b>\n'
    else:
        caption += "Nobody owns this character yet."

    try:
        await send_media_safe(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            media_id=character["img_url"],
            media_type=character.get("type", "photo"),
            caption=caption,
            parse_mode="HTML",
        )
    except Exception:
        await update.message.reply_text(caption, parse_mode="HTML")

async def stats(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    uc = await count_users()
    gc = len(await distinct_group_ids())
    await update.message.reply_text(f"Total Users: {uc}\nTotal groups: {gc}")

async def send_users_document(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("only For Sudo users...")
        return
    rows = await all_pm_users()
    user_list = "".join(f"{r['first_name']}\n" for r in rows)
    with io.BytesIO(user_list.encode("utf-8")) as out_file:
        out_file.name = "users.txt"
        await context.bot.send_document(chat_id=update.effective_chat.id, document=out_file)

async def send_groups_document(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    rows = await all_top_groups()
    group_list = "".join(f"{r['group_name']}\n\n" for r in rows)
    with io.BytesIO(group_list.encode("utf-8")) as out_file:
        out_file.name = "groups.txt"
        await context.bot.send_document(chat_id=update.effective_chat.id, document=out_file)

# ============================================================
#  بخش ۱۱: شروع و راهنما
# ============================================================
async def start(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    existing = await get_pm_user(user_id)
    if existing is None:
        await db_execute("none", "INSERT INTO pm_users(id, first_name, username) VALUES(?,?,?)",
                         (user_id, first_name, username), write=True)
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"New user Started The Bot..\n User: <a href='tg://user?id={user_id}'>{escape(first_name)}</a>",
            parse_mode="HTML",
        )

    keyboard = [
        [InlineKeyboardButton("Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ", url=f"http://t.me/{BOT_USERNAME}?startgroup=new", style="primary", icon_custom_emoji_id=EMOJI_IDS["add"])],
        [InlineKeyboardButton("Sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}", style="primary", icon_custom_emoji_id=EMOJI_IDS["support"]),
         InlineKeyboardButton("Uᴘᴅᴀᴛᴇꜱ", url=f"https://t.me/{UPDATE_CHAT}", style="primary", icon_custom_emoji_id=EMOJI_IDS["updates"])],
        [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help", style="success", icon_custom_emoji_id=EMOJI_IDS["help"])],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    photo_url = random.choice(PHOTO_URL)

    if update.effective_chat.type == "private":
        caption = (
            "<tg-emoji emoji-id=\"5395444514028529554\">🎴</tg-emoji> <b>Welcome to the Character Catcher!</b> <tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji>\n\n"
            "I drop random <b>Waifu &amp; Husbando</b> characters in your group chats. "
            "Add me, chat away, and every so often a new character appears for everyone to catch.\n\n"
            "<tg-emoji emoji-id=\"5339055695125837138\">🎯</tg-emoji> <code>/guess</code> — claim the character for your Harem\n"
            "<tg-emoji emoji-id=\"5339174987842482774\">📖</tg-emoji> <code>/harem</code> — view your collection\n\n"
            "<i>Tap Help below to see the full command list.</i>"
        )
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url, caption=caption,
                                     reply_markup=reply_markup, parse_mode="HTML")
    else:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url,
                                     caption="<tg-emoji emoji-id=\"5395444514028529554\">🎴</tg-emoji> <b>I'm alive!</b> <tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji>\nMessage me in PM for more info.",
                                     reply_markup=reply_markup, parse_mode="HTML")

_HELP_TEXT = """<tg-emoji emoji-id=\"5339174987842482774\">📖</tg-emoji> <b>Help &amp; Commands</b>

<tg-emoji emoji-id=\"5339055695125837138\">🎯</tg-emoji> <b>Catching</b>
<code>/guess</code> — Guess the character (groups only)
<code>/fav</code> — Set your favorite character

<tg-emoji emoji-id=\"5339160183090212029\">👤</tg-emoji> <b>Profile &amp; Collection</b>
<code>/profile</code> — View your Catcher profile &amp; progress
<code>/harem</code> or <code>/collection</code> — View your collection
<code>/trade</code> — Trade characters with another user
<code>/gift</code> — Gift a character from your collection

<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> <b>Economy</b>
<code>/bal</code> — Check your coin balance
<code>/daily</code> — Claim your daily coins
<code>/sell &lt;id&gt;</code> — Sell a character to the bot
<code>/gacha</code> — Roll the gacha

<tg-emoji emoji-id=\"5339468076410759828\">🛒</tg-emoji> <b>Marketplace</b>
<code>/market</code> — Browse the player marketplace
<code>/market sell &lt;id&gt; &lt;price&gt;</code> — List a character
<code>/market buy &lt;token&gt;</code> — Buy a listed character
<code>/market cancel &lt;token&gt;</code> — Cancel your listing
<code>/mymarket</code> — View your active listings

<tg-emoji emoji-id=\"5337020112555767066\">🏆</tg-emoji> <b>Leaderboards &amp; Events</b>
<code>/topgroups</code> — Top groups
<code>/top</code> — Top users
<code>/ctop</code> — Chat leaderboard
<code>/event</code> — Current active event
<code>/events</code> — All available events"""

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        help_keyboard = [[InlineKeyboardButton("Bᴀᴄᴋ", callback_data="back", style="danger", icon_custom_emoji_id=EMOJI_IDS["back"])]]
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id, message_id=query.message.message_id,
            caption=_HELP_TEXT, reply_markup=InlineKeyboardMarkup(help_keyboard), parse_mode="HTML")
    elif query.data == "back":
        caption = (
            "<tg-emoji emoji-id=\"5395444514028529554\">🎴</tg-emoji> <b>Welcome to the Character Catcher!</b> <tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji>\n\n"
            "I drop random <b>Waifu &amp; Husbando</b> characters in your group chats. "
            "Add me and every so often a new character appears for everyone to catch."
        )
        keyboard = [
            [InlineKeyboardButton("Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ", url=f"http://t.me/{BOT_USERNAME}?startgroup=new", style="primary", icon_custom_emoji_id=EMOJI_IDS["add"])],
            [InlineKeyboardButton("Sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}", style="primary", icon_custom_emoji_id=EMOJI_IDS["support"]),
             InlineKeyboardButton("Uᴘᴅᴀᴛᴇꜱ", url=f"https://t.me/{UPDATE_CHAT}", style="primary", icon_custom_emoji_id=EMOJI_IDS["updates"])],
            [InlineKeyboardButton("Hᴇʟᴘ", callback_data="help", style="success", icon_custom_emoji_id=EMOJI_IDS["help"])],
        ]
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id, message_id=query.message.message_id,
            caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ============================================================
#  بخش ۱۲: کوئری اینلاین
# ============================================================
async def inlinequery(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    user = None
    if query.startswith("collection."):
        user_id, *search_terms = query.split(" ")[0].split(".")[1], " ".join(query.split(" ")[1:])
        if user_id.isdigit():
            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = await get_user(int(user_id))
                user_collection_cache[user_id] = user

            if user:
                all_chars = list({v["id"]: v for v in user["characters"]}.values())
                if search_terms:
                    rx = re.compile(" ".join(search_terms), re.IGNORECASE)
                    all_chars = [c for c in all_chars if rx.search(c["name"]) or rx.search(c["anime"])]
            else:
                all_chars = []
        else:
            all_chars = []
    else:
        if query:
            all_chars = await characters_search(query)
        else:
            if "all_characters" in all_characters_cache:
                all_chars = all_characters_cache["all_characters"]
            else:
                all_chars = await characters_all()
                all_characters_cache["all_characters"] = all_chars

    characters = all_chars[offset:offset + 50]
    end_index = offset + len(characters)
    # اگه هنوز آیتم بیشتری بعد از این صفحه مونده، next_offset رو می‌فرستیم تا
    # کلاینت تلگرام همین که کاربر اسکرول کرد، صفحه‌ی بعدی رو با آفست جدید بخواد.
    # اگه دیگه چیزی نمونده، رشته‌ی خالی می‌فرستیم تا تلگرام بفهمه نتایج تموم شده
    # (فرستادن یه عدد غیرصفر همیشگی باعث می‌شد کلاینت فکر کنه همیشه نتیجه‌ی
    # بیشتری هست ولی بی‌فایده دوباره و دوباره با همون آفست درخواست بزنه).
    next_offset = str(end_index) if end_index < len(all_chars) else ""

    results = []
    for character in characters:
        global_count = await character_global_count(character["id"])
        anime_characters = await characters_count_by_anime(character["anime"])

        if query.startswith("collection.") and user:
            uc = sum(c["id"] == character["id"] for c in user["characters"])
            ua = sum(c["anime"] == character["anime"] for c in user["characters"])
            
            event_mark = f" {get_event_emoji(character['event'])}" if character.get("event") else ""

            caption = (f"<b> Look At <a href='tg://user?id={user['id']}'>{(escape(user.get('first_name', user['id'])))}</a>'s Character</b>\n\n"
                       f"<tg-emoji emoji-id=\"5337327602149389705\">🌸</tg-emoji> <b>{character['id']} {escape(character['name'])}{event_mark} (x{uc})</b>\n"
                       f"🏖️ <b>Anime:</b> {escape(character['anime'])} ({ua}/{anime_characters})\n"
                       f"<tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji> <b>Rarity:</b> {escape(character['rarity'])}")
        else:
            event_mark = f" {get_event_emoji(character['event'])}" if character.get("event") else ""
            caption = (f"<b>Look At This Character !!</b>\n\n"
                       f"<tg-emoji emoji-id=\"5337327602149389705\">🌸</tg-emoji>: <b>{escape(character['name'])}{event_mark}</b>\n🏖️: <b>{escape(character['anime'])}</b>\n"
                       f"<b>{escape(character['rarity'])}</b>\n🆔️: <b>{character['id']}</b>\n\n"
                       f"<b>Globally Guessed {global_count} Times...</b>")

        m_type = character.get("type", "photo")
        res_id = f"{character['id']}_{time.time()}"
        
        if m_type == "video":
            results.append(InlineQueryResultCachedVideo(
                id=res_id, video_file_id=character["img_url"], title=character["name"], description=character["anime"], caption=caption, parse_mode="HTML"
            ))
        elif m_type == "animation":
            results.append(InlineQueryResultCachedMpeg4Gif(
                id=res_id, mpeg4_file_id=character["img_url"], title=character["name"], caption=caption, parse_mode="HTML"
            ))
        else:
            results.append(InlineQueryResultCachedPhoto(
                id=res_id, photo_file_id=character["img_url"], title=character["name"], description=character["anime"], caption=caption, parse_mode="HTML"
            ))

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

# ============================================================
#  بخش ۱۳: آپلود و ویرایش کاراکترها
# ============================================================
WRONG_FORMAT_TEXT = """Wrong <tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> format...

To upload a character, send a Photo/Video/GIF with a caption like this:

/upload
Character Name
Anime Name
Rarity Number
Event Name  (optional)
Code  (optional)

rarity_map = 1 (⚪️ Common), 2 (🟢 Medium), 3 (🟣 Rare), 4 (🟡 Legendary), 5 (🪼 Elemental), 6 (⛩️ Mastery), 7 (🎗 Celestial), 8 (🎭 Asteral)"""

UPDATE_PHOTO_FORMAT_TEXT = """Wrong <tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> format...

To change a character's media, send the new Photo/Video/GIF with a caption like this:

/update
Code"""

def _parse_caption_fields(raw_text: str) -> list:
    lines = [line.strip() for line in (raw_text or "").split("\n")]
    if lines and (lines[0].lower().startswith("/upload") or lines[0].lower().startswith("/update")):
        data = lines[1:]
    else:
        data = lines
    while data and data[-1] == "":
        data.pop()
    return data

async def _do_upload(update: Update, context: CallbackContext, photo_message, raw_text: str) -> None:
    data = _parse_caption_fields(raw_text)

    if len(data) not in (3, 4, 5):
        await update.effective_message.reply_text(WRONG_FORMAT_TEXT)
        return

    character_name = data[0].replace("-", " ").title()
    anime = data[1].replace("-", " ").title()

    try:
        rarity = RARITY_MAP[int(data[2])]
    except (ValueError, KeyError):
        await update.effective_message.reply_text("Invalid rarity. Please use 1, 2, 3, 4, 5, or 6.")
        return

    event = None
    custom_code = None
    if len(data) == 4:
        raw_field = data[3].strip()
        # اگه خط چهارم خالی نیست، چک میکنیم که ایونت معتبر باشه یا عدد (کد سفارشی)
        if raw_field:
            if raw_field.isdigit():
                # عدد تنها = کد سفارشی، ایونت نداریم
                custom_code = raw_field
            else:
                # متن باید حتماً توی لیست ایونت‌ها باشه
                normalized = DEFAULT_EVENTS_LOWER.get(raw_field.lower())
                if normalized is None:
                    valid_list = "، ".join(DEFAULT_EVENTS.keys())
                    await update.effective_message.reply_text(
                        f"❌ <b>ایونت «{escape(raw_field)}» معتبر نیست.</b>\n\n"
                        f"ایونت‌های مجاز:\n<code>{valid_list}</code>",
                        parse_mode="HTML"
                    )
                    return
                event = normalized
    elif len(data) == 5:
        raw_event = data[3].strip()
        custom_code = data[4].strip()
        if raw_event:
            normalized = DEFAULT_EVENTS_LOWER.get(raw_event.lower())
            if normalized is None:
                valid_list = "، ".join(DEFAULT_EVENTS.keys())
                await update.effective_message.reply_text(
                    f"❌ <b>ایونت «{escape(raw_event)}» معتبر نیست.</b>\n\n"
                    f"ایونت‌های مجاز:\n<code>{valid_list}</code>",
                    parse_mode="HTML"
                )
                return
            event = normalized

    if custom_code:
        if await character_by_id(custom_code):
            await update.effective_message.reply_text("This Code is already used by another character. Choose a different one.")
            return
        cid = custom_code
    else:
        cid = str(await next_sequence("character_id")).zfill(2)

    media_type = 'photo'
    if getattr(photo_message, 'photo', None):
        media_file_id = photo_message.photo[-1].file_id
        media_type = 'photo'
    elif getattr(photo_message, 'video', None):
        media_file_id = photo_message.video.file_id
        media_type = 'video'
    elif getattr(photo_message, 'animation', None):
        media_file_id = photo_message.animation.file_id
        media_type = 'animation'
    else:
        await update.effective_message.reply_text("Please send a valid media (Photo, Video, or GIF).")
        return

    character = {
        "img_url": media_file_id,
        "type": media_type,
        "name": character_name,
        "anime": anime,
        "rarity": rarity,
        "event": event,
        "id": cid,
    }

    caption_lines = [
        f"<b>Character Name:</b> {escape(character_name)}",
        f"<b>Anime Name:</b> {escape(anime)}",
        f"<b>Rarity:</b> {escape(rarity)}",
    ]
    if event:
        caption_lines.append(f"<b>Event:</b> {escape(event)}")
    caption_lines.append(f"<b>ID:</b> {cid}")
    caption_lines.append(f'Added by <a href="tg://user?id={update.effective_user.id}">{escape(update.effective_user.first_name)}</a>')

    try:
        sent = await send_media_safe(
            bot=context.bot, chat_id=CHARA_CHANNEL_ID, media_id=media_file_id, media_type=media_type,
            caption="\n".join(caption_lines), parse_mode="HTML"
        )
        character["message_id"] = sent.message_id
        await insert_character(character)
        await update.effective_message.reply_text("CHARACTER ADDED....")
    except Exception as e:
        await insert_character(character)
        await update.effective_message.reply_text(f"Character Added but failed to send to Channel. Error: {e}")

async def _do_update_photo(update: Update, context: CallbackContext, photo_message, raw_text: str) -> None:
    data = _parse_caption_fields(raw_text)

    if len(data) != 1:
        await update.effective_message.reply_text(UPDATE_PHOTO_FORMAT_TEXT)
        return

    cid = data[0]
    character = await character_by_id(cid)
    if not character:
        await update.effective_message.reply_text("Character not found.")
        return

    media_type = 'photo'
    if getattr(photo_message, 'photo', None):
        media_file_id = photo_message.photo[-1].file_id
        media_type = 'photo'
    elif getattr(photo_message, 'video', None):
        media_file_id = photo_message.video.file_id
        media_type = 'video'
    elif getattr(photo_message, 'animation', None):
        media_file_id = photo_message.animation.file_id
        media_type = 'animation'
    else:
        await update.effective_message.reply_text("Please send a valid media (Photo, Video, or GIF).")
        return

    try:
        try:
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character["message_id"])
        except Exception:
            pass

        caption_lines = [
            f'<b>Character Name:</b> {escape(character["name"])}',
            f'<b>Anime Name:</b> {escape(character["anime"])}',
            f'<b>Rarity:</b> {escape(character["rarity"])}',
        ]
        if character.get("event"):
            caption_lines.append(f'<b>Event:</b> {escape(character["event"])}')
        caption_lines.append(f'<b>ID:</b> {character["id"]}')
        caption_lines.append(f'Updated by <a href="tg://user?id={update.effective_user.id}">{escape(update.effective_user.first_name)}</a>')

        sent = await send_media_safe(
            bot=context.bot, chat_id=CHARA_CHANNEL_ID, media_id=media_file_id, media_type=media_type,
            caption="\n".join(caption_lines), parse_mode="HTML"
        )
        await update_character(cid, "img_url", media_file_id)
        try: await update_character(cid, "type", media_type)
        except: pass
        
        await update_character(cid, "message_id", sent.message_id)
        await update.effective_message.reply_text("Updated Done in Database....")
    except Exception:
        await update.effective_message.reply_text("Failed to update character media.")

async def photo_command_handler(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    if not is_owner_or_sudo(update.effective_user.id):
        return

    caption = message.caption or ""
    first_line = caption.split("\n", 1)[0].strip().lower()

    if first_line.startswith("/upload"):
        await _do_upload(update, context, message, caption)
    elif first_line.startswith("/update"):
        await _do_update_photo(update, context, message, caption)

async def upload(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Ask My Owner...")
        return

    reply = update.message.reply_to_message
    if reply and (reply.photo or getattr(reply, 'video', None) or getattr(reply, 'animation', None)):
        await _do_upload(update, context, reply, reply.caption or "")
        return

    await update.message.reply_text(WRONG_FORMAT_TEXT)

async def delete(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Ask my Owner to use this Command...")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Incorrect format... Please use: /delete ID")
            return

        existing = await db_execute("one", "SELECT message_id FROM characters WHERE id=?", (args[0],))
        if existing:
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=existing["message_id"])
            await delete_character(args[0])
            await update.message.reply_text("DONE")
        else:
            await delete_character(args[0])
            await update.message.reply_text("Deleted Successfully from db, but character not found In Channel")
    except Exception as e:
        await update.message.reply_text(f"{str(e)}")

async def update_char_field(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("You do not have permission to use this command.")
        return

    reply = update.message.reply_to_message
    if reply and (reply.photo or getattr(reply, 'video', None) or getattr(reply, 'animation', None)):
        await _do_update_photo(update, context, reply, update.message.text or "")
        return

    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Incorrect format. Please use: /update id field new_value")
            return

        character = await character_by_id(args[0])
        if not character:
            await update.message.reply_text("Character not found.")
            return

        valid_fields = ["name", "anime", "rarity", "event"]
        if args[1] not in valid_fields:
            await update.message.reply_text(f"Invalid field. Please use one of: {', '.join(valid_fields)}")
            return

        if args[1] in ["name", "anime"]:
            new_value = " ".join(args[2:]).replace("-", " ").title()
        elif args[1] == "rarity":
            try:
                new_value = RARITY_MAP[int(args[2])]
            except (ValueError, KeyError):
                await update.message.reply_text("Invalid rarity. Please use 1, 2, 3, 4, 5, or 6.")
                return
        elif args[1] == "event":
            new_value = " ".join(args[2:])

        await update_character(args[0], args[1], new_value)
        character[args[1]] = new_value
        caption_lines = [
            f'<b>Character Name:</b> {escape(character["name"])}',
            f'<b>Anime Name:</b> {escape(character["anime"])}',
            f'<b>Rarity:</b> {escape(character["rarity"])}',
        ]
        if character.get("event"):
            caption_lines.append(f'<b>Event:</b> {escape(character["event"])}')
        caption_lines.append(f'<b>ID:</b> {character["id"]}')
        caption_lines.append(f'Updated by <a href="tg://user?id={update.effective_user.id}">{escape(update.effective_user.first_name)}</a>')
        await context.bot.edit_message_caption(
            chat_id=CHARA_CHANNEL_ID, message_id=character["message_id"],
            caption="\n".join(caption_lines),
            parse_mode="HTML")

        await update.message.reply_text("Updated Done in Database....")
    except Exception:
        await update.message.reply_text("Failed to update character.")

# ============================================================
#  بخش ۱۴: ارسال همگانی، بکاپ و پینگ
# ============================================================
async def broadcast(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message to broadcast.")
        return
    msg = update.message.reply_to_message

    targets = set(await distinct_top_group_ids() + await distinct_pm_user_ids())
    failed = 0
    for chat_id in targets:
        try:
            await context.bot.forward_message(chat_id=chat_id, from_chat_id=msg.chat_id, message_id=msg.message_id)
        except Exception:
            failed += 1
    await update.message.reply_text(f"Broadcast complete. Failed to send to {failed} chats/users.")

async def ping(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Nouu.. its Sudo user's Command..")
        return
    start_time = time.time()
    message = await update.message.reply_text("Pong!")
    await message.edit_text(f"Pong! {round((time.time() - start_time) * 1000, 3)}ms")

async def export_db(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only the owner can do this.")
        return
    with open(DB_PATH, "rb") as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename="db.sqlite3")

async def import_db(update: Update, context: CallbackContext) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only the owner can do this.")
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Reply to a db file (document) to import.")
        return

    doc = update.message.reply_to_message.document
    new_path = "db_imported.sqlite3"
    file = await context.bot.get_file(doc.file_id)
    data = await file.download_as_bytearray()
    with open(new_path, "wb") as f:
        f.write(data)

    os.replace(new_path, DB_PATH)
    await update.message.reply_text("Database replaced successfully.")

async def empty_codes_command(update: Update, context: CallbackContext) -> None:
    """
    /emptycodes — فقط برای اونر
    کدهای (IDهای) خالی از ۰۰ تا آخرین کارت آپلودشده رو پیدا میکنه و
    توی یه فایل txt میفرسته.
    """
    if str(update.effective_user.id) != str(OWNER_ID):
        await update.message.reply_text("❌ این دستور فقط برای اونر هست.")
        return

    # همه‌ی ID های موجود رو میگیریم
    rows = await db_execute("all", "SELECT id FROM characters ORDER BY id")
    existing_ids = {r["id"] for r in rows}

    if not existing_ids:
        await update.message.reply_text("هنوز هیچ کاراکتری آپلود نشده.")
        return

    # آخرین sequence ثبت‌شده رو بگیر
    seq_row = await db_execute("one", "SELECT sequence_value FROM sequences WHERE id='character_id'")
    max_seq = seq_row["sequence_value"] if seq_row else 0

    # کدهای عددی موجود (zfill(2) شده) رو جدا کن؛ کدهای سفارشی غیرعددی رو نادیده بگیر
    numeric_existing = set()
    for cid in existing_ids:
        try:
            numeric_existing.add(int(cid))
        except ValueError:
            pass  # کد سفارشی غیرعددی — نادیده

    # خلاءها رو پیدا کن: از ۰ تا max_seq
    gaps = []
    for i in range(0, max_seq + 1):
        if i not in numeric_existing:
            gaps.append(str(i).zfill(2))

    if not gaps:
        await update.message.reply_text("✅ هیچ خلائی پیدا نشد! همه کدها پُر هستن.")
        return

    content_lines = [
        f"کدهای خالی از ۰۰ تا آخرین آرت (sequence={max_seq:02d})",
        f"تعداد کل خلاء: {len(gaps)}",
        "=" * 40,
    ] + gaps

    file_content = "\n".join(content_lines).encode("utf-8")
    with io.BytesIO(file_content) as out_file:
        out_file.name = "empty_codes.txt"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=out_file,
            caption=f"🗂 <b>کدهای خالی: {len(gaps)} عدد</b>",
            parse_mode="HTML",
        )

# ============================================================
#  بخش ۱۵: معامله و هدیه کاراکتر
# ============================================================
pending_trades = {}
pending_gifts = {}
pending_coin_transfers = {}

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    message = update.effective_message
    if not message or not message.from_user:
        return

    sender_id = message.from_user.id
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text("You need to reply to a user's message to trade a character!")
        return

    receiver_id = message.reply_to_message.from_user.id
    if sender_id == receiver_id:
        await message.reply_text("You can't trade a character with yourself!")
        return

    if len(context.args) != 2:
        await message.reply_text("You need to provide two character IDs!")
        return

    sender_character_id, receiver_character_id = context.args[0], context.args[1]
    sender = await get_user(sender_id)
    receiver = await get_user(receiver_id)

    if not sender or not receiver:
        await message.reply_text("One of the users is not registered.")
        return

    sender_character = next((c for c in sender["characters"] if c["id"] == sender_character_id), None)
    receiver_character = next((c for c in receiver["characters"] if c["id"] == receiver_character_id), None)

    if not sender_character:
        await message.reply_text("You don't have the character you're trying to trade!")
        return
    if not receiver_character:
        await message.reply_text("The other user doesn't have the character they're trying to trade!")
        return

    pending_trades[(sender_id, receiver_id)] = (sender_character_id, receiver_character_id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Cᴏɴғɪʀᴍ", callback_data="confirm_trade", style="success", icon_custom_emoji_id=EMOJI_IDS["confirm"]),
            InlineKeyboardButton("Cᴀɴᴄᴇʟ", callback_data="cancel_trade", style="danger", icon_custom_emoji_id=EMOJI_IDS["cancel"]),
        ]
    ])

    target_name = escape(message.reply_to_message.from_user.first_name or "User")
    await message.reply_text(
        f"<a href='tg://user?id={receiver_id}'>{target_name}</a>, do you accept this trade?",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

async def trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()
    receiver_id = query.from_user.id

    trade_key = next((key for key in pending_trades if key[1] == receiver_id), None)
    if trade_key is None:
        await query.answer("This trade is no longer available.", show_alert=True)
        return

    sender_id, _ = trade_key
    sc_id, rc_id = pending_trades[trade_key]

    if query.data == "cancel_trade":
        pending_trades.pop(trade_key, None)
        if query.message:
            await query.message.edit_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>️ Sad Cancelled....")
        return

    sender = await get_user(sender_id)
    receiver = await get_user(receiver_id)

    if not sender or not receiver:
        pending_trades.pop(trade_key, None)
        await query.answer("One of the users is no longer registered.", show_alert=True)
        return

    sender_character = next((c for c in sender["characters"] if c["id"] == sc_id), None)
    receiver_character = next((c for c in receiver["characters"] if c["id"] == rc_id), None)

    if not sender_character or not receiver_character:
        pending_trades.pop(trade_key, None)
        await query.answer("One of the characters is no longer available.", show_alert=True)
        return

    sender["characters"].remove(sender_character)
    receiver["characters"].remove(receiver_character)
    sender["characters"].append(receiver_character)
    receiver["characters"].append(sender_character)

    await set_user_characters(sender_id, sender["characters"])
    await set_user_characters(receiver_id, receiver["characters"])

    pending_trades.pop(trade_key, None)
    if query.message:
        await query.message.edit_text("<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Trade completed successfully!")

async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    message = update.effective_message
    if not message or not message.from_user:
        return

    sender_id = message.from_user.id
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text("You need to reply to a user's message to gift a character!")
        return

    receiver_id = message.reply_to_message.from_user.id
    receiver_username = message.reply_to_message.from_user.username
    receiver_first_name = message.reply_to_message.from_user.first_name or "User"

    if sender_id == receiver_id:
        await message.reply_text("You can't gift a character to yourself!")
        return

    if len(context.args) != 1:
        await message.reply_text("You need to provide a character ID!")
        return

    sender = await get_user(sender_id)
    if not sender:
        await message.reply_text("You are not registered.")
        return

    character = next((c for c in sender["characters"] if c["id"] == context.args[0]), None)
    if not character:
        await message.reply_text("You don't have this character in your collection!")
        return

    pending_gifts[(sender_id, receiver_id)] = {
        "character": character,
        "receiver_username": receiver_username,
        "receiver_first_name": receiver_first_name,
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Cᴏɴғɪʀᴍ", callback_data="confirm_gift", style="success", icon_custom_emoji_id=EMOJI_IDS["confirm"]),
            InlineKeyboardButton("Cᴀɴᴄᴇʟ", callback_data="cancel_gift", style="danger", icon_custom_emoji_id=EMOJI_IDS["cancel"]),
        ]
    ])

    media_id = character.get("img_url")
    m_type = character.get("type", "photo")
    caption = f"Do You Really Want To Gift <b>{escape(character['name'])}</b> To <a href='tg://user?id={receiver_id}'>{escape(receiver_first_name)}</a>?"

    await send_media_safe(
        bot=context.bot,
        chat_id=message.chat_id,
        media_id=media_id,
        media_type=m_type,
        caption=caption,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def gift_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()
    sender_id = query.from_user.id

    gift_key = next((key for key in pending_gifts if key[0] == sender_id), None)
    if gift_key is None:
        await query.answer("This gift is no longer available.", show_alert=True)
        return

    receiver_id = gift_key[1]
    gift_data = pending_gifts[gift_key]
    character = gift_data["character"]

    if query.data == "cancel_gift":
        pending_gifts.pop(gift_key, None)
        if query.message:
            try:
                await query.message.edit_caption(caption="<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>️ Gift Cancelled....", reply_markup=None)
            except Exception:
                await query.message.edit_text("<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>️ Gift Cancelled....", reply_markup=None)
        return

    sender = await get_user(sender_id)
    receiver = await get_user(receiver_id)

    if not sender:
        pending_gifts.pop(gift_key, None)
        await query.answer("Sender is no longer registered.", show_alert=True)
        return

    sender_character = next((c for c in sender["characters"] if c["id"] == character["id"]), None)
    if sender_character is None:
        pending_gifts.pop(gift_key, None)
        await query.answer("This character is no longer in your collection.", show_alert=True)
        return

    sender["characters"].remove(sender_character)
    await set_user_characters(sender_id, sender["characters"])

    if receiver:
        receiver["characters"].append(character)
        await set_user_characters(receiver_id, receiver["characters"])
    else:
        await upsert_user(receiver_id, gift_data["receiver_username"], gift_data["receiver_first_name"])
        await add_user_character(receiver_id, character)

    pending_gifts.pop(gift_key, None)
    if query.message:
        success_msg = f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> You have successfully gifted <b>{escape(character['name'])}</b> to {escape(gift_data['receiver_first_name'])}!"
        try:
            await query.message.edit_caption(caption=success_msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            await query.message.edit_text(success_msg, parse_mode="HTML", reply_markup=None)

async def change_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.from_user or not update.effective_chat:
        return

    user_id = message.from_user.id
    chat_id = update.effective_chat.id
    is_privileged = is_owner_or_sudo(user_id)

    if not is_privileged:
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ("administrator", "creator"):
                await message.reply_text("You are not an Admin.")
                return
        except Exception as e:
            await message.reply_text(f"Failed to check admin status: {e}")
            return

    if len(context.args) != 1:
        await message.reply_text("Please use: /changetime NUMBER")
        return

    try:
        new_frequency = int(context.args[0])
    except ValueError:
        await message.reply_text("The frequency must be a number.")
        return

    if new_frequency <= 0:
        await message.reply_text("The frequency must be a positive number.")
        return

    # فقط اونر و سودو اجازه دارن زیر ۱۰۰ هم ست کنن؛ ادمین‌های عادی همون محدودیت قبلی رو دارن.
    if not is_privileged and new_frequency < 100:
        await message.reply_text("The message frequency must be greater than or equal to 100.")
        return

    await set_frequency(str(chat_id), new_frequency)
    await message.reply_text(f"Successfully changed {new_frequency}")

# ============================================================
#  بخش ۱۶: مدیریت ایونت‌ها و ریرتی
# ============================================================
async def set_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setevent Event Name")
        return
    event_name = " ".join(context.args)
    await set_active_event(event_name)
    count = len(await characters_by_event(event_name))
    await update.message.reply_text(f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Event set to: {event_name}\nCharacters found for this event: {count}", parse_mode="HTML")

async def end_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    await clear_active_event()
    await update.message.reply_text("<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Event ended. Normal characters will spawn now.", parse_mode="HTML")

async def current_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    events_enabled = await is_event_system_enabled()
    system_line = (
        "<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Event system: ON (normal restrictions apply)\n\n"
        if events_enabled else
        "<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Event system: OFF (all characters spawn regardless of event, via /eventsoff)\n\n"
    )
    active_event = await get_active_event()
    if not active_event:
        await update.message.reply_text(system_line + "No active event right now.", parse_mode="HTML")
        return
    chars = await characters_by_event(active_event)
    msg = system_line + f"<tg-emoji emoji-id=\"5339183745280798256\">🎉</tg-emoji> Active Event: <b>{escape(active_event)}</b>\nCharacters: {len(chars)}\n\n"
    for c in chars:
        msg += f'{c["id"]} - {c["name"]} ({c["rarity"]})\n'
    await update.message.reply_text(msg, parse_mode="HTML")

async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = await db_execute("all", "SELECT DISTINCT event FROM characters WHERE event IS NOT NULL AND event != ''")
    db_events = {r["event"] for r in rows if r["event"]} if rows else set()
    all_event_names = set(DEFAULT_EVENTS.keys()).union(db_events)
    
    msg = "<b><tg-emoji emoji-id=\"5413879192267805083\">📅</tg-emoji> All Events:</b>\n\n"
    for ev_name in sorted(all_event_names):
        chars = await characters_by_event(ev_name)
        emoji = get_event_emoji(ev_name)
        msg += f"{emoji} <b>{escape(ev_name)}</b> — {len(chars)} characters\n"
        
    await update.message.reply_text(msg, parse_mode="HTML")

async def rarity_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    if not context.args or not context.args[0].isdigit() or int(context.args[0]) not in RARITY_MAP:
        await update.message.reply_text("Usage: /rarityon <1-6>")
        return
    rarity = RARITY_MAP[int(context.args[0])]
    await set_rarity_enabled(rarity, True)
    await update.message.reply_text(f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Spawning enabled for rarity: {rarity}", parse_mode="HTML")

async def rarity_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    if not context.args or not context.args[0].isdigit() or int(context.args[0]) not in RARITY_MAP:
        await update.message.reply_text("Usage: /rarityoff <1-6>")
        return
    rarity = RARITY_MAP[int(context.args[0])]
    await set_rarity_enabled(rarity, False)
    await update.message.reply_text(f"<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Spawning disabled for rarity: {rarity}", parse_mode="HTML")

async def rarities_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rarities_enabled = await is_rarity_system_enabled()
    system_line = (
        "<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Rarity system: ON (individual settings below apply)\n\n"
        if rarities_enabled else
        "<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Rarity system: OFF (all rarities spawn regardless of the settings below, via /rarityalloff)\n\n"
    )
    disabled = await get_disabled_rarities()
    msg = system_line + "<tg-emoji emoji-id=\"5395444514028529554\">🎴</tg-emoji> Rarity spawn status:\n\n"
    for num, name in RARITY_MAP.items():
        status = "<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> OFF" if name in disabled else "<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> ON"
        msg += f"{num}. {name} — {status}\n"
    await update.message.reply_text(msg, parse_mode="HTML")

async def events_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    await set_event_system_enabled(True)
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Event restriction system is now ON.\n"
        "Normal behavior: only the active event's characters (plus non-event ones) will spawn.",
        parse_mode="HTML",
    )

async def events_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    await set_event_system_enabled(False)
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Event restriction system is now OFF.\n"
        "All characters (event or not) can spawn normally, regardless of the active event.",
        parse_mode="HTML",
    )

async def rarity_all_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    await set_rarity_system_enabled(True)
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> Rarity restriction system is now ON.\n"
        "Individual /rarityon and /rarityoff settings apply again.",
        parse_mode="HTML",
    )

async def rarity_all_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    await set_rarity_system_enabled(False)
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5260293700088511294\">⛔️</tg-emoji> Rarity restriction system is now OFF.\n"
        "All rarities can spawn normally, regardless of individual /rarityon /rarityoff settings.",
        parse_mode="HTML",
    )

async def whoami_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دستور تشخیصی موقت: مشخص می‌کنه این پاسخ از کدوم پروسه و کدوم فایل رو دیسک اومده.
    اگه توی گروه /eventson و بقیه‌ی دستورات جدید جواب نمی‌دن ولی این دستور جواب می‌ده،
    یعنی همین پروسه‌ای که الان جواب داد فایل جدید رو داره و مشکل جای دیگه‌ست
    (یه پروسه‌ی دوم/قدیمی هنوز داره با همون توکن پول می‌کنه).
    """
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    file_path = os.path.abspath(__file__)
    try:
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file_path)))
    except OSError:
        mtime = "unknown"
    await update.message.reply_text(
        "<b>Process debug info</b>\n"
        f"PID: <code>{os.getpid()}</code>\n"
        f"File: <code>{file_path}</code>\n"
        f"File last modified: <code>{mtime}</code>\n"
        f"Has /eventson handler loaded: <code>True</code>",
        parse_mode="HTML",
    )

# ============================================================
#  بخش جدید: انتقال سکه بین پلیرها
# ============================================================
async def transfer_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /transfer <amount>  -- در ریپلای به پیام گیرنده.
    مثل gift، اول یه پیام تأیید/رد نشون می‌ده و فقط بعد از تأیید گیرنده،
    سکه‌ها واقعاً منتقل می‌شن.
    """
    if await is_user_banned(update.effective_user.id):
        return

    message = update.effective_message
    if not message or not message.from_user:
        return

    sender_id = message.from_user.id
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text("باید روی پیام کسی که می‌خوای بهش سکه بدی ریپلای کنی!")
        return

    receiver_user = message.reply_to_message.from_user
    receiver_id = receiver_user.id
    receiver_first_name = receiver_user.first_name or "User"

    if sender_id == receiver_id:
        await message.reply_text("نمی‌تونی به خودت سکه انتقال بدی!")
        return
    if receiver_user.is_bot:
        await message.reply_text("نمی‌تونی به یه ربات سکه انتقال بدی!")
        return

    if not context.args or not context.args[0].isdigit():
        await message.reply_text("<b>Usage:</b> <code>/transfer &lt;amount&gt;</code> (در ریپلای به گیرنده)", parse_mode="HTML")
        return

    amount = int(context.args[0])
    if amount <= 0:
        await message.reply_text("مقدار باید یه عدد مثبت باشه.")
        return

    await upsert_user(sender_id, message.from_user.username, message.from_user.first_name)
    sender = await get_user(sender_id)
    if not sender or sender["coins"] < amount:
        await message.reply_text(
            f"سکه‌ی کافی نداری! موجودی فعلیت: <b>{sender['coins'] if sender else 0:,}</b>",
            parse_mode="HTML",
        )
        return

    pending_coin_transfers[(sender_id, receiver_id)] = {
        "amount": amount,
        "receiver_username": receiver_user.username,
        "receiver_first_name": receiver_first_name,
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Cᴏɴғɪʀᴍ", callback_data="confirm_coin_transfer", style="success", icon_custom_emoji_id=EMOJI_IDS["confirm"]),
            InlineKeyboardButton("Cᴀɴᴄᴇʟ", callback_data="cancel_coin_transfer", style="danger", icon_custom_emoji_id=EMOJI_IDS["cancel"]),
        ]
    ])

    await message.reply_text(
        f"<tg-emoji emoji-id=\"5834605246462039136\">🪙</tg-emoji> آیا مطمئنی می‌خوای <b>{amount:,}</b> سکه به "
        f"<a href='tg://user?id={receiver_id}'>{escape(receiver_first_name)}</a> انتقال بدی؟\n\n"
        "این پیام باید توسط <b>گیرنده</b> تأیید بشه.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )

async def coin_transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()
    clicker_id = query.from_user.id

    transfer_key = next((key for key in pending_coin_transfers if key[1] == clicker_id), None)
    if transfer_key is None:
        await query.answer("این درخواست دیگه معتبر نیست، یا فقط گیرنده می‌تونه تأییدش کنه.", show_alert=True)
        return

    sender_id, receiver_id = transfer_key
    data = pending_coin_transfers[transfer_key]
    amount = data["amount"]

    if query.data == "cancel_coin_transfer":
        pending_coin_transfers.pop(transfer_key, None)
        if query.message:
            await query.message.edit_text(
                "<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>️ انتقال سکه لغو شد.",
                parse_mode="HTML", reply_markup=None,
            )
        return

    sender = await get_user(sender_id)
    if not sender or sender["coins"] < amount:
        pending_coin_transfers.pop(transfer_key, None)
        await query.answer("فرستنده دیگه سکه‌ی کافی نداره.", show_alert=True)
        if query.message:
            await query.message.edit_text(
                "<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji>️ فرستنده دیگه سکه‌ی کافی نداره؛ انتقال لغو شد.",
                parse_mode="HTML", reply_markup=None,
            )
        return

    await upsert_user(receiver_id, data["receiver_username"], data["receiver_first_name"])
    await add_user_coins(sender_id, -amount)
    await add_user_coins(receiver_id, amount)
    pending_coin_transfers.pop(transfer_key, None)

    if query.message:
        await query.message.edit_text(
            f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>{amount:,}</b> سکه با موفقیت به "
            f"<a href='tg://user?id={receiver_id}'>{escape(data['receiver_first_name'])}</a> منتقل شد!",
            parse_mode="HTML", reply_markup=None,
        )

# ============================================================
#  بخش جدید: درصد اسپان ریریتی (rarity weight)
# ============================================================
async def set_rarity_percent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setrarity <rarity_number> <percent>
    درصد اسپان یک ریریتی رو دستی تنظیم می‌کنه (روی جدول rarity_settings.weight
    که از قبل توی send_image برای انتخاب وزن‌دار استفاده می‌شه).
    مثال: /setrarity 1 50   -> ریریتی شماره ۱ (Common) با وزن ۵۰ اسپان می‌شه.
    توجه: این‌ها وزن نسبی هستن نه درصد مطلق؛ اگه می‌خوای دقیقاً «درصد از ۱۰۰»
    باشه، باید مجموع همه‌ی وزن‌های فعال رو خودت ۱۰۰ نگه داری.
    """
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return

    if len(context.args) != 2 or not context.args[0].isdigit() or int(context.args[0]) not in RARITY_MAP:
        rarity_list = "\n".join(f"<code>{k}</code> — {v}" for k, v in RARITY_MAP.items())
        await update.message.reply_text(
            "<b>Usage:</b> <code>/setrarity &lt;rarity_number&gt; &lt;weight&gt;</code>\n\n"
            f"<b>Rarities:</b>\n{rarity_list}\n\n"
            "مثال: <code>/setrarity 1 50</code>",
            parse_mode="HTML",
        )
        return

    try:
        weight = float(context.args[1])
        if weight < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("وزن باید یه عدد مثبت (یا صفر) باشه.")
        return

    rarity = RARITY_MAP[int(context.args[0])]
    await set_rarity_weight(rarity, weight)
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> وزن اسپان <b>{escape(rarity)}</b> "
        f"روی <b>{weight}</b> تنظیم شد.",
        parse_mode="HTML",
    )

async def show_rarity_percent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rarityweights - نمایش وزن فعلی هر ریریتی"""
    lines = []
    for num, name in RARITY_MAP.items():
        w = await get_rarity_weight(name)
        enabled = await is_rarity_enabled(name)
        status = "" if enabled else " (غیرفعال)"
        lines.append(f"<code>{num}</code> {name} — وزن: <b>{w}</b>{status}")
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5336969552200758497\">✨</tg-emoji> <b>وزن‌های فعلی اسپان:</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )

async def instant_spawn(update: Update, context: CallbackContext) -> None:
    if await is_user_banned(update.effective_user.id):
        return

    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("This command only works in groups.")
        return

    user_id = str(update.effective_user.id)
    if not is_owner_or_sudo(user_id):
        try:
            member = await context.bot.get_chat_member(chat_id, update.effective_user.id)
            if member.status not in ("administrator", "creator"):
                await update.message.reply_text("You must be an admin to use this command.")
                return
        except Exception as e:
            LOGGER.error(f"instant_spawn: get_chat_member failed for chat={chat_id} user={user_id}: {e}")
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5210952531676504517\">❌</tg-emoji> Couldn't verify your admin status "
                "(the bot may be missing permissions in this group). Please try again or check the bot's rights.",
                parse_mode="HTML",
            )
            return

    # این دستور کاملاً وضعیت باز/بسته بودن ایونت و ریرتی رو نادیده می‌گیره
    # و یه کاراکتر رو از کل دیتابیس فوری اسپان می‌کنه.
    await send_image(update, context, notify_empty=True, ignore_restrictions=True)
    message_counts[chat_id] = 0

async def set_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("Only For Sudo users...")
        return
    if len(context.args) != 2 or not context.args[0].isdigit() or int(context.args[0]) not in RARITY_MAP:
        await update.message.reply_text("Usage: /setweight <1-6> <weight>")
        return
    try:
        weight = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Weight must be a number.")
        return
    rarity = RARITY_MAP[int(context.args[0])]
    await set_rarity_weight(rarity, weight)
    await update.message.reply_text(f"<tg-emoji emoji-id=\"5339055695125837138\">🎯</tg-emoji> Spawn weight for {rarity} set to {weight}", parse_mode="HTML")

# ============================================================
#  بخش ۱۷: اجرای کد (eval/exec)
# ============================================================
def namespace_of(chat, update, bot):
    if chat not in namespaces:
        namespaces[chat] = {
            "__builtins__": globals()["__builtins__"],
            "bot": bot,
            "effective_message": update.effective_message,
            "effective_user": update.effective_user,
            "effective_chat": update.effective_chat,
            "update": update,
        }
    return namespaces[chat]

def log_input(update):
    LOGGER.info(f"IN: {update.effective_message.text} (user={update.effective_user.id}, chat={update.effective_chat.id})")

async def send_output(msg, bot, update):
    if len(str(msg)) > 2000:
        with io.BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            await bot.send_document(
                chat_id=update.effective_chat.id, document=out_file,
                message_thread_id=update.effective_message.message_thread_id if update.effective_chat.is_forum else None,
            )
    else:
        LOGGER.info(f"OUT: '{msg}'")
        await bot.send_message(
            chat_id=update.effective_chat.id, text=f"`{msg}`", parse_mode=ParseMode.MARKDOWN,
            message_thread_id=update.effective_message.message_thread_id if update.effective_chat.is_forum else None,
        )

def cleanup_code(code):
    if code.startswith("```") and code.endswith("```"):
        return "\n".join(code.split("\n")[1:-1])
    return code.strip("` \n")

async def run_code(func, bot, update):
    log_input(update)
    content = update.message.text.split(" ", 1)[-1]
    body = cleanup_code(content)
    env = namespace_of(update.message.chat_id, update, bot)

    os.chdir(os.getcwd())
    with open("temp.txt", "w") as temp:
        temp.write(body)

    stdout = io.StringIO()
    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
    try:
        exec(to_compile, env)
    except Exception as e:
        return f"{e.__class__.__name__}: {e}"

    func = env["func"]
    try:
        with redirect_stdout(stdout):
            func_return = await func()
    except Exception as e:
        return f"{stdout.getvalue()}{traceback.format_exc()}"
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f"{value}"
            else:
                try:
                    result = f"{repr(eval(body, env))}"
                except Exception:
                    pass
        else:
            result = f"{value}{func_return}"
        if result:
            return result

async def evaluate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.id not in DEV_LIST:
        return
    await send_output(await run_code(eval, context.bot, update), context.bot, update)

async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.id not in DEV_LIST:
        return
    await send_output(await run_code(exec, context.bot, update), context.bot, update)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.from_user.id not in DEV_LIST:
        return
    log_input(update)
    global namespaces
    chat_id = update.message.chat_id
    if chat_id in namespaces:
        del namespaces[chat_id]
    await send_output("Cleared locals.", context.bot, update)

# ============================================================
#  بخش ۱۸: ثبت تمام هندلرها و شروع ربات
# ============================================================
def main() -> None:
    # مهاجرت یک‌باره‌ی اسم ایونت‌ها به فرمت استاندارد (Title Case)، مثلاً
    # "neko" قدیمی روی کاراکترها -> "Neko"
    asyncio.get_event_loop().run_until_complete(normalize_existing_event_names())

    # دستورات نظارتی و مدیریتی ساب/مالک
    application.add_handler(CommandHandler("ban", ban_command, block=False))
    application.add_handler(CommandHandler("unban", unban_command, block=False))
    application.add_handler(CommandHandler(["banned", "bannedlist"], banned_list_command, block=False))
    application.add_handler(CommandHandler(["wipeharem", "resetharem"], wipe_harem_command, block=False))
    application.add_handler(CommandHandler(["wipecoins", "resetcoins"], wipe_coins_command, block=False))
    application.add_handler(CommandHandler("givechar", give_char_command, block=False))
    application.add_handler(CommandHandler("takechar", take_char_command, block=False))
    application.add_handler(CommandHandler("givecoins", give_coins_command, block=False))
    application.add_handler(CommandHandler("takecoins", take_coins_command, block=False))

    # دستورات پایه و حدس
    application.add_handler(CommandHandler(["drop", "spawn", "forcedrop"], force_drop, block=False))
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(CommandHandler("pin", pin_character, block=False))
    application.add_handler(CommandHandler("unpin", unpin_character, block=False))

    # حرم‌سرا و پروفایل کاربر
    application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
    application.add_handler(CommandHandler(["profile", "me", "stats_me"], profile_command, block=False))
    application.add_handler(CallbackQueryHandler(harem_callback, pattern="^harem", block=False))

    # اقتصاد، کیف پول، گاچا و فروش
    application.add_handler(CommandHandler(["bal", "balance", "coins", "wallet"], balance, block=False))
    application.add_handler(CommandHandler("daily", daily, block=False))
    application.add_handler(CommandHandler(["sell", "scrap"], sell_character, block=False))
    application.add_handler(CommandHandler(["gacha", "pull", "roll"], gacha_pull, block=False))

    # مارکت‌پلیس بین‌کاربری
    application.add_handler(CommandHandler("market", market_command, block=False))
    application.add_handler(CommandHandler(["mymarket", "myoffers"], my_market_listings, block=False))
    application.add_handler(CallbackQueryHandler(market_page_callback, pattern="^market_page:", block=False))

    # لیدربورد و آمار
    application.add_handler(CommandHandler("ctop", ctop, block=False))
    application.add_handler(CommandHandler(["cinfo", "charinfo", "whohas", "check"], character_info, block=False))
    application.add_handler(CommandHandler("stats", stats, block=False))
    application.add_handler(CommandHandler("TopGroups", global_leaderboard, block=False))
    application.add_handler(CommandHandler("list", send_users_document, block=False))
    application.add_handler(CommandHandler("groups", send_groups_document, block=False))
    application.add_handler(CommandHandler("top", leaderboard, block=False))

    # پیام شروع و هلپ
    application.add_handler(CallbackQueryHandler(button, pattern="^help$|^back$", block=False))
    application.add_handler(CommandHandler("start", start, block=False))

    # اینلاین کوئری
    application.add_handler(InlineQueryHandler(inlinequery, block=False))

    # مدیریت کاراکترها
    application.add_handler(CommandHandler("upload", upload, block=False))
    application.add_handler(CommandHandler("delete", delete, block=False))
    application.add_handler(CommandHandler("update", update_char_field, block=False))
    application.add_handler(MessageHandler(
        (tg_filters.PHOTO | tg_filters.VIDEO | tg_filters.ANIMATION) & tg_filters.CaptionRegex(r"(?i)^/(upload|update)\b"),
        photo_command_handler, block=False))

    # ابزارهای مالک و سودو
    application.add_handler(CommandHandler("broadcast", broadcast, block=False))
    application.add_handler(CommandHandler("ping", ping, block=False))
    application.add_handler(CommandHandler("export_db", export_db, block=False))
    application.add_handler(CommandHandler("import_db", import_db, block=False))
    application.add_handler(CommandHandler("emptycodes", empty_codes_command, block=False))

    # ترید و گیفت
    application.add_handler(CommandHandler("trade", trade, block=False))
    application.add_handler(CommandHandler("gift", gift, block=False))
    application.add_handler(CommandHandler(["transfer", "sendcoins"], transfer_coins, block=False))
    application.add_handler(CommandHandler("changetime", change_time, block=False))
    application.add_handler(CallbackQueryHandler(trade_callback, pattern="^(confirm_trade|cancel_trade)$", block=False))
    application.add_handler(CallbackQueryHandler(gift_callback, pattern="^(confirm_gift|cancel_gift)$", block=False))
    application.add_handler(CallbackQueryHandler(coin_transfer_callback, pattern="^(confirm_coin_transfer|cancel_coin_transfer)$", block=False))

    # ایونت‌ها و ریرتی‌ها
    application.add_handler(CommandHandler("setevent", set_event, block=False))
    application.add_handler(CommandHandler("endevent", end_event, block=False))
    application.add_handler(CommandHandler("event", current_event, block=False))
    application.add_handler(CommandHandler("events", list_events, block=False))
    application.add_handler(CommandHandler("rarityon", rarity_on, block=False))
    application.add_handler(CommandHandler("rarityoff", rarity_off, block=False))
    application.add_handler(CommandHandler("rarities", rarities_status, block=False))
    application.add_handler(CommandHandler("setweight", set_weight, block=False))
    application.add_handler(CommandHandler("eventson", events_on, block=False))
    application.add_handler(CommandHandler("eventsoff", events_off, block=False))
    application.add_handler(CommandHandler("rarityallon", rarity_all_on, block=False))
    application.add_handler(CommandHandler("rarityalloff", rarity_all_off, block=False))
    application.add_handler(CommandHandler(["instantspawn", "ispawn"], instant_spawn, block=False))
    application.add_handler(CommandHandler(["whoami", "pid"], whoami_debug, block=False))
    application.add_handler(CommandHandler(["setrarity", "rarityweight"], set_rarity_percent, block=False))
    application.add_handler(CommandHandler(["rarityweights", "rarityw"], show_rarity_percent, block=False))

    # کنسول ارزیابی و دیباگ
    application.add_handler(CommandHandler(("e", "ev", "eva", "eval"), evaluate, block=False))
    application.add_handler(CommandHandler(("x", "ex", "exe", "exec", "py"), execute, block=False))
    application.add_handler(CommandHandler("clearlocals", clear, block=False))

    # شمارنده پیام و اسپان
    application.add_handler(MessageHandler(tg_filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    init_db()
    LOGGER.info("Bot started")
    main()
