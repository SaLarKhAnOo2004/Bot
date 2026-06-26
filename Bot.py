# -*- coding: utf-8 -*-
"""
د Fakemail بوټ - د عادي کیبورد مینو سره
ټولې دندې: /generate, /id, /set, /phone, /domain, /block, /about, /transfer
"""

import json
import random
import string
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ---------- تنظیمات ----------
TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"  # خپل توکن دلته دننه کړئ
MAILTM_API = "https://api.mail.tm"
DATA_FILE = "user_data.json"

# ---------- د معلوماتو لوستل/لیکل ----------
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ---------- د mail.tm سره د کار کولو فنکشنونه ----------
def create_account(custom_address=None):
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    address = custom_address if custom_address else f"{username}@mail.tm"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    response = requests.post(f"{MAILTM_API}/accounts", json={
        "address": address,
        "password": password
    })
    if response.status_code == 201:
        return {"address": address, "password": password, "id": response.json()["id"]}
    return None

def get_token(email, password):
    response = requests.post(f"{MAILTM_API}/token", json={
        "address": email,
        "password": password
    })
    if response.status_code == 200:
        return response.json()["token"]
    return None

def get_messages(email, password):
    token = get_token(email, password)
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAILTM_API}/messages", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_message_content(email, password, message_id):
    token = get_token(email, password)
    if not token:
        return None
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAILTM_API}/messages/{message_id}", headers=headers)
    if response.status_code == 200:
        return response.json().get("text", "")
    return None

# ---------- د عادي کیبورد جوړول ----------
def get_main_keyboard():
    """د تل لپاره ښکاره کیدونکی کیبورد (مینو)"""
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

# ---------- د بوټ کمانډونه ----------

# د /start کمانډ - مینو ښکاره کول
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *سلام! د Fakemail بوټ ته ښه راغلاست!*\n\n"
        "لاندې له مینو څخه خپل مطلوب کار غوره کړئ:\n"
        "(هره تڼۍ یو کمانډ لیږي)",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# د /generate کمانډ
async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})

    await update.message.reply_text("⏳ *نوی برېښنالیک جوړیږي...*", parse_mode="Markdown")
    new_acc = create_account()
    if new_acc:
        user_info['email'] = new_acc['address']
        user_info['password'] = new_acc['password']
        user_info['last_count'] = 0
        data[user_id] = user_info
        save_data(data)
        await update.message.reply_text(
            f"✅ *نوی برېښنالیک جوړ شو!*\n\n"
            f"📧 `{new_acc['address']}`\n"
            f"🔑 پټنوم: `{new_acc['password']}`\n\n"
            "_پټنوم په خوندي ځای کې وساتئ._",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ د برېښنالیک جوړول ناکام شول. بیا هڅه وکړئ.")

# د /id کمانډ
async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})
    email = user_info.get('email', 'هیڅ برېښنالیک نشته. لومړی /generate وکاروئ.')
    await update.message.reply_text(
        f"🆔 *ستاسو اوسنی برېښنالیک پته:*\n\n`{email}`",
        parse_mode="Markdown"
    )

# د /set کمانډ
async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_set'] = True
    await update.message.reply_text(
        "⚙️ *د دودیز برېښنالیک تنظیمول*\n\n"
        "مهرباني وکړئ خپل مطلوب نوم (د '@' پرته) ولیکئ.\n"
        "بڼه به داسې وي: `yourname@mail.tm`\n\n"
        "مثال: `ahmad`\n"
        "د لغوه کولو لپاره /cancel وکاروئ.",
        parse_mode="Markdown"
    )

# د /phone کمانډ
async def phone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_phone'] = True
    await update.message.reply_text(
        "📱 *د بیا رغونې شمېره اضافه/تازه کول*\n\n"
        "مهرباني وکړئ خپل د تلیفون شمېره د هیواد کوډ سره ولیکئ.\n"
        "بڼه: `+937XXXXXXXX`\n"
        "د لغوه کولو لپاره /cancel وکاروئ.",
        parse_mode="Markdown"
    )

