from flask import Flask, request, jsonify
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

try:
    import routeros_api
except Exception:
    routeros_api = None

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "BILLING"),
    "autocommit": False
}

consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
shortcode = os.getenv("BUSINESS_SHORTCODE")
passkey = os.getenv("PASSKEY")
callback_url = os.getenv("CALLBACK_URL")

MIKROTIK_HOST = os.getenv("MIKROTIK_HOST")
MIKROTIK_USER = os.getenv("MIKROTIK_USER")
MIKROTIK_PASS = os.getenv("MIKROTIK_PASS")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT", "8728"))
MIKROTIK_HOTSPOT_SERVER = os.getenv("MIKROTIK_HOTSPOT_SERVER", "")


# -------------------------- DB HELPERS --------------------------
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_plan_by_id(plan_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_plans WHERE id=%s", (plan_id,))
    plan = cursor.fetchone()
    cursor.close()
    conn.close()
    return plan


def create_transaction(phone, plan_id, amount, hotspot_data=None):
    tx = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_transactions 
        (transaction_uuid, client_phone, plan_id, amount, status, mac, ip, username, sessionid, created_at)
        VALUES (%s,%s,%s,%s,'pending',%s,%s,%s,%s,%s)
    """, (tx, phone, plan_id, amount,
          hotspot_data.get("mac"),
          hotspot_data.get("ip"),
          hotspot_data.get("user"),
          hotspot_data.get("sessionid"),
          datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    return tx


def update_transaction_with_stk_ids(tx, merchant_id, checkout_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions 
        SET merchant_request_id=%s, checkout_request_id=%s 
        WHERE transaction_uuid=%s
    """, (merchant_id, checkout_id, tx))
    conn.commit()
    cursor.close()
    conn.close()


def mark_tx_success(tx, receipt):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions 
        SET status='success', mpesa_receipt=%s, callback_received_at=%s 
        WHERE transaction_uuid=%s
    """, (receipt, datetime.now(), tx))
    conn.commit()
    cursor.close()
    conn.close()


def mark_tx_failed(tx):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_transactions SET status='failed' WHERE transaction_uuid=%s", (tx,))
    conn.commit()
    cursor.close()
    conn.close()


def get_pending_tx(older=25):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cutoff = datetime.now() - timedelta(seconds=older)
    cursor.execute("SELECT * FROM user_transactions WHERE status='pending' AND created_at < %s", (cutoff,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# -------------------------- SAFARICOM --------------------------
def generate_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(consumer_key, consumer_secret))
    return r.json().get("access_token")


def stk_push(phone, amount, tx):
    token = generate_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    pwd = base64.b64encode((shortcode + passkey + timestamp).encode()).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": pwd,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": f"{callback_url}?tx={tx}",
        "AccountReference": "Hotspot",
        "TransactionDesc": "Hotspot Payment"
    }

    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                      json=payload, headers=headers)
    res = r.json()

    update_transaction_with_stk_ids(
        tx,
        res.get("MerchantRequestID"),
        res.get("CheckoutRequestID")
    )

    return res


def stk_query(checkout_id):
    token = generate_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    pwd = base64.b64encode((shortcode + passkey + timestamp).encode()).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": pwd,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_id
    }

    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
                      json=payload, headers=headers)
    return r.json()


# -------------------------- MIKROTIK --------------------------
def connect_router():
    api = routeros_api.RouterOsApiPool(
        MIKROTIK_HOST, username=MIKROTIK_USER,
        password=MIKROTIK_PASS, port=MIKROTIK_PORT,
        plaintext_login=True
    )
    return api


def authorize_user(mac, username, profile, mins):
    try:
        api = connect_router()
        with api.get_api() as cli:
            # add user
            cli.get_resource("/ip/hotspot/user").add(
                name=username,
                profile=profile
            )
            # bypass binding
            cli.get_resource("/ip/hotspot/ip-binding").add(
                mac_address=mac,
                type="bypassed"
            )
        api.disconnect()
        return True
    except Exception as e:
        logging.error(e)
        return False


# -------------------------- BACKGROUND RECONCILER --------------------------
def reconciler():
    pend = get_pending_tx()

    for tx in pend:
        logging.info("Reconciling tx %s", tx['transaction_uuid'])
        if not tx["checkout_request_id"]:
            continue

        res = stk_query(tx["checkout_request_id"])

        if not res:
            continue

        if res.get("ResultCode") == 0:
            receipt = res["CallbackMetadata"]["Item"][1]["Value"]

            mark_tx_success(tx["transaction_uuid"], receipt)

            # Authorize user
            plan = get_plan_by_id(tx["plan_id"])
            authorize_user(tx["mac"], tx["transaction_uuid"], plan["mikrotik_profile"], plan["duration_minutes"])

        else:
            mark_tx_failed(tx["transaction_uuid"])

threading.Timer(25, reconciler).start()


#threading.Timer(5, reconciler).start()


# -------------------------- ROUTES --------------------------
@app.route('/pay', methods=['POST'])
def pay():
    data = request.get_json()
    phone = data["phone"]
    plan_id = data["plan_id"]
    hotspot = data.get("hotspot_data", {})

    plan = get_plan_by_id(plan_id)
    amount = int(plan["price"])

    tx = create_transaction(phone, plan_id, amount, hotspot)

    res = stk_push(phone, amount, tx)
    return jsonify(res)


@app.route('/callback', methods=['POST'])
def callback():
    tx = request.args.get("tx")
    data = request.get_json()

    stk = data["Body"]["stkCallback"]
    code = stk["ResultCode"]

    if code == 0:
        items = {item["Name"]: item["Value"] for item in stk["CallbackMetadata"]["Item"]}
        receipt = items["MpesaReceiptNumber"]

        mark_tx_success(tx, receipt)

        # authorize user instantly
        conn = get_connection()
        c = conn.cursor(dictionary=True)
        c.execute("SELECT * FROM user_transactions WHERE transaction_uuid=%s", (tx,))
        row = c.fetchone()
        c.close()
        conn.close()

        plan = get_plan_by_id(row["plan_id"])
        authorize_user(row["mac"], tx, plan["mikrotik_profile"], plan["duration_minutes"])

    else:
        mark_tx_failed(tx)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
