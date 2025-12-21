# payments/mpesa_base.py
import base64
import requests
from datetime import datetime

class MpesaBase:
    def __init__(self, consumer_key, consumer_secret, environment):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.environment = environment

        if environment == "PRODUCTION":
            self.token_url = "https://api.safaricom.co.ke/oauth/v1/generate"
            self.stk_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        else:
            self.token_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
            self.stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    def get_access_token(self):
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()

        r = requests.get(
            f"{self.token_url}?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}"},
            timeout=10
        )
        r.raise_for_status()
        return r.json()["access_token"]