# د /domain کمانډ - د موجودو دامنو لیست
async def domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domains = ["mail.tm", "geek.it", "slushmail.com", "drdrb.com", "spam4.me"]
    text = "🌐 *د موجودو دامنو لیست:*\n\n"
    for d in domains:
        text += f"• `{d}`\n"
    text += "\n_د دامن بدلول یوازې د تادیه شوي پلان سره ممکن دي._"
    await update.message.reply_text(text, parse_mode="Markdown")

# د /block کمانډ
async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})
    blocklist = user_info.get('blocklist', [])
    if not blocklist:
        blocklist_text = "هیڅ بلاک شوي فرستونکی نشته."
    else:
        blocklist_text = "\n".join([f"• `{b}`" for b in blocklist])
    await update.message.reply_text(
        f"🚫 *د بلاک لیست مدیریت*\n\nاوسنی لیست:\n{blocklist_text}\n\n"
        "د فرستونکي (برېښنالیک یا دامنه) د بلاک کولو لپاره، /block اضافه کړئ.\n"
        "مثال: `/block spammer@example.com`\n"
        "د لرې کولو لپاره: `/unblock example.com`",
        parse_mode="Markdown"
    )

# د /unblock کمانډ
async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})
    if not context.args:
        await update.message.reply_text("مهرباني وکړئ د لرې کولو لپاره یو برېښنالیک یا دامنه ورکړئ.\nمثال: `/unblock spammer@example.com`")
        return
    target = context.args[0]
    blocklist = user_info.get('blocklist', [])
    if target in blocklist:
        blocklist.remove(target)
        user_info['blocklist'] = blocklist
        data[user_id] = user_info
        save_data(data)
        await update.message.reply_text(f"✅ `{target}` له بلاک لیست څخه لرې شو.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ `{target}` په بلاک لیست کې نه و.", parse_mode="Markdown")

# د /about کمانډ
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *د بوټ په اړه*\n\n"
        "دا بوټ ستاسو د اصلي برېښنالیک ساتنه کوي او تاسو ته لنډمهالي پتې درکوي.\n"
        "په بشپړه توګه وړیا دی، د mail.tm خدمت کاروي.\n"
        "ټول معلومات په خوندي ډول ساتل کیږي.\n"
        "نسخه: 1.0",
        parse_mode="Markdown"
    )

# د /transfer کمانډ
async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_transfer'] = True
    await update.message.reply_text(
        "🔄 *آدرس بل تلګرام اکاونټ ته لېږدول*\n\n"
        "مهرباني وکړئ د هغه کارونکي آيډی یا یوزرنیم ولیکئ.\n"
        "بڼه: `@username` یا `123456789`\n"
        "د لغوه کولو لپاره /cancel وکاروئ.",
        parse_mode="Markdown"
    )

# د /cancel کمانډ
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ ټول انتظار حالتونه لغوه شول. له مینو څخه بیا پیل کړئ.")

# د /read کمانډ - د پیغام لوستل
async def read_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})
    if not context.args:
        await update.message.reply_text("مهرباني وکړئ د پیغام آيډي ورکړئ.\nمثال: `/read 12345`")
        return
    msg_id = context.args[0]
    email = user_info.get('email')
    password = user_info.get('password')
    if not email or not password:
        await update.message.reply_text("لومړی /generate وکاروئ.")
        return
    content = get_message_content(email, password, msg_id)
    if content:
        await update.message.reply_text(
            f"📄 *بشپړ متن:*\n\n{content}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ پیغام ونه موندل شو یا لاسرسی نشته.")

