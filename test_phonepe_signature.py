#!/usr/bin/env python3
"""
Test PhonePe signature generation with correct credentials
"""
import hashlib
import json
import base64

# Test credentials
PHONEPE_MERCHANT_ID = "PGTESTPAYUAT"
PHONEPE_SALT_KEY = "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399"
PHONEPE_SALT_INDEX = 1

def generate_phonepe_checksum_correct(payload_base64: str, endpoint: str) -> str:
    """
    Generate PhonePe checksum/signature (X-VERIFY header)
    Correct Formula per PhonePe docs:
    1. payload_hash = SHA256(base64_payload)
    2. base_string = endpoint + payload_hash
    3. signature_string = base_string + "###" + salt_index + salt_key
    4. X-VERIFY = SHA256(signature_string) + "###" + salt_index
    """
    # Step 1: Hash the base64 payload
    payload_hash = hashlib.sha256(payload_base64.encode()).hexdigest()
    
    # Step 2: Create base string
    base_string = endpoint + payload_hash
    
    # Step 3: Append salt info
    signature_string = base_string + "###" + str(PHONEPE_SALT_INDEX) + PHONEPE_SALT_KEY
    
    # Step 4: Hash and format final checksum
    final_hash = hashlib.sha256(signature_string.encode()).hexdigest()
    checksum = final_hash + "###" + str(PHONEPE_SALT_INDEX)
    
    return checksum

# Test payload
payload_data = {
    "merchantId": PHONEPE_MERCHANT_ID,
    "merchantTransactionId": "MT1737000000001",
    "merchantUserId": "USER_ORD12345",
    "amount": 10000,
    "redirectUrl": "https://techstore-4riw.onrender.com/api/payment/callback",
    "redirectMode": "POST",
    "callbackUrl": "https://techstore-4riw.onrender.com/api/payment/callback",
    "mobileNumber": "9999999999",
    "paymentInstrument": {
        "type": "PAY_PAGE"
    }
}

# Generate base64 payload
payload_json = json.dumps(payload_data)
payload_base64 = base64.b64encode(payload_json.encode()).decode()

# Generate checksum
endpoint = "/pg/v1/pay"
checksum = generate_phonepe_checksum_correct(payload_base64, endpoint)

print("=" * 80)
print("PhonePe Signature Generation Test")
print("=" * 80)
print(f"\nMerchant ID: {PHONEPE_MERCHANT_ID}")
print(f"Salt Key: {PHONEPE_SALT_KEY}")
print(f"Salt Index: {PHONEPE_SALT_INDEX}")
print(f"\nEndpoint: {endpoint}")
print(f"\nPayload (JSON):")
print(json.dumps(payload_data, indent=2))
print(f"\nPayload (Base64):")
print(payload_base64[:100] + "..." if len(payload_base64) > 100 else payload_base64)
print(f"\nGenerated X-VERIFY Header:")
print(checksum)
print(f"\nAPI Request:")
print(f"POST https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay")
print(f"Headers:")
print(f"  Content-Type: application/json")
print(f"  X-VERIFY: {checksum}")
print(f"Body:")
print(json.dumps({"request": payload_base64}, indent=2))
print("=" * 80)
