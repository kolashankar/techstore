#!/usr/bin/env python3
"""
Debug PhonePe API request to understand the exact issue
"""

import json
import base64
import hashlib
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# PhonePe Configuration
PHONEPE_MERCHANT_ID = os.environ.get('PHONEPE_MERCHANT_ID', 'M23HX1NJIDUCT_2601152130')
PHONEPE_SALT_KEY = os.environ.get('PHONEPE_SALT_KEY', 'YTM3YjQwMjEtNGE5Yy00ZTA2LTg5Y2QtYzJjNDM5ZjA3N2Zh')
PHONEPE_SALT_INDEX = int(os.environ.get('PHONEPE_SALT_INDEX', '1'))
PHONEPE_ENV = os.environ.get('PHONEPE_ENV', 'production')

print("=== PhonePe Configuration Debug ===")
print(f"Merchant ID: {PHONEPE_MERCHANT_ID}")
print(f"Salt Key: {PHONEPE_SALT_KEY}")
print(f"Salt Index: {PHONEPE_SALT_INDEX}")
print(f"Environment: {PHONEPE_ENV}")
print()

# PhonePe API URLs
if PHONEPE_ENV == 'sandbox':
    PHONEPE_BASE_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox"
else:
    PHONEPE_BASE_URL = "https://api.phonepe.com/apis/pg"

print(f"Base URL: {PHONEPE_BASE_URL}")
print()

def generate_phonepe_checksum(payload: str, endpoint: str) -> str:
    """Generate PhonePe checksum/signature"""
    string_to_hash = payload + endpoint + PHONEPE_SALT_KEY
    print(f"String to hash: {string_to_hash}")
    sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
    print(f"SHA256 hash: {sha256_hash}")
    checksum = sha256_hash + "###" + str(PHONEPE_SALT_INDEX)
    print(f"Final checksum: {checksum}")
    return checksum

# Test payload
merchant_transaction_id = "MT1737048000000"
amount_in_paise = 99936  # 999.36 * 100

payload_data = {
    "merchantId": PHONEPE_MERCHANT_ID,
    "merchantTransactionId": merchant_transaction_id,
    "merchantUserId": "USER_ORD-A4504B2F",
    "amount": amount_in_paise,
    "redirectUrl": "https://phonepe-gateway-2.preview.emergentagent.com/api/payment/callback",
    "redirectMode": "POST",
    "callbackUrl": "https://phonepe-gateway-2.preview.emergentagent.com/api/payment/callback",
    "mobileNumber": "9999999999",
    "paymentInstrument": {
        "type": "PAY_PAGE"
    }
}

print("=== Request Payload ===")
payload_json = json.dumps(payload_data)
print(f"JSON payload: {payload_json}")

payload_base64 = base64.b64encode(payload_json.encode()).decode()
print(f"Base64 payload: {payload_base64}")
print()

# Generate checksum
endpoint = "/pg/v1/pay"
print(f"Endpoint: {endpoint}")

print("\n=== Checksum Generation ===")
checksum = generate_phonepe_checksum(payload_base64, endpoint)
print()

# Prepare request
headers = {
    "Content-Type": "application/json",
    "X-VERIFY": checksum
}

api_payload = {
    "request": payload_base64
}

phonepe_url = f"{PHONEPE_BASE_URL}{endpoint}"

print("=== Final Request ===")
print(f"URL: {phonepe_url}")
print(f"Headers: {headers}")
print(f"Request body: {api_payload}")
print()

# Make the request
print("=== Making Request ===")
try:
    response = requests.post(phonepe_url, json=api_payload, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.headers.get('content-type', '').startswith('application/json'):
        try:
            response_data = response.json()
            print(f"Parsed JSON: {json.dumps(response_data, indent=2)}")
        except:
            print("Failed to parse JSON response")
            
except Exception as e:
    print(f"Request failed: {str(e)}")