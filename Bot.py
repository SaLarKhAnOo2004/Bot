#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ============================================================
# مجازی شمېرې بوټ - د خطا تشخیص سره تازه شوی
# ============================================================

import sqlite3
import time
import threading
import re
from datetime import datetime, timedelta
import requests
import phonenumbers
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ============================================================
# تنظیمات (خپل توکنونه دلته دننه کړئ)
# ============================================================

USER_BOT_TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"
AUTO_BOT_TOKEN = "8890120628:AAFf-cLeuNw1PXLKGN9L6nDVR26L-3yNzn0"
ADMIN_IDS = [5887665463]

ONLINESIM_API_KEY = ""  # که لرئ، دلته یې دننه کړئ
ONLINESIM_BASE_URL = "https://onlinesim.io/api"

DATABASE_FILE = "numbers.db"
AUTO_CHECK_INTERVAL = 30
MAX_NUMBERS_PER_COUNTRY = 50

# ============================================================
# د هیوادونو کوډونه (د OnlineSim سره سم)
# ============================================================

COUNTRIES = {
    "روسیه": 0,
    "اوکراین": 1,
    "قزاقستان": 2,
    "امریکا": 3,
    "انګلستان": 4,
    "چین": 5,
    "هند": 6,
    "افغانستان": 18,
    "پاکستان": 15,
    "ازبکستان": 17,
}

COUNTRY_FLAGS = {
    "افغانستان": "🇦🇫", "روسیه": "🇷🇺", "اوکراین": "🇺🇦",
    "قزاقستان": "🇰🇿", "امریکا": "🇺🇸", "انګلستان": "🇬🇧",
    "چین": "🇨🇳", "هند": "🇮🇳", "پاکستان": "🇵🇰", "ازبکستان": "🇺🇿",
}

# د خدماتو کوډونه (د OnlineSim سره سم)
SERVICES = {
    "telegram": 1,
    "whatsapp": 2,
    "facebook": 3,
    "instagram": 4,
    "gmail": 5,
}

# د ازمایښت لپاره تضمیني ترکیبونه (تل شته)
TEST_COMBOS = [
    {"country": "روسیه", "service": "telegram"},
    {"country": "روسیه", "service": "whatsapp"},
    {"country": "امریکا", "service": "telegram"},
    {"country": "انګلستان", "service": "telegram"},
]

# ============================================================
# د ډیټابیس او API دندې (هماغسې)
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE,
        country TEXT,
        service TEXT,
        tzid TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT,
        service TEXT,
        code TEXT,
        message_text TEXT,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        service TEXT,
        country TEXT,
        phone_number TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def add_number(phone, country, service, tzid=None, expires_minutes=10):
    conn = get_db_connection()
    c = conn.cursor()
    expires_at = datetime.now() + timedelta(minutes=expires_minutes)
    try:
        c.execute('INSERT OR REPLACE INTO numbers (phone_number, country, service, tzid, expires_at, is_active) VALUES (?,?,?,?,?,1)',
                  (phone, country, service, tzid, expires_at))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

def get_active_numbers(country=None, service=None):
    conn = get_db_connection()
    c = conn.cursor()
    q = "SELECT * FROM numbers WHERE is_active=1 AND expires_at > datetime('now')"
    p = []
    if country:
        q += " AND country=?"
        p.append(country)
    if service:
        q += " AND service=?"
        p.append(service)
    c.execute(q, p)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_message(phone, service, code=None, text=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO messages (phone_number, service, code, message_text) VALUES (?,?,?,?)',
              (phone, service, code, text))
    conn.commit()
    conn.close()

def create_user_request(user_id, service, country):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO user_requests (user_id, service, country, status) VALUES (?,?,?,"pending")',
              (user_id, service, country))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid

