#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ============================================================
# مجازی شمېرې بوټ - ټول په یو فایل کې (د کارونکي + اتومات)
# ============================================================

# -------------------- ۱. کتابتونونه --------------------
import sqlite3
import json
import time
import threading
import re
from datetime import datetime, timedelta

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
import phonenumbers
import countryflag

# ============================================================
# -------------------- ۲. تنظیمات (Config) --------------------
# ============================================================

# د Telegram بوټ توکنونه
USER_BOT_TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"  # د کارونکي بوټ
AUTO_BOT_TOKEN = "8890120628:AAFf-cLeuNw1PXLKGN9L6nDVR26L-3yNzn0"  # د اتومات بوټ

# د مدیرانو ID لیست (یوازې دا کسان کولای شي بوټ وکاروي)
ADMIN_IDS = [5887665463]  # خپل Telegram ID دلته دننه کړئ

# د OnlineSim API تنظیمات (که API کیلي لرئ)
ONLINESIM_API_KEY = ""  # که نه لرئ، خالي پرېږدئ
ONLINESIM_BASE_URL = "https://onlinesim.io/api"

# د ډیټابیس فایل نوم
DATABASE_FILE = "numbers.db"

# د اتومات بوټ تنظیمات
AUTO_CHECK_INTERVAL = 30  # هره ۳۰ ثانیه یو ځل چیک کړي
MAX_NUMBERS_PER_COUNTRY = 50  # د هر هیواد لپاره ډېرې شمېرې

# د OnlineSim لپاره د هیوادونو کوډونه
COUNTRIES = {
    "افغانستان": 18,
    "روسیه": 0,
    "اوکراین": 1,
    "قزاقستان": 2,
    "امریکا": 3,
    "انګلستان": 4,
    "چین": 5,
    "هند": 6,
    "پاکستان": 15,
    "ازبکستان": 17,
}

# د خدماتو نومونه (لکه څنګه چې OnlineSim پېژني)
SERVICES = {
    "telegram": 1,
    "whatsapp": 2,
    "facebook": 3,
    "instagram": 4,
    "gmail": 5,
}

