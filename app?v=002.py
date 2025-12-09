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

# Optional: routeros_api for Mikrotik interactions
try:
    import routeros_api
except Exception:
    routeros_api = None

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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions
        SET status='SUCCESS', mpesa_receipt=%s, callback_received_at=%s, updated_at=%s
        WHERE transaction_uuid=%s
    """, (mpesa_receipt, callback_time or datetime.now(), datetime.now(), transaction_uuid))
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

def get_pending_transactions(older_than_seconds=120):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cutoff = datetime.now() - timedelta(seconds=older_than_seconds)
    cursor.execute("SELECT * FROM user_transactions WHERE status='PENDING' AND created_at < %s", (cutoff,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

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

# -------------------------
# MikroTik RouterOS helpers
# -------------------------
#AUTO-LOGIN
def auto_login_html(username, link_login=None):
    if link_login is None:
        link_login = "/login"
    return f"""
    <html>
        <body onload="document.forms[0].submit()">
            <form action="{link_login}" method="post">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="">
            </form>
        </body>
    </html>
    """



ROUTEROS_CONNECT_RETRY = 2
ROUTEROS_CONNECT_TIMEOUT = 10  # seconds

LOG = logging.getLogger(__name__)

def connect_routeros():
    """
    Create a RouterOsApiPool and return (pool, api).
    Caller MUST call pool.disconnect() when finished.
    This avoids using `with` which some routeros_api versions don't support.
    """
    if routeros_api is None:
        raise RuntimeError("routeros_api library not installed")

    attempts = 0
    while True:
        try:
            pool = routeros_api.RouterOsApiPool(
                MIKROTIK_HOST,
                username=MIKROTIK_USER,
                password=MIKROTIK_PASS,
                port=MIKROTIK_PORT,
                plaintext_login=True,
                use_ssl=False,
                #timeout=ROUTEROS_CONNECT_TIMEOUT
            )
            api = pool.get_api()  # get usable API object (not a context manager)
            LOG.info("Connected to MikroTik %s", MIKROTIK_HOST)
            return pool, api
        except Exception as exc:
            attempts += 1
            LOG.exception("RouterOS connection attempt %s failed: %s", attempts, exc)
            if attempts >= ROUTEROS_CONNECT_RETRY:
                raise
            LOG.info("Retrying RouterOS connection...")

def _resource_exists(api, path, lookup_key, lookup_value):
    """Utility: return True if resource at path with lookup exists."""
    try:
        res = api.get_resource(path)
        found = res.call('print', {f'?{lookup_key}': lookup_value})
        return bool(found)
    except Exception:
        return False

def set_or_create_hotspot_profile(api, profile_name, rate_limit):
    """
    Try to set rate-limit on an existing hotspot profile.
    If profile doesn't exist, create it. If router returns "action cancelled",
    log and return False (caller can fallback).
    """
    profiles = api.get_resource('/ip/hotspot/user/profile')
    try:
        # check existence
        #existing = profiles.call('print', {'?name': profile_name})
        existing = profiles.get(name=profile_name)

        if existing:
            LOG.info("Updating existing hotspot profile '%s' with rate-limit=%s", profile_name, rate_limit)
            # Use numbers param to set fields — find the .id of the profile
            profile_id = existing[0].get('.id')
            profiles.call('set', {'numbers': profile_id, 'rate-limit': rate_limit})
            return True
        else:
            LOG.info("Creating hotspot profile '%s' with rate-limit=%s", profile_name, rate_limit)
            profiles.call('add', {'name': profile_name, 'rate-limit': rate_limit})
            return True
    except Exception as exc:
        LOG.exception("Could not set/create hotspot profile '%s': %s", profile_name, exc)
        return False

def create_or_update_simple_queue(api, target_ip, max_limit):
    """
    Fallback when profile rate-limit not supported or you don't have profile control.
    Creates a queue named 'mpesa-<target_ip>' or updates it if exists.
    """
    try:
        queues = api.get_resource('/queue/simple')
        # attempt to find by target (exact match)
        #existing = queues.call('print', {'?target': target_ip})

        existing = queues.get(target=target_ip)
        if existing:
            qid = existing[0].get('.id')
            LOG.info("Updating simple queue for %s => %s", target_ip, max_limit)
            queues.call('set', {'numbers': qid, 'max-limit': max_limit})
        else:
            LOG.info("Adding simple queue for %s => %s", target_ip, max_limit)
            queues.call('add', {'name': f'mpesa-{target_ip}', 'target': target_ip, 'max-limit': max_limit})
        return True
    except Exception:
        LOG.exception("Failed to create/update simple queue for %s", target_ip)
        return False

def add_or_update_ip_binding(api, mac, ip=None, comment=None, binding_type='regular'):
    """
    Add or update an ip-binding for the MAC. binding_type usually 'regular' or 'bypassed'.
    If an entry for this MAC exists, update it; otherwise create new.
    """
    try:
        ipb = api.get_resource('/ip/hotspot/ip-binding')
        # Try to find by mac-address
        #found = ipb.call('print', {'?mac-address': mac})

        found = ipb.get(mac_address=mac)
        data = {'mac-address': mac, 'type': binding_type}
        if ip:
            data['address'] = ip
        if comment:
            data['comment'] = comment

        if found:
            bid = found[0].get('.id')
            LOG.info("Updating ip-binding %s (mac=%s)", bid, mac)
            data_to_set = data.copy()
            data_to_set['numbers'] = bid
            ipb.call('set', data_to_set)
        else:
            LOG.info("Adding ip-binding for mac=%s ip=%s", mac, ip)
            ipb.call('add', data)
        return True
    except Exception:
        LOG.exception("Failed to add/update ip-binding for mac=%s", mac)
        return False

def remove_ip_binding(api, mac=None, ip=None):
    """Remove ip-binding entries by mac or address."""
    try:
        ipb = api.get_resource('/ip/hotspot/ip-binding')
        if mac:
            #found = ipb.call('print', {'?mac-address': mac})

            found = ipb.get(mac_address=mac)
            for f in found:
                try:
                    ipb.call('remove', {'numbers': f.get('.id')})
                except Exception:
                    LOG.exception("Failed to remove ip-binding id %s", f.get('.id'))
        if ip:
            #found = ipb.call('print', {'?address': ip})

            found = ipb.get(address=ip)
            for f in found:
                try:
                    ipb.call('remove', {'numbers': f.get('.id')})
                except Exception:
                    LOG.exception("Failed to remove ip-binding id %s", f.get('.id'))
        return True
    except Exception:
        LOG.exception("remove_ip_binding failed")
        return False
    

def remove_other_active_sessions(api, username, except_mac):

    """
    Disconnect all other active hotspot sessions for this username, 
    leaving only the most recent connection.
    """
    try:
        active = api.get_resource('/ip/hotspot/active')
        all_sessions = active.call('print')  # fetch all, no filtering
        logging.info("Fetched %d active sessions", len(all_sessions))

        # Filter sessions for this username in Python
        user_sessions = [s for s in all_sessions if s.get('user') == username]

        if len(user_sessions) <= 1:
            logging.info("No extra active sessions for user %s", username)
            return

        # Sort by uptime or .id to remove older sessions (keep the last one)
        user_sessions.sort(key=lambda x: int(x.get('uptime', '0').split('s')[0]))  # optional
        # Remove all but the last session
        for session in user_sessions[:-1]:

            if except_mac and session.get('mac-address') == except_mac:
                logging.info("Skipping session %s (MAC %s) for user %s", session.get('.id'), except_mac, username)
                continue
            try:
                logging.info("Removing old session %s for user %s", session.get('.id'), username)
                active.call('remove', {'numbers': session.get('.id')})
            except Exception as e:
                logging.exception("Failed to remove session %s: %s", session.get('.id'), e)

    except Exception as e:
        logging.exception("Failed to fetch active sessions: %s", e)

'''
def remove_other_active_sessions(api, username=None, except_mac=None):
    """
    Enforce single-device: remove all active sessions for `username` except the one with except_mac.
    If username not provided but except_mac is, remove other sessions with same MAC? (not typical)
    """
    try:
        active = api.get_resource('/ip/hotspot/active')
        # fetch by user if available
        query = {}
        if username:
            query['?user'] = username
        active_sessions = active.call('print', query)
        logging.info("Active sessions for user %s: %s", username, active_sessions)

        for sess in active_sessions:
            sess_mac = sess.get('mac-address') or sess.get('mac-address') or sess.get('mac')
            sess_user = sess.get('user') or sess.get('user')
            if except_mac and sess_mac and sess_mac.lower() == except_mac.lower():
                # keep this session
                continue
            # remove others
            try:
                LOG.info("Removing active session %s (user=%s, mac=%s)", sess.get('.id'), sess_user, sess_mac)
                active.call('remove', {'numbers': sess.get('.id')})
            except Exception:
                LOG.exception("Failed to remove active session %s", sess.get('.id'))
        return True
    except Exception:
        LOG.exception("Failed to inspect/remove active sessions")
        return False
'''

def authorize_hotspot_user(mac, username, profile, duration_minutes, rate_limit, client_ip, single_device=True):
    """
    Universal authorize function:
    - ensures hotspot user exists (or creates it)
    - enforces single-device if single_device=True by removing other active sessions
    - creates/updates ip-binding for the mac (if provided)
    - attempts to apply rate_limit via profile or fallback queue (if client_ip provided)
    - returns dict: {ok:bool, message:str}
    """
    pool = api = None
    try:
        pool, api = connect_routeros()
        users = api.get_resource('/ip/hotspot/user')

        # 1) Ensure single-device: remove other active sessions for username (before adding new user)
        if single_device and username:
            try:
                LOG.info("Enforcing single-device: removing other sessions for user=%s", username)
                remove_other_active_sessions(api, username, mac)
            except Exception:
                LOG.exception("Non-fatal: failed to remove other sessions")

        # 2) Create user only if it doesn't exist. Use print ?name= to check.
        #exists = users.call('print', {'?name': username})
        exists = users.get(name=username)
        if exists:
            LOG.info("Hotspot user '%s' already exists. skipping add.", username)
            user_id = exists[0].get('.id')
        else:
            LOG.info("Creating hotspot user '%s' (profile=%s)", username, profile)
            add_args = {'name': username}
            # password can be empty for one-time username auth
            add_args['password'] = ''
            if profile:
                add_args['profile'] = profile
            # some RouterOS versions require different param names; supplying common ones
            try:
                users.call('add', add_args)
            except Exception as exc:
                LOG.exception("Failed to add hotspot user with add_args=%s : %s", add_args, exc)
                # Try alternate low-level add form
                try:
                    users.call('add', {'name': username, 'password': ''})
                except Exception:
                    raise

            # fetch again to get id
            #created = users.call('print', {'?name': username})
            created = users.get(name=username)
            user_id = created[0].get('.id') if created else None

        # 3) Set user uptime/limit if supported (best-effort)
        try:
            if user_id:
                # Some routers accept 'limit-uptime' or 'uptime' style fields — use 'limit-uptime' where possible
                LOG.info("Setting limit-uptime for user %s => %sm", username, duration_minutes)
                users.call('set', {'numbers': user_id, 'limit-uptime': f'{duration_minutes}m'})
        except Exception:
            LOG.exception("Setting limit-uptime failed; continuing")

        # 4) Add/Update ip-binding (optional but useful)
        if mac:
            try:
                LOG.info("Adding/updating ip-binding for mac=%s", mac)
                add_or_update_ip_binding(api, mac, ip=client_ip, comment=f"tx:{username}", binding_type='regular')
            except Exception:
                LOG.exception("ip-binding step failed; continuing")

        # 5) Apply rate limit: try profile update/creation first, fallback to simple queue if client_ip provided
        if rate_limit:
            try:
                LOG.info("Applying rate-limit %s for username=%s", rate_limit, username)
                ok = set_or_create_hotspot_profile(api, profile or f'auto-{rate_limit}', rate_limit)
                if not ok and client_ip:
                    LOG.info("Profile approach failed; trying simple queue fallback for IP %s", client_ip)
                    create_or_update_simple_queue(api, client_ip, rate_limit)
            except Exception:
                LOG.exception("Rate-limit application failed; continuing")

        LOG.info("✔ Hotspot user %s authorized successfully", username)
        return {"ok": True, "message": "authorized", "user_id": user_id}
    except Exception as exc:
        LOG.exception("Failed authorize user: %s", exc)
        return {"ok": False, "message": str(exc)}
    finally:
        try:
            if pool:
                pool.disconnect()
                LOG.info("Disconnected from MikroTik")
        except Exception:
            LOG.exception("Failed disconnecting RouterOS pool")

def remove_hotspot_user(username=None, mac=None):
    """
    Universal removal:
    - remove active session(s) for username or mac
    - remove static hotspot user entry (by name)
    - remove ip-binding entries for mac
    """
    pool = api = None
    try:
        pool, api = connect_routeros()

        active = api.get_resource('/ip/hotspot/active')
        users = api.get_resource('/ip/hotspot/user')
        ipb = api.get_resource('/ip/hotspot/ip-binding')

        # Remove active sessions
        if username:
            try:
                #sessions = active.call('print', {'?user': username})
                sessions = active.get(user=username)
                for s in sessions:
                    try:
                        active.call('remove', {'numbers': s.get('.id')})
                    except Exception:
                        LOG.exception("Failed to remove active session %s", s.get('.id'))
            except Exception:
                LOG.exception("Active session removal by username failed")

        if mac:
            try:
                #sessions = active.call('print', {'?mac-address': mac})

                sessions = active.get(mac_address=mac)
                for s in sessions:
                    try:
                        active.call('remove', {'numbers': s.get('.id')})
                    except Exception:
                        LOG.exception("Failed to remove active session %s", s.get('.id'))
            except Exception:
                LOG.exception("Active session removal by mac failed")

        # Remove static user
        if username:
            try:
                #found = users.call('print', {'?name': username})
                found = users.get(name=username)
                for f in found:
                    try:
                        users.call('remove', {'numbers': f.get('.id')})
                    except Exception:
                        LOG.exception("Failed to remove static user %s", f.get('.id'))
            except Exception:
                LOG.exception("Static user removal failed")

        # Remove ip-binding
        if mac:
            try:
                #bindings = ipb.call('print', {'?mac-address': mac})

                bindings = ipb.get(mac_address=mac)
                
                for b in bindings:
                    try:
                        ipb.call('remove', {'numbers': b.get('.id')})
                    except Exception:
                        LOG.exception("Failed to remove ip-binding %s", b.get('.id'))
            except Exception:
                LOG.exception("ip-binding removal failed")

        return {"ok": True}
    except Exception as exc:
        LOG.exception("Failed removing hotspot user: %s", exc)
        return {"ok": False, "message": str(exc)}
    finally:
        try:
            if pool:
                pool.disconnect()
        except Exception:
            pass



'''
import logging
from datetime import datetime, timedelta

# routeros_api may or may not be present; we handle it gracefully
try:
    import routeros_api
except Exception:
    routeros_api = None

# MIKROTIK_* variables are expected to be defined already in your module
# MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS, MIKROTIK_PORT, MIKROTIK_HOTSPOT_SERVER

LOG = logging.getLogger(__name__)

# -------------------------
# Core connection helper
# -------------------------
def connect_routeros_pool():
    """
    Returns (pool, api) where:
      - pool is RouterOsApiPool instance (must be disconnected after use)
      - api is the API connection object (not a context manager in some versions)
    Caller MUST call pool.disconnect() when done.
    """
    if routeros_api is None:
        raise RuntimeError("routeros_api library not installed")

    pool = None
    api = None
    try:
        pool = routeros_api.RouterOsApiPool(
            MIKROTIK_HOST,
            username=MIKROTIK_USER,
            password=MIKROTIK_PASS,
            port=MIKROTIK_PORT,
            plaintext_login=True,
            #use_tls=False,
            #auto_open=True,
        )
        # Older/newer versions differ: pool.get_api() returns the connection object
        api = pool.get_api()
        LOG.debug("Connected to RouterOS %s@%s:%s", MIKROTIK_USER, MIKROTIK_HOST, MIKROTIK_PORT)
        return pool, api
    except Exception:
        # ensure pool cleaned up if partially created
        try:
            if pool:
                pool.disconnect()
        except Exception:
            pass
        LOG.exception("Failed connecting to RouterOS")
        raise

# -------------------------
# Small utility for resource calls (tolerant to call signatures)
# -------------------------
def safe_resource_call(resource, cmd, params=None):
    """
    Try the two common calling styles:
      - resource.call('add', **params)
      - resource.call('add', params)
    Return the result or raise the last exception.
    """
    params = params or {}
    try:
        # first attempt keyword-style (works in many versions)
        return resource.call(cmd, **params)
    except TypeError as e1:
        try:
            # fallback: single dict param style
            return resource.call(cmd, params)
        except Exception as e2:
            LOG.exception("Both resource.call styles failed for %s with params=%s", cmd, params)
            raise

# -------------------------
# Find user helper
# -------------------------
def find_hotspot_user(api, username):
    users = api.get_resource('/ip/hotspot/user')
    # Try printing by name; some versions accept '?name' filter
    try:
        rows = users.call('print', {'?name': username})
    except Exception:
        try:
            rows = users.call('print', {'name': username})
        except Exception:
            # try fetching all and filter locally
            rows = users.call('print')
    # rows might be a list-like; return first match
    for r in rows or []:
        if r.get('name') == username or r.get('user') == username or r.get('.id') == username:
            return r
    # last-ditch check:
    for r in rows or []:
        if r.get('name') == username:
            return r
    return None

# -------------------------
# Authorize hotspot user (universal)
# -------------------------
def authorize_hotspot_user(mac, username, profile, duration_minutes, rate_limit):
    """
    Add or update a hotspot user and optionally add an IP-binding (MAC lock).
    - mac: MAC address string (optional)
    - username: unique username (we recommend use transaction_uuid)
    - profile: mikrotik hotspot profile name (preferred way to assign speed)
    - duration_minutes: time to grant access
    - rate_limit: optional, e.g. '2M/2M' — if provided we attempt to apply via user profile or simple queue
    Returns True on success, False on failure.
    """
    if routeros_api is None:
        LOG.error("routeros_api not installed; cannot authorize hotspot user")
        return False

    pool = None
    try:
        pool, api = connect_routeros_pool()
        users = api.get_resource('/ip/hotspot/user')
        ipb = api.get_resource('/ip/hotspot/ip-binding')
        LOG.info("Authorizing hotspot user %s (mac=%s) profile=%s duration=%s", username, mac, profile, duration_minutes)

        # 1) If user exists, update profile / expiry; else add
        existing = None
        try:
            existing = find_hotspot_user(api, username)
        except Exception:
            LOG.exception("Error finding existing hotspot user; continuing to attempt add")

        if existing:
            LOG.info("Hotspot user %s already exists; updating profile/expiry", username)
            # find identifier .id to use in set call
            numbers = existing.get('.id') or existing.get(' .id') or existing.get('id') or username
            set_params = {"numbers": numbers}
            if profile:
                set_params['profile'] = profile
            # some RouterOS versions support 'limit-uptime' or 'expires-after'
            set_params['limit-uptime'] = f"{duration_minutes}m"
            try:
                # safe set call
                try:
                    users.call('set', **set_params)
                except TypeError:
                    users.call('set', set_params)
                LOG.info("Updated existing user %s", username)
            except Exception:
                LOG.exception("Failed to update existing user %s", username)
        else:
            LOG.info("Creating hotspot user %s", username)
            add_args = {
                "name": username,
                "password": "",   # leave empty for hotspot one-time username auth
            }
            if profile:
                add_args['profile'] = profile
            # comment to help identify
            add_args['comment'] = f"tx:{username}"

            # try adding
            try:
                safe_resource_call(users, 'add', add_args)
                LOG.info("Hotspot user %s added", username)
            except routeros_api.exceptions.RouterOsApiCommunicationError as e:
                # if 'already have user' error race occurred, log and continue
                LOG.warning("Add user failed with RouterOS error; will try to locate existing user: %s", e)
                existing = find_hotspot_user(api, username)
                if not existing:
                    raise

        # 2) Ensure expiry / limit-uptime is set (best-effort)
        try:
            found = find_hotspot_user(api, username)
            if found:
                rid = found.get('.id') or found.get(' .id') or found.get('id')
                try:
                    set_params = {"numbers": rid, "limit-uptime": f"{duration_minutes}m"}
                    try:
                        users.call('set', **set_params)
                    except TypeError:
                        users.call('set', set_params)
                    LOG.info("Set expiry/limit-uptime for user %s -> %sm", username, duration_minutes)
                except Exception:
                    LOG.exception("Failed to set expiry via users.set for %s", username)
        except Exception:
            LOG.exception("Error ensuring expiry for user %s", username)

        # 3) Add IP-binding (MAC lock) if mac provided
        if mac:
            try:
                # check if binding exists
                exists_bind = None
                try:
                    exists_list = ipb.call('print', {'?mac-address': mac})
                except Exception:
                    exists_list = ipb.call('print')
                for b in exists_list or []:
                    if b.get('mac-address', '').lower() == mac.lower():
                        exists_bind = b
                        break

                if exists_bind:
                    LOG.info("IP-binding already exists for MAC %s, skipping add", mac)
                else:
                    bind_args = {"mac-address": mac, "type": "regular", "comment": f"tx:{username}"}
                    try:
                        safe_resource_call(ipb, 'add', bind_args)
                        LOG.info("Added IP-binding for MAC %s", mac)
                    except Exception:
                        LOG.exception("Failed to add IP-binding for %s", mac)
            except Exception:
                LOG.exception("IP-binding step failed for mac %s", mac)

        # 4) OPTIONAL: rate-limit fallback — try to ensure profile has rate-limit (preferred),
        # otherwise you could create a simple-queue if you know the client's IP (not available always).
        if rate_limit:
            LOG.info("Rate-limit provided (%s). Best practice: create a hotspot profile with this rate and reference it in plan.", rate_limit)
            # If you want to create a simple queue you need the IP of the client.
            # We skip auto queue creation here because client's IP may not be known.
            # If the user's session has an IP (not available here), you can create /queue/simple add target=1.2.3.4 max-limit=rate_limit
            # This is left as a manual step or a separate endpoint when you know the IP.

        # success
        pool.disconnect()
        LOG.info("✔ Hotspot user %s authorized successfully", username)
        return True

    except Exception as e:
        LOG.exception("Failed authorize user: %s", e)
        try:
            if pool:
                pool.disconnect()
        except Exception:
            pass
        return False

# -------------------------
# Remove hotspot user + cleanup (universal)
# -------------------------
def remove_hotspot_user(username=None, mac=None):
    """
    Remove hotspot user + active session + ip-binding.
    Provide either username or mac (or both).
    Returns True if operations completed (best-effort).
    """
    if routeros_api is None:
        LOG.error("routeros_api not installed; cannot remove hotspot user")
        return False

    pool = None
    ok = True
    try:
        pool, api = connect_routeros_pool()
        users = api.get_resource('/ip/hotspot/user')
        active = api.get_resource('/ip/hotspot/active')
        ipb = api.get_resource('/ip/hotspot/ip-binding')

        LOG.info("Removing hotspot user username=%s mac=%s", username, mac)

        # 1) Remove active sessions by username and/or mac
        try:
            if username:
                try:
                    active_items = active.call('print', {'?user': username})
                except Exception:
                    active_items = active.call('print')
                for it in active_items or []:
                    nid = it.get('.id')
                    try:
                        active.call('remove', {'numbers': nid})
                        LOG.info("Removed active session %s for user %s", nid, username)
                    except Exception:
                        LOG.exception("Failed removing active session %s", nid)
            if mac:
                try:
                    active_items = active.call('print', {'?mac-address': mac})
                except Exception:
                    active_items = active.call('print')
                for it in active_items or []:
                    nid = it.get('.id')
                    try:
                        active.call('remove', {'numbers': nid})
                        LOG.info("Removed active session %s for mac %s", nid, mac)
                    except Exception:
                        LOG.exception("Failed removing active session %s", nid)
        except Exception:
            LOG.exception("Error while removing active sessions")

        # 2) Remove static hotspot user entry(s)
        try:
            if username:
                # find user entries
                try:
                    rows = users.call('print', {'?name': username})
                except Exception:
                    rows = users.call('print')
                for u in rows or []:
                    if u.get('name') == username:
                        try:
                            users.call('remove', {'numbers': u.get('.id')})
                            LOG.info("Removed hotspot user %s", username)
                        except Exception:
                            LOG.exception("Failed to remove hotspot user %s", username)
        except Exception:
            LOG.exception("Error removing static hotspot user")

        # 3) Remove ip-binding entries by mac
        try:
            if mac:
                try:
                    binds = ipb.call('print', {'?mac-address': mac})
                except Exception:
                    binds = ipb.call('print')
                for b in binds or []:
                    if b.get('mac-address', '').lower() == mac.lower():
                        try:
                            ipb.call('remove', {'numbers': b.get('.id')})
                            LOG.info("Removed ip-binding for %s", mac)
                        except Exception:
                            LOG.exception("Failed removing ip-binding %s", mac)
        except Exception:
            LOG.exception("Error removing ip-binding entries")

        pool.disconnect()
        return ok

    except Exception as e:
        LOG.exception("Failed to remove hotspot user: %s", e)
        try:
            if pool:
                pool.disconnect()
        except Exception:
            pass
        return False


def connect_routeros():
    """
    Safely create API pool and return pool + API connection.
    Works for RouterOS v6 and v7.
    """
    try:
        api_pool = routeros_api.RouterOsApiPool(
            host=MIKROTIK_HOST,
            username=MIKROTIK_USER,
            password=MIKROTIK_PASS,
            port=MIKROTIK_PORT,
            plaintext_login=True
        )
        api = api_pool.get_api()
        logging.info("Connected to MikroTik")
        return api_pool, api
    except Exception as e:
        logging.exception("❌ MikroTik connection failed: %s", e)
        return None, None


def authorize_hotspot_user(mac, username, profile, duration_minutes, rate_limit):
    """
    Universally creates a hotspot user, assigns plan, uptime and MAC-binding.
    Works on RouterOS v6 and v7.
    """
    try:
        pool, api = connect_routeros()
        if not api:
            return False

        users = api.get_resource('/ip/hotspot/user')
        ipb   = api.get_resource('/ip/hotspot/ip-binding')

        logging.info(f"🔵 Creating hotspot user: {username}")

        # -------- BUILD USER ARGS -------- #
        add_args = {
            "name": username,
            "password": "",
            "comment": f"tx:{username}",
        }

        if profile:
            add_args["profile"] = profile

        # Universal add format
        users.call("add", add_args)

        # -------- APPLY LIMIT-UPTIME -------- #
        logging.info(f"⏳ Setting user uptime: {duration_minutes} minutes")

        set_args = {
            "numbers": username,
            "limit-uptime": f"{duration_minutes}m"
        }

        users.call("set", set_args)

        # -------- APPLY RATE LIMIT -------- #
        if rate_limit:
            try:
                logging.info(f"🚀 Applying rate-limit {rate_limit} to {username}")
                users.call("set", {
                    "numbers": username,
                    "rate-limit": rate_limit
                })
            except Exception:
                logging.warning("⚠ RouterOS version does not support rate-limit directly")

        # -------- MAC BINDING -------- #
        if mac:
            logging.info(f"🔗 Adding MAC binding for {mac}")
            try:
                ipb.call("add", {
                    "mac-address": mac,
                    "type": "bypassed",
                    "comment": f"tx:{username}"
                })
            except Exception as e:
                logging.warning(f"⚠ MAC binding failed: {e}")

        pool.disconnect()
        logging.info(f"✔ Hotspot user {username} authorized successfully")
        return True

    except Exception as e:
        logging.exception("❌ Failed to authorize user: %s", e)
        return False


def remove_hotspot_user(username=None, mac=None):
    """
    Universally removes hotspot user, active sessions, and MAC bindings.
    Compatible with RouterOS v6 + v7.
    """
    try:
        pool, api = connect_routeros()
        if not api:
            return False

        users  = api.get_resource('/ip/hotspot/user')
        active = api.get_resource('/ip/hotspot/active')
        ipb    = api.get_resource('/ip/hotspot/ip-binding')

        # ----- REMOVE ACTIVE SESSION ----- #
        if username:
            logging.info(f"🧹 Removing active session for user {username}")
            for session in active.call("print", {"?user": username}):
                active.call("remove", {"numbers": session[".id"]})

        if mac:
            logging.info(f"🧹 Removing active session for MAC {mac}")
            for session in active.call("print", {"?mac-address": mac}):
                active.call("remove", {"numbers": session[".id"]})

        # ----- REMOVE STATIC USER ----- #
        if username:
            logging.info(f"🗑 Removing static user {username}")
            for u in users.call("print", {"?name": username}):
                users.call("remove", {"numbers": u[".id"]})

        # ----- REMOVE MAC BINDING ----- #
        if mac:
            logging.info(f"🧹 Removing MAC binding {mac}")
            for b in ipb.call("print", {"?mac-address": mac}):
                ipb.call("remove", {"numbers": b[".id"]})

        pool.disconnect()
        logging.info(f"✔ User {username} removed cleanly")
        return True

    except Exception as e:
        logging.exception("❌ Failed to remove hotspot user: %s", e)
        return False

'''
    

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

'''
# -------------------------
# Background reconciler
# -------------------------

def reconcile_pending_transactions():
    logging.info("Background reconciler running")
    pending = get_pending_transactions(older_than_seconds=20)  # check pending older than 20s
    for tx in pending:
        try:
            logging.info("Reconciling tx %s", tx['transaction_uuid'])
            # If we have a checkout_request_id, run STK query
            if tx.get('checkout_request_id'):
                res = stk_query(tx['checkout_request_id'])
                if res and res.get('ResultCode') == 0:
                    # success; mark transaction success and grant access
                    mark_transaction_success(tx['transaction_uuid'], mpesa_receipt=(res.get('Result') or {}).get('MpesaReceiptNumber'))
                    # grant access to hotspot
                    plan = get_plan_by_id(tx['plan_id'])
                    duration = plan['duration_minutes'] if plan else 60
                    # Use username as transaction_uuid for uniqueness
                    authorize_hotspot_user(tx.get('mac') or '', tx['transaction_uuid'], plan.get('mikrotik_profile') if plan else '', duration)
                elif res and res.get('ResultCode') not in (0, 1):
                    # non success
                    mark_transaction_failed(tx['transaction_uuid'])
            else:
                # If no checkout id available, attempt to use merchant_request_id or skip
                logging.info("No checkout_request_id for tx %s — skipping STK query", tx['transaction_uuid'])
        except Exception as exc:
            logging.exception("Error reconciling tx: %s", exc)

    # schedule next run
    threading.Timer(25, reconcile_pending_transactions).start()

 # start background reconciler after short delay
threading.Timer(5, reconcile_pending_transactions).start() 
'''

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
                authorize_hotspot_user(mac, tx_id, profile, duration, rate_limit, client_ip)
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


# Start first run after 5 seconds




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

    try:
        stk_response = stk_push(phone, amount, tx_uuid, hotspot_data=hotspot_data)
    except Exception as e:
        logging.exception("stk push failed: %s", e)
        return jsonify({"error": str(e)}), 500

    # Return the raw STK response to frontend (keeps original contract)
    return jsonify(stk_response)
    #HOTSPOT_GATEWAY_IP = '10.0.0.1'
    #return auto_login_html(tx_uuid, f"http://{HOTSPOT_GATEWAY_IP}/login")


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
                plan = get_plan_by_id(tx['plan_id'])
                duration = plan['duration_minutes'] if plan else 1
                # authorize on Mikrotik
                authorize_hotspot_user(tx.get('mac') or '', transaction_uuid, plan.get('mikrotik_profile') if plan else '', duration, plan.get("rate_limit") if plan else None, tx.get('ip') or ''  )


                # store in hotspot_users table
                conn = get_connection()
                cur = conn.cursor()
                expires_at = datetime.now() + timedelta(minutes=duration)
                cur.execute("""
                    INSERT INTO hotspot_users (transaction_uuid, mac, username, mikrotik_profile, expires_at, client_ip)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (transaction_uuid, tx.get('mac'), transaction_uuid, plan.get('mikrotik_profile') if plan else '', expires_at, tx.get('ip')))
                conn.commit()
                cur.close()
                conn.close()
                
            logging.info("Payment SUCCESS for tx %s", transaction_uuid)
        else:
            # failed/cancelled
            mark_transaction_failed(transaction_uuid)
            logging.info("Payment FAILED: %s", result_desc)
    except Exception as e:
        logging.exception("Error handling callback: %s", e)

    return jsonify(response), 200
    

