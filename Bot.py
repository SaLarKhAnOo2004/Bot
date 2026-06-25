#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
import requests
import sqlite3
import time
import random
import re
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ==================== تنظیمات ====================
USER_TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"
ADMIN_IDS = [5887665463]

# د هیوادونه او نښې
COUNTRIES = {
    "روسیه": 0, "اوکراین": 1, "قزاقستان": 2,
    "امریکا": 3, "انګلستان": 4, "افغانستان": 18
}
FLAGS = {"روسیه": "🇷🇺", "اوکراین": "🇺🇦", "قزاقستان": "🇰🇿", "امریکا": "🇺🇸", "انګلستان": "🇬🇧", "افغانستان": "🇦🇫"}
SERVICES = {"telegram": 1, "whatsapp": 2, "facebook": 3, "instagram": 4}

bot = telebot.TeleBot(USER_TOKEN)

# ==================== د API دندې ====================

def get_online_sim(country_code, service_code):
    """د OnlineSim څخه شمېره ترلاسه کوي"""
    url = "https://onlinesim.io/api/getNum.php"
    params = {"service": service_code, "country": country_code, "operator": "any"}
    try:
        r = requests.get(url, params=params, timeout=10)
        d = r.json()
        if d.get("response") == "1":
            return {"success": True, "number": d["number"], "tzid": d["tzid"], "source": "OnlineSim"}
        return {"success": False, "error": d.get("msg", "نامعلومه")}
    except:
        return {"success": False, "error": "آنلاین نه دی"}

def get_five_sim(country_code, service_code):
    """د 5sim څخه شمېره ترلاسه کوي (د وړیا API سره)"""
    # 5sim وړیا نه دی، خو که API کیلي ولرئ، دلته یې دننه کړئ
    # د کارونکي لپاره، موږ یوازې OnlineSim کاروو
    return {"success": False, "error": "5sim ته API کیلي نشته"}

def get_number(country_name, service_name):
    """د دواړو سرچینو څخه شمېره ترلاسه کوي"""
    country_code = COUNTRIES.get(country_name)
    service_code = SERVICES.get(service_name.lower())
    if country_code is None or service_code is None:
        return {"success": False, "error": "هیواد یا خدمت ونه موندل شو"}
    
    # لومړی OnlineSim
    result = get_online_sim(country_code, service_code)
    if result["success"]:
        return result
    
    # که OnlineSim ناکامه شو، 5sim (که کیلي وي)
    result = get_five_sim(country_code, service_code)
    if result["success"]:
        return result
    
    # که دواړه ناکامه شول
    return {"success": False, "error": "هیڅ سرچینه شمېره ونه موندله. مهرباني وکړئ بل هیواد یا خدمت وکاروئ."}

def get_inbox(tzid):
    """د پیغامونو ترلاسه کول"""
    url = "https://onlinesim.io/api/getMessages.php"
    try:
        r = requests.get(url, params={"tzid": tzid}, timeout=10)
        d = r.json()
        return d if isinstance(d, list) else []
    except:
        return []

# ==================== د بوټ امرونه ====================

@bot.message_handler(commands=['start'])
def start(m):
    if m.from_user.id not in ADMIN_IDS:
        bot.reply_to(m, "⛔ تاسو اجازه نلرئ.")
        return
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📞 نوی شمېره"), KeyboardButton("🌍 هیوادونه"), KeyboardButton("❓ مرسته"))
    bot.reply_to(m, "🌟 **مجازی شمېرې بوټ**\n\nد شمېرې ترلاسه کولو لپاره تڼۍ وکاروئ.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🌍 هیوادونه")