# ============================================================
# -------------------- ۳. د ډیټابیس عملیات --------------------
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE NOT NULL,
            country TEXT NOT NULL,
            service TEXT NOT NULL,
            tzid TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL,
            service TEXT NOT NULL,
            code TEXT,
            message_text TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (phone_number) REFERENCES numbers (phone_number)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            country TEXT NOT NULL,
            phone_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_number(phone_number, country, service, tzid=None, expires_minutes=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    expires_at = datetime.now() + timedelta(minutes=expires_minutes)
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO numbers 
            (phone_number, country, service, tzid, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (phone_number, country, service, tzid, expires_at))
        conn.commit()
        return True
    except Exception as e:
        print(f"خطا: {e}")
        return False
    finally:
        conn.close()

def get_active_numbers(country=None, service=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM numbers WHERE is_active = 1 AND expires_at > datetime('now')"
    params = []
    if country:
        query += " AND country = ?"
        params.append(country)
    if service:
        query += " AND service = ?"
        params.append(service)
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_number_by_phone(phone_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM numbers WHERE phone_number = ?", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def deactivate_number(phone_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE numbers SET is_active = 0 WHERE phone_number = ?", (phone_number,))
    conn.commit()
    conn.close()

def save_message(phone_number, service, code=None, message_text=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (phone_number, service, code, message_text)
        VALUES (?, ?, ?, ?)
    ''', (phone_number, service, code, message_text))
    conn.commit()
    conn.close()

def get_messages(phone_number, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM messages 
        WHERE phone_number = ? 
        ORDER BY received_at DESC 
        LIMIT ?
    ''', (phone_number, limit))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def create_user_request(user_id, service, country):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_requests (user_id, service, country, status)
        VALUES (?, ?, ?, 'pending')
    ''', (user_id, service, country))
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    return request_id

def update_user_request(request_id, phone_number, status='completed'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_requests 
        SET phone_number = ?, status = ? 
        WHERE id = ?
    ''', (phone_number, status, request_id))
    conn.commit()
    conn.close()

# ============================================================
# -------------------- ۴. د API اړیکه --------------------
# ============================================================

def get_virtual_number(country_name, service_name):
    country_code = COUNTRIES.get(country_name, 0)
    service_code = SERVICES.get(service_name.lower(), 1)
    url = f"{ONLINESIM_BASE_URL}/getNum.php"
    params = {
        "service": service_code,
        "country": country_code,
        "operator": "any"
    }
    if ONLINESIM_API_KEY:
        params["apikey"] = ONLINESIM_API_KEY
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if response.status_code == 200 and data.get("response") == "1":
            return {
                "success": True,
                "number": data.get("number"),
                "tzid": data.get("tzid"),
                "country": country_name,
                "service": service_name
            }
        else:
            error = data.get("msg", "نامعلومه خطا")
            return {"success": False, "error": error}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_inbox(tzid):
    url = f"{ONLINESIM_BASE_URL}/getMessages.php"
    params = {"tzid": tzid}
    if ONLINESIM_API_KEY:
        params["apikey"] = ONLINESIM_API_KEY
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if isinstance(data, list):
            return data
        else:
            return []
    except:
        return []

def extract_verification_code(message_text):
    patterns = [
        r'\b(\d{4,6})\b',
        r'کد[:\s]*(\d{4,6})',
        r'code[:\s]*(\d{4,6})',
        r'verification[:\s]*(\d{4,6})',
    ]
    for pattern in patterns:
        match = re.search(pattern, message_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

# ============================================================
# -------------------- ۵. د کارونکي بوټ (User Bot) --------------------
# ============================================================

user_bot = telebot.TeleBot(USER_BOT_TOKEN)

def is_allowed(user_id):
    return user_id in ADMIN_IDS if ADMIN_IDS else True

@user_bot.message_handler(commands=['start'])
def start_command(message):
    if not is_allowed(message.from_user.id):
        user_bot.reply_to(message, "⛔ بخښنه، تاسو د دې بوټ کارولو اجازه نلرئ.")
        return
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("📞 نوی مجازی شمېره"),
        KeyboardButton("📥 زما شمېرې"),
        KeyboardButton("🌍 هیوادونه"),
        KeyboardButton("❓ مرسته")
    )
    user_bot.reply_to(message,
        "🌟 **مجازی شمېرې بوټ ته ښه راغلاست!**\n\n"
        "زه کولی شم تاسو ته د فیسبوک، ټیلیګرام، واتساپ او نورو خدماتو لپاره "
        "مجازی شمېرې او تایید کوډونه درکړم.\n\n"
        "لاندې تڼۍ وکاروئ:\n"
        "• **نوی مجازی شمېره** - یوه نوې شمېره ترلاسه کړئ\n"
        "• **زما شمېرې** - خپلې فعالې شمېرې وګورئ\n"
        "• **هیوادونه** - د شته هیوادونو لست",
        parse_mode="Markdown",
        reply_markup=markup
    )

@user_bot.message_handler(func=lambda m: m.text == "🌍 هیوادونه")
def show_countries(message):
    if not is_allowed(message.from_user.id):
        return
    text = "🌍 **شته هیوادونه:**\n\n"
    for country in COUNTRIES.keys():
        text += f"• {country}\n"
    user_bot.reply_to(message, text, parse_mode="Markdown")

@user_bot.message_handler(func=lambda m: m.text == "📞 نوی مجازی شمېره")
def start_new_number(message):
    if not is_allowed(message.from_user.id):
        return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📱 ټیلیګرام", callback_data="service_telegram"),
        InlineKeyboardButton("💬 واتساپ", callback_data="service_whatsapp"),
        InlineKeyboardButton("📘 فیسبوک", callback_data="service_facebook"),
        InlineKeyboardButton("📸 انسټاګرام", callback_data="service_instagram"),
        InlineKeyboardButton("📧 جیمیل", callback_data="service_gmail")
    )
    user_bot.reply_to(message, "لومړی هغه خدمت وټاکئ چې ورته شمېرې غواړئ:", reply_markup=markup)

@user_bot.callback_query_handler(func=lambda call: call.data.startswith("service_"))
def select_service(call):
    if not is_allowed(call.from_user.id):
        user_bot.answer_callback_query(call.id, "اجازه نشته", show_alert=True)
        return
    service = call.data.replace("service_", "")
    user_bot.answer_callback_query(call.id, f"خدمت {service} انتخاب شو")
    markup = InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES.keys():
        markup.add(InlineKeyboardButton(country, callback_data=f"country_{country}_{service}"))
    user_bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"اوس د {service} لپاره هیواد وټاکئ:",
        reply_markup=markup
    )

