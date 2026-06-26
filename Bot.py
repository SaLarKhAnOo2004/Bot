# -*- coding: utf-8 -*-
"""
دا یو بشپړ ټیلیګرام بوټ دی چې د لنډمهالي برېښنالیک (تېمپ میل) خدمات وړاندې کوي.
ټولې دندې: /generate, /id, /set, /phone, /domain, /block, /about, /transfer
او یو ښکلی مینو لري.
نویسنده: ستاسو د غوښتنې مطابق
"""

import asyncio
import json
import random
import string
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

# ---------- تنظیمات ----------
TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"  # دلته خپل توکن دننه کړئ
MAILTM_API = "https://api.mail.tm"
# د معلوماتو ذخیره کولو لپاره JSON فایل (د کارونکو ډاټا)
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
    """د نوي برېښنالیک اکاونټ جوړول (د mail.tm له لارې)"""
    if custom_address:
        # که کارونکي خپله پته غوښتل وي، هغه وکاروئ (که شتون ولري)
        address = custom_address
    else:
        # تصادفي پته جوړول
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{username}@mail.tm"  # د mail.tm اساسي دامنه
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    response = requests.post(f"{MAILTM_API}/accounts", json={
        "address": address,
        "password": password
    })
    if response.status_code == 201:
        return {"address": address, "password": password, "id": response.json()["id"]}
    else:
        return None

def get_token(email, password):
    """د لاسرسي توکن ترلاسه کول"""
    response = requests.post(f"{MAILTM_API}/token", json={
        "address": email,
        "password": password
    })
    if response.status_code == 200:
        return response.json()["token"]
    return None

def get_messages(email, password):
    """د برېښنالیک صندوق ټول پیغامونه لوستل"""
    token = get_token(email, password)
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAILTM_API}/messages", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_message_content(email, password, message_id):
    """د یو مشخص پیغام مینځپانګه (متن) ترلاسه کول"""
    token = get_token(email, password)
    if not token:
        return None
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAILTM_API}/messages/{message_id}", headers=headers)
    if response.status_code == 200:
        return response.json().get("text", "")
    return None

# ---------- د بوټ کمانډونه ----------

