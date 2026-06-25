# auto_bot.py

import telebot
import time
import threading
from datetime import datetime
from config import AUTO_BOT_TOKEN, ADMIN_IDS, AUTO_CHECK_INTERVAL, MAX_NUMBERS_PER_COUNTRY
from database import *
from api_client import COUNTRIES, SERVICES, get_virtual_number, get_inbox, extract_verification_code

bot = telebot.TeleBot(AUTO_BOT_TOKEN)

# ==================== د اتومات شمېره اخیستونکی ====================
def auto_collect_numbers():
    """په اتوماتیک ډول له ټولو هیوادونو او خدماتو څخه شمېرې راټولوي"""
    while True:
        try:
            for country in COUNTRIES.keys():
                for service in SERVICES.keys():
                    # وګورئ چې آیا دغه هیواد او خدمت لپاره کافي شمېرې شته
                    existing = get_active_numbers(country, service)
                    if len(existing) >= MAX_NUMBERS_PER_COUNTRY:
                        continue
                    
                    # نوې شمېره ترلاسه کړئ
                    result = get_virtual_number(country, service)
                    
                    if result["success"]:
                        phone = result["number"]
                        tzid = result["tzid"]
                        
                        # په ډیټابیس کې خوندي کول
                        add_number(phone, country, service, tzid)
                        
                        # د اتومات بوټ له لارې خبر ورکول (یوازې مدیرانو ته)
                        for admin_id in ADMIN_IDS:
                            try:
                                bot.send_message(admin_id, 
                                    f"🔄 **نوې شمېره اضافه شوه!**\n"
                                    f"📞 +{phone}\n"
                                    f"🌍 {country}\n"
                                    f"📱 {service}"
                                )
                            except:
                                pass
                        
                        time.sleep(2)  # د API محدودیت لپاره
                        
        except Exception as e:
            print(f"خطا په اتومات راټولونکي کې: {e}")
        
        time.sleep(AUTO_CHECK_INTERVAL)

# ==================== د اتومات پیغام چیک کونکی ====================
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
                            # تایید کوډ خوندي کول
                            save_message(num['phone_number'], num['service'], code, text)
                            
                            # مدیرانو ته خبر ورکول
                            for admin_id in ADMIN_IDS:
                                try:
                                    bot.send_message(admin_id,
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

# ==================== د بوټ امرونه ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ تاسو مدیر نه یاست.")
        return
    
    bot.reply_to(message,
        "🤖 **اتومات بوټ فعال دی!**\n\n"
        "دا بوټ په شالید کې کار کوي او په اتوماتیک ډول:\n"
        "• له آنلاین سرچینو څخه مجازی شمېرې راټولوي\n"
        "• د شمېرو پیغامونه چیک کوي\n"
        "• تایید کوډونه استخراج او خوندي کوي\n\n"
        "ټول معلومات په ډیټابیس کې خوندي کیږي."
    )

@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    numbers = get_active_numbers()
    total = len(numbers)
    
    # د هیوادونو شمېر
    country_stats = {}
    for num in numbers:
        country_stats[num['country']] = country_stats.get(num['country'], 0) + 1
    
    text = f"📊 **احصایې:**\n\n"
    text += f"📞 ټول فعالې شمېرې: {total}\n\n"
    text += "**د هیوادونو له مخې:**\n"
    for country, count in country_stats.items():
        text += f"• {country}: {count}\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ==================== بوټ چلول ====================
if __name__ == "__main__":
    init_database()
    
    # د اتومات پروسې په جلا تارونو کې پیل کول
    collector_thread = threading.Thread(target=auto_collect_numbers, daemon=True)
    collector_thread.start()
    
    checker_thread = threading.Thread(target=auto_check_messages, daemon=True)
    checker_thread.start()
    
    print("✅ د اتومات بوټ پیل شو...")
    print("🔄 د شمېرو راټولونکی او پیغام چیک کونکی فعال شو.")
    
    bot.infinity_polling(skip_pending=True)