@user_bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def select_country(call):
    if not is_allowed(call.from_user.id):
        user_bot.answer_callback_query(call.id, "اجازه نشته", show_alert=True)
        return
    parts = call.data.split("_")
    country = parts[1]
    service = parts[2]
    user_bot.answer_callback_query(call.id, f"هیواد {country} انتخاب شو")
    request_id = create_user_request(call.from_user.id, service, country)
    sent_msg = user_bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"⏳ د {country} لپاره د {service} شمېره ترلاسه کېږي...\nمهرباني وکړئ یو څه انتظار وکړئ."
    )
    result = get_virtual_number(country, service)
    if result["success"]:
        phone = result["number"]
        tzid = result["tzid"]
        add_number(phone, country, service, tzid)
        update_user_request(request_id, phone)
        try:
            parsed = phonenumbers.parse(f"+{phone}")
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            flag = countryflag.getflag(phonenumbers.region_code_for_country_code(parsed.country_code))
        except:
            formatted = f"+{phone}"
            flag = "🌍"
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📥 پیغامونه (Inbox)", callback_data=f"inbox_{tzid}_{phone}"),
            InlineKeyboardButton("🔄 نوې شمېره", callback_data=f"new_{service}_{country}"),
            InlineKeyboardButton("ℹ️ پروفایل", url=f"tg://resolve?phone=+{phone}")
        )
        user_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=sent_msg.message_id,
            text=f"{flag} **ستاسو مجازی شمېره:**\n`{formatted}`\n\n"
                 f"📱 خدمت: {service}\n"
                 f"🌍 هیواد: {country}\n\n"
                 "د تایید کوډ ترلاسه کولو لپاره، په همدې شمېره یې واستوئ او بیا د 'پیغامونه' تڼۍ کېکاږئ.",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        user_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=sent_msg.message_id,
            text=f"❌ شمېره ترلاسه نه شوه.\nخطا: {result.get('error', 'نامعلومه')}\n\n"
                 "مهرباني وکړئ بیا هڅه وکړئ یا بل هیواد وکاروئ."
        )

@user_bot.callback_query_handler(func=lambda call: call.data.startswith("inbox_"))
def show_inbox(call):
    if not is_allowed(call.from_user.id):
        user_bot.answer_callback_query(call.id, "اجازه نشته", show_alert=True)
        return
    parts = call.data.split("_")
    tzid = parts[1]
    phone = parts[2] if len(parts) > 2 else None
    user_bot.answer_callback_query(call.id, "پیغامونه راوړل کیږي...")
    messages = get_inbox(tzid)
    if messages:
        for msg in messages[:5]:
            text = msg.get("text", "پیغام نشته")
            date = msg.get("date", "نامعلوم وخت")
            code = extract_verification_code(text)
            if phone:
                save_message(phone, "unknown", code, text)
            msg_text = f"📩 **نېټه:** {date}\n"
            if code:
                msg_text += f"🔑 **تایید کوډ:** `{code}`\n"
            msg_text += f"📝 **متن:** {text}"
            user_bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")
    else:
        user_bot.send_message(call.message.chat.id, 
            "📭 د دې شمېرې لپاره هېڅ پیغام نشته.\n"
            "که تاسو تایید کوډ واستولی وي، مهرباني وکړئ یو څه انتظار وکړئ او بیا هڅه وکړئ."
        )

@user_bot.message_handler(func=lambda m: m.text == "📥 زما شمېرې")
def my_numbers(message):
    if not is_allowed(message.from_user.id):
        return
    numbers = get_active_numbers()
    if not numbers:
        user_bot.reply_to(message, "📭 تاسو لا تر اوسه کومه فعاله شمېره نلرئ.\nد نوي شمېرې لپاره 'نوی مجازی شمېره' وکاروئ.")
        return
    text = "📋 **ستاسو فعالې شمېرې:**\n\n"
    for num in numbers:
        text += f"📞 +{num['phone_number']}\n"
        text += f"   🌍 {num['country']} | 📱 {num['service']}\n"
        text += f"   ⏳ پای: {num['expires_at']}\n\n"
    user_bot.reply_to(message, text, parse_mode="Markdown")

@user_bot.message_handler(func=lambda m: m.text == "❓ مرسته")
def help_command(message):
    if not is_allowed(message.from_user.id):
        return
    user_bot.reply_to(message,
        "🔧 **لارښود:**\n\n"
        "1. 'نوی مجازی شمېره' کلیک کړئ\n"
        "2. مطلوب خدمت (فیسبوک، ټیلیګرام، واتساپ) وټاکئ\n"
        "3. هیواد وټاکئ\n"
        "4. بوټ به تاسو ته یوه شمېره درکړي\n"
        "5. د تایید کوډ ترلاسه کولو لپاره 'پیغامونه' تڼۍ وکاروئ\n\n"
        "⚠️ **یادونه:** دا شمېرې وړیا دي او ممکن تل فعالې نه وي.\n"
        "هره شمېره یوازې د ۱۰ دقیقو لپاره فعاله وي."
    )

# ============================================================
# -------------------- ۶. د اتومات بوټ (Auto Bot) --------------------
# ============================================================

