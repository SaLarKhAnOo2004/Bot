#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
import requests
import re
import time
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ============================================
# تنظیمات - خپل توکن دلته دننه کړئ
# ============================================
USER_BOT_TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"
ADMIN_IDS = [5887665463]

# ============================================
# د هیوادونو لیست (د ویب پاڼو سره سم)
# ============================================
COUNTRIES = {
    "روسیه": "russia",
    "امریکا": "usa",
    "انګلستان": "uk",
    "افغانستان": "afghanistan",
    "هند": "india",
    "پاکستان": "pakistan",
}

FLAGS = {
    "روسیه": "🇷🇺", "امریکا": "🇺🇸", "انګلستان": "🇬🇧",
    "افغانستان": "🇦🇫", "هند": "🇮🇳", "پاکستان": "🇵🇰"
}

SERVICES = {
    "telegram": "tg",
    "whatsapp": "wa",
    "facebook": "fb",
    "instagram": "ig",
}

# د وړیا ویب پاڼو لیست
FREE_SITES = [
    "https://receive-sms-online.cc",
    "https://temp-number.org",
    "https://textnow.com",
]

# ============================================
# بوټ جوړول
# ============================================
bot = telebot.TeleBot(USER_BOT_TOKEN)

# ============================================
# له وړیا ویب پاڼو څخه شمېرې راټولول
# ============================================

def get_free_number(country_name, service_name):
    """له وړیا ویب پاڼو څخه شمېره ترلاسه کوي"""
    country_en = COUNTRIES.get(country_name, "russia")
    service_short = SERVICES.get(service_name.lower(), "tg")
    
    # لومړۍ ویب پاڼه: receive-sms-online.cc
    try:
        url = f"https://receive-sms-online.cc/{service_short}/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=10)
        
        # د شمېرو استخراج
        numbers = re.findall(r'<span class="number">\+?(\d+)</span>', r.text)
        if numbers:
            return {
                "success": True,
                "number": numbers[0],
                "source": "receive-sms-online.cc",
                "url": url,
                "country": country_name,
                "service": service_name
            }
    except:
        pass
    
    # دوهمه ویب پاڼه: temp-number.org
    try:
        url = f"https://temp-number.org/{country_en}/"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        numbers = re.findall(r'<div class="number">\+?(\d+)</div>', r.text)
        if numbers:
            return {
                "success": True,
                "number": numbers[0],
                "source": "temp-number.org",
                "url": url,
                "country": country_name,
                "service": service_name
            }
    except:
        pass
    
    # که هیڅ شمېره ونه موندل شوه
    return {"success": False, "error": "په وړیا ویب پاڼو کې شمېره ونه موندله"}

def get_all_free_numbers(country_name, service_name):
    """له ټولو سرچینو څخه شمېرې راټولوي"""
    results = []
    
    # 1. receive-sms-online.cc
    try:
        service_short = SERVICES.get(service_name.lower(), "tg")
        url = f"https://receive-sms-online.cc/{service_short}/"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        numbers = re.findall(r'<span class="number">\+?(\d+)</span>', r.text)
        for num in numbers[:3]:
            results.append({"number": num, "source": "receive-sms-online.cc", "url": url})
    except:
        pass
    
    # 2. temp-number.org
    try:
        country_en = COUNTRIES.get(country_name, "russia")
        url = f"https://temp-number.org/{country_en}/"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        numbers = re.findall(r'<div class="number">\+?(\d+)</div>', r.text)
        for num in numbers[:3]:
            results.append({"number": num, "source": "temp-number.org", "url": url})
    except:
        pass
    
    return results

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
        KeyboardButton("📞 نوی وړیا شمېره"),
        KeyboardButton("🌍 هیوادونه"),
        KeyboardButton("📡 ټولې سرچینې"),
        KeyboardButton("❓ مرسته")
    )
    bot.reply_to(message,
        "🌟 **وړیا مجازی شمېرې بوټ**\n\n"
        "دې بوټ له **وړیا ویب پاڼو** څخه شمېرې راوباسي:\n"
        "• receive-sms-online.cc\n"
        "• temp-number.org\n\n"
        "⚠️ **یادونه:** دا شمېرې عامه دي او ممکن پیغامونه د نورو سره شریک وي.\n"
        "د پیغامونو لیدلو لپاره په ورکړل شوي لینک کلیک وکړئ.",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "🌍 هیوادونه")
