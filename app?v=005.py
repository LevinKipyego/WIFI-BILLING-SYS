from passwords import generate_random_password
from APIs import get_mikrotik_api, \
    find_active_session_by_username, \
        remove_active_session_by_id, \
            mikrotik_config
from radius_db import upsert_radcheck, upsert_radreply

from flask import Flask, redirect, render_template, request, jsonify, make_response
import requests
import base64
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

import mysql.connector
import uuid
from flask_cors import CORS
import threading
import time
import logging
import urllib.parse

# Optional: routeros_api for Mikrotik interactions


# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Logging
logging.basicConfig(level=logging.INFO)

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

# FreeRADIUS DB config (if separate)
RADIUS_DB = {
    "host": os.getenv("RADIUS_DB_HOST", DB_CONFIG["host"]),
    "user": os.getenv("RADIUS_DB_USER", DB_CONFIG["user"]),
    "password": os.getenv("RADIUS_DB_PASS", DB_CONFIG["password"]),
    "database": os.getenv("RADIUS_DB_NAME", "radius")
}

# -------------------------
# M-Pesa / Daraja Configuration
# -------------------------
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
shortcode = os.getenv("BUSINESS_SHORTCODE")
passkey = os.getenv("PASSKEY")
callback_url = os.getenv("CALLBACK_URL")  # e.g. https://yourserver.com/callback

# -------------------------
# MikroTik (RouterOS) config
# -------------------------
MIKROTIK_HOST = os.getenv("MIKROTIK_HOST")
MIKROTIK_USER = os.getenv("MIKROTIK_USER")
MIKROTIK_PASS = os.getenv("MIKROTIK_PASS")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT", "8728"))
MIKROTIK_HOTSPOT_SERVER = os.getenv("MIKROTIK_HOTSPOT_SERVER", "")

# ---------- DB Helpers ----------
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

# --- FreeRADIUS DB helpers ---
def get_radius_connection():
    return mysql.connector.connect(**RADIUS_DB)