# Endpoint to query STK status manually

@app.route('/query_stk', methods=['POST', 'GET'])
def query_stk_route():
    data = request.get_json() or {}
    checkout_id = data.get('checkout_request_id')
    if not checkout_id:
        return jsonify({"error":"checkout_request_id required"}), 400
    res = stk_query(checkout_id)
    return jsonify(res or {"error":"query failed"})

# -------------------------
# Hotspot control endpoints
# -------------------------
@app.route('/hotspot/disconnect', methods=['POST'])
def hotspot_disconnect():
    data = request.get_json() or {}
    mac = data.get('mac')
    username = data.get('username')
    if not mac and not username:
        return jsonify({"error":"mac or username required"}), 400
    ok = remove_hotspot_user(username=username, mac=mac)
    return jsonify({"ok": ok})

@app.route('/hotspot/check_active/<username>', methods=['GET'])
def hotspot_check_active(username):
    # This tries to see if a user is in active sessions (best-effort)
    if routeros_api is None:
        return jsonify({"error":"routeros_api not installed"}), 500
    try:
        api = connect_routeros()
        with api.get_api() as api_conn:
            active = api_conn.get_resource('/ip/hotspot/active').call('print', {'?user': username})
        api.disconnect()
        return jsonify({"active": bool(active)})
    except Exception as e:
        logging.exception("check active failed: %s", e)
        return jsonify({"error": str(e)}), 500

# -------------------------
# Start Flask
# -------------------------
if __name__ == '__main__':
    if not os.getenv("WERKZEUG_RUN_MAIN"):  # Only start in main process, not reloader
        threading.Timer(5, reconcile_pending_transactions).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
