from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
from datetime import datetime, timedelta
import os
import asyncio
from telegram.ext import ApplicationBuilder
from apscheduler.schedulers.background import BackgroundScheduler

DB_FILE = 'wills.db'

# DB setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS digital_wills (
        user_id INTEGER PRIMARY KEY,
        recipient_username TEXT,
        message TEXT,
        days INTEGER,
        last_checkin TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome. Use /register to set your digital will.")

# /register
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Usage: /register @recipient days message")
            return
        recipient, days = args[0], int(args[1])
        message = ' '.join(args[2:])

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("REPLACE INTO digital_wills VALUES (?, ?, ?, ?, ?)",
                  (user_id, recipient, message, days, datetime.utcnow()))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"Digital will registered. Recipient: {recipient}, Days: {days}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# /imalive
async def imalive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE digital_wills SET last_checkin = ? WHERE user_id = ?", (datetime.utcnow(), user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("Check-in recorded. You're alive!")

# Periodic job to check inactivity
def check_inactivity(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, recipient_username, message, days, last_checkin FROM digital_wills")
    for user_id, recipient, message, days, last_checkin in c.fetchall():
        if datetime.utcnow() - datetime.fromisoformat(last_checkin) > timedelta(days=days):
            context.bot.send_message(chat_id=recipient, text=f"🕊️ Message from {user_id}:\n{message}")
            c.execute("DELETE FROM digital_wills WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

init_db()

TOKEN = os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("register", register))
app.add_handler(CommandHandler("imalive", imalive))

scheduler = BackgroundScheduler()
scheduler.add_job(lambda: check_inactivity(app), 'interval', minutes=2)
scheduler.start()

app.run_polling()
