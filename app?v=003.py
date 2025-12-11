# flask_radius_integration.py
from flask import Flask, request, jsonify, make_response
import os, uuid, logging, base64, requests
from datetime import datetime, timedelta
import mysql.connector
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# DB (your billing DB + FreeRADIUS DB can be same or separate)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "BILLING")
}

# FreeRADIUS DB config (if separate)
RADIUS_DB = {
    "host": os.getenv("RADIUS_DB_HOST", DB_CONFIG["host"]),
    "user": os.getenv("RADIUS_DB_USER", DB_CONFIG["user"]),
    "password": os.getenv("RADIUS_DB_PASS", DB_CONFIG["password"]),
    "database": os.getenv("RADIUS_DB_NAME", "radius")
}

# M-Pesa (Daraja) credentials
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
shortcode = os.getenv("BUSINESS_SHORTCODE")
passkey = os.getenv("PASSKEY")
callback_url = os.getenv("CALLBACK_URL")  # will include ?tx=uuid

# Helper DB connectors
def get_connection(cfg=DB_CONFIG):
    return mysql.connector.connect(**cfg)

# --- transaction helpers (simple) ---
def create_transaction(phone, plan_id, amount, hotspot_data=None):
    tx_uuid = str(uuid.uuid4())
    conn = get_connection()
    cur = conn.cursor()
    # note: ensure number of placeholders equals values
    cur.execute("""
        INSERT INTO user_transactions
        (transaction_uuid, client_phone, plan_id, amount, status, mac, ip, username, sessionid, link_login, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        tx_uuid, phone, plan_id, amount, 'pending',
        (hotspot_data or {}).get('mac'),
        (hotspot_data or {}).get('ip'),
        (hotspot_data or {}).get('user') or '',
        (hotspot_data or {}).get('sessionid') or '',
        (hotspot_data or {}).get('link_login') or '',
        datetime.now()
    ))
    conn.commit()
    cur.close()
    conn.close()
    return tx_uuid

def update_transaction_with_stk_response(transaction_uuid, merchant_request_id=None, checkout_request_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE user_transactions
        SET merchant_request_id=%s, checkout_request_id=%s, updated_at=%s
        WHERE transaction_uuid=%s
    """, (merchant_request_id, checkout_request_id, datetime.now(), transaction_uuid))
    conn.commit()
    cur.close()
    conn.close()

