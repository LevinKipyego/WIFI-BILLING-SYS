from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime
import os
from dotenv import load_dotenv
import mysql.connector
import uuid
# Load environment variables
load_dotenv()

app = Flask(__name__)

# -------------------------
# Database Configuration
# -------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",       # <-- change this to your MySQL password
    "database": "wifi_billing"
}

# -------------------------
# M-Pesa API Configuration
# -------------------------
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
shortcode = os.getenv("BUSINESS_SHORTCODE")
passkey = os.getenv("PASSKEY")
callback_url = os.getenv("CALLBACK_URL")

# -------------------------
# Database Helpers
# -------------------------
def get_connection():
    """Return a MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)

def get_plan_by_id(plan_id):
    """Return plan details as a dict."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM plans WHERE id = %s", (plan_id,))
    plan = cursor.fetchone()
    cursor.close()
    conn.close()
    return plan

def create_transaction(phone, plan_id, amount):
    """Insert a pending transaction and return UUID."""
    tx_uuid = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (transaction_uuid, client_phone, plan_id, amount, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (tx_uuid, phone, plan_id, amount, 'pending', datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    return tx_uuid


# -------------------------
# M-Pesa Functions
# -------------------------
def generate_access_token():
    #Fetch OAuth token from Daraja API. and returns the token to the function that will be accessed later during stk push

    access_token_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(access_token_url, auth=(consumer_key, consumer_secret))
    access_token = response.json().get("access_token")
    return access_token

# 2️⃣ Initiate STK Push
#@app.route('/stkpush', methods=['GET', 'POST'])
def stk_push(phone, amount, transaction_uuid, account_ref="FRADENET SOLUTIONs", description="WiFi Access Payment"):
    """Send STK Push request to M-Pesa API."""

    access_token = generate_access_token()
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    # STK Push request details
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,  # You can change this
        "PartyA": phone,  # Test phone number
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": f"{callback_url}?tx={transaction_uuid}",
        "AccountReference": account_ref,
        "TransactionDesc": description
         }

    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/json"
               }
    
    #stk Push
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        return jsonify(response.json())
    except Exception as e:
        return {"error": str(e)}

# 3️⃣ Handle callback
@app.route('/callback', methods=['POST'])
def callback():
    data = request.get_json()
    print("Callback received:", data)

    # Extract transaction_uuid from query string (added earlier)
    transaction_uuid = request.args.get('tx')

    # Default response to M-Pesa (must always return 0)
    response = {"ResultCode": 0, "ResultDesc": "Accepted"}

    try:
        # Check if payment was successful
        result_code = data["Body"]["stkCallback"]["ResultCode"]
        result_desc = data["Body"]["stkCallback"]["ResultDesc"]

        if result_code == 0:
            # SUCCESSFUL PAYMENT
            amount = data["Body"]["stkCallback"]["CallbackMetadata"]["Item"][0]["Value"]
            mpesa_receipt = data["Body"]["stkCallback"]["CallbackMetadata"]["Item"][1]["Value"]
            phone = data["Body"]["stkCallback"]["CallbackMetadata"]["Item"][4]["Value"]

            # ✅ Update your MySQL transaction record
            #cur = mysql.connection.cursor()
            conn = get_connection()
            cur = conn.cursor(dictionary=True)

            cur.execute("""
                UPDATE transactions
                SET status=%s, mpesa_receipt=%s
                WHERE transaction_uuid=%s
            """, ("success", mpesa_receipt, transaction_uuid))
            conn.commit()
            cur.close()
            conn.close()

            print(f"Payment SUCCESS for {phone}, amount: {amount}, receipt: {mpesa_receipt}")
        else:
            # FAILED or CANCELLED
            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE transactions
                SET status=%s
                WHERE transaction_uuid=%s
            """, ("failed", transaction_uuid))
            mysql.connection.commit()
            cur.close()

            print(f"Payment FAILED: {result_desc}")

    except Exception as e:
        print("Error handling callback:", e)

    # Always respond to Safaricom quickly
    return jsonify(response)

# 4️⃣ Home route
@app.route('/')
def home():
    return "Welcome to Daraja Flask Demo."

#route to payment
@app.route('/pay', methods = ['GET', 'POST'])
def payment():
    #fetching data from frontend as json
    print("Headers:", request.headers)
    print("Raw Data:", request.data)
    
    data = request.get_json() or {}
    phone = data.get("phone")
    plan_id = data.get("plan_id")

    plan =  get_plan_by_id(plan_id)
    amount = plan['price']

    # Create transaction record
    tx_uuid = create_transaction(phone, plan_id, amount)
    
    # Trigger STK push
    stk_details = stk_push(phone,amount,tx_uuid)
    
    return stk_details

if __name__ == '__main__':
    app.run(debug=True)
