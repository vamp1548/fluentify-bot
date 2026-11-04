import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# تنظیمات لاگ‌گیری برای رصد وضعیت ربات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# خواندن کلیدها از متغیرهای محیطی هاست
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# پیکربندی هوش مصنوعی جمینای
genai.configure(api_key=GEMINI_API_KEY)
# استفاده از مدل استاندارد و قدرتمند جمینای
model = genai.GenerativeModel("gemini-1.5-flash")

# دیتابیس ساده در حافظه برای نگهداری پروفایل کاربران (جدا کردن کاربران از یکدیگر)
user_profiles = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع و خوش‌آمدگویی به کاربر"""
    user_id = update.effective_user.id
    
    # ساخت پروفایل پیش‌فرض برای کاربر جدید
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "language": "English",
            "level": "B1",
            "score": 0,
            "vocabulary": []
        }
        
    welcome_message = (
        "سلام! من مربی هوشمند زبان شما (Fluentify) هستم.\n\n"
        "ما اینجا قرار است به صورت کاملاً اختصاصی روی زبان و پیشرفت شما کار کنیم.\n"
        "دستورات اصلی:\n"
        "🔹 /setlang [زبان] - تعیین زبان مورد نظر (مثل French, English, German)\n"
        "🔹 /setlevel [سطح] - تعیین سطح (مثل A2, B1, B2)\n\n"
        "هم همین الان می‌تونی یک متن یا ویس برام بفرستی تا تمرین رو شروع کنیم!"
    )
    await update.message.reply_text(welcome_message)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم زبان مورد نظر کاربر"""
    user_id = update.effective_user.id
    if context.args:
        lang = context.args[0]
        if user_id not in user_profiles:
            user_profiles[user_id] = {"language": lang, "level": "B1", "score": 0, "vocabulary": []}
        else:
            user_profiles[user_id]["language"] = lang
        await update.message.reply_text(f"زبان تمرین شما با موفقیت روی **{lang}** تنظیم شد.")
    else:
        await update.message.reply_text("لطفاً نام زبان را وارد کنید. مثال:\n`/setlang French` یا `/setlang English`", parse_mode="Markdown")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم سطح زبان کاربر"""
    user_id = update.effective_user.id
    if context.args:
        lvl = context.args[0]
        if user_id not in user_profiles:
            user_profiles[user_id] = {"language": "English", "level": lvl, "score": 0, "vocabulary": []}
        else:
            user_profiles[user_id]["level"] = lvl
        await update.message.reply_text(f"سطح زبان شما با موفقیت روی **{lvl}** تنظیم شد.")
    else:
        await update.message.reply_text("لطفاً سطح خود را وارد کنید. مثال:\n`/setlevel B2`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌ها، تصحیح متن‌ها و بازخورد هوش مصنوعی"""
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # دریافت تنظیمات اختصاصی این کاربر خاص
    profile = user_profiles.get(user_id, {"language": "English", "level": "B1", "score": 0, "vocabulary": []})
    target_lang = profile["language"]
    target_level = profile["level"]

    prompt = (
        f"You are an expert AI language coach. The user is practicing {target_lang} at {target_level} level. "
        f"Review the following user message: '{user_text}'.\n"
        f"Provide:\n"
        f"1. Grammar and vocabulary corrections.\n"
        f"2. Natural paraphrasing or better native alternatives.\n"
        f"3. A constructive score out of 10 and encouraging feedback.\n"
        f"Respond clearly and concisely."
    )

    try:
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        reply_text = "متأسفانه در ارتباط با هوش مصنوعی خطایی رخ داد. لطفاً دوباره تلاش کنید."

    await update.message.reply_text(reply_text)

def main():
    """راه‌اندازی و اجرای ربات"""
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # ثبت دستورات و هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setlang", set_language))
    application.add_handler(CommandHandler("setlevel", set_level))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()