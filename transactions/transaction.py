from flask_db import get_connection
from passwords import generate_random_password
import uuid
import datetime

def create_transaction(phone, plan_id, vendor_id, mikrotik_id, amount, hotspot_data=None):

    tx_uuid = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_transactions (transaction_uuid, client_phone, plan_id, vendor_id, mikrotik_id, amount, status, mac, ip, username, sessionid, created_at, link_login)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (tx_uuid, phone, plan_id, vendor_id, mikrotik_id, amount, 'pending',
          (hotspot_data or {}).get('mac'),
          (hotspot_data or {}).get('ip'),
          (hotspot_data or {}).get('user'),
          (hotspot_data or {}).get('sessionid'),
          datetime.now(),
          (hotspot_data or {}).get('link_login')
        ))
    conn.commit()
    cursor.close()
    conn.close()
    return tx_uuid

def update_transaction_with_stk_response(transaction_uuid, merchant_request_id=None, checkout_request_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions SET merchant_request_id=%s, checkout_request_id=%s, updated_at=%s
        WHERE transaction_uuid=%s
    """, (merchant_request_id, checkout_request_id, datetime.now(), transaction_uuid))
    conn.commit()
    cursor.close()
    conn.close()

def mark_transaction_success(transaction_uuid, mpesa_receipt=None, callback_time=None):

    code_6char = generate_random_password(length=6, include_symbols=False, include_uppercase=True, include_digits=True)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions
        SET status='SUCCESS', mpesa_receipt=%s, callback_received_at=%s, updated_at=%s, code_6char=%s
        WHERE transaction_uuid=%s
    """, (mpesa_receipt, callback_time or datetime.now(), datetime.now(), code_6char, transaction_uuid))
    conn.commit()
    cursor.close()
    conn.close()

def mark_transaction_failed(transaction_uuid):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions SET status='FAILED', updated_at=%s WHERE transaction_uuid=%s
    """, (datetime.now(), transaction_uuid))
    conn.commit()
    cursor.close()
    conn.close()