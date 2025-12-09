def tests():
    x = {
  "CheckoutRequestID": "ws_CO_07122025175117515712083124",
  "CustomerMessage": "Success. Request accepted for processing",
  "MerchantRequestID": "1a19-423e-be39-c093844fb0c45522",
  "ResponseCode": "0",
  "ResponseDescription": "Success. Request accepted for processing"
}
    print(x['CustomerMessage'])
tests()