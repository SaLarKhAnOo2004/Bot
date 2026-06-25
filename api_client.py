# api_client.py

import requests
import time
import random
from config import ONLINESIM_API_KEY, ONLINESIM_BASE_URL

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

def get_virtual_number(country_name, service_name):
    """د OnlineSim.io څخه یوه نوې مجازی شمېره ترلاسه کوي"""
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
    """د یوې شمېرې د راغلو پیغامونو لیست ترلاسه کوي"""
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
    """د پیغام متن څخه د تایید کوډ استخراج کوي"""
    import re
    # د ۴-۶ عددونو کوډ موندلو هڅه
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