# ---------- د متن پیغامونو اداره کول (د کیبورد تڼیو لپاره) ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    data = load_data()
    user_info = data.get(user_id, {})

    # که کارونکی د /set یا /phone یا /transfer په انتظار کې وي
    if context.user_data.get('awaiting_set'):
        custom_name = text.strip().lower()
        if '@' in custom_name:
            await update.message.reply_text("❌ مهرباني وکړئ یوازې نوم ولیکئ، د '@' پرته.")
            return
        full_address = f"{custom_name}@mail.tm"
        new_acc = create_account(full_address)
        if new_acc:
            user_info['email'] = new_acc['address']
            user_info['password'] = new_acc['password']
            user_info['last_count'] = 0
            data[user_id] = user_info
            save_data(data)
            await update.message.reply_text(
                f"✅ *دودیز برېښنالیک جوړ شو!*\n\n"
                f"📧 `{new_acc['address']}`\n"
                f"🔑 پټنوم: `{new_acc['password']}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ دا نوم لا دمخه نیول شوی یا ناسم دی. بله هڅه وکړئ.")
        context.user_data['awaiting_set'] = False
        return

    if context.user_data.get('awaiting_phone'):
        phone = text.strip()
        if phone.startswith('+') and len(phone) > 8:
            user_info['phone'] = phone
            data[user_id] = user_info
            save_data(data)
            await update.message.reply_text(f"📱 *شمېره خوندي شوه:* `{phone}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ ناسمه بڼه. مهرباني وکړئ د + او هیواد کوډ سره ولیکئ.")
        context.user_data['awaiting_phone'] = False
        return

    if context.user_data.get('awaiting_transfer'):
        target = text.strip()
        user_info['transfer_to'] = target
        data[user_id] = user_info
        save_data(data)
        await update.message.reply_text(
            f"🔄 *د لېږد غوښتنه ثبت شوه.*\n"
            f"کله چې کارونکی `{target}` ومني، ستاسو برېښنالیک به هغه ته انتقال شي.",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_transfer'] = False
        return

    # که کارونکی د کیبورد تڼۍ کلیک کړی وي، د هغې په مطابق کمانډ اجرا کړئ
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
        await block_command(update, context)
    elif text == "ℹ️ About this bot":
        await about_command(update, context)
    elif text == "🔄 Transfer Address":
        await transfer_command(update, context)
    else:
        await update.message.reply_text("مهرباني وکړئ له مینو څخه یوه تڼۍ وټاکئ یا یو معتبر کمانډ وکاروئ.")

# ---------- د ریښتني وخت خبرتیاوې (JobQueue) ----------
async def check_emails(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    for user_id, info in data.items():
        email = info.get('email')
        password = info.get('password')
        if email and password:
            messages = get_messages(email, password)
            if messages:
                last_count = info.get('last_count', 0)
                if len(messages) > last_count:
                    new_msgs = messages[last_count:]
                    for msg in new_msgs:
                        sender = msg.get('from', {}).get('address', '')
                        blocklist = info.get('blocklist', [])
                        if any(block in sender for block in blocklist):
                            continue
                        content = get_message_content(email, password, msg['id'])
                        if content and len(content) > 500:
                            content = content[:500] + "..."
                        try:
                            await context.bot.send_message(
                                user_id,
                                f"📩 *نوی برېښنالیک!*\n\n"
                                f"📤 فرستونکی: `{sender}`\n"
                                f"📌 موضوع: `{msg.get('subject', 'بې موضوع')}`\n"
                                f"📝 لنډیز:\n{content}\n\n"
                                f"د بشپړ لوستلو لپاره /read `{msg['id']}` وکاروئ.",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                    info['last_count'] = len(messages)
                    data[user_id] = info
                    save_data(data)

# ---------- اصلي فعالیت ----------
def main():
    app = Application.builder().token(TOKEN).build()

    # کمانډونه
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("id", show_id))
    app.add_handler(CommandHandler("set", set_command))
    app.add_handler(CommandHandler("phone", phone_command))
    app.add_handler(CommandHandler("domain", domain_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("transfer", transfer_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("read", read_command))

    # د متن پیغامونو لپاره (د کیبورد تڼیو او نورو متنونو لپاره)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # د JobQueue تنظیمول - هر ۳۰ ثانیې یو ځل چک کول
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_emails, interval=30, first=10)

    print("✅ بوټ روان دی...")
    app.run_polling()

if __name__ == "__main__":
    main()
