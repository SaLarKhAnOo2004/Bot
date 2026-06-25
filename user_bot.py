# user_bot.py


import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import phonenumbers
import countryflag
from config import USER_BOT_TOKEN, ADMIN_IDS
from database import *
from api_client import COUNTRIES, SERVICES, get_virtual_number, get_inbox, extract_verification_code

bot = telebot.TeleBot(USER_BOT_TOKEN)

# ==================== د اجازې چک ====================
def is_allowed(user_id):
    return user_id in ADMIN_IDS if ADMIN_IDS else True

# ==================== اصلي مینو ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    if not is_allowed(message.from_user.id):
        bot.reply_to(message, "⛔ بخښنه، تاسو د دې بوټ کارولو اجازه نلرئ.")
        return
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("📞 نوی مجازی شمېره"),
        KeyboardButton("📥 زما شمېرې"),
        KeyboardButton("🌍 هیوادونه"),
        KeyboardButton("❓ مرسته")
    )
    
    bot.reply_to(message,
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

# ==================== د هیوادونو لست ====================
@bot.message_handler(func=lambda m: m.text == "🌍 هیوادونه")
def show_countries(message):
    if not is_allowed(message.from_user.id):
        return
    
    text = "🌍 **شته هیوادونه:**\n\n"
    for country in COUNTRIES.keys():
        text += f"• {country}\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ==================== د نوي شمېرې پروسه ====================
@bot.message_handler(func=lambda m: m.text == "📞 نوی مجازی شمېره")
def start_new_number(message):
    if not is_allowed(message.from_user.id):
        return
    
    # د خدمت انتخاب
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📱 ټیلیګرام", callback_data="service_telegram"),
        InlineKeyboardButton("💬 واتساپ", callback_data="service_whatsapp"),
        InlineKeyboardButton("📘 فیسبوک", callback_data="service_facebook"),
        InlineKeyboardButton("📸 انسټاګرام", callback_data="service_instagram"),
        InlineKeyboardButton("📧 جیمیل", callback_data="service_gmail")
    )
    
    bot.reply_to(message, 
        "لومړی هغه خدمت وټاکئ چې ورته شمېرې غواړئ:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("service_"))
def select_service(call):
    if not is_allowed(call.from_user.id):
        bot.answer_callback_query(call.id, "اجازه نشته", show_alert=True)
        return
    
    service = call.data.replace("service_", "")
    bot.answer_callback_query(call.id, f"خدمت {service} انتخاب شو")
    
    # د هیواد انتخاب
    markup = InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES.keys():
        markup.add(InlineKeyboardButton(country, callback_data=f"country_{country}_{service}"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"اوس د {service} لپاره هیواد وټاکئ:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def select_country(call):
    if not is_allowed(call.from_user.id):
        bot.answer_callback_query(call.id, "اجازه نشته", show_alert=True)
        return
    
    parts = call.data.split("_")
    country = parts[1]
    service = parts[2]
    
    bot.answer_callback_query(call.id, f"هیواد {country} انتخاب شو")
    
    # د کارونکي غوښتنه ثبتول
    request_id = create_user_request(call.from_user.id, service, country)
    
    # د شمېرې ترلاسه کول
    sent_msg = bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"⏳ د {country} لپاره د {service} شمېره ترلاسه کېږي...\nمهرباني وکړئ یو څه انتظار وکړئ."
    )
    
    # له API څخه شمېره ترلاسه کول
    result = get_virtual_number(country, service)
    
    if result["success"]:
        phone = result["number"]
        tzid = result["tzid"]
        
        # په ډیټابیس کې خوندي کول
        add_number(phone, country, service, tzid)
        update_user_request(request_id, phone)
        
        # د شمېرې بڼه ښایسته کول
        try:
            parsed = phonenumbers.parse(f"+{phone}")
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            flag = countryflag.getflag(phonenumbers.region_code_for_country_code(parsed.country_code))
        except:
            formatted = f"+{phone}"
            flag = "🌍"
        
        # کیبورډ جوړول
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📥 پیغامونه (Inbox)", callback_data=f"inbox_{tzid}_{phone}"),
            InlineKeyboardButton("🔄 نوې شمېره", callback_data=f"new_{service}_{country}"),
            InlineKeyboardButton("ℹ️ پروفایل", url=f"tg://resolve?phone=+{phone}")
        )
        
        bot.edit_message_text(
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
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=sent_msg.message_id,
            text=f"❌ شمېره ترلاسه نه شوه.\nخطا: {result.get('error', 'نامعلومه')}\n\n"
                 "مهرباني وکړئ بیا هڅه وکړئ یا بل هیواد وکاروئ."
        )

# ==================== د پیغامونو لیدل ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("inbox_"))
def show_inbox(call):
    if not is_allowed(call.from_user.id):
        bot.answer_callback_query(call.id, "اجازه نشته", show_alert=True)
        return
    
    parts = call.data.split("_")
    tzid = parts[1]
    phone = parts[2] if len(parts) > 2 else None
    
    bot.answer_callback_query(call.id, "پیغامونه راوړل کیږي...")
    
    # له API څخه پیغامونه ترلاسه کول
    messages = get_inbox(tzid)
    
    if messages:
        for msg in messages[:5]:
            text = msg.get("text", "پیغام نشته")
            date = msg.get("date", "نامعلوم وخت")
            
            # د تایید کوډ استخراج
            code = extract_verification_code(text)
            
            # په ډیټابیس کې خوندي کول
            if phone:
                save_message(phone, "unknown", code, text)
            
            msg_text = f"📩 **نېټه:** {date}\n"
            if code:
                msg_text += f"🔑 **تایید کوډ:** `{code}`\n"
            msg_text += f"📝 **متن:** {text}"
            
            bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, 
            "📭 د دې شمېرې لپاره هېڅ پیغام نشته.\n"
            "که تاسو تایید کوډ واستولی وي، مهرباني وکړئ یو څه انتظار وکړئ او بیا هڅه وکړئ."
        )

