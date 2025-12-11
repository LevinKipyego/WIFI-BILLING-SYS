import logging
import os
from dotenv import load_dotenv

load_dotenv()
mikrotik_config={
    "HOTSPOT_LOGIN_URL": f"http://10.0.0.1/login",   # MikroTik hotspot login endpoint
    "MIKROTIK_HOST": os.getenv("MIKROTIK_HOST"),
    "MIKROTIK_USER": os.getenv("MIKROTIK_USER"),
    "MIKROTIK_PASS": os.getenv("MIKROTIK_PASS"),
    "MIKROTIK_PORT": int(os.getenv("MIKROTIK_PORT", "8728")),
    "MIKROTIK_USE_SSL": False,
    "MIKROTIK_HOTSPOT_SERVER": os.getenv("MIKROTIK_HOTSPOT_SERVER", "")
}

# --------------------------------------------------------------------
### ---------- Helper: connect to MikroTik RouterOS API ----------

try:
    from routeros_api import RouterOsApiPool
except Exception:
    RouterOsApiPool = None

def get_mikrotik_api():
    # returns a RouterOS API connection (remember to call disconnect() when done)
    api = RouterOsApiPool(mikrotik_config["MIKROTIK_HOST"],\
                           username=mikrotik_config["MIKROTIK_USER"],\
                           password=mikrotik_config["MIKROTIK_PASS"],\
                           use_ssl=mikrotik_config["MIKROTIK_USE_SSL"],\
                           plaintext_login=True,\
                           port=mikrotik_config["MIKROTIK_PORT"]).get_api()
                           
    return api

### ---------- Helper: query MikroTik active hotspot sessions ----------

def _ensure_api(api_conn):
    """
    Normalizes an API connection object (RouterOsApiPool vs. direct API object).
    """
    try:
        # If it has a get_api method (like RouterOsApiPool), use it.
        if hasattr(api_conn, "get_api") and callable(api_conn.get_api):
            return api_conn.get_api()
        # Otherwise, assume it is already the API object.
        return api_conn
    except Exception as e:
        # Fallback in case of unexpected connection error
        logging.warning("Failed to normalize API connection: %s", e)
        return api_conn

def find_active_session_by_username(api_conn, identity_value):
    """
    Finds an active hotspot session by either the 'user' field (username/RADIUS ID)
    or the 'mac-address' field.

    Args:
        api_conn: The MikroTik API connection object or pool.
        identity_value: The username (e.g., phone number) or MAC address to search for.

    Returns:
        The active session dictionary or None.
    """
    try:
        api = _ensure_api(api_conn)
        resource = api.get_resource("/ip/hotspot/active")
        
        # 1. Search by 'user' (This is the primary field for username/RADIUS ID in V6)
        try:
            sessions = resource.get(user=identity_value)
            if sessions:
                logging.info(f"Found active session by user: {identity_value}")
                return _normalize_session(sessions[0])
        except Exception as e:
            logging.debug(f"Search by 'user' failed or returned empty: {e}")

        # 2. Search by 'mac-address' (Fallback, especially useful if MAC is used as identity)
        # Note: RouterOS API field names use hyphens, not underscores.
        try:
            sessions = resource.get(**{'mac-address': identity_value})
            if sessions:
                logging.info(f"Found active session by mac-address: {identity_value}")
                return _normalize_session(sessions[0])
        except Exception as e:
            logging.debug(f"Search by 'mac-address' failed or returned empty: {e}")
            
        logging.info(f"No active session found for identity: {identity_value}")
        return None

    except Exception as e:
        logging.error("Critical error accessing /ip/hotspot/active resource.", exc_info=True)
        return None

def _normalize_session(session):
    """
    Normalizes the ID field across different RouterOS API responses.
    """
    # Prefer '.id' which is standard in recent routeros-api usage
    session['internal_id'] = (
        session.get('.id') or
        session.get('*id') or
        session.get('id')
    )
    return session



def remove_active_session_by_id(api_conn, session):
    """
    Removes a hotspot session safely using its internal ID.
    
    'session' can be:
        - dictionary returned by find_active_session
        - raw .id string
        - ID format from RouterOS v6/v7

    Handles both normalized (internal_id) and raw ID formats.
    """

    try:
        # Use the normalized API object retrieval
        api = _ensure_api(api_conn)
        resource = api.get_resource("/ip/hotspot/active")

        # Accept multiple input forms (dict, id string)
        if isinstance(session, dict):
            # Prioritize the normalized ID
            mik_id = (
                session.get('internal_id') or
                session.get('.id') or
                session.get('id') or
                session.get('*id')
            )
        else:
            # Assume it's a raw ID string
            mik_id = session

        if not mik_id:
            logging.warning("Attempted to remove session, but no valid ID found.")
            return False

        # The routeros-api wrapper typically maps the 'id' keyword argument to '.id' internally.
        resource.remove(id=mik_id)
        logging.info(f"Successfully removed hotspot session with ID: {mik_id}")
        return True

    except Exception as e:
        logging.exception(f"Error removing hotspot session with ID {mik_id}: {e}")
        return False
