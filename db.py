import os
from dotenv import load_dotenv
import logging
import mysql.connector

# Load environment variables
load_dotenv()

# -------------------------
# DB CONFIG (use env or defaults)
# -------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "BILLING"),
    "autocommit": False
}

def get_connection():
    """Get a new database connection."""
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn



#_______DEF QUERY_COUNT_________________##
def update_query_count(tx_uid):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions
        SET query_count = query_count + 1
        WHERE transaction_uuid = %s
    """, (tx_uid,))
    conn.commit()
    cursor.close()
    conn.close()



def test():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_transactions WHERE status = 'failed'")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    if result:
        return result
    return None
test()

def test2():
    data = test()
    if data:
      
        for x in data:
            
            update_query_count(x['transaction_uuid'])
            print(f"Updated query count for transaction UUID: {x['transaction_uuid']}")
    return None
test2()
'''
def init_db():
    """Create tables if they don't exist (safe to run multiple times)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Create plans table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_plans (
      id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(128),
      price DECIMAL(10,2),
      duration_minutes INT,
      mikrotik_profile VARCHAR(128),
      rate_limit VARCHAR(64),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Transactions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_transactions (
      id INT AUTO_INCREMENT PRIMARY KEY,
      transaction_uuid VARCHAR(64) UNIQUE,
      client_phone VARCHAR(32),
      plan_id INT,
      amount DECIMAL(10,2),
      status ENUM('pending','success','failed','processing') DEFAULT 'pending',
      merchant_request_id VARCHAR(128),
      checkout_request_id VARCHAR(128),
      mpesa_receipt VARCHAR(64),
      mac VARCHAR(64),
      ip VARCHAR(64),
      username VARCHAR(128),
      sessionid VARCHAR(128),
      callback_received_at DATETIME NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NULL,
      expires_at DATETIME NULL
    );
    """)
    # Hotspot users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hotspot_users (
      id INT AUTO_INCREMENT PRIMARY KEY,
      transaction_uuid VARCHAR(64),
      mac VARCHAR(64),
      username VARCHAR(128),
      mikrotik_profile VARCHAR(128),
      expires_at DATETIME,
      active TINYINT(1) DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()
'''