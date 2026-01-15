# Payment Gateway Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER JOURNEY                                │
└─────────────────────────────────────────────────────────────────────┘

    [User Opens Shop]
           ↓
    [Clicks Buy Now]
           ↓
    ┌──────────────────┐
    │  CheckoutPage    │ ← Creates Order via /api/orders
    │  (React)         │
    └──────────────────┘
           ↓
    [Selects UPI App: PhonePe/GPay/BHIM/Paytm]
           ↓
    ┌──────────────────────────────────────────────────────┐
    │ Frontend calls: POST /api/payment/initiate          │
    │ Body: { order_id, payment_app }                     │
    └──────────────────────────────────────────────────────┘
           ↓
    ┌──────────────────────────────────────────────────────┐
    │ Backend (FastAPI):                                   │
    │ 1. Get order from MongoDB                           │
    │ 2. Generate PhonePe payload + signature             │
    │ 3. Call PhonePe API: /pg/v1/pay                     │
    │ 4. Return payment_url to frontend                   │
    └──────────────────────────────────────────────────────┘
           ↓
    [User Redirected to PhonePe Payment Page]
           ↓
    [User Completes Payment in UPI App]
           ↓
    ┌──────────────────────────────────────────────────────┐
    │ PhonePe sends POST callback to:                      │
    │ /api/payment/callback                                │
    │ With: response (base64) + checksum                   │
    └──────────────────────────────────────────────────────┘
           ↓
    ┌──────────────────────────────────────────────────────┐
    │ Backend Callback Handler:                            │
    │ 1. Verify checksum (SHA256)                         │
    │ 2. Decode base64 response                           │
    │ 3. Check payment status                             │
    │ 4. Update order in MongoDB                          │
    │ 5. Redirect user to success/failure page            │
    └──────────────────────────────────────────────────────┘
           ↓
           ├─ [SUCCESS] → /payment-success?order_id=XXX
           │              ┌──────────────────────────┐
           │              │ PaymentSuccessPage       │
           │              │ - Shows order details    │
           │              │ - Confirmation message   │
           │              │ - Action buttons         │
           │              └──────────────────────────┘
           │
           └─ [FAILED] → /payment-failed?order_id=XXX
                         ┌──────────────────────────┐
                         │ PaymentFailedPage        │
                         │ - Shows error            │
                         │ - Retry button           │
                         │ - Back to home           │
                         └──────────────────────────┘

```

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                              │
│  Port: 3000                                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Pages:                                                              │
│  - ShopPage.jsx (/)                                                 │
│  - CheckoutPage.jsx (/checkout)                                     │
│  - PaymentSuccessPage.jsx (/payment-success)                       │
│  - PaymentFailedPage.jsx (/payment-failed)                         │
│                                                                      │
│  Features:                                                           │
│  ✓ Zero UTR input (removed)                                        │
│  ✓ Automatic payment redirect                                       │
│  ✓ White-labeled UI (no PhonePe branding)                          │
│  ✓ Loading states and error handling                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↕ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                             │
│  Port: 8001                                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Endpoints:                                                          │
│  - POST /api/orders                     (Create order)              │
│  - GET  /api/orders/{order_id}         (Get order)                 │
│  - POST /api/payment/initiate           (Start payment)            │
│  - POST /api/payment/callback           (PhonePe callback)         │
│  - GET  /api/payment/status/{order_id}  (Check status)            │
│                                                                      │
│  PhonePe Integration:                                               │
│  ✓ Signature generation (SHA256)                                   │
│  ✓ Checksum verification                                            │
│  ✓ API communication                                                │
│  ✓ Callback handling                                                │
│                                                                      │
│  Removed:                                                            │
│  ✗ POST /api/verify-payment (deleted)                              │
│  ✗ UTR validation logic (deleted)                                   │
│  ✗ Manual verification (deleted)                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────┐
│                        DATABASE (MongoDB)                            │
│  Port: 27017                                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Collections:                                                        │
│                                                                      │
│  orders:                                                             │
│    - id, order_id, product_id, product_name                        │
│    - base_amount, unique_amount                                     │
│    - status (pending/processing/success/failed)                    │
│    - payment_method (phonepe/gpay/bhim/paytm)                      │
│    - payment_gateway_txn_id (PhonePe transaction ID)               │
│    - gateway_response (Full PhonePe response)                      │
│    - timestamps, user_agent, ip_address                            │
│                                                                      │
│  Removed Fields:                                                     │
│  ✗ utr (deleted)                                                    │
│  ✗ confidence_score (deleted)                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↕ HTTPS
┌─────────────────────────────────────────────────────────────────────┐
│                    PHONEPE PAYMENT GATEWAY                           │
│  https://api.phonepe.com/apis/hermes                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  APIs Used:                                                          │
│  - POST /pg/v1/pay              (Initiate payment)                 │
│  - GET  /pg/v1/status/{mid}/{tid} (Check status)                   │
│                                                                      │
│  Credentials:                                                        │
│  - Merchant ID: M23HX1NJIDUCT_2601152130                           │
│  - Salt Key: YTM3Yj...ZjA3N2Zh                                     │
│  - Salt Index: 1                                                    │
│                                                                      │
│  Security:                                                           │
│  ✓ X-VERIFY header (checksum)                                      │
│  ✓ Base64 payload encoding                                          │
│  ✓ SHA256 signature                                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Payment Initiation

```
Frontend                  Backend                    PhonePe Gateway
   │                         │                             │
   │  1. Click UPI App       │                             │
   │ ──────────────────────→ │                             │
   │                         │                             │
   │                         │  2. Generate Payload        │
   │                         │     - merchantTransactionId  │
   │                         │     - amount (in paise)     │
   │                         │     - redirectUrl           │
   │                         │     - callbackUrl           │
   │                         │                             │
   │                         │  3. Encode Base64           │
   │                         │     payload_base64          │
   │                         │                             │
   │                         │  4. Generate Checksum       │
   │                         │     SHA256(payload +        │
   │                         │     endpoint + salt)        │
   │                         │                             │
   │                         │  5. POST /pg/v1/pay         │
   │                         │ ──────────────────────────→ │
   │                         │                             │
   │                         │  6. Response                │
   │                         │ ←────────────────────────── │
   │                         │     { payment_url }         │
   │                         │                             │
   │  7. Payment URL         │                             │
   │ ←────────────────────── │                             │
   │                         │                             │
   │  8. Redirect User       │                             │
   │ ─────────────────────────────────────────────────────→│
   │                         │                             │
   │                    User Pays in UPI App               │
   │                         │                             │
