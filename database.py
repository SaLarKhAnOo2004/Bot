# database.py

import sqlite3
import json
from datetime import datetime, timedelta
from config import DATABASE_FILE

def get_db_connection():
    """د ډیټابیس سره اړیکه جوړوي"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """د اړینو جدولونو جوړول"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # د شمېرو جدول
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
    
    # د پیغامونو/کوډونو جدول
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
    
    # د کارونکو د غوښتنو جدول (د کارونکي بوټ لپاره)
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

# --- د شمېرو عملیات ---

def add_number(phone_number, country, service, tzid=None, expires_minutes=10):
    """نوې مجازی شمېره ډیټابیس ته اضافه کوي"""
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
    """د فعالو شمېرو لیست ترلاسه کوي"""
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
    """د یوې ځانګړې شمېرې معلومات ترلاسه کوي"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM numbers WHERE phone_number = ?", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def deactivate_number(phone_number):
    """یوه شمېره غیرفعالوي"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE numbers SET is_active = 0 WHERE phone_number = ?", (phone_number,))
    conn.commit()
    conn.close()

# --- د پیغامونو عملیات ---

def save_message(phone_number, service, code=None, message_text=None):
    """یو پیغام یا تایید کوډ خوندي کوي"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (phone_number, service, code, message_text)
        VALUES (?, ?, ?, ?)
    ''', (phone_number, service, code, message_text))
    conn.commit()
    conn.close()

def get_messages(phone_number, limit=5):
    """د یوې شمېرې وروستي پیغامونه ترلاسه کوي"""
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

# --- د کارونکو غوښتنې ---

def create_user_request(user_id, service, country):
    """د کارونکي نوې غوښتنه ثبتوي"""
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
    """د کارونکي غوښتنه تازه کوي"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_requests 
        SET phone_number = ?, status = ? 
        WHERE id = ?
    ''', (phone_number, status, request_id))
    conn.commit()
    conn.close()