auto_bot = telebot.TeleBot(AUTO_BOT_TOKEN)

def auto_collect_numbers():
    """په اتوماتیک ډول له ټولو هیوادونو او خدماتو څخه شمېرې راټولوي"""
    while True:
        try:
            for country in COUNTRIES.keys():
                for service in SERVICES.keys():
                    existing = get_active_numbers(country, service)
                    if len(existing) >= MAX_NUMBERS_PER_COUNTRY:
                        continue
                    result = get_virtual_number(country, service)
                    if result["success"]:
                        phone = result["number"]
                        tzid = result["tzid"]
                        add_number(phone, country, service, tzid)
                        for admin_id in ADMIN_IDS:
                            try:
                                auto_bot.send_message(admin_id, 
                                    f"🔄 **نوې شمېره اضافه شوه!**\n"
                                    f"📞 +{phone}\n"
                                    f"🌍 {country}\n"
                                    f"📱 {service}"
                                )
                            except:
                                pass
                        time.sleep(2)
        except Exception as e:
            print(f"خطا په اتومات راټولونکي کې: {e}")
        time.sleep(AUTO_CHECK_INTERVAL)

def auto_check_messages():
    """د ټولو فعالو شمېرو پیغامونه چیک کوي او تایید کوډونه استخراج کوي"""
    while True:
        try:
            numbers = get_active_numbers()
            for num in numbers:
                if not num.get('tzid'):
                    continue
                messages = get_inbox(num['tzid'])
                if messages:
                    for msg in messages:
                        text = msg.get("text", "")
                        code = extract_verification_code(text)
                        if code:
                            save_message(num['phone_number'], num['service'], code, text)
                            for admin_id in ADMIN_IDS:
                                try:
                                    auto_bot.send_message(admin_id,
                                        f"🔑 **نوی تایید کوډ!**\n"
                                        f"📞 شمېره: +{num['phone_number']}\n"
                                        f"🌍 هیواد: {num['country']}\n"
                                        f"📱 خدمت: {num['service']}\n"
                                        f"🔐 کوډ: `{code}`"
                                    )
                                except:
                                    pass
                            time.sleep(1)
        except Exception as e:
            print(f"خطا په اتومات پیغام چیک کونکي کې: {e}")
        time.sleep(AUTO_CHECK_INTERVAL)

@auto_bot.message_handler(commands=['start'])
def auto_start_command(message):
    if message.from_user.id not in ADMIN_IDS:
        auto_bot.reply_to(message, "⛔ تاسو مدیر نه یاست.")
        return
    auto_bot.reply_to(message,
        "🤖 **اتومات بوټ فعال دی!**\n\n"
        "دا بوټ په شالید کې کار کوي او په اتوماتیک ډول:\n"
        "• له آنلاین سرچینو څخه مجازی شمېرې راټولوي\n"
        "• د شمېرو پیغامونه چیک کوي\n"
        "• تایید کوډونه استخراج او خوندي کوي\n\n"
        "ټول معلومات په ډیټابیس کې خوندي کیږي."
    )

@auto_bot.message_handler(commands=['stats'])
def auto_stats_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    numbers = get_active_numbers()
    total = len(numbers)
    country_stats = {}
    for num in numbers:
        country_stats[num['country']] = country_stats.get(num['country'], 0) + 1
    text = f"📊 **احصایې:**\n\n"
    text += f"📞 ټول فعالې شمېرې: {total}\n\n"
    text += "**د هیوادونو له مخې:**\n"
    for country, count in country_stats.items():
        text += f"• {country}: {count}\n"
    auto_bot.reply_to(message, text, parse_mode="Markdown")

# ============================================================
# -------------------- ۷. د بوټونو چلول (په جلا تارونو کې) --------------------
# ============================================================

def run_user_bot():
    print("✅ د کارونکي بوټ پیل شو...")
    user_bot.infinity_polling(skip_pending=True)

def run_auto_bot():
    # د اتومات پروسې په جلا تارونو کې پیل کول
    threading.Thread(target=auto_collect_numbers, daemon=True).start()
    threading.Thread(target=auto_check_messages, daemon=True).start()
    print("✅ د اتومات بوټ پیل شو...")
    print("🔄 د شمېرو راټولونکی او پیغام چیک کونکی فعال شو.")
    auto_bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    init_database()
    # دوه بوټونه په جلا تارونو کې چلول
    t1 = threading.Thread(target=run_user_bot, daemon=True)
    t2 = threading.Thread(target=run_auto_bot, daemon=True)
    t1.start()
    t2.start()
    # د تارونو فعال ساتل
    while True:
        time.sleep(1)
