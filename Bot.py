#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
import requests
import time
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ============================================
# تنظیمات - خپل توکن او آئی ډی دلته دننه کړئ
# ============================================
USER_BOT_TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"
ADMIN_IDS = [5887665463]

# که د 5sim API کیلي لرئ، دلته یې دننه کړئ (که نه لرئ، هماغسې پرېږدئ)
FIVESIM_API_KEY = ""  # که نه لرئ، خالي پرېږدئ

# ============================================
# د هیوادونو او خدماتو کوډونه
# ============================================
COUNTRIES = {
    "روسیه": 0,
    "اوکراین": 1,
    "قزاقستان": 2,
    "امریکا": 3,
    "انګلستان": 4,
    "افغانستان": 18,
}

FLAGS = {
    "روسیه": "🇷🇺", "اوکراین": "🇺🇦", "قزاقستان": "🇰🇿",
    "امریکا": "🇺🇸", "انګلستان": "🇬🇧", "افغانستان": "🇦🇫"
}

SERVICES = {
    "telegram": 1,
    "whatsapp": 2,
    "facebook": 3,
    "instagram": 4,
    "gmail": 5,
}

# تضمیني ترکیبونه (تل شته)
GUARANTEED_COMBOS = [
    ("روسیه", "telegram"),
    ("روسیه", "whatsapp"),
    ("امریکا", "telegram"),
    ("انګلستان", "telegram"),
]

# ============================================
# بوټ جوړول
# ============================================
bot = telebot.TeleBot(USER_BOT_TOKEN)

# ============================================
# د API دندې
# ============================================

def get_from_onlinesim(country_code, service_code):
    """د OnlineSim څخه شمېره ترلاسه کوي"""
    url = "https://onlinesim.io/api/getNum.php"
    params = {"service": service_code, "country": country_code, "operator": "any"}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("response") == "1":
            return {"success": True, "number": data["number"], "tzid": data["tzid"], "source": "OnlineSim"}
        else:
            return {"success": False, "error": data.get("msg", "نامعلومه")}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_from_fivesim(country_code, service_code):
    """د 5sim څخه شمېره ترلاسه کوي (که API کیلي شتون ولري)"""
    if not FIVESIM_API_KEY:
        return {"success": False, "error": "5sim API کیلي نشته"}
    # د 5sim لپاره د هیواد نوم بدلول (د دوی کوډونه توپیر لري)
    country_map = {0: "ru", 1: "ua", 2: "kz", 3: "us", 4: "uk", 18: "af"}
    service_map = {1: "telegram", 2: "whatsapp", 3: "facebook", 4: "instagram", 5: "gmail"}
    country = country_map.get(country_code, "ru")
    service = service_map.get(service_code, "telegram")
    url = f"https://5sim.net/v1/user/buy/activation/{country}/{service}/any"
    headers = {"Authorization": f"Bearer {FIVESIM_API_KEY}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if "phone" in data and "id" in data:
            return {"success": True, "number": data["phone"], "tzid": data["id"], "source": "5sim"}
        else:
            return {"success": False, "error": data.get("detail", "نامعلومه")}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_number(country_name, service_name):
    """د دواړو سرچینو څخه شمېره ترلاسه کوي"""
    country_code = COUNTRIES.get(country_name)
    service_code = SERVICES.get(service_name.lower())
    if country_code is None or service_code is None:
        return {"success": False, "error": "هیواد یا خدمت ونه موندل شو"}
    
    # لومړی OnlineSim
    result = get_from_onlinesim(country_code, service_code)
    if result["success"]:
        return result
    
    # که OnlineSim ناکامه شو، 5sim
    result = get_from_fivesim(country_code, service_code)
    if result["success"]:
        return result
    
    # که دواړه ناکامه شول
    return {"success": False, "error": "هیڅ سرچینه شمېره ونه موندله"}

def get_inbox(tzid):
    """د OnlineSim څخه پیغامونه ترلاسه کوي"""
    url = "https://onlinesim.io/api/getMessages.php"
    try:
        r = requests.get(url, params={"tzid": tzid}, timeout=10)
        data = r.json()
        return data if isinstance(data, list) else []
    except:
        return []

def extract_code(text):
    """د متن څخه د ۴-۶ عددونو کوډ استخراج کوي"""
    match = re.search(r'\b(\d{4,6})\b', text)
    return match.group(1) if match else None

# ============================================
# د بوټ امرونه
# ============================================

@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ تاسو اجازه نلرئ.")
        return
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("📞 نوی مجازی شمېره"),
        KeyboardButton("🌍 هیوادونه"),
        KeyboardButton("❓ مرسته")
    )
    bot.reply_to(message,
        "🌟 **مجازی شمېرې بوټ**\n\n"
        "د نوي شمېرې لپاره تڼۍ وکاروئ.\n"
        "که شمېره ترلاسه نشي، نو **روسیه + telegram** یا **روسیه + whatsapp** وکاروئ.",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "🌍 هیوادونه")
