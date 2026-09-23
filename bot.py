import sqlite3
import asyncio
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8851176173:AAF9gTlYJdDfgA-n1h3ZkPq70kzOHEYSDrg"

db = sqlite3.connect("bot.db", check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    topic TEXT DEFAULT 'free',
    xp INTEGER DEFAULT 0,
    chats INTEGER DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS blocks (
    user_id INTEGER,
    blocked_id INTEGER,
    PRIMARY KEY(user_id, blocked_id)
)
""")

db.commit()

waiting = {}
active = {}
topics = {
    "free": "💬 گپ آزاد",
    "game": "🎮 گیم",
    "music": "🎵 موسیقی",
    "movie": "🎬 فیلم",
    "sport": "⚽ ورزش",
    "tech": "💻 تکنولوژی",
    "study": "📚 درس",
    "fun": "😂 فان"
}


def add_user(user):
    db.execute(
        "INSERT OR IGNORE INTO users(id, name) VALUES(?, ?)",
        (user.id, user.first_name or "کاربر")
    )
    db.commit()


def get_topic(user_id):
    row = db.execute(
        "SELECT topic FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    return row[0] if row else "free"


def blocked(a, b):
    x = db.execute(
        "SELECT 1 FROM blocks WHERE user_id=? AND blocked_id=?",
        (a, b)
    ).fetchone()

    y = db.execute(
        "SELECT 1 FROM blocks WHERE user_id=? AND blocked_id=?",
        (b, a)
    ).fetchone()

    return x is not None or y is not None


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔎 پیدا کردن دوست",
                callback_data="find"
            )
        ],
        [
            InlineKeyboardButton(
                "👤 پروفایل",
                callback_data="profile"
            ),
            InlineKeyboardButton(
                "🎯 موضوع",
                callback_data="topics"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="stats"
            ),
            InlineKeyboardButton(
                "🚫 بلاک‌ها",
                callback_data="blocks"
            )
        ],
        [
            InlineKeyboardButton(
                "❓ راهنما",
                callback_data="help"
            )
        ]
    ])


def search_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ لغو جستجو",
                callback_data="cancel"
            )
        ]
    ])


def chat_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚫 بلاک کاربر",
                callback_data="block"
            ),
            InlineKeyboardButton(
                "🛑 پایان چت",
                callback_data="stop"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 دوست بعدی",
                callback_data="next"
            ),
            InlineKeyboardButton(
                "🚨 گزارش",
                callback_data="report"
            )
        ]
    ])


def topic_keyboard():
    buttons = []

    for key, name in topics.items():
        buttons.append([
            InlineKeyboardButton(
                name,
                callback_data="topic_" + key
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="back"
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    add_user(user)

    await update.message.reply_text(
        "👋 به دوست ناشناس خوش آمدی!\n\n"
        "از منوی زیر استفاده کن:",
        reply_markup=main_keyboard()
    )


async def find_friend(user_id, bot):

    if user_id in active:
        return

    if user_id in waiting:
        return

    my_topic = get_topic(user_id)

    selected = None
    selected_time = None

    for other_id, start_time in list(waiting.items()):

        if other_id == user_id:
            continue

        if other_id in active:
            continue

        if blocked(user_id, other_id):
            continue

        other_topic = get_topic(other_id)

        if other_topic != my_topic:
            continue

        if selected is None or start_time < selected_time:
            selected = other_id
            selected_time = start_time

    if selected is None:

        for other_id, start_time in list(waiting.items()):

            if other_id == user_id:
                continue

            if other_id in active:
                continue

            if blocked(user_id, other_id):
                continue

            if selected is None or start_time < selected_time:
                selected = other_id
                selected_time = start_time

    if selected is None:

        waiting[user_id] = time.time()

        await bot.send_message(
            user_id,
            "🔎 در حال جستجوی دوست...\n\n"
            "برای لغو جستجو دکمه زیر را بزن.",
            reply_markup=search_keyboard()
        )

        return

    waiting.pop(selected, None)

    active[user_id] = selected
    active[selected] = user_id

    db.execute(
        "UPDATE users SET chats=chats+1, xp=xp+10 WHERE id=?",
        (user_id,)
    )

    db.execute(
        "UPDATE users SET chats=chats+1, xp=xp+10 WHERE id=?",
        (selected,)
    )

    db.commit()

    text = (
        "✅ دوست پیدا شد!\n\n"
        "چت ناشناس شروع شد.\n"
        "شماره و username طرف مقابل نمایش داده نمی‌شود."
    )

    await bot.send_message(
        user_id,
        text,
        reply_markup=chat_keyboard()
    )

    await bot.send_message(
        selected,
        text,
        reply_markup=chat_keyboard()
    )


def security(text):
    if not text:
        return True

    bad = [
        "http://",
        "https://",
        "www.",
        "t.me/",
        "@",
        "telegram.me",
        "instagram.com",
        "discord.gg"
    ]

    for word in bad:
        if word.lower() in text.lower():
            return False

    digits = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩0123456789"

    count = 0

    for char in text:
        if char in digits:
            count += 1

    if count >= 8:
        return False

    return True


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    add_user(query.from_user)

    await query.answer()

    if data == "find":

        if user_id in active:
            await query.message.reply_text(
                "⚠️ تو الان داخل چت هستی.",
                reply_markup=chat_keyboard()
            )
            return

        if user_id in waiting:
            await query.message.reply_text(
                "🔎 هنوز در حال جستجو هستی.",
                reply_markup=search_keyboard()
            )
            return

        await find_friend(
            user_id,
            context.bot
        )

        return

    if data == "cancel":

        waiting.pop(user_id, None)

        await query.message.edit_text(
            "❌ جستجو لغو شد.",
            reply_markup=main_keyboard()
        )

        return

    if data == "stop":

        friend = active.pop(user_id, None)

        if friend is None:
            await query.message.edit_text(
                "چت فعالی نداری.",
                reply_markup=main_keyboard()
            )
            return

        active.pop(friend, None)

        await query.message.edit_text(
            "🛑 چت پایان یافت.",
            reply_markup=main_keyboard()
        )

        try:
            await context.bot.send_message(
                friend,
                "🛑 دوستت چت را پایان داد.",
                reply_markup=main_keyboard()
            )
        except Exception:
            pass

        return

    if data == "next":

        friend = active.pop(user_id, None)

        if friend is not None:

            active.pop(friend, None)

            try:
                await context.bot.send_message(
                    friend,
                    "🔄 دوستت چت را ترک کرد.",
                    reply_markup=main_keyboard()
                )
            except Exception:
                pass

        waiting.pop(user_id, None)

        await query.message.edit_text(
            "🔎 در حال پیدا کردن دوست جدید...",
            reply_markup=search_keyboard()
        )

        await find_friend(
            user_id,
            context.bot
        )

        return

    if data == "block":

        friend = active.pop(user_id, None)

        if friend is None:
            return

        active.pop(friend, None)

        db.execute(
            "INSERT OR IGNORE INTO blocks VALUES(?, ?)",
            (user_id, friend)
        )

        db.commit()

        await query.message.edit_text(
            "🚫 کاربر بلاک شد و چت پایان یافت.",
            reply_markup=main_keyboard()
        )

        try:
            await context.bot.send_message(
                friend,
                "🛑 چت پایان یافت.",
                reply_markup=main_keyboard()
            )
        except Exception:
            pass

        return

    if data == "report":

        friend = active.pop(user_id, None)

        if friend is None:
            return

        active.pop(friend, None)

        await query.message.edit_text(
            "🚨 گزارش ثبت شد و چت پایان یافت.",
            reply_markup=main_keyboard()
        )

        try:
            await context.bot.send_message(
                friend,
                "🛑 چت پایان یافت.",
                reply_markup=main_keyboard()
            )
        except Exception:
            pass

        return

    if data == "profile":

        row = db.execute(
            "SELECT * FROM users WHERE id=?",
            (user_id,)
        ).fetchone()

        level = (row["xp"] // 100) + 1

        text = (
            "👤 پروفایل\n\n"
            f"نام: {row['name']}\n"
            f"⭐ XP: {row['xp']}\n"
            f"🏅 سطح: {level}\n"
            f"💬 چت‌ها: {row['chats']}"
        )

        await query.message.edit_text(
            text,
            reply_markup=main_keyboard()
        )

        return

    if data == "stats":

        row = db.execute(
            "SELECT xp, chats FROM users WHERE id=?",
            (user_id,)
        ).fetchone()

        await query.message.edit_text(
            "📊 آمار\n\n"
            f"⭐ XP: {row['xp']}\n"
            f"💬 تعداد چت: {row['chats']}\n"
            f"🏅 سطح: {(row['xp'] // 100) + 1}",
            reply_markup=main_keyboard()
        )

        return

    if data == "topics":

        await query.message.edit_text(
            "🎯 موضوع مورد علاقه‌ات را انتخاب کن:",
            reply_markup=topic_keyboard()
        )

        return

    if data.startswith("topic_"):

        key = data.replace("topic_", "")

        if key in topics:

            db.execute(
                "UPDATE users SET topic=? WHERE id=?",
                (key, user_id)
            )

            db.commit()

            await query.message.edit_text(
                "✅ موضوع انتخاب شد:\n\n"
                + topics[key],
                reply_markup=main_keyboard()
            )

        return

    if data == "blocks":

        rows = db.execute(
            "SELECT blocked_id FROM blocks WHERE user_id=?",
            (user_id,)
        ).fetchall()

        if not rows:

            await query.message.edit_text(
                "🚫 لیست بلاک‌ها خالی است.",
                reply_markup=main_keyboard()
            )

            return

        buttons = []

        for i, row in enumerate(rows, 1):

            buttons.append([
                InlineKeyboardButton(
                    f"👤 کاربر {i}",
                    callback_data="nothing"
                ),
                InlineKeyboardButton(
                    "🔓 لغو بلاک",
                    callback_data=f"unblock_{row['blocked_id']}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back"
            )
        ])

        await query.message.edit_text(
            "🚫 کاربران بلاک‌شده:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        return

    if data.startswith("unblock_"):

        target = int(
            data.replace("unblock_", "")
        )

        db.execute(
            "DELETE FROM blocks WHERE user_id=? AND blocked_id=?",
            (user_id, target)
        )

        db.commit()

        await query.message.edit_text(
            "🔓 بلاک لغو شد.",
            reply_markup=main_keyboard()
        )

        return

    if data == "nothing":
        return

    if data == "help":

        await query.message.edit_text(
            "❓ راهنما\n\n"
            "🔎 پیدا کردن دوست = شروع جستجو\n"
            "🔄 دوست بعدی = پیدا کردن فرد جدید\n"
            "🛑 پایان چت = بستن چت\n"
            "🚫 بلاک = جلوگیری از match دوباره\n"
            "🚨 گزارش = گزارش کاربر\n\n"
            "شماره، username و لینک‌ها فیلتر می‌شوند.",
            reply_markup=main_keyboard()
        )

        return

    if data == "back":

        await query.message.edit_text(
            "🏠 منوی اصلی",
            reply_markup=main_keyboard()
        )


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.message

    if message is None:
        return

    user_id = message.from_user.id

    add_user(message.from_user)

    if user_id not in active:
        await message.reply_text(
            "از منوی اصلی استفاده کن.",
            reply_markup=main_keyboard()
        )
        return

    text = message.text or message.caption or ""

    if not security(text):
        await message.reply_text(
            "❌ ارسال شماره، username یا لینک مجاز نیست.",
            reply_markup=chat_keyboard()
        )
        return

    friend = active.get(user_id)

    if friend is None:
        return

    try:

        await message.copy(
            chat_id=friend
        )

        db.execute(
            "UPDATE users SET xp=xp+1 WHERE id=?",
            (user_id,)
        )

        db.commit()

    except Exception:

        active.pop(user_id, None)
        active.pop(friend, None)

        await message.reply_text(
            "⚠️ ارسال پیام انجام نشد.",
            reply_markup=main_keyboard()
        )


async def other_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    if message is None:
        return

    user_id = message.from_user.id

    add_user(message.from_user)

    if user_id not in active:
        return

    if message.contact:
        await message.reply_text(
            "❌ ارسال شماره تماس مجاز نیست."
        )
        return

    if message.location:
        await message.reply_text(
            "❌ ارسال موقعیت مکانی مجاز نیست."
        )
        return

    if message.venue:
        await message.reply_text(
            "❌ ارسال موقعیت مکانی مجاز نیست."
        )
        return

    caption = message.caption or ""

    if not security(caption):
        await message.reply_text(
            "❌ اطلاعات تماس یا لینک مجاز نیست."
        )
        return

    friend = active.get(user_id)

    if friend is None:
        return

    try:
        await message.copy(
            chat_id=friend
        )
    except Exception:
        pass


def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(callback)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            messages
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.TEXT & ~filters.COMMAND,
            other_messages
        )
    )

    print("BOT STARTED")

    app.run_polling()


if __name__ == "__main__":
    main()
