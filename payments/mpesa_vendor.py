# payments/mpesa_vendor.py
import base64
from datetime import datetime
from payments.mpesa_base import MpesaBase
import logging
import requests

class VendorMpesaService(MpesaBase):
    def __init__(
        self,
        business_shortcode,
        passkey,
        consumer_key,
        consumer_secret,
        environment,
        transaction_updater
    ):
        super().__init__(consumer_key, consumer_secret, environment)

        self.business_shortcode = business_shortcode
        self.passkey = passkey
        self.update_transaction = transaction_updater

    def stk_push(self, transaction_uuid, phone, amount, callback_url, account_reference, description):
        token = self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        password = base64.b64encode(
            f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": self.business_shortcode,
            "PhoneNumber": phone,
            "CallBackURL": callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": description
        }

        r = requests.post(
            self.stk_url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )

        r.raise_for_status()
        data = r.json()

    
        logging.info(
        "STK push sent tx=%s checkout=%s",
        transaction_uuid,
        data.get("CheckoutRequestID")
)


        # Save MerchantRequestID / CheckoutRequestID if available
        merchant_id = data.get("MerchantRequestID")
        checkout_id = data.get("CheckoutRequestID")

        if merchant_id or checkout_id:
            try:
                self.update_transaction(transaction_uuid, merchant_id, checkout_id)
            except Exception:
                logging.exception("Failed to save stk ids")

        return data