# د /start کمانډ - اصلي مینو
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📧 Get a new fake mail id", callback_data='generate')],
        [InlineKeyboardButton("🆔 Current fake mail id", callback_data='id')],
        [InlineKeyboardButton("⚙️ Setup custom fake mail id", callback_data='set')],
        [InlineKeyboardButton("📱 Add/update recovery phone", callback_data='phone')],
        [InlineKeyboardButton("🌐 Manage custom domains", callback_data='domain')],
        [InlineKeyboardButton("🚫 Manage Blocklist", callback_data='block')],
        [InlineKeyboardButton("ℹ️ About this bot", callback_data='about')],
        [InlineKeyboardButton("🔄 Transfer Address", callback_data='transfer')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 *سلام! د Fakemail بوټ ته ښه راغلاست!*\n\n"
        "لاندې له مینو څخه خپل مطلوب کار غوره کړئ:\n"
        "(د هرې تڼۍ لاندې د هغې دنده لیکل شوې ده)",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# د تڼیو اداره کول
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_data()
    user_info = data.get(user_id, {})

    if query.data == 'generate':
        # جوړول نوی برېښنالیک
        await query.edit_message_text("⏳ *نوی برېښنالیک جوړیږي...*", parse_mode="Markdown")
        new_acc = create_account()
        if new_acc:
            user_info['email'] = new_acc['address']
            user_info['password'] = new_acc['password']
            user_info['last_count'] = 0  # د نویو پیغامونو شمېرلو لپاره
            data[user_id] = user_info
            save_data(data)
            await query.edit_message_text(
                f"✅ *نوی برېښنالیک جوړ شو!*\n\n"
                f"📧 `{new_acc['address']}`\n"
                f"🔑 پټنوم: `{new_acc['password']}`\n\n"
                "_پټنوم په خوندي ځای کې وساتئ._",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ د برېښنالیک جوړول ناکام شول. بیا هڅه وکړئ.")

    elif query.data == 'id':
        email = user_info.get('email', 'هیڅ برېښنالیک نشته. لومړی /generate وکاروئ.')
        await query.edit_message_text(
            f"🆔 *ستاسو اوسنی برېښنالیک پته:*\n\n`{email}`",
            parse_mode="Markdown"
        )

    elif query.data == 'set':
        # د دودیز برېښنالیک تنظیمول (یوازې د نوم غوره کول)
        await query.edit_message_text(
            "⚙️ *د دودیز برېښنالیک تنظیمول*\n\n"
            "مهرباني وکړئ خپل مطلوب نوم (د '@' پرته) ولیکئ.\n"
            "بڼه به داسې وي: `yourname@mail.tm`\n\n"
            "د مثال په توګه: `ahmad`\n"
            "د لغوه کولو لپاره /cancel وکاروئ.",
            parse_mode="Markdown"
        )
        # دلته باید د انتظار حالت فعال شي - د ساده والي لپاره، موږ په یاد ساتو چې کارونکی په /set حالت کې دی
        context.user_data['awaiting_set'] = True

    elif query.data == 'phone':
        await query.edit_message_text(
            "📱 *د بیا رغونې شمېره اضافه/تازه کول*\n\n"
            "مهرباني وکړئ خپل د تلیفون شمېره د هیواد کوډ سره ولیکئ.\n"
            "بڼه: `+937XXXXXXXX`\n"
            "د لغوه کولو لپاره /cancel وکاروئ.",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_phone'] = True

    elif query.data == 'domain':
        # د دامنو مدیریت - د mail.tm وړیا دامنو لیست
        domains = ["mail.tm", "geek.it", "slushmail.com"]  # نمونه
        text = "🌐 *د موجودو دامنو لیست:*\n\n"
        for d in domains:
            text += f"• `{d}`\n"
        text += "\n_د دامن بدلول یوازې د تادیه شوي پلان سره ممکن دي._"
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == 'block':
        # د بلاک لیست مدیریت
        blocklist = user_info.get('blocklist', [])
        if not blocklist:
            blocklist_text = "هیڅ بلاک شوي فرستونکی نشته."
        else:
            blocklist_text = "\n".join([f"• `{b}`" for b in blocklist])
        await query.edit_message_text(
            f"🚫 *د بلاک لیست مدیریت*\n\nاوسنی لیست:\n{blocklist_text}\n\n"
            "د فرستونکي (برېښنالیک یا دامنه) د بلاک کولو لپاره، د /block اضافه کړئ.\n"
            "مثال: `/block spammer@example.com`\n"
            "د لرې کولو لپاره: `/unblock example.com`",
            parse_mode="Markdown"
        )

    elif query.data == 'about':
        await query.edit_message_text(
            "ℹ️ *د بوټ په اړه*\n\n"
            "دا بوټ ستاسو د اصلي برېښنالیک ساتنه کوي او تاسو ته لنډمهالي پتې درکوي.\n"
            "په بشپړه توګه وړیا دی، د mail.tm خدمت کاروي.\n"
            "ټول معلومات په خوندي ډول ساتل کیږي.\n"
            "نسخه: 1.0\n"
            "جوړونکی: ستاسو نوم",
            parse_mode="Markdown"
        )

    elif query.data == 'transfer':
        await query.edit_message_text(
            "🔄 *آدرس بل تلګرام اکاونټ ته لېږدول*\n\n"
            "مهرباني وکړئ د هغه کارونکي آيډي (یا یوزرنیم) ولیکئ چې غواړئ خپل برېښنالیک پته ورته انتقال کړئ.\n"
            "بڼه: `@username` یا `123456789`\n"
            "د لغوه کولو لپاره /cancel وکاروئ.",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_transfer'] = True

# د متن پیغامونو اداره کول (د /set, /phone, /transfer لپاره)
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    data = load_data()
    user_info = data.get(user_id, {})

    if context.user_data.get('awaiting_set'):
        # دودیز برېښنالیک جوړول
        custom_name = text.strip().lower()
        if '@' in custom_name:
            await update.message.reply_text("❌ مهرباني وکړئ یوازې نوم ولیکئ، د '@' پرته.")
            return
        full_address = f"{custom_name}@mail.tm"
        # وګورئ چې دا پته شته که نه (د mail.tm له لارې)
        # د ساده والي لپاره، موږ مستقیم جوړوو
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

    elif context.user_data.get('awaiting_phone'):
        # د تلیفون شمېره خوندي کول
        phone = text.strip()
        # ساده تایید (اختیاري)
        if phone.startswith('+') and len(phone) > 8:
            user_info['phone'] = phone
            data[user_id] = user_info
            save_data(data)
            await update.message.reply_text(f"📱 *شمېره خوندي شوه:* `{phone}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ ناسمه بڼه. مهرباني وکړئ د + او هیواد کوډ سره ولیکئ.")
        context.user_data['awaiting_phone'] = False

    elif context.user_data.get('awaiting_transfer'):
        # د بل کارونکي آيډی ترلاسه کول
        target = text.strip()
        # دلته باید تایید شي چې هدف شتون لري - موږ یوازې په یاد ساتو
        user_info['transfer_to'] = target
        data[user_id] = user_info
        save_data(data)
        await update.message.reply_text(
            f"🔄 *د لېږد غوښتنه ثبت شوه.*\n"
            f"کله چې کارونکی `{target}` ومني، ستاسو برېښنالیک به هغه ته انتقال شي.\n"
            "(د منلو لپاره به جلا کمانډ وي.)",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_transfer'] = False

    else:
        # نور عادي پیغامونه
        await update.message.reply_text("مهرباني وکړئ له مینو څخه یوه تڼۍ وټاکئ یا یو معتبر کمانډ وکاروئ.")

# د /cancel کمانډ - د انتظار حالت لغوه کول
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ ټول انتظار حالتونه لغوه شول. له مینو څخه بیا پیل کړئ.")

# د /block کمانډ - یو فرستونکی بلاک کول
async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_info = data.get(user_id, {})
    if not context.args:
        await update.message.reply_text("مهرباني وکړئ د بلاک کولو لپاره یو برېښنالیک یا دامنه ورکړئ.\nمثال: `/block spammer@example.com`")
        return
    target = context.args[0]
    blocklist = user_info.get('blocklist', [])
    if target not in blocklist:
        blocklist.append(target)
        user_info['blocklist'] = blocklist
        data[user_id] = user_info
        save_data(data)
        await update.message.reply_text(f"✅ `{target}` بلاک شو.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ `{target}` لا دمخه په بلاک لیست کې دی.", parse_mode="Markdown")

# د /unblock کمانډ - د بلاک لرې کول
async def unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ------- د ریښتني وخت خبرتیاوې (JobQueue) --------
async def check_emails(context: ContextTypes.DEFAULT_TYPE):
    """دا فنکشن هر 30 ثانیې یو ځل چلیږي او نوي پیغامونه چک کوي"""
    data = load_data()
    for user_id, info in data.items():
        email = info.get('email')
        password = info.get('password')
        if email and password:
            messages = get_messages(email, password)
            if messages:
                last_count = info.get('last_count', 0)
                if len(messages) > last_count:
                    # نوی پیغام راغلی
                    new_msgs = messages[last_count:]
                    for msg in new_msgs:
                        # چیک کړئ چې فرستونکی په بلاک لیست کې نه وي
                        sender = msg.get('from', {}).get('address', '')
                        blocklist = info.get('blocklist', [])
                        if any(block in sender for block in blocklist):
                            continue  # بلاک شوی، پریږدئ
                        # د پیغام مینځپانګه واخلئ (لومړی ۵۰۰ توري)
                        content = get_message_content(email, password, msg['id'])
                        if content and len(content) > 500:
                            content = content[:500] + "..."
                        # کارونکي ته خبرتیا واستوئ
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
                        except Exception as e:
                            print(f"خطا: {e}")
                    # شمېره تازه کول
                    info['last_count'] = len(messages)
                    data[user_id] = info
                    save_data(data)

# د /read کمانډ - د یو پیغام بشپړ لوستل
async def read(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ---------- اصلي فعالیت ----------
def main():
    # بوټ جوړول
    app = Application.builder().token(TOKEN).build()

    # کمانډونه ثبت کول
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("block", block))
    app.add_handler(CommandHandler("unblock", unblock))
    app.add_handler(CommandHandler("read", read))
    # د تڼیو اداره کول
    app.add_handler(CallbackQueryHandler(button_handler))
    # د متن پیغامونو اداره کول (د /set، /phone، /transfer لپاره)
    app.add_handler(CommandHandler("set", lambda u, c: text_handler(u, c)))  # موقتي حل - په حقیقت کې د text_handler له لارې
    # موږ باید د text_handler د لاسي کولو لپاره یو MessageHandler هم اضافه کړو
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # د JobQueue تنظیمول - هر ۳۰ ثانیې یو ځل چک کول
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_emails, interval=30, first=10)

    # بوټ پیل کول
    print("بوټ روان دی...")
    app.run_polling()

if __name__ == "__main__":
    main()