def show_countries(m):
    text = "🌍 **شته هیوادونه:**\n"
    for c in COUNTRIES.keys():
        text += f"{FLAGS.get(c, '🌍')} {c}\n"
    bot.reply_to(m, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 نوی شمېره")
def new_number(m):
    markup = InlineKeyboardMarkup(row_width=2)
    for s in SERVICES.keys():
        markup.add(InlineKeyboardButton(f"📱 {s.title()}", callback_data=f"srv_{s}"))
    bot.reply_to(m, "خدمت وټاکئ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("srv_"))
def select_service(c):
    service = c.data.replace("srv_", "")
    bot.answer_callback_query(c.id, f"{service} انتخاب شو")
    markup = InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES.keys():
        flag = FLAGS.get(country, "🌍")
        markup.add(InlineKeyboardButton(f"{flag} {country}", callback_data=f"cnt_{country}_{service}"))
    bot.edit_message_text(f"د {service} لپاره هیواد وټاکئ:", c.message.chat.id, c.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cnt_"))
def select_country(c):
    parts = c.data.split("_")
    country = parts[1]
    service = parts[2]
    bot.answer_callback_query(c.id, f"{country} انتخاب شو")
    
    msg = bot.edit_message_text(f"⏳ د {country} لپاره د {service} شمېره ترلاسه کېږي...", c.message.chat.id, c.message.message_id)
    
    # شمېره ترلاسه کول
    result = get_number(country, service)
    
    if result["success"]:
        phone = result["number"]
        tzid = result["tzid"]
        source = result.get("source", "نامعلومه")
        
        try:
            import phonenumbers
            parsed = phonenumbers.parse(f"+{phone}")
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except:
            formatted = f"+{phone}"
        
        flag = FLAGS.get(country, "🌍")
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📥 پیغامونه", callback_data=f"inbox_{tzid}_{phone}"),
            InlineKeyboardButton("🔄 نوې شمېره", callback_data=f"new_{service}_{country}")
        )
        bot.edit_message_text(
            f"{flag} **ستاسو شمېره:**\n`{formatted}`\n\n📱 خدمت: {service}\n🌍 هیواد: {country}\n📡 سرچینه: {source}\n\nد 'پیغامونه' تڼۍ سره کوډ وګورئ.",
            c.message.chat.id, msg.message_id, parse_mode="Markdown", reply_markup=markup
        )
    else:
        error = result.get("error", "نامعلومه")
        bot.edit_message_text(
            f"❌ **شمېره ترلاسه نه شوه.**\nخطا: `{error}`\n\n"
            "لاندې ترکیبونه ازمایئ:\n"
            "• روسیه + telegram\n"
            "• روسیه + whatsapp\n"
            "• امریکا + telegram",
            c.message.chat.id, msg.message_id, parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("inbox_"))
def show_inbox(c):
    parts = c.data.split("_")
    tzid = parts[1]
    phone = parts[2] if len(parts) > 2 else None
    bot.answer_callback_query(c.id, "پیغامونه راوړل کیږي...")
    msgs = get_inbox(tzid)
    if msgs:
        for msg in msgs[:5]:
            text = msg.get("text", "پیغام نشته")
            date = msg.get("date", "نامعلوم")
            code = re.search(r'\b(\d{4,6})\b', text)
            code = code.group(1) if code else None
            txt = f"📩 **نېټه:** {date}\n"
            if code:
                txt += f"🔑 **کوډ:** `{code}`\n"
            txt += f"📝 {text}"
            bot.send_message(c.message.chat.id, txt, parse_mode="Markdown")
    else:
        bot.send_message(c.message.chat.id, "📭 پیغام نشته. که کوډ مو استولی وي، یو څه انتظار وکړئ.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("new_"))
def renew(c):
    parts = c.data.split("_")
    service = parts[1]
    country = parts[2]
    bot.answer_callback_query(c.id, "نوې شمېره ترلاسه کیږي...")
    # د نوي شمېرې لپاره پروسه بیا پیل کړئ
    markup = InlineKeyboardMarkup(row_width=2)
    for country_name in COUNTRIES.keys():
        flag = FLAGS.get(country_name, "🌍")
        markup.add(InlineKeyboardButton(f"{flag} {country_name}", callback_data=f"cnt_{country_name}_{service}"))
    bot.edit_message_text(f"د {service} لپاره هیواد وټاکئ:", c.message.chat.id, c.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "❓ مرسته")
def help_cmd(m):
    bot.reply_to(m,
        "🔧 **لارښود:**\n"
        "1. 'نوی شمېره' کلیک کړئ\n"
        "2. خدمت وټاکئ (telegram, whatsapp...)\n"
        "3. هیواد وټاکئ\n"
        "4. که شمېره ترلاسه نشي، روسیه + telegram ازمایئ\n"
        "5. د کوډ لپاره 'پیغامونه' تڼۍ وکاروئ.\n\n"
        "⚠️ **یادونه:** وړیا شمېرې محدودې دي."
    )

# ==================== بوټ چلول ====================
if __name__ == "__main__":
    print("✅ بوټ پیل شو...")
    bot.infinity_polling()