def mark_transaction_success(transaction_uuid, mpesa_receipt=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE user_transactions
        SET status='success', mpesa_receipt=%s, callback_received_at=%s, updated_at=%s
        WHERE transaction_uuid=%s
    """, (mpesa_receipt, datetime.now(), datetime.now(), transaction_uuid))
    conn.commit()
    cur.close()
    conn.close()

# --- FreeRADIUS helpers ---
def create_radius_user(username, password, profile_name=None, rate_limit=None, expire_minutes=60):
    """
    Insert user into radcheck & radreply so RADIUS will accept login.
    This example uses FreeRADIUS default schema: radcheck, radreply.
    """
    conn = mysql.connector.connect(**RADIUS_DB)
    cur = conn.cursor()
    try:
        # radcheck: username | attribute | op | value
        cur.execute("INSERT INTO radcheck (username, attribute, op, value) VALUES (%s,%s,%s,%s)",
                    (username, 'Cleartext-Password', ':=', password))
        # Radreply entries (Vendor specific attributes for MikroTik)
        if rate_limit:
            # mikrotik expects "Mikrotik-Rate-Limit" in radreply
            cur.execute("INSERT INTO radreply (username, attribute, op, value) VALUES (%s,%s,%s,%s)",
                        (username, 'Mikrotik-Rate-Limit', ':=', rate_limit))
        if profile_name:
            # you can also set a Group or other attribute if you use groups
            cur.execute("INSERT INTO radreply (username, attribute, op, value) VALUES (%s,%s,%s,%s)",
                        (username, 'User-Profile', ':=', profile_name))
        # expiration: freeRadius can check against radcheck 'Expiration' if you have rlm_sql configured
        # We'll also store expiry in our billing DB for cleanup
        conn.commit()
        return True
    except Exception as e:
        logging.exception("Failed to create radius user: %s", e)
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

def remove_radius_user(username):
    conn = mysql.connector.connect(**RADIUS_DB)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM radreply WHERE username = %s", (username,))
        cur.execute("DELETE FROM radcheck WHERE username = %s", (username,))
        conn.commit()
    except Exception as e:
        logging.exception("Failed to remove radius user: %s", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# --- Daraja helpers (simplified) ---
def generate_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(consumer_key, consumer_secret), timeout=10)
    r.raise_for_status()
    return r.json().get('access_token')

def stk_push(phone, amount, transaction_uuid, account_ref="WiFi", description="Hotspot payment"):
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
    return r.json()

# --- Endpoints ---

@app.route('/pay', methods=['POST'])
def pay():
    """
    Frontend sends phone, plan_id and hotspot_data (mac, ip, link_login, sessionid).
    Returns STK push response (so frontend shows "Enter PIN" prompt).
    """
    data = request.get_json() or {}
    phone = data.get('phone')
    plan_id = data.get('plan_id')
    hotspot_data = data.get('hotspot_data') or {}

    if not phone or not plan_id:
        return jsonify({"error":"phone and plan_id required"}), 400

    # get plan details from billing DB
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_plans WHERE id=%s", (plan_id,))
    plan = cur.fetchone()
    cur.close(); conn.close()
    if not plan:
        return jsonify({"error":"plan not found"}), 400

    amount = float(plan['price'])
    tx_uuid = create_transaction(phone, plan_id, amount, hotspot_data)

    try:
        stk_resp = stk_push(phone, amount, tx_uuid)
        # Save merchant/checkout ids to tx
        merchant = stk_resp.get("MerchantRequestID")
        checkout = stk_resp.get("CheckoutRequestID")
        update_transaction_with_stk_response(tx_uuid, merchant, checkout)
    except Exception as e:
        logging.exception("STK push failed: %s", e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"tx": tx_uuid, "stk": stk_resp})

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
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_transactions WHERE transaction_uuid = %s", (tx,))
    tx_row = cur.fetchone()
    cur.close(); conn.close()
    if not tx_row:
        return "Transaction not found", 404

    # the username we created for RADIUS is the tx id (or other unique value)
    username = tx_row['transaction_uuid']
    password = ""  # we created empty password in radcheck earlier
    link_login = tx_row.get('link_login') or '/login'  # fallback

    # Build auto-post HTML. The hotspot login URL form fields vary by RouterOS version:
    # Many RouterOS hotspots accept "username" and "password" POST to link_login.
    html = f"""
    <html>
      <body onload="document.forms[0].submit()">
        <form action="{link_login}" method="post">
          <input type="hidden" name="username" value="{username}">
          <input type="hidden" name="password" value="{password}">
        </form>
        <p>Logging you in...</p>
      </body>
    </html>
    """
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html'
    return resp

@app.route('/callback', methods=['POST'])
def callback():
    """
    Safaricom server callback. We mark tx success and create radcheck entries.
    Important: Safaricom will call this server-to-server (not the captive browser).
    """
    data = request.get_json() or {}
    logging.info("Callback received: %s", data)
    transaction_uuid = request.args.get('tx')
    if not transaction_uuid:
        return jsonify({"ResultCode": 1, "ResultDesc":"tx missing"}), 400

    try:
        body = data.get('Body', {})
        stk = body.get('stkCallback', {})
        result_code = int(stk.get('ResultCode', 1))

        # attempt to get metadata
        metadata = stk.get('CallbackMetadata', {}).get('Item', [])
        meta_map = {item.get('Name'): item.get('Value') for item in metadata if isinstance(item, dict)}
        mpesa_receipt = meta_map.get('MpesaReceiptNumber')
        amount = meta_map.get('Amount')

        # update transaction and mark success
        if result_code == 0:
            mark_transaction_success(transaction_uuid, mpesa_receipt)

            # create RADIUS user (username==transaction_uuid)
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM user_transactions WHERE transaction_uuid=%s", (transaction_uuid,))
            tx = cur.fetchone()
            cur.close(); conn.close()
            if tx:
                plan = None
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM user_plans WHERE id=%s", (tx['plan_id'],))
                plan = cur.fetchone()
                cur.close(); conn.close()

                # create radius user
                username = transaction_uuid
                password = ""  # empty password (RouterOS hotspot will POST username/password)
                rate_limit = plan.get('rate_limit') if plan else None
                duration_minutes = plan.get('duration_minutes', 60) if plan else 60

                created = create_radius_user(username, password, profile_name=plan.get('mikrotik_profile') if plan else None, rate_limit=rate_limit, expire_minutes=duration_minutes)

                # Save expiry / hotspot_users record in your DB so you can cleanup later
                conn = get_connection()
                cur = conn.cursor()
                expires_at = datetime.now() + timedelta(minutes=duration_minutes)
                cur.execute("""
                    INSERT INTO hotspot_users (transaction_uuid, mac, username, mikrotik_profile, expires_at, client_ip)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (transaction_uuid, tx.get('mac'), username, plan.get('mikrotik_profile') if plan else None, expires_at, tx.get('ip')))
                conn.commit(); cur.close(); conn.close()

            # Always respond 200 quickly to Safaricom
            return jsonify({"ResultCode":0, "ResultDesc":"Accepted"}), 200
        else:
            # failed / canceled
            # optionally mark failed
            return jsonify({"ResultCode":1, "ResultDesc":"Failed"}), 200
    except Exception as e:
        logging.exception("Error in callback: %s", e)
        return jsonify({"ResultCode":1, "ResultDesc":"Error"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)), debug=False)
