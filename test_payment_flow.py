#!/usr/bin/env python3
"""
Test PhonePe payment initiation with corrected signature
"""
import requests
import json

# Base URL
BASE_URL = "http://localhost:8001/api"

print("=" * 80)
print("Testing PhonePe Payment Integration")
print("=" * 80)

# Step 1: Create an order
print("\n[1/3] Creating test order...")
order_data = {
    "product_id": "test_product_1",
    "product_name": "Test Product",
    "amount": 999.99
}

response = requests.post(f"{BASE_URL}/orders", json=order_data)
if response.status_code == 200:
    order = response.json()
    order_id = order['order_id']
    print(f"✅ Order created successfully!")
    print(f"   Order ID: {order_id}")
    print(f"   Amount: ₹{order['unique_amount']}")
    print(f"   Status: {order['status']}")
else:
    print(f"❌ Failed to create order: {response.status_code}")
    print(response.text)
    exit(1)

# Step 2: Initiate payment
print(f"\n[2/3] Initiating PhonePe payment for order {order_id}...")
payment_data = {
    "order_id": order_id
}

response = requests.post(f"{BASE_URL}/payment/initiate", json=payment_data)
print(f"Response status: {response.status_code}")
print(f"Response body: {response.text[:500]}")

if response.status_code == 200:
    payment = response.json()
    print(f"✅ Payment initiated successfully!")
    print(f"   Transaction ID: {payment.get('transaction_id', 'N/A')}")
    print(f"   Payment URL: {payment.get('payment_url', 'N/A')[:100]}...")
    print(f"   Message: {payment.get('message', 'N/A')}")
    
    # Step 3: Check payment status
    print(f"\n[3/3] Checking payment status...")
    response = requests.get(f"{BASE_URL}/payment/status/{order_id}")
    if response.status_code == 200:
        status = response.json()
        print(f"✅ Status check successful!")
        print(f"   Status: {status.get('status', 'N/A')}")
        print(f"   Message: {status.get('message', 'N/A')}")
    else:
        print(f"⚠️  Status check failed: {response.status_code}")
        print(response.text)
else:
    print(f"❌ Payment initiation failed!")
    print(f"   Error: {response.text}")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