# ==================== د کارونکي شمېرې ====================
@bot.message_handler(func=lambda m: m.text == "📥 زما شمېرې")
def my_numbers(message):
    if not is_allowed(message.from_user.id):
        return
    
    numbers = get_active_numbers()
    
    if not numbers:
        bot.reply_to(message, "📭 تاسو لا تر اوسه کومه فعاله شمېره نلرئ.\nد نوي شمېرې لپاره 'نوی مجازی شمېره' وکاروئ.")
        return
    
    text = "📋 **ستاسو فعالې شمېرې:**\n\n"
    for num in numbers:
        text += f"📞 +{num['phone_number']}\n"
        text += f"   🌍 {num['country']} | 📱 {num['service']}\n"
        text += f"   ⏳ پای: {num['expires_at']}\n\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ==================== مرسته ====================
@bot.message_handler(func=lambda m: m.text == "❓ مرسته")
def help_command(message):
    if not is_allowed(message.from_user.id):
        return
    
    bot.reply_to(message,
        "🔧 **لارښود:**\n\n"
        "1. 'نوی مجازی شمېره' کلیک کړئ\n"
        "2. مطلوب خدمت (فیسبوک، ټیلیګرام، واتساپ) وټاکئ\n"
        "3. هیواد وټاکئ\n"
        "4. بوټ به تاسو ته یوه شمېره درکړي\n"
        "5. د تایید کوډ ترلاسه کولو لپاره 'پیغامونه' تڼۍ وکاروئ\n\n"
        "⚠️ **یادونه:** دا شمېرې وړیا دي او ممکن تل فعالې نه وي.\n"
        "هره شمېره یوازې د ۱۰ دقیقو لپاره فعاله وي."
    )

# ==================== بوټ چلول ====================
if __name__ == "__main__":
    init_database()
    print("✅ د کارونکي بوټ پیل شو...")
    bot.infinity_polling(skip_pending=True)