def show_countries(message):
    text = "🌍 **شته هیوادونه:**\n\n"
    for c in COUNTRIES.keys():
        text += f"{FLAGS.get(c, '🌍')} {c}\n"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 نوی مجازی شمېره")
def new_number(message):
    markup = InlineKeyboardMarkup(row_width=2)
    for s in SERVICES.keys():
        markup.add(InlineKeyboardButton(f"📱 {s.title()}", callback_data=f"srv_{s}"))
    bot.reply_to(message, "لومړی خدمت وټاکئ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("srv_"))
def select_service(callback):
    service = callback.data.replace("srv_", "")
    bot.answer_callback_query(callback.id, f"خدمت {service} انتخاب شو")
    markup = InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES.keys():
        flag = FLAGS.get(country, "🌍")
        markup.add(InlineKeyboardButton(f"{flag} {country}", callback_data=f"cnt_{country}_{service}"))
    bot.edit_message_text(
        f"د **{service}** لپاره هیواد وټاکئ:",
        callback.message.chat.id,
        callback.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("cnt_"))
def select_country(callback):
    parts = callback.data.split("_")
    country = parts[1]
    service = parts[2]
    bot.answer_callback_query(callback.id, f"هیواد {country} انتخاب شو")
    
    # د انتظار پیغام
    try:
        msg = bot.edit_message_text(
            f"⏳ د **{country}** لپاره د **{service}** شمېره ترلاسه کېږي...\nمهرباني وکړئ انتظار وکړئ.",
            callback.message.chat.id,
            callback.message.message_id,
            parse_mode="Markdown"
        )
    except:
        msg = bot.send_message(
            callback.message.chat.id,
            f"⏳ د **{country}** لپاره د **{service}** شمېره ترلاسه کېږي...\nمهرباني وکړئ انتظار وکړئ.",
            parse_mode="Markdown"
        )
    
    # شمېره ترلاسه کول
    result = get_number(country, service)
    
    if result["success"]:
        phone = result["number"]
        tzid = result["tzid"]
        source = result.get("source", "نامعلومه")
        
        # د شمېرې بڼه ښایسته کول
        try:
            import phonenumbers
            parsed = phonenumbers.parse(f"+{phone}")
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except:
            formatted = f"+{phone}"
        
        flag = FLAGS.get(country, "🌍")
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📥 پیغامونه (Inbox)", callback_data=f"inbox_{tzid}_{phone}"),
            InlineKeyboardButton("🔄 نوې شمېره", callback_data=f"new_{service}_{country}"),
            InlineKeyboardButton("ℹ️ پروفایل", url=f"tg://resolve?phone=+{phone}")
        )
        
        bot.edit_message_text(
            f"{flag} **ستاسو مجازی شمېره:**\n`{formatted}`\n\n"
            f"📱 خدمت: **{service}**\n"
            f"🌍 هیواد: **{country}**\n"
            f"📡 سرچینه: {source}\n\n"
            "د تایید کوډ ترلاسه کولو لپاره، په همدې شمېره یې واستوئ او بیا د **'پیغامونه'** تڼۍ کېکاږئ.",
            callback.message.chat.id,
            msg.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        error = result.get("error", "نامعلومه")
        
        # د تضمیني ترکیبونو لست
        combo_text = ""
        for c, s in GUARANTEED_COMBOS:
            combo_text += f"• {FLAGS.get(c, '🌍')} {c} + {s}\n"
        
        bot.edit_message_text(
            f"❌ **شمېره ترلاسه نه شوه.**\n\n"
            f"خطا: `{error}`\n\n"
            "**لاندې ترکیبونه ازمایئ (تقریباً تل شته):**\n"
            f"{combo_text}\n"
            "که بیا هم کار ونه کړي، نو د OnlineSim API محدودیتونه دي. یو څه انتظار وکړئ او بیا هڅه وکړئ.",
            callback.message.chat.id,
            msg.message_id,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("inbox_"))
def show_inbox(callback):
    parts = callback.data.split("_")
    tzid = parts[1]
    phone = parts[2] if len(parts) > 2 else None
    bot.answer_callback_query(callback.id, "پیغامونه راوړل کیږي...")
    
    messages = get_inbox(tzid)
    if messages:
        for msg in messages[:5]:
            text = msg.get("text", "پیغام نشته")
            date = msg.get("date", "نامعلوم وخت")
            code = extract_code(text)
            
            msg_text = f"📩 **نېټه:** {date}\n"
            if code:
                msg_text += f"🔑 **تایید کوډ:** `{code}`\n"
            msg_text += f"📝 **متن:** {text}"
            bot.send_message(callback.message.chat.id, msg_text, parse_mode="Markdown")
    else:
        bot.send_message(
            callback.message.chat.id,
            "📭 د دې شمېرې لپاره هېڅ پیغام نشته.\n"
            "که تاسو تایید کوډ واستولی وي، مهرباني وکړئ یو څه انتظار وکړئ او بیا هڅه وکړئ."
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("new_"))
def renew_number(callback):
    parts = callback.data.split("_")
    service = parts[1]
    country = parts[2]
    bot.answer_callback_query(callback.id, "نوې شمېره ترلاسه کیږي...")
    
    # د هیواد بیا انتخاب
    markup = InlineKeyboardMarkup(row_width=2)
    for country_name in COUNTRIES.keys():
        flag = FLAGS.get(country_name, "🌍")
        markup.add(InlineKeyboardButton(f"{flag} {country_name}", callback_data=f"cnt_{country_name}_{service}"))
    
    bot.edit_message_text(
        f"د **{service}** لپاره هیواد وټاکئ:",
        callback.message.chat.id,
        callback.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "❓ مرسته")
def help_command(message):
    bot.reply_to(message,
        "🔧 **لارښود:**\n\n"
        "1. 'نوی مجازی شمېره' کلیک کړئ\n"
        "2. خدمت وټاکئ (telegram، whatsapp، facebook، instagram، gmail)\n"
        "3. هیواد وټاکئ\n"
        "4. که شمېره ترلاسه نشي، دا ترکیبونه ازمایئ:\n"
        "   • روسیه + telegram\n"
        "   • روسیه + whatsapp\n"
        "   • امریکا + telegram\n"
        "5. د تایید کوډ ترلاسه کولو لپاره 'پیغامونه' تڼۍ وکاروئ.\n\n"
        "⚠️ **یادونه:** دا شمېرې وړیا دي او ممکن محدودیتونه ولري."
    )

# ============================================
# بوټ چلول
# ============================================
if __name__ == "__main__":
    print("✅ بوټ پیل شو...")
    print(f"د کارونکي بوټ: @{USER_BOT_TOKEN.split(':')[0]}")
    bot.infinity_polling()