def show_countries(message):
    text = "🌍 **شته هیوادونه:**\n\n"
    for c in COUNTRIES.keys():
        text += f"{FLAGS.get(c, '🌍')} {c}\n"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📡 ټولې سرچینې")
def show_sources(message):
    text = (
        "📡 **وړیا سرچینې:**\n\n"
        "1. **receive-sms-online.cc** - مشهوره ویب پاڼه\n"
        "2. **temp-number.org** - بله وړیا پاڼه\n\n"
        "دا پاڼې تاسو ته وړیا شمېرې درکوي، خو عامه دي."
    )
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == "📞 نوی وړیا شمېره")
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
    
    msg = bot.edit_message_text(
        f"⏳ د **{country}** لپاره د **{service}** وړیا شمېره ترلاسه کېږي...\n"
        "له وړیا ویب پاڼو څخه چیک کیږي...",
        callback.message.chat.id,
        callback.message.message_id,
        parse_mode="Markdown"
    )
    
    # شمېره ترلاسه کول
    result = get_free_number(country, service)
    
    if result["success"]:
        phone = result["number"]
        source = result["source"]
        url = result.get("url", "#")
        
        flag = FLAGS.get(country, "🌍")
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🌐 پیغامونه وګورئ", url=url),
            InlineKeyboardButton("🔄 نوې شمېره", callback_data=f"new_{service}_{country}")
        )
        
        bot.edit_message_text(
            f"{flag} **ستاسو وړیا مجازی شمېره:**\n`{phone}`\n\n"
            f"📱 خدمت: **{service}**\n"
            f"🌍 هیواد: **{country}**\n"
            f"📡 سرچینه: **{source}**\n\n"
            "🔴 **مهم:**\n"
            "• دا شمېره عامه ده (نور خلک هم کاروي)\n"
            "• د پیغامونو لیدلو لپاره لاندې تڼۍ کلیک کړئ\n"
            "• په ویب پاڼه کې خپله شمېره ومومئ او پیغامونه وګورئ",
            callback.message.chat.id,
            msg.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        error = result.get("error", "نامعلومه")
        bot.edit_message_text(
            f"❌ **شمېره ترلاسه نه شوه.**\n\n"
            f"خطا: `{error}`\n\n"
            "**لارښوونه:**\n"
            "• په وړیا ویب پاڼو کې ممکن شمېرې پای ته رسېدلي وي.\n"
            "• بل هیواد یا خدمت وکاروئ.\n"
            "• روسیه + telegram یا امریکا + telegram ازمایئ.\n\n"
            "تاسو کولی شئ په لاسي ډول دې پاڼو ته لاړ شئ:\n"
            "• https://receive-sms-online.cc\n"
            "• https://temp-number.org",
            callback.message.chat.id,
            msg.message_id,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("new_"))
def renew_number(callback):
    parts = callback.data.split("_")
    service = parts[1] if len(parts) > 1 else "telegram"
    country = parts[2] if len(parts) > 2 else "روسیه"
    bot.answer_callback_query(callback.id, "نوې شمېره ترلاسه کیږي...")
    
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
        "1. 'نوی وړیا شمېره' کلیک کړئ\n"
        "2. خدمت وټاکئ (telegram، whatsapp، facebook، instagram)\n"
        "3. هیواد وټاکئ\n"
        "4. که شمېره ترلاسه نشي، دا ترکیبونه ازمایئ:\n"
        "   • روسیه + telegram\n"
        "   • روسیه + whatsapp\n"
        "   • امریکا + telegram\n"
        "5. د پیغامونو لیدلو لپاره 'پیغامونه وګورئ' تڼۍ کلیک کړئ\n\n"
        "⚠️ **مهم:** دا شمېرې عامه دي! که پیغام ونه مومئ، نو بل څوک یې ترلاسه کړی دی."
    )

# ============================================
# بوټ چلول
# ============================================
if __name__ == "__main__":
    print("✅ وړیا بوټ پیل شو...")
    print("📡 له وړیا ویب پاڼو څخه شمېرې راوباسي:")
    print("   • receive-sms-online.cc")
    print("   • temp-number.org")
    bot.infinity_polling()