# -------------------------
# Plan helpers
# -------------------------
def get_plan_by_id(plan_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_plans WHERE id = %s", (plan_id,))
    plan = cursor.fetchone()
    cursor.close()
    conn.close()
    return plan

# -------------------------
# Transaction helpers
# -------------------------
def create_transaction(phone, plan_id, amount, hotspot_data=None):

    tx_uuid = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_transactions (transaction_uuid, client_phone, plan_id, amount, status, mac, ip, username, sessionid, created_at, link_login)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (tx_uuid, phone, plan_id, amount, 'pending',
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



##______________PENDING TRANSACTIONS FETCHER_________________##
def get_pending_transactions(older_than_seconds=120):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cutoff = datetime.now() - timedelta(seconds=older_than_seconds)
    cursor.execute("SELECT * FROM user_transactions WHERE status='PENDING' AND created_at < %s", (cutoff,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows



#_______UPDATE LAST_QUERY_TIME_________________##
def update_last_query_time(transaction_uuid):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE user_transactions
        SET last_query_time = NOW()
        WHERE transaction_uuid = %s
    """, (transaction_uuid,))

    conn.commit()
    cursor.close()
    conn.close()



#_______UPDATE QUERY_COUNT_________________##
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



# --- FreeRADIUS HELPERS ---
def create_or_update_radius_user(
    username,
    password,
    profile_name=None,
    rate_limit=None,
    expire_minutes=60,
    expires_at=None
):
    """
    Create or update a RADIUS user in radcheck and radreply.
    username = phone number
    """

    session_timeout = '3600'
    Acct_Interim_Interval = '60'

    conn = get_radius_connection()
    cur = conn.cursor(buffered=True)

    try:
        # ----------------------------------------------------
        # 1) CHECK IF USER EXISTS IN radcheck
        # ----------------------------------------------------
        cur.execute("SELECT id FROM radcheck WHERE username=%s", (username,))
        user_exists = cur.fetchone() is not None

        # ----------------------------------------------------
        # 2) UPDATE OR INSERT PASSWORD (radcheck)
        # ----------------------------------------------------
        if user_exists:
            # UPDATE the password
            cur.execute("""
                UPDATE radcheck 
                SET value=%s 
                WHERE username=%s AND attribute='Cleartext-Password'
            """, (password, username))
        else:
            # INSERT new password row
            cur.execute("""
                INSERT INTO radcheck (username, attribute, op, value) 
                VALUES (%s,'Cleartext-Password',':=',%s)
            """, (username, password))

        conn.commit()

        # ----------------------------------------------------
        # 3) radreply UPSERT helper
        # ----------------------------------------------------
        def upsert_radreply(attr, value):
            cur.execute("""
                SELECT id FROM radreply 
                WHERE username=%s AND attribute=%s
            """, (username, attr))
            row = cur.fetchone()

            if row:
                cur.execute("""
                    UPDATE radreply SET value=%s 
                    WHERE id=%s
                """, (value, row[0]))
            else:
                cur.execute("""
                    INSERT INTO radreply (username, attribute, op, value)
                    VALUES (%s, %s, ':=', %s)
                """, (username, attr, value))
            conn.commit()

        # ----------------------------------------------------
        # 4) UPSERT radreply attributes
        # ----------------------------------------------------
        if rate_limit:
            upsert_radreply("Mikrotik-Rate-Limit", rate_limit)

        if profile_name:
            upsert_radreply("User-Profile", profile_name)

        upsert_radreply("Session-Timeout", session_timeout)
        upsert_radreply("Acct-Interim-Interval", Acct_Interim_Interval)

        # ----------------------------------------------------
        # 5) EXPIRATION handling (radcheck)
        # ----------------------------------------------------
        if expires_at:
            expiration_timestamp = int(expires_at.timestamp())

            # check if expiration exists
            cur.execute("""
                SELECT id FROM radcheck 
                WHERE username=%s AND attribute='Expiration'
            """, (username,))
            row = cur.fetchone()

            if row:
                cur.execute("""
                    UPDATE radcheck 
                    SET value=%s 
                    WHERE id=%s
                """, (str(expiration_timestamp), row[0]))
            else:
                cur.execute("""
                    INSERT INTO radcheck (username, attribute, op, value)
                    VALUES (%s,'Expiration',':=',%s)
                """, (username, str(expiration_timestamp)))

            conn.commit()

            logging.info(f"Expiration set for {username}: {expiration_timestamp}")

        return True

    except Exception as e:
        logging.exception("Failed to create/update radius user: %s", e)
        conn.rollback()
        return False

    finally:
        cur.close()
        conn.close()


# -------------------------
# M-Pesa functions
# -------------------------
def generate_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(consumer_key, consumer_secret), timeout=10)
    r.raise_for_status()
    return r.json().get('access_token')

def stk_push(phone, amount, transaction_uuid, hotspot_data=None, account_ref="WinNet Technologies", description="Hotspot payment"):
    access_token = generate_access_token()
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": f"{callback_url}?tx={transaction_uuid}",
        "AccountReference": account_ref,
        "TransactionDesc": description
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    r = requests.post(api_url, json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()

    #logging.info("STK Push response for tx %s: %s", transaction_uuid, data)

    # Save MerchantRequestID / CheckoutRequestID if available
    merchant_id = data.get("MerchantRequestID")
    checkout_id = data.get("CheckoutRequestID")
    if merchant_id or checkout_id:
        try:
            update_transaction_with_stk_response(transaction_uuid, merchant_id, checkout_id)
        except Exception as exc:
            logging.exception("Failed to save stk ids: %s", exc)

    return data



# -------------------------
##_________________STK_QUERY____________________##
def stk_query(checkout_request_id):
    """Call STK Query API to confirm a checkout id status."""
    try:
        token = generate_access_token()
        url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.exception("STK query failed: %s", e)
        return None



# -------------------------
# Background reconciler
# -------------------------

def reconcile_pending_transactions():
    logging.info(f"🔄 Reconciler started::::::::: {datetime.now()}")

    # Fetch transactions that have been pending for at least 120s
    pending = get_pending_transactions(older_than_seconds=120)

    for tx in pending:
        try:
            tx_id = tx.get('transaction_uuid')
            checkout_id = tx.get('checkout_request_id')
            created_at = tx.get('created_at')
            updated_last_query_time = tx.get('last_query_time')
            query_count = tx.get('query_count')
            client_ip = tx.get('ip')

            logging.info(f"Processing TX = {tx_id}")

            # ---------------------------------------------------------------
            # 1️⃣ SAFETY CHECK – skip if too soon since last query
            # ---------------------------------------------------------------
            if updated_last_query_time:
                seconds_since_query = (datetime.now() - updated_last_query_time).total_seconds()
                if seconds_since_query < 120:
                    logging.info(f"⏳ TX {tx_id} skipped: last queried {seconds_since_query:.0f}s ago")
                    continue

            '''
            # ---------------------------------------------------------------
            # 2️⃣ AUTO-FAIL very old transactions
            #    (Safaricom won’t process after 2 min anyway)
            # ---------------------------------------------------------------
            seconds_since_created = (datetime.now() - created_at).total_seconds()
            if seconds_since_created > 180:
                logging.info(f"❌ TX {tx_id} auto-failed (created {seconds_since_created:.0f}s ago)")
                mark_transaction_failed(tx_id)
                continue
            '''
                
             # ---------------------------------------------------------------
            # 2️⃣ AUTO-FAIL very old transactions based on query count
            #    (Safaricom won’t process after 2 min anyway)
            # ---------------------------------------------------------------

            if  query_count >= 3:
                logging.info(f"❌ TX {tx_id} auto-failed (max query attempts reached)")
                mark_transaction_failed(tx_id)
                continue
                
            # ---------------------------------------------------------------
            # 3️⃣ Missing checkout ID — cannot query
            # ---------------------------------------------------------------
            if not checkout_id:
                logging.warning(f"⚠️ TX {tx_id} has no checkout_request_id — skipping")
                mark_transaction_failed(tx_id)
                continue

            # ---------------------------------------------------------------
            # 4️⃣ STK Query
            # ---------------------------------------------------------------
            logging.info(f"📡 Querying STK for TX {tx_id} …")
            result = stk_query(checkout_id)

            # Save last query time
            update_last_query_time(tx_id)

            # Increment query count
            update_query_count(tx_id)

            logging.info(f"📨 STK Result TX {tx_id}: {result}")

            if not result:
                logging.info(f"⏳ STK still processing TX {tx_id}")
                continue

            result_code = int(result.get("ResultCode"))

            # ---------------------------------------------------------------
            # 5️⃣ SUCCESS → mark & give internet
            # ---------------------------------------------------------------
            if result_code == 0:
                mpesa_receipt = (result.get("Result") or {}).get("MpesaReceiptNumber")
                mark_transaction_success(tx_id, mpesa_receipt)

                plan = get_plan_by_id(tx['plan_id'])
                duration = plan['duration_minutes'] if plan else 60
                rate_limit = plan.get("rate_limit") if plan else None
                profile = plan.get("mikrotik_profile") if plan else ""

                mac = tx.get("mac") or ""

                logging.info(f"✅ Transaction {tx_id} SUCCESS — granting access")
                #authorize_hotspot_user(mac, tx_id, profile, duration, rate_limit, client_ip)
                continue

            # ---------------------------------------------------------------
            # 6️⃣ PERMANENT FAILURE
            # ---------------------------------------------------------------
            if result_code not in (0, 1):
                logging.info(f"❌ TX {tx_id} FAILED: {result.get('ResultDesc')} (code {result_code})")
                mark_transaction_failed(tx_id)
                continue

            # ---------------------------------------------------------------
            # 7️⃣ ResultCode == 1 → still pending
            # ---------------------------------------------------------------
            logging.info(f"⏳ TX {tx_id} still pending (ResultCode 1)")

        except Exception as exc:
            logging.exception(f"🔥 Error reconciling TX {tx.get('transaction_uuid')}: {exc}")

    # Run again after 30s
    threading.Timer(30, reconcile_pending_transactions).start()



# -------------------------
# Routes (existing ones enhanced)
# -------------------------
@app.route('/')
def home():
    return "<html><body><h1>WinNet Hotspot Billing API</h1><p>Version 002</p><div class='footer'><li><a href='/docs'>API Documentation</a></li></div></body></html>"

@app.route('/pay', methods=['GET', 'POST'])
def payment():
    # fetch data from frontend as json
    print(request.headers)
    print(request.data)
    
    data = request.get_json() or {}
    phone = data.get("phone")
    plan_id = data.get("plan_id")
    hotspot_data = data.get("hotspot_data") or {}

    if not phone or not plan_id:
        return jsonify({"error": "phone and plan_id required"}), 400

    plan = get_plan_by_id(plan_id)
    if not plan:
        return jsonify({"error":"plan not found"}), 400

    amount = int(plan['price'])

    # Create transaction record
    tx_uuid = create_transaction(phone, plan_id, amount, hotspot_data)
    logging.info(f'TX DATA {tx_uuid} ')

    try:
        stk_response = stk_push(phone, amount, tx_uuid, hotspot_data=hotspot_data)
        logging.info("STK Push response for tx %s: %s", tx_uuid, stk_response)

    except Exception as e:
        logging.exception("stk push failed: %s", e)
        return jsonify({"error": str(e)}), 500

    # Return the raw STK response to frontend (keeps original contract)
    return jsonify({
    "status": "success",
    "message": stk_response.get("CustomerMessage", "STK Push initiated"),
    "tx_id": tx_uuid,
    "username": tx_uuid
}
)
    


@app.route('/callback', methods=['POST', 'GET'])
def callback():
    data = request.get_json()
    logging.info("Callback received: %s", data)

    transaction_uuid = request.args.get('tx')  # from callBackURL query param
    # immediate ack to Safaricom
    response = {"ResultCode": 0, "ResultDesc": "Accepted"}

    try:
        body = data.get('Body', {})
        stk = body.get('stkCallback', {})
        result_code = int(stk.get('ResultCode'))
        result_desc = stk.get('ResultDesc')

        # Attempt to pull merchant/checkout ids if present in callback/properties
        merchant_req = stk.get('MerchantRequestID') 
        checkout_req = stk.get('CheckoutRequestID') 

        # update transaction if ids found
        if merchant_req or checkout_req:
            update_transaction_with_stk_response(transaction_uuid, merchant_req, checkout_req)

        if result_code == 0:
            # Attempt to fetch callback metadata fields robustly
            metadata = stk.get('CallbackMetadata', {}).get('Item', [])
            # Items might appear in different orders; map by Name
            meta_map = {item.get('Name'): item.get('Value') for item in metadata if isinstance(item, dict)}
            amount = meta_map.get('Amount')
            mpesa_receipt = meta_map.get('MpesaReceiptNumber')
            phone = meta_map.get('PhoneNumber')

            # mark transaction success
            mark_transaction_success(transaction_uuid, mpesa_receipt, datetime.now())

            # grant hotspot access
            # fetch plan to get duration and profile
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM user_transactions WHERE transaction_uuid = %s", (transaction_uuid,))
            tx = cur.fetchone()
            cur.close()
            conn.close()
            if tx:
                plan = None
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM user_plans WHERE id=%s", (tx['plan_id'],))
                plan = cur.fetchone()
                cur.close(); conn.close()

                # create radius user
                username = tx.get('client_phone')
                password = tx.get('code_6char')
                rate_limit = plan.get('rate_limit') if plan else None
                duration_minutes = plan.get('duration_minutes', 60) if plan else 60
                expires_at = datetime.now() + timedelta(minutes=duration_minutes)

                created = create_or_update_radius_user(username, password, profile_name=plan.get('mikrotik_profile') if plan else None, rate_limit=rate_limit, expire_minutes=duration_minutes, expires_at=expires_at)
                logging.info("  Radius user created: %s", created)
                

                # store in hotspot_users table
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("""
                    SELECT * FROM hotspot_users WHERE username = %s
                    """, (username,))
                    user = cur.fetchone()
                    if user:
                        cur.execute("""
                                    UPDATE hotspot_users SET transaction_uuid=%s, mac=%s, mikrotik_profile=%s, expires_at=%s, client_ip=%s, link_login=%s, code_6char=%s
                                    WHERE username=%s
                                """, (transaction_uuid, tx.get('mac'), plan.get('mikrotik_profile') if plan else '', expires_at, tx.get('ip'), tx.get('link_login'), password, username))
                        conn.commit()
                        
                        logging.info("  Hotspot user updated: %s", username)

                    else:

                        cur.execute("""
                            INSERT INTO hotspot_users (transaction_uuid, mac, username, mikrotik_profile, expires_at, client_ip, link_login, code_6char)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (transaction_uuid, tx.get('mac'), username, plan.get('mikrotik_profile') if plan else '', expires_at, tx.get('ip'), tx.get('link_login'), password))
                        conn.commit()
                        logging.info("  Hotspot user inserted: %s", username)

                except Exception as e:
                    logging.exception("Failed to insert/update hotspot user: %s", e)
                    conn.rollback()

                finally:
                    cur.close()
                    conn.close()
                
            logging.info("Payment SUCCESS for tx %s", transaction_uuid)
            # Always respond 200 quickly to Safaricom
            return jsonify({"ResultCode":0, "ResultDesc":"Accepted"}), 200
        else:
            # failed/cancelled
            mark_transaction_failed(transaction_uuid)
            logging.info("Payment FAILED: %s", result_desc)
    except Exception as e:
        logging.exception("Error handling callback: %s", e)
        return jsonify({"ResultCode":1, "ResultDesc":"Error"}), 500

    return jsonify(response), 200
    

@app.route('/check_tx', methods=['GET'])
def check_tx():
    """Frontend polls this endpoint to learn tx status."""
    tx = request.args.get('tx')
    if not tx:
        return jsonify({"error":"tx required"}), 400
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT status, mpesa_receipt, checkout_request_id FROM user_transactions WHERE transaction_uuid=%s", (tx,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return jsonify({"error":"tx not found"}), 404
    return jsonify(row)

@app.route('/auto_login/<tx>', methods=['GET'])
def auto_login(tx):
    """
    Called by the captive browser after payment success.
    Returns an auto-posting HTML that posts username & password to the hotspot login URL (link_login).
    The frontend should open this URL in the captive browser window (or navigate there).
    """
    # fetch transaction and link_login

    logging.info(f"Auto-login requested for TX {tx}")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM hotspot_users WHERE transaction_uuid = %s", (tx,))
    tx_row = cur.fetchone()
    cur.close(); conn.close()
    
    if not tx_row:
        # Payment not yet confirmed → auto-refresh page every 5 seconds
        html = """
            <html>
                <head>
                    <!-- CRITICAL FIX: The viewport meta tag ensures the browser renders the page 
                        at the width of the device, not a desktop default. -->
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    
                    <!-- START FONT IMPLEMENTATION: Poppins via Google Fonts CDN -->
                    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
                    <!-- END FONT IMPLEMENTATION -->
                    
                    <style>

                        @font-face {
                            font-family: "Sour Gummy";
                            src: url("/static/fonts/sour-gummy_5.2.8/webfonts/sour-gummy-latin-400-normal.woff") format("woff"),
                                url("/static/fonts/sour-gummy_5.2.8/webfonts/sour-gummy-latin-400-normal.woff2") format("woff2");
                            font-weight: normal;
                            font-style: normal;
                            font-display: swap;
                            }  

                        body {
                            /* Set Poppins as the primary font family */
                            /*font-family: 'Poppins', Arial, sans-serif;*/
                            font-family: "Sour Gummy", sans-serif;
                            text-align: center;
                            background: #f7f7f7;
                            /* Use flexbox to center the content vertically and horizontally */
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0; /* Remove default body margin */
                        }
                        h3 {
                            color: #333;
                            margin-top: 0;
                        }
                        p {
                            color: #666;
                        }
                        .progress-container {
                            width: 100%; /* Make it responsive within the main-content max-width */
                            background: #ddd;
                            height: 12px;
                            border-radius: 10px;
                            margin: 20px 0;
                            overflow: hidden;
                        }
                        .progress-bar {
                            height: 100%;
                            width: 90%;
                            background: #4CAF50;
                            transition: width 1s linear;
                            border-radius: 10px; /* Match container border radius */
                        }
                        #counter {
                            
                            color: #444;
                            margin-top: 10px;
                            font-weight: 500;
                        }

                        .main-content {
                            background: #fff;
                            padding: 30px;
                            border-radius: 8px;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                            /* Center content within itself */
                            display: flex;
                            flex-direction: column; 
                            align-items: center;
                            max-width: 500px; /* Set a reasonable max width for the card */
                            width: 90%; /* Responsive width */
                            margin: 20px;
                            font-size: 1em;
                            line-height: 1.6em;
                        }
                        .wrap {
                            width: 100%;
                            text-align: justify;
                        }

                        /* Responsive adjustments are now primarily handled by max-width and percentage widths */
                        @media (max-width: 600px) {
                            .main-content {
                                padding: 20px;
                                max-width:480px;
                            }
                        }
                    </style>

                    <script>
                        let refreshInterval = 5;  // seconds until next auto-refresh
                        let countdown = refreshInterval;

                        function startCountdown() {
                            const bar = document.getElementById("bar");
                            const counter = document.getElementById("counter");

                            function tick() {
                                // Calculate the percentage remaining
                                const percentage = (countdown / refreshInterval) * 100;
                                
                                counter.textContent = countdown + "s";
                                // Update the bar width based on the countdown
                                bar.style.width = percentage + "%";

                                countdown--;

                                if (countdown < 0) {
                                    // When countdown finishes, reload the page to check status
                                    window.location.reload();
                                } else {
                                    // Continue counting down
                                    setTimeout(tick, 1000);
                                }
                            }
                            tick();
                        }
                        
                        // Start the countdown when the window loads
                        window.onload = startCountdown;
                    </script>
                </head>

                <body>
                    <div class='main-content'>
                        <div class="wrap">
                            <h3>Payment is processing...</h3>
                            <p>Please wait — we will log you in automatically once your payment is confirmed.</p>
                        </div>
                        <!-- Progress Bar -->
                        <div class="progress-container">
                            <div class="progress-bar" id="bar"></div>
                        </div>
                        <!-- Countdown Timer -->
                        <div id="counter">5s</div>
                        <p style="color:#777; margin-top:20px;">Checking your payment...</p>
                    </div>
                </body>
            </html>
        """
        return html, 202

    # the username we created for RADIUS is the tx id (or other unique value)
    username = tx_row.get('username')
    password = tx_row.get('code_6char') 
    link_login = tx_row.get('link_login') or 'http://10.0.0.1/login'  # fallback
    #link_login = 'http://10.0.0.1/login'
    #dst_url = tx_row.get('dst_url', 'http://www.googleapis.com/generate_204')
    dst_url = 'http://www.googleapis.com/generate_204'
    dst_youtube = 'https://www.youtube.com/watch?v=pJK53pL_6sg&list=RDpJK53pL_6sg&start_radio=1'
    client_ip = tx_row.get('client_ip')
    client_mac = tx_row.get('mac')

    # Build auto-post HTML. The hotspot login URL form fields vary by RouterOS version:
    # Many RouterOS hotspots accept "username" and "password" POST to link_login.

    logging.info(f"Auto-login HTML posting to {link_login} with username {username}")
    
    html = f"""
    <html>
        <head>
             <meta http-equiv="refresh" content="2;url=https://www.youtube.com/watch?v=pJK53pL_6sg">
        </head>
      <body onload="document.forms[0].submit()">
        <form action="{link_login}" method="post">
          <input type="hidden" name="username" value="{username}">
          <input type="hidden" name="password" value="{password}">
          
          <input type="hidden" name="mac" value="{client_mac}">
          <input type="hidden" name="ip" value="{client_ip}">
          <input type="hidden" name="login-by" value="name">
          <input type="hidden" name="dst" value="{dst_url}">
        </form>
        
        <p>Logging you in...</p>
      </body>
    </html>
    """
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html'
    return resp


#_________________________CHECK USER ROUTE_________________________##

### ---------- Main route: reconnect & device-switch detection ----------
@app.route("/reconnect/<username>", methods=["POST", "GET"])
def reconnect(username):
    """
    POST with JSON { "password": "xxxxx", "mac": "AA:BB:CC", "client_ip": "10.0.0.5", "dst": "...optional..." }
    Logic:
     - verify provided passcode against hotspot_users.code_6char or radcheck (depending your flow)
     - if account active on different MAC => show switch page
     - if confirm switch (POST to /switch-device) => remove old session, update DB, return auto-login HTML
     - otherwise return auto-login HTML immediately
    """
    # Accept both JSON (fetch) or form POST
    data = request.get_json(silent=True) or request.form or {}
    provided_password = data.get("password") or data.get("code")
    new_mac = data.get("mac") or request.remote_addr  # mac should be provided by frontend if available
    client_ip = data.get("ip") or request.remote_addr
    dst = data.get("dst") or data.get("redirect") or "http://www.googleapis.com/generate_204"
    dst = dst if dst.startswith("http") else "http://"+dst
    dst_enc = urllib.parse.quote(dst, safe='')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Get most recent user record
        cur.execute("SELECT * FROM hotspot_users WHERE username=%s ORDER BY id DESC LIMIT 1", (username,))
        user = cur.fetchone()
        if not user:
            return jsonify({"status":"error","message":"User not found"}), 404

        # If password mismatch -> fail (you may also consult radcheck instead)
        expected = user.get('code_6char') or user.get('password')
        if not provided_password or provided_password != expected:
            return jsonify({"status":"error","message":"Authentication failed"}), 401

        # Check existing active session for this username using MikroTik API
        api = get_mikrotik_api()
        try:
            active = find_active_session_by_username(api, username)
            logging.info("Active session for %s: %s", username, active)
        
        finally:
            # keep api connection open until removal step maybe; we'll disconnect after potential remove
            pass

        # If there's an active session and MAC differs -> present switch page
        if active and active.get('mac-address') and (active.get('mac-address').lower() != (new_mac or "").lower()):
            # produce device switch decision page
            old_mac = active.get('mac-address')
            old_ip = active.get('address') or active.get('ip-address') or active.get('address')
            old_id = active.get('.id') or active.get('id') or active.get('session-id')

            logging.info("Device switch detected for %s: old MAC %s vs new MAC %s", username, old_mac, new_mac)

            html = f"""
            <html>
            <head><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
            <body style="font-family:Arial,Helvetica,sans-serif;padding:20px;">
                <h3>Device switch detected</h3>
                <p>Your account is currently active on another device (MAC: {old_mac}, IP: {old_ip}).</p>
                <p>Do you want to disconnect the other device and continue on this one?</p>
                <form method="POST" action="http://192.168.100.88:5000/switch-device/{username}">
                    <input type="hidden" name="old_id" value="{urllib.parse.quote(str(old_id))}">
                    <input type="hidden" name="new_mac" value="{new_mac}">
                    <input type="hidden" name="client_ip" value="{client_ip}">
                    <input type="hidden" name="dst" value="{dst_enc}">
                    <button type="submit" style="padding:12px 18px;font-size:16px;">Yes, switch device</button>
                </form>
                <p style="margin-top:16px;"><em>If you don't switch, you will stay logged in on the other device.</em></p>
            </body>
            </html>
            """
            return make_response(html, 200, {"Content-Type":"text/html"})

        # No conflicting session -> proceed to auto-login HTML
        # Ensure radcheck/radreply up to date (you might have already updated on payment)
        upsert_radcheck(username, expected)
        # Example radreply entries (session timeout etc) - adapt to packages
        upsert_radreply(username, "Session-Timeout", str(3600))
        upsert_radreply(username, "Acct-Interim-Interval", "60")

        # Save client info & mark active in your app DB
        cur.execute("""
            UPDATE hotspot_users
            SET mac=%s, client_ip=%s, session_status='active', updated_at=NOW()
            WHERE id=%s
        """, (new_mac, client_ip, user['id']))
        conn.commit()

        # Build the auto-post HTML that posts to MikroTik login
        # include popup=true to improve CNA behavior
        html = f"""
        <html>
            <head><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
            <body onload="document.forms[0].submit()">
                <form action="{mikrotik_config['HOTSPOT_LOGIN_URL']}" method="post">
                    <input type="hidden" name="username" value="{username}">
                    <input type="hidden" name="password" value="{expected}">
                    <input type="hidden" name="dst" value="{dst}">
                    <input type="hidden" name="popup" value="true">
                </form>
                <p>Logging you in... If the page doesn&apos;t redirect automatically, <a href="{mikrotik_config['HOTSPOT_LOGIN_URL']}">click here</a>.</p>
            </body>
        </html>
        """
        return make_response(html, 200, {"Content-Type":"text/html"})

    except Exception as e:
        logging.exception("Reconnect error: %s", e)
        return jsonify({"status":"error","message":str(e)}), 500

    finally:
        cur.close()
        conn.close()
        try:
            api.disconnect()
        except Exception:
            pass

### ---------- Switch-device handler ----------
@app.route("/switch-device/<username>", methods=["POST"])
def switch_device(username):
    """
    Called when user confirms device switch.
    POST fields: old_id (mikrotik active .id), new_mac, client_ip, dst
    """
    old_id = request.form.get("old_id")
    new_mac = request.form.get("new_mac")
    client_ip = request.form.get("client_ip")
    dst_enc = request.form.get("dst") or urllib.parse.quote("http://www.googleapis.com/generate_204", safe='')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    api = get_mikrotik_api()
    try:
        # Remove the old active session on MikroTik
        removed = False
        try:
            # old_id may be quoted in the form
            old_id_decoded = urllib.parse.unquote(old_id)
            removed = remove_active_session_by_id(api, old_id_decoded)
            logging.info("Attempted removal of old session %s -> %s", old_id_decoded, removed)
        except Exception:
            logging.exception("Failed removing active session")

        # Update DB - mark previous session expired
        cur.execute("SELECT id FROM hotspot_users WHERE username=%s AND session_status='active' ORDER BY id DESC LIMIT 1", (username,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE hotspot_users SET session_status='expired', updated_at=NOW() WHERE id=%s", (row['id'],))
            conn.commit()

        # Get user record and prepare auto-login HTML for new device (use existing passcode)
        cur.execute("SELECT * FROM hotspot_users WHERE username=%s ORDER BY id DESC LIMIT 1", (username,))
        user = cur.fetchone()
        if not user:
            return "User record missing", 404

        password = user.get('code_6char') or user.get('password')
        # update DB with new mac and active status
        cur.execute("UPDATE hotspot_users SET mac=%s, client_ip=%s, session_status='active', updated_at=NOW() WHERE id=%s",
                    (new_mac, client_ip, user['id']))
        conn.commit()

        # return auto-login HTML
        dst = urllib.parse.unquote(dst_enc)
        html = f"""
        <html>
            <head><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
            <body onload="document.forms[0].submit()">
                <form action="{mikrotik_config['HOTSPOT_LOGIN_URL']}" method="post">
                    <input type="hidden" name="username" value="{username}">
                    <input type="hidden" name="password" value="{password}">
                    <input type="hidden" name="dst" value="{dst}">
                    <input type="hidden" name="popup" value="true">
                    <input type="hidden" name="mac" value="{new_mac}">
                </form>
                <p>Switching device and logging you in...</p>
            </body>
        </html>
        """
        return make_response(html, 200, {"Content-Type":"text/html"})

    except Exception as e:
        logging.exception("switch-device error: %s", e)
        return str(e), 500

    finally:
        try:
            api.disconnect()
        except Exception:
            pass
        cur.close()
        conn.close()


#
# -------------------------
# Start Flask
# -------------------------
if __name__ == '__main__':
    if not os.getenv("WERKZEUG_RUN_MAIN"):  # Only start in main process, not reloader
        threading.Timer(5, reconcile_pending_transactions).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