def update_user_request(rid, phone, status="completed"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE user_requests SET phone_number=?, status=? WHERE id=?', (phone, status, rid))
    conn.commit()
    conn.close()

# ============================================================
# د API اړیکه (د دقیقې خطا تشخیص سره)
# ============================================================

def get_virtual_number(country_name, service_name):
    country_code = COUNTRIES.get(country_name)
    service_code = SERVICES.get(service_name.lower())
    
    # که کوډ ونه موندل شي
    if country_code is None:
        return {"success": False, "error": f"هیواد '{country_name}' ونه موندل شو"}
    if service_code is None:
        return {"success": False, "error": f"خدمت '{service_name}' ونه موندل شو"}
    
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
        
        # د API ځواب چک کول
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP خطا: {response.status_code}"}
        
        if data.get("response") == "1":
            number = data.get("number")
            tzid = data.get("tzid")
            if number and tzid:
                return {
                    "success": True,
                    "number": number,
                    "tzid": tzid,
                    "country": country_name,
                    "service": service_name
                }
            else:
                return {"success": False, "error": "API ځواب کې شمېره یا tzid نشته"}
        else:
            # د API اصلي خطا
            error_msg = data.get("msg", "نامعلومه خطا")
            return {"success": False, "error": f"API خطا: {error_msg}"}
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "د API غوښتنه وخت وت (Timeout)"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "انټرنیټ اړیکه نشته"}
    except Exception as e:
        return {"success": False, "error": f"نور خطا: {str(e)}"}

def get_inbox(tzid):
    url = f"{ONLINESIM_BASE_URL}/getMessages.php"
    params = {"tzid": tzid}
    if ONLINESIM_API_KEY:
        params["apikey"] = ONLINESIM_API_KEY
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if isinstance(data, list):
            return data
        return []
    except:
        return []

def extract_verification_code(text):
    patterns = [r'\b(\d{4,6})\b', r'کد[:\s]*(\d{4,6})', r'code[:\s]*(\d{4,6})', r'verification[:\s]*(\d{4,6})']
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

# ============================================================
# د کارونکي بوټ
# ============================================================

user_bot = telebot.TeleBot(USER_BOT_TOKEN)

def is_allowed(uid):
    return uid in ADMIN_IDS if ADMIN_IDS else True

@user_bot.message_handler(commands=['start'])
def start_cmd(m):
    if not is_allowed(m.from_user.id):
        user_bot.reply_to(m, "⛔ تاسو اجازه نلرئ.")
        return
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📞 نوی مجازی شمېره"), KeyboardButton("📥 زما شمېرې"), KeyboardButton("🌍 هیوادونه"), KeyboardButton("❓ مرسته"))
    user_bot.reply_to(m, "🌟 **مجازی شمېرې بوټ ته ښه راغلاست!**\n\nزه کولی شم تاسو ته د فیسبوک، ټیلیګرام، واتساپ او نورو لپاره مجازی شمېرې درکړم.", parse_mode="Markdown", reply_markup=markup)

@user_bot.message_handler(func=lambda m: m.text == "🌍 هیوادونه")
def show_countries(m):
    if not is_allowed(m.from_user.id): return
    text = "🌍 **شته هیوادونه:**\n\n"
    for c in COUNTRIES.keys():
        text += f"{COUNTRY_FLAGS.get(c, '🌍')} {c}\n"
    user_bot.reply_to(m, text, parse_mode="Markdown")

@user_bot.message_handler(func=lambda m: m.text == "📞 نوی مجازی شمېره")
def start_new_number(m):
    if not is_allowed(m.from_user.id): return
    markup = InlineKeyboardMarkup(row_width=2)
    for srv in SERVICES.keys():
        markup.add(InlineKeyboardButton(f"📱 {srv.title()}", callback_data=f"service_{srv}"))
    user_bot.reply_to(m, "لومړی خدمت وټاکئ:", reply_markup=markup)

@user_bot.callback_query_handler(func=lambda c: c.data.startswith("service_"))
def select_service(c):
    if not is_allowed(c.from_user.id):
        user_bot.answer_callback_query(c.id, "اجازه نشته", True)
        return
    service = c.data.replace("service_", "")
    user_bot.answer_callback_query(c.id, f"خدمت {service} انتخاب شو")
    markup = InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES.keys():
        flag = COUNTRY_FLAGS.get(country, "🌍")
        markup.add(InlineKeyboardButton(f"{flag} {country}", callback_data=f"country_{country}_{service}"))
    user_bot.edit_message_text(f"اوس د {service} لپاره هیواد وټاکئ:", c.message.chat.id, c.message.message_id, reply_markup=markup)

@user_bot.callback_query_handler(func=lambda c: c.data.startswith("country_"))
def select_country(c):
    if not is_allowed(c.from_user.id):
        user_bot.answer_callback_query(c.id, "اجازه نشته", True)
        return
    parts = c.data.split("_")
    country = parts[1]
    service = parts[2]
    user_bot.answer_callback_query(c.id, f"هیواد {country} انتخاب شو")
    request_id = create_user_request(c.from_user.id, service, country)
    sent = user_bot.edit_message_text(f"⏳ د {country} لپاره د {service} شمېره ترلاسه کېږي...", c.message.chat.id, c.message.message_id)
    
    # د شمېرې ترلاسه کول
    result = get_virtual_number(country, service)
    
    if result["success"]:
        phone = result["number"]
        tzid = result["tzid"]
        add_number(phone, country, service, tzid)
        update_user_request(request_id, phone)
        try:
            parsed = phonenumbers.parse(f"+{phone}")
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except:
            formatted = f"+{phone}"
        flag = COUNTRY_FLAGS.get(country, "🌍")
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📥 پیغامونه", callback_data=f"inbox_{tzid}_{phone}"),
            InlineKeyboardButton("🔄 نوې شمېره", callback_data=f"new_{service}_{country}"),
            InlineKeyboardButton("ℹ️ پروفایل", url=f"tg://resolve?phone=+{phone}")
        )
        user_bot.edit_message_text(
            f"{flag} **ستاسو مجازی شمېره:**\n`{formatted}`\n\n📱 خدمت: {service}\n🌍 هیواد: {country}\n\nد 'پیغامونه' تڼۍ سره تایید کوډ ترلاسه کړئ.",
            c.message.chat.id, sent.message_id, parse_mode="Markdown", reply_markup=markup
        )
    else:
        # خطا تشخیص - د کارونکي لارښوونه
        error = result.get("error", "نامعلومه")
        help_text = f"❌ **شمېره ترلاسه نه شوه.**\nخطا: `{error}`\n\n"
        if "API خطا" in error and "not found" in error:
            help_text += "دغه هیواد او خدمت شتون نلري. مهرباني وکړئ بل هیواد یا خدمت وکاروئ.\n"
            help_text += "تضمیني ترکیبونه: روسیه+ټیلیګرام، روسیه+واتساپ، امریکا+ټیلیګرام"
        elif "Timeout" in error:
            help_text += "انټرنیټ ورو دی یا API نه رسیږي. یو څه انتظار وکړئ او بیا هڅه وکړئ."
        elif "انټرنیټ" in error:
            help_text += "خپل انټرنیټ وګورئ او بیا هڅه وکړئ."
        else:
            help_text += "د OnlineSim API ممکن محدودیت ولري یا شمېرې پای ته رسېدلي وي.\n"
            help_text += "لاندې ترکیبونه ازمایئ: **روسیه + ټیلیګرام**، **روسیه + واتساپ**، **امریکا + ټیلیګرام**"
        
        user_bot.edit_message_text(help_text, c.message.chat.id, sent.message_id, parse_mode="Markdown")

@user_bot.callback_query_handler(func=lambda c: c.data.startswith("inbox_"))
def show_inbox(c):
    if not is_allowed(c.from_user.id):
        user_bot.answer_callback_query(c.id, "اجازه نشته", True)
        return
    parts = c.data.split("_")
    tzid = parts[1]
    phone = parts[2] if len(parts) > 2 else None
    user_bot.answer_callback_query(c.id, "پیغامونه راوړل کیږي...")
    msgs = get_inbox(tzid)
    if msgs:
        for msg in msgs[:5]:
            text = msg.get("text", "پیغام نشته")
            date = msg.get("date", "نامعلوم")
            code = extract_verification_code(text)
            if phone:
                save_message(phone, "unknown", code, text)
            txt = f"📩 **نېټه:** {date}\n"
            if code:
                txt += f"🔑 **کوډ:** `{code}`\n"
            txt += f"📝 {text}"
            user_bot.send_message(c.message.chat.id, txt, parse_mode="Markdown")
    else:
        user_bot.send_message(c.message.chat.id, "📭 پیغام نشته. که کوډ مو استولی وي، یو څه انتظار وکړئ او بیا هڅه وکړئ.")

@user_bot.message_handler(func=lambda m: m.text == "📥 زما شمېرې")
def my_numbers(m):
    if not is_allowed(m.from_user.id): return
    nums = get_active_numbers()
    if not nums:
        user_bot.reply_to(m, "📭 فعاله شمېره نشته.")
        return
    text = "📋 **ستاسو شمېرې:**\n\n"
    for n in nums:
        flag = COUNTRY_FLAGS.get(n['country'], "🌍")
        text += f"{flag} +{n['phone_number']} ({n['service']}) - تر {n['expires_at']}\n"
    user_bot.reply_to(m, text, parse_mode="Markdown")

@user_bot.message_handler(func=lambda m: m.text == "❓ مرسته")
def help_cmd(m):
    if not is_allowed(m.from_user.id): return
    user_bot.reply_to(m,
        "🔧 **لارښود:**\n"
        "1. 'نوی مجازی شمېره' کلیک کړئ\n"
        "2. خدمت وټاکئ (ټیلیګرام، واتساپ، فیسبوک...)\n"
        "3. هیواد وټاکئ\n"
        "4. که شمېره ترلاسه نشي، له دې ترکیبونو څخه کار واخلئ:\n"
        "   • روسیه + ټیلیګرام\n"
        "   • روسیه + واتساپ\n"
        "   • امریکا + ټیلیګرام\n\n"
        "5. د کوډ ترلاسه کولو لپاره 'پیغامونه' تڼۍ وکاروئ."
    )

# ============================================================
# د اتومات بوټ
# ============================================================

auto_bot = telebot.TeleBot(AUTO_BOT_TOKEN)

def auto_collect():
    while True:
        try:
            for country in COUNTRIES.keys():
                for service in SERVICES.keys():
                    if len(get_active_numbers(country, service)) >= MAX_NUMBERS_PER_COUNTRY:
                        continue
                    res = get_virtual_number(country, service)
                    if res["success"]:
                        add_number(res["number"], country, service, res["tzid"])
                        for aid in ADMIN_IDS:
                            try:
                                auto_bot.send_message(aid, f"🔄 نوې شمېره: +{res['number']} ({country} - {service})")
                            except: pass
                        time.sleep(2)
        except Exception as e:
            print(f"Auto collect error: {e}")
        time.sleep(AUTO_CHECK_INTERVAL)

def auto_check():
    while True:
        try:
            for num in get_active_numbers():
                if not num.get('tzid'): continue
                msgs = get_inbox(num['tzid'])
                for msg in msgs:
                    text = msg.get("text", "")
                    code = extract_verification_code(text)
                    if code:
                        save_message(num['phone_number'], num['service'], code, text)
                        for aid in ADMIN_IDS:
                            try:
                                auto_bot.send_message(aid, f"🔑 کوډ: {code} (+{num['phone_number']})")
                            except: pass
                        time.sleep(1)
        except Exception as e:
            print(f"Auto check error: {e}")
        time.sleep(AUTO_CHECK_INTERVAL)

@auto_bot.message_handler(commands=['start'])
def auto_start(m):
    if m.from_user.id not in ADMIN_IDS: return
    auto_bot.reply_to(m, "🤖 اتومات بوټ فعال دی. شمېرې راټولوي او کوډونه چیک کوي.")

# ============================================================
# د بوټونو چلول
# ============================================================

def run_user():
    print("✅ د کارونکي بوټ پیل شو...")
    user_bot.infinity_polling()

def run_auto():
    threading.Thread(target=auto_collect, daemon=True).start()
    threading.Thread(target=auto_check, daemon=True).start()
    print("✅ د اتومات بوټ پیل شو...")
    auto_bot.infinity_polling()

if __name__ == "__main__":
    init_database()
    t1 = threading.Thread(target=run_user, daemon=True)
    t2 = threading.Thread(target=run_auto, daemon=True)
    t1.start()
    t2.start()
    while True:
        time.sleep(1)
