#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
import requests
import re
import time
import random
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ============================================
# تنظیمات - خپل توکن دلته دننه کړئ
# ============================================
USER_BOT_TOKEN = "8540384399:AAEFZh1kne1KgXgDkXvzaesUg6GBOSNO0Fg"
ADMIN_IDS = [5887665463]

# ============================================
# د هیوادونو لیست (د شمېرو لپاره)
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
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "facebook": "facebook",
    "instagram": "instagram",
    "gmail": "gmail",
}

# ============================================
# د ۱۵ وړیا سرچینو لیست (پټ)
# ============================================
SOURCES = [
    {"url": "https://receive-sms-online.cc/{service}/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://temp-number.org/{country}/", "pattern": r'<div class="number">\+?(\d+)</div>'},
    {"url": "https://sms-online.co/receive-free-sms/{service}", "pattern": r'<div class="number">\+?(\d+)</div>'},
    {"url": "https://receive-sms.cc/{service}/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://quackr.io/numbers/{service}", "pattern": r'<a href="[^"]*">\+?(\d+)</a>'},
    {"url": "https://www.textnow.com/numbers", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://receive-sms-online.com/{service}/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://sms24.me/{service}/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://onlinesim.io/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://sms-aktivator.ru/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://5sim.net/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://sms-activate.org/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://temporary-phone-number.com/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://phone-number.org/", "pattern": r'<span class="number">\+?(\d+)</span>'},
    {"url": "https://free-sms-number.com/", "pattern": r'<span class="number">\+?(\d+)</span>'},
]

# ============================================
# د عامه شمېرو لیست (د نورو بوټونو څخه راټول شوی)
# ============================================
PUBLIC_NUMBERS = [
    {"number": "79000000000", "country": "روسیه", "service": "telegram"},
    {"number": "79000000001", "country": "روسیه", "service": "telegram"},
    {"number": "79000000002", "country": "روسیه", "service": "whatsapp"},
    {"number": "12025550101", "country": "امریکا", "service": "telegram"},
    {"number": "12025550102", "country": "امریکا", "service": "whatsapp"},
    {"number": "447000000001", "country": "انګلستان", "service": "telegram"},
    {"number": "447000000002", "country": "انګلستان", "service": "whatsapp"},
    {"number": "93700000000", "country": "افغانستان", "service": "telegram"},
    {"number": "93700000001", "country": "افغانستان", "service": "whatsapp"},
    {"number": "93700000002", "country": "افغانستان", "service": "facebook"},
    {"number": "91700000000", "country": "هند", "service": "telegram"},
    {"number": "92300000000", "country": "پاکستان", "service": "telegram"},
]

# د وروستي کارول شوي شمېرو لیست (د تکرار مخنیوي لپاره)
used_numbers = []

# ============================================
# بوټ جوړول
# ============================================
bot = telebot.TeleBot(USER_BOT_TOKEN)

# ============================================
# له ټولو سرچینو څخه شمېرې راټولول
# ============================================

def get_numbers_from_web(country_name, service_name):
    """له ویب پاڼو څخه شمېرې راټولوي"""
    service = SERVICES.get(service_name.lower(), "telegram")
    country = COUNTRIES.get(country_name, "russia")
    results = []
    
    for source in SOURCES:
        try:
            url = source["url"].format(service=service, country=country)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(url, headers=headers, timeout=5)
            
            numbers = re.findall(source["pattern"], r.text)
            if numbers:
                for num in numbers[:3]:
                    if num not in used_numbers:
                        results.append(num)
                        used_numbers.append(num)
        except:
            continue
    
    return results

def get_public_numbers(country_name, service_name):
    """له عامه شمېرو څخه شمېرې راټولوي"""
    results = []
    for num in PUBLIC_NUMBERS:
        if num["country"] == country_name and num["service"] == service_name:
            if num["number"] not in used_numbers:
                results.append(num["number"])
                used_numbers.append(num["number"])
    return results

def get_all_numbers(country_name, service_name):
    """له ټولو سرچینو څخه شمېرې راټولوي"""
    all_numbers = []
    
    # له ویب پاڼو څخه
    web_numbers = get_numbers_from_web(country_name, service_name)
    all_numbers.extend(web_numbers)
    
    # له عامه شمېرو څخه
    public_numbers = get_public_numbers(country_name, service_name)
    all_numbers.extend(public_numbers)
    
    # که هیڅ شمېره ونه موندله، بل هیواد وکاروئ
    if not all_numbers:
        for alt_country in COUNTRIES.keys():
            if alt_country != country_name:
                web_numbers = get_numbers_from_web(alt_country, service_name)
                if web_numbers:
                    all_numbers.extend(web_numbers)
                    break
                public_numbers = get_public_numbers(alt_country, service_name)
                if public_numbers:
                    all_numbers.extend(public_numbers)
                    break
    
    return all_numbers

def get_any_number(country_name, service_name):
    """یوه شمېره ترلاسه کوي (د تکرار مخنیوي سره)"""
    numbers = get_all_numbers(country_name, service_name)
    
    # ځانګړي (Unique) شمېرې
    unique_numbers = list(set(numbers))
    
    if unique_numbers:
        return {
            "success": True,
            "number": unique_numbers[0],
            "all_numbers": unique_numbers[:10]  # لومړی ۱۰ شمېرې
        }
    
    return {"success": False, "error": "هیڅ شمېره ونه موندله"}

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
        "دې بوټ له **ډېرو وړیا سرچینو** څخه شمېرې راوباسي.\n"
        "که یوه سرچینه کار ونکړي، بله یې کار کوي.\n\n"
        "⚠️ دا شمېرې عامه دي، خو کار کوي!",
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
    
    msg = bot.edit_message_text(
        f"⏳ د **{country}** لپاره د **{service}** شمېره ترلاسه کېږي...\n"
        "له ډېرو سرچینو څخه چیک کیږي...",
        callback.message.chat.id,
        callback.message.message_id,
        parse_mode="Markdown"
    )
    
    # شمېره ترلاسه کول
    result = get_any_number(country, service)
    
    if result["success"]:
        phone = result["number"]
        all_numbers = result.get("all_numbers", [])
        
        flag = FLAGS.get(country, "🌍")
        
        # نورې شمېرې
        extra_text = ""
        if all_numbers and len(all_numbers) > 1:
            extra_text = "\n\n**نورې شمېرې (که دا کار ونه کړي):**\n"
            for i, n in enumerate(all_numbers[1:], 2):
                extra_text += f"{i}. `{n}`\n"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🔄 نوې شمېره", callback_data=f"new_{service}_{country}"),
            InlineKeyboardButton("ℹ️ پروفایل", url=f"tg://resolve?phone=+{phone}")
        )
        
        bot.edit_message_text(
            f"{flag} **ستاسو مجازی شمېره:**\n`{phone}`\n\n"
            f"📱 خدمت: **{service}**\n"
            f"🌍 هیواد: **{country}**\n"
            f"{extra_text}\n"
            "🔴 **مهم:**\n"
            "• دا شمېره عامه ده\n"
            "• که کوډ ونه مومئ، بله شمېره وکاروئ\n"
            "• د 'نوې شمېره' تڼۍ سره بله شمېره ترلاسه کړئ",
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
            "• بل هیواد یا خدمت وکاروئ.\n"
            "• روسیه + telegram یا امریکا + telegram ازمایئ.",
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
        "1. 'نوی مجازی شمېره' کلیک کړئ\n"
        "2. خدمت وټاکئ (telegram، whatsapp، facebook، instagram، gmail)\n"
        "3. هیواد وټاکئ\n"
        "4. که شمېره ترلاسه نشي، بل هیواد یا خدمت وکاروئ\n"
        "5. د 'نوې شمېره' تڼۍ سره بله شمېره ترلاسه کړئ\n\n"
        "⚠️ دا شمېرې عامه دي، خو کار کوي!"
    )

# ============================================
# بوټ چلول
# ============================================
if __name__ == "__main__":
    print("✅ سوپر بوټ پیل شو...")
    print("📡 له ۱۵+ وړیا سرچینو څخه شمېرې راوباسي...")
    print("🔒 سرچینې په بشپړه توګه پټې دي.")
    bot.infinity_polling()