```

---

## Data Flow: Payment Callback

```
PhonePe Gateway           Backend                    Frontend
   │                         │                             │
   │  1. POST /callback      │                             │
   │ ──────────────────────→ │                             │
   │     { response (base64),│                             │
   │       checksum }        │                             │
   │                         │                             │
   │                         │  2. Verify Checksum         │
   │                         │     SHA256(response + salt) │
   │                         │                             │
   │                         │  3. Decode Base64           │
   │                         │     Get transaction data    │
   │                         │                             │
   │                         │  4. Check Status            │
   │                         │     PAYMENT_SUCCESS?        │
   │                         │                             │
   │                         │  5. Update Order            │
   │                         │     status = "success"      │
   │                         │     verified_at = now()     │
   │                         │                             │
   │                         │  6. Redirect                │
   │                         │ ──────────────────────────→ │
   │                         │     /payment-success        │
   │                         │                             │
   │                         │                             │  7. Display
   │                         │                             │     Success Page
```

---

## Security Flow

```
┌─────────────────────────────────────────────────────────┐
│              SIGNATURE GENERATION                        │
└─────────────────────────────────────────────────────────┘

Step 1: Create Payload
{
  merchantId: "M23HX1NJIDUCT_2601152130",
  merchantTransactionId: "MT1234567890",
  amount: 49954,  // in paise
  redirectUrl: "https://example.com/callback",
  paymentInstrument: { type: "PAY_PAGE" }
}

Step 2: Encode to Base64
payload_base64 = Base64(JSON.stringify(payload))
// eyJtZXJjaGFudElk...

Step 3: Generate Signature String
string_to_hash = payload_base64 + "/pg/v1/pay" + salt_key
// eyJtZXJjaGFudElk.../pg/v1/payYTM3YjQwMjE...

Step 4: Calculate SHA256
sha256_hash = SHA256(string_to_hash)
// 8f7d3a9b2c1e...

Step 5: Create Checksum
checksum = sha256_hash + "###" + salt_index
// 8f7d3a9b2c1e...###1

Step 6: Send to PhonePe
Headers: { "X-VERIFY": checksum }
Body: { "request": payload_base64 }
```

---

## Order Status Lifecycle

```
   [pending]
      │
      │ User clicks UPI app
      │ Backend initiates payment
      ↓
[processing]
      │
      │ User completes payment
      │ PhonePe sends callback
      ↓
      ├─→ [success] (PAYMENT_SUCCESS)
      │   - Order verified
      │   - verified_at timestamp
      │   - User sees success page
      │
      └─→ [failed] (PAYMENT_FAILED or CANCELLED)
          - Order marked failed
          - User sees failure page
          - Retry option available
```

---

## Environment Variables

```bash
# Backend (.env)
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS="*"

# Backend URL for callbacks
REACT_APP_BACKEND_URL="https://upiflow-platform.preview.emergentagent.com"

# PhonePe Configuration
PHONEPE_MERCHANT_ID="M23HX1NJIDUCT_2601152130"
PHONEPE_SALT_KEY="YTM3YjQwMjEtNGE5Yy00ZTA2LTg5Y2QtYzJjNDM5ZjA3N2Zh"
PHONEPE_SALT_INDEX="1"
PHONEPE_ENV="production"
```

```bash
# Frontend (.env)
REACT_APP_BACKEND_URL="https://upiflow-platform.preview.emergentagent.com"
WDS_SOCKET_PORT="443"
ENABLE_HEALTH_CHECK="false"
```

---

## Key Differences: Old vs New

| Aspect | Old System (UTR) | New System (PhonePe) |
|--------|------------------|---------------------|
| **User Input** | Manual UTR entry | Zero manual input |
| **Verification** | Confidence scoring | Gateway verification |
| **Payment Flow** | Multi-step | Single click |
| **Reliability** | Prone to errors | 100% accurate |
| **UPI Apps** | Manual process | All apps supported |
| **Branding** | N/A | White-labeled |
| **Callback** | Manual check | Automatic |
| **Time to Verify** | Manual delay | Instant |

---

**Architecture is complete and ready for deployment!** 🚀
