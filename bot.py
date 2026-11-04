import os
import logging
import asyncio
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# خواندن کلیدها از متغیرهای محیطی هاست
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# پیکربندی هوش مصنوعی جمینای
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.8-flash")

# دیتابیس ساده در حافظه برای نگهداری پروفایل کاربران و Chat ID ها
user_profiles = {}
active_chat_ids = set()

# --- ساخت وب‌سرور فلاسگ برای Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Fluentify Bot is running!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    active_chat_ids.add(chat_id)
    
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "language": "French",
            "level": "B1",
            "score": 0,
            "vocabulary": []
        }
        
    welcome_message = (
        "سلام! من مربی هوشمند زبان شما (Fluentify) هستم.\n\n"
        "من هر روز ساعت ۱۲ ظهر به طور خودکار یک موضوع، متن تمرین و واژگان جدید برایت می‌فرستم تا با هم تمرین کنیم!\n\n"
        "دستورات اصلی:\n"
        "🔹 /setlang [زبان] - تعیین زبان مورد نظر (مثل French, English)\n"
        "🔹 /setlevel [سطح] - تعیین سطح (مثل A2, B1, B2)\n\n"
        "حالا آماده‌ای؟ هر وقت خواستی می‌تونی تمرینت را بفرستی."
    )
    await update.message.reply_text(welcome_message)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.args:
        lang = context.args[0]
        if user_id not in user_profiles:
            user_profiles[user_id] = {"language": lang, "level": "B1", "score": 0, "vocabulary": []}
        else:
            user_profiles[user_id]["language"] = lang
        
        await update.message.reply_text(
            f"✅ زبان تمرین شما روی **{lang}** تنظیم شد.\n"
            f"هر روز ساعت ۱۲ ظهر با تمرین‌های جدید {lang} در خدمتت خواهم بود!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("لطفاً نام زبان را وارد کنید. مثال:\n`/setlang French`", parse_mode="Markdown")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.args:
        lvl = context.args[0]
        if user_id not in user_profiles:
            user_profiles[user_id] = {"language": "English", "level": lvl, "score": 0, "vocabulary": []}
        else:
            user_profiles[user_id]["level"] = lvl
        await update.message.reply_text(f"سطح زبان شما روی **{lvl}** تنظیم شد.")
    else:
        await update.message.reply_text("لطفاً سطح خود را وارد کنید. مثال:\n`/setlevel B2`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    active_chat_ids.add(chat_id)
    user_text = update.message.text
    
    profile = user_profiles.get(user_id, {"language": "French", "level": "B1", "score": 0, "vocabulary": []})
    target_lang = profile["language"]
    target_level = profile["level"]

    prompt = (
        f"You are an expert AI language coach. The user is practicing {target_lang} at {target_level} level. "
        f"Review the following user message: '{user_text}'.\n"
        f"Provide:\n"
        f"1. Grammar and vocabulary corrections.\n"
        f"2. Natural paraphrasing or better native alternatives.\n"
        f"3. A constructive score out of 10 and encouraging feedback.\n"
        f"Respond clearly and concisely in Persian/English as appropriate."
    )

    try:
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        logger.error(f"Detailed Gemini Error: {str(e)}")
        reply_text = f"خطای فنی هوش مصنوعی: {str(e)}"

    await update.message.reply_text(reply_text)

# --- تابع ارسال خودکار تمرین روزانه ساعت ۱۲ ظهر ---
def send_daily_lesson(application):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def job():
        for chat_id in active_chat_ids:
            try:
                prompt = (
                    "Generate a daily language learning lesson for a B1 level student learning French. "
                    "Include: 1. A new interesting daily topic. 2. A short practice text in French. "
                    "3. 3 key vocabulary words with Persian/English meanings. "
                    "Keep it structured and engaging."
                )
                response = model.generate_content(prompt)
                lesson_text = f"☀️ **تمرین روزانه جدید (ساعت ۱۲ ظهر):**\n\n{response.text}"
                await application.bot.send_message(chat_id=chat_id, text=lesson_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Failed to send daily lesson to {chat_id}: {e}")

    loop.run_until_complete(job())
    loop.close()

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

async def main():
    import threading
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setlang", set_language))
    application.add_handler(CommandHandler("setlevel", set_level))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # تنظیم زمان‌سنج برای اجرای هر روز ساعت 12:00 ظهر
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: send_daily_lesson(application), CronTrigger(hour=12, minute=0))
    scheduler.start()

    print("Bot, Web Server, and Scheduler are running...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    stop_event = asyncio.Event()
    await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
