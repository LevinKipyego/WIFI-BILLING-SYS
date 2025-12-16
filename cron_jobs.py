from app import get_pending_transactions, mark_transaction_failed, \
    mark_transaction_success, stk_query, update_last_query_time, \
    update_query_count, get_plan_by_id
    
from flask_db import get_connection
import threading
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

def expire_hotspot_users():
    logging.info(f"⏰ Expire Hotspot Users Job started at {datetime.now()}")
    try:
        conn = get_connection()
        cur = conn.cursor()

        sql = """
        UPDATE hotspot_users
        SET session_status = 'expired'
        WHERE expires_at <= NOW()
          AND session_status = 'active';
        """
        cur.execute(sql)
        conn.commit()

        logging.info(f"[Cron] Expired accounts updated at {datetime.now()}")

        cur.close()
        conn.close()

    except Exception as e:
        logging.exception(f"[Cron] Error updating expired users: {e}")



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




def run_cron_jobs():
    try:
        reconcile_pending_transactions()
        expire_hotspot_users()
    except Exception as e:
        logging.exception(f"Cron error: {e}")
    finally:
        # schedule next run after 60 seconds
        threading.Timer(60, run_cron_jobs).start()

