import os
import sqlite3
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler
import db

import os
TOKEN = os.getenv("BOT_TOKEN")
print("Token is:", TOKEN)  # Should print your full token in Railway logs


conn = sqlite3.connect("todo.db", check_same_thread=False)
cursor = conn.cursor()

WEEKDAY_MAP = {"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}

# ---------- Commands ----------
async def start(update, context):
    await update.message.reply_text(
        "👋 Weekly Todo Bot\n\n"
        "/add task amount\n"
        "/schedule task amount mon 08:30\n"
        "/schedule_list\n"
        "/delete_schedule ID\n"
        "/edit_schedule ID Task Amount Day HH:MM\n"
        "/today\n"
        "/total"
    )

async def add(update, context):
    user_id = update.effective_user.id
    text = update.message.text.replace("/add", "").strip()
    task, amount = text.rsplit(" ", 1)
    amount = float(amount)
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO todo (user_id, task, amount, date) VALUES (?,?,?,?)",
                   (user_id, task, amount, today))
    conn.commit()
    await update.message.reply_text("✅ Added")

# ---------- Schedule ----------
async def schedule_list(update, context):
    user_id = update.effective_user.id
    cursor.execute("SELECT id, task, amount, weekday, hour, minute FROM todo_schedule WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("📭 No scheduled habits")
        return
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    msg = "⏰ Scheduled Habits:\n"
    for id, task, amount, wd, h, m in rows:
        msg += f"{id}. {task} - ${amount} → {days[wd]} {h:02d}:{m:02d}\n"
    await update.message.reply_text(msg)

async def delete_schedule(update, context):
    user_id = update.effective_user.id
    try:
        sched_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ Usage: /delete_schedule ID")
        return
    cursor.execute("DELETE FROM todo_schedule WHERE id=? AND user_id=?", (sched_id, user_id))
    conn.commit()
    await update.message.reply_text(f"✅ Deleted schedule {sched_id}")

async def edit_schedule(update, context):
    user_id = update.effective_user.id
    try:
        sched_id = int(context.args[0])
        task = context.args[1]
        amount = float(context.args[2])
        day = context.args[3].lower()
        hour, minute = map(int, context.args[4].split(":"))
        weekday = WEEKDAY_MAP[day]
    except:
        await update.message.reply_text("❌ Usage: /edit_schedule ID Task Amount Day HH:MM")
        return
    cursor.execute("UPDATE todo_schedule SET task=?, amount=?, weekday=?, hour=?, minute=? WHERE id=? AND user_id=?",
                   (task, amount, weekday, hour, minute, sched_id, user_id))
    conn.commit()
    await update.message.reply_text(f"✅ Updated schedule {sched_id}")

# ---------- Daily check ----------
def check_schedules(app):
    now = datetime.now()
    wd = now.weekday()
    cursor.execute("SELECT user_id, task, amount, hour, minute FROM todo_schedule WHERE weekday=?", (wd,))
    for u, t, a, h, m in cursor.fetchall():
        if h == now.hour and m == now.minute:
            today = now.strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO todo (user_id, task, amount, date) VALUES (?,?,?,?)", (u, t, a, today))
            conn.commit()
            app.bot.send_message(u, f"⏰ {t} - ${a}")

# ---------- App ----------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("schedule_list", schedule_list))
app.add_handler(CommandHandler("delete_schedule", delete_schedule))
app.add_handler(CommandHandler("edit_schedule", edit_schedule))

scheduler = BackgroundScheduler()
scheduler.add_job(check_schedules, "interval", minutes=1, args=[app])
scheduler.start()

print("🤖 Bot running...")
app.run_polling()
