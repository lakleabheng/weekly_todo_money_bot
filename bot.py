from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import sqlite3
import os

# ==============================
# CONFIG
# ==============================
TOKEN = os.getenv("BOT_TOKEN")  # Set in Railway Variables

DB_NAME = "todo.db"

# ==============================
# DATABASE
# ==============================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task TEXT,
            amount REAL,
            weekday TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# ==============================
# COMMANDS
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Weekly Todo Bot\n\n"
        "Commands:\n"
        "/add <task> <money> <day>\n"
        "Example:\n"
        "/add Gym 5 Sunday\n\n"
        "/list – show your todos\n"
        "/summary – weekly money summary"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/add", "").strip()

    parts = text.split()

    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Usage:\n/add <task> <money> <day>\n"
            "Example:\n/add Gym 5 Sunday"
        )
        return

    day = parts[-1].capitalize()

    try:
        amount = float(parts[-2])
        task = " ".join(parts[:-2])
    except ValueError:
        await update.message.reply_text("❌ Money must be a number")
        return

    user_id = update.effective_user.id

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO todos (user_id, task, amount, weekday, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, task, amount, day, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Added\n📝 {task}\n💰 ${amount}\n📅 {day}"
    )

async def list_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT task, amount, weekday FROM todos WHERE user_id=?",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 No todos yet")
        return

    msg = "📋 Your Todos:\n\n"
    for task, amount, day in rows:
        msg += f"📝 {task} | 💰 ${amount} | 📅 {day}\n"

    await update.message.reply_text(msg)

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT SUM(amount) FROM todos WHERE user_id=?",
        (user_id,)
    )
    total = c.fetchone()[0] or 0
    conn.close()

    await update.message.reply_text(f"📊 Weekly Total: 💰 ${total}")

# ==============================
# WEEKLY SUNDAY REPORT
# ==============================
async def sunday_report(app):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, SUM(amount)
        FROM todos
        GROUP BY user_id
    """)
    rows = c.fetchall()
    conn.close()

    for user_id, total in rows:
        await app.bot.send_message(
            chat_id=user_id,
            text=f"📅 Sunday Summary\n💰 Total spent: ${total}"
        )

# ==============================
# MAIN
# ==============================
def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_todos))
    app.add_handler(CommandHandler("summary", summary))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sunday_report,
        "cron",
        day_of_week="sun",
        hour=20,
        minute=0,
        args=[app]
    )
    scheduler.start()

    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
