import logging
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

RADIUS_DB = {
    "host": os.getenv("RADIUS_DB_HOST", "localhost"),
    "user": os.getenv("RADIUS_DB_USER", "root"),
    "password": os.getenv("RADIUS_DB_PASS", ""),
    "database": os.getenv("RADIUS_DB_NAME", "radius")
}

# --- FreeRADIUS DB helpers ---
def get_radius_connection():
    return mysql.connector.connect(**RADIUS_DB)




### ---------- Helper: upsert radcheck & radreply ----------
def upsert_radcheck(username, password):
    conn = get_radius_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # check if Cleartext-Password exists
        cur.execute("SELECT id, value FROM radcheck WHERE username=%s AND attribute='Cleartext-Password'", (username,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE radcheck SET value=%s WHERE id=%s", (password, row['id']))
        else:
            cur.execute("INSERT INTO radcheck (username, attribute, op, value) VALUES (%s,'Cleartext-Password',':=',%s)", (username, password))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logging.exception("Failed to upsert radcheck")
        return False
    finally:
        cur.close()
        conn.close()

def upsert_radreply(username, attribute, value):
    conn = get_radius_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM radreply WHERE username=%s AND attribute=%s", (username, attribute))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE radreply SET value=%s WHERE id=%s", (value, row['id']))
        else:
            cur.execute("INSERT INTO radreply (username, attribute, op, value) VALUES (%s, %s, ':=', %s)", (username, attribute, value))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logging.exception("Failed to upsert radreply")
        return False
    finally:
        cur.close()
        conn.close()