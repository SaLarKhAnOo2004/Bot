# -*- coding: utf-8 -*-
import json
import random
import string
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"  # خپل توکن دلته دننه کړئ
MAILTM_API = "https://api.mail.tm"
DATA_FILE = "user_data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def create_account(custom_address=None):
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    address = custom_address if custom_address else f"{username}@mail.tm"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    response = requests.post(f"{MAILTM_API}/accounts", json={"address": address, "password": password})
    if response.status_code == 201:
        return {"address": address, "password": password, "id": response.json()["id"]}
    return None

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📧 Get a new fake mail id")],
        [KeyboardButton("🆔 Current fake mail id")],
        [KeyboardButton("⚙️ Setup custom fake mail id")],
        [KeyboardButton("📱 Add/update recovery phone")],
        [KeyboardButton("🌐 Manage custom domains")],
        [KeyboardButton("🚫 Manage Blocklist")],
        [KeyboardButton("ℹ️ About this bot")],
        [KeyboardButton("🔄 Transfer Address")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *سلام! Fakemail بوټ ته ښه راغلاست!*\nلاندې مینو وکاروئ:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})
    await update.message.reply_text("⏳ نوی برېښنالیک جوړیږي...")
    new_acc = create_account()
    if new_acc:
        user_info['email'] = new_acc['address']
        user_info['password'] = new_acc['password']
        user_info['last_count'] = 0
        data[user_id] = user_info
        save_data(data)
        await update.message.reply_text(
            f"✅ *نوی برېښنالیک:*\n`{new_acc['address']}`\n🔑 پټنوم: `{new_acc['password']}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ ناکام شو.")

async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})
    email = user_info.get('email', 'هیڅ برېښنالیک نشته.')
    await update.message.reply_text(f"🆔 ستاسو پته: `{email}`", parse_mode="Markdown")

async def domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domains = ["mail.tm", "geek.it", "slushmail.com", "drdrb.com"]
    text = "🌐 *دامنو لیست:*\n" + "\n".join([f"• `{d}`" for d in domains])
    await update.message.reply_text(text, parse_mode="Markdown")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ دا یو وړیا تېمپ میل بوټ دی.")

async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_set'] = True
    await update.message.reply_text("خپل مطلوب نوم ولیکئ (د '@' پرته):")

async def phone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_phone'] = True
    await update.message.reply_text("خپل شمېره د + سره ولیکئ:")

async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_transfer'] = True
    await update.message.reply_text("د بل کارونکي یوزرنیم ولیکئ:")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("لغوه شو.")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    data = load_data()
    user_info = data.get(user_id, {})

    # د انتظار حالتونه
    if context.user_data.get('awaiting_set'):
        full_address = f"{text.strip().lower()}@mail.tm"
        new_acc = create_account(full_address)
        if new_acc:
            user_info['email'] = new_acc['address']
            user_info['password'] = new_acc['password']
            user_info['last_count'] = 0
            data[user_id] = user_info
            save_data(data)
            await update.message.reply_text(f"✅ جوړ شو: `{new_acc['address']}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ نوم نیول شوی یا ناسم دی.")
        context.user_data['awaiting_set'] = False
        return

    if context.user_data.get('awaiting_phone'):
        phone = text.strip()
        if phone.startswith('+') and len(phone) > 8:
            user_info['phone'] = phone
            data[user_id] = user_info
            save_data(data)
            await update.message.reply_text(f"📱 شمېره خوندي شوه: `{phone}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ بڼه سمه نه ده (لکه +937...)")
        context.user_data['awaiting_phone'] = False
        return

    if context.user_data.get('awaiting_transfer'):
        target = text.strip()
        user_info['transfer_to'] = target
        data[user_id] = user_info
        save_data(data)
        await update.message.reply_text(f"🔄 لېږد ته چمتو دی: `{target}`", parse_mode="Markdown")
        context.user_data['awaiting_transfer'] = False
        return

    # د کیبورد تڼیو اداره کول
    if text == "📧 Get a new fake mail id":
        await generate(update, context)
    elif text == "🆔 Current fake mail id":
        await show_id(update, context)
    elif text == "⚙️ Setup custom fake mail id":
        await set_command(update, context)
    elif text == "📱 Add/update recovery phone":
        await phone_command(update, context)
    elif text == "🌐 Manage custom domains":
        await domain_command(update, context)
    elif text == "🚫 Manage Blocklist":
        await update.message.reply_text("د بلاک لیست لپاره /block وکاروئ.")
    elif text == "ℹ️ About this bot":
        await about_command(update, context)
    elif text == "🔄 Transfer Address":
        await transfer_command(update, context)
    else:
        await update.message.reply_text("مهرباني وکړئ له مینو څخه یوه تڼۍ وټاکئ.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("بوټ روان دی...")
    app.run_polling()

if __name__ == "__main__":
    main()
