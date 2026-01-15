# Payment Gateway Implementation Plan

## Overview
Implement white-labeled UPI payment system using PhonePe Payment Gateway with automatic callback verification. Zero PhonePe branding visible to users.

## Completion Status: 0%

---

## Phase 1: Backend Implementation (0%)

### 1.1 PhonePe Payment Controller
- [ ] Create payment models (PaymentInitiation, PaymentCallback, PaymentStatus)
- [ ] Implement signature/checksum generation using PhonePe's algorithm
- [ ] Create PhonePe API client helper functions

### 1.2 Payment Endpoints
- [ ] `/api/payment/initiate` - Generate payment token and redirect URL
- [ ] `/api/payment/callback` - Handle PhonePe callback after payment
- [ ] `/api/payment/status/{transaction_id}` - Check payment status

### 1.3 Database Updates
- [ ] Add payment_gateway_txn_id to Order model
- [ ] Add payment_method field (phonepe, gpay, bhim, etc.)
- [ ] Add gateway_response field for storing callback data
- [ ] Remove UTR-related fields and validation

### 1.4 Remove UTR System
- [ ] Remove `/api/verify-payment` endpoint
- [ ] Remove UTR validation logic
- [ ] Remove manual verification code
- [ ] Clean up Payment model (remove UTR field)

---

## Phase 2: Frontend Implementation (0%)

### 2.1 Update Checkout Flow
- [ ] Remove UTR input form completely
- [ ] Remove manual verification step (Step 2)
- [ ] Update payment flow: Select App → Auto-redirect → Auto-verify → Success

### 2.2 Payment Initiation
- [ ] Call `/api/payment/initiate` when user selects UPI app
- [ ] Receive payment URL from backend
- [ ] Auto-redirect user to PhonePe payment page

### 2.3 Callback Handling
- [ ] Create success page to receive callback
- [ ] Auto-check payment status on return
- [ ] Display success/failure message based on verification

### 2.4 UI Updates
- [ ] Remove "Enter UTR" UI elements
- [ ] Update loading states for automatic verification
- [ ] Add "Processing payment..." state
- [ ] Update success page with auto-verification message

---

## Phase 3: Testing (0%)

### 3.1 Backend Testing
- [ ] Test payment initiation API
- [ ] Test signature generation
- [ ] Test callback handling
- [ ] Test status verification

### 3.2 Frontend Testing
- [ ] Test UPI app selection
- [ ] Test payment redirect
- [ ] Test callback reception
- [ ] Test success/failure flows

### 3.3 Integration Testing
- [ ] End-to-end payment flow
- [ ] Test with different UPI apps
- [ ] Test payment expiry
- [ ] Test duplicate payment prevention

---

## Technical Details

### PhonePe Credentials
```
Client ID: M23HX1NJIDUCT_2601152130
Client Secret: YTM3YjQwMjEtNGE5Yy00ZTA2LTg5Y2QtYzJjNDM5ZjA3N2Zh
```

### PhonePe API Endpoints
- Base URL: `https://api.phonepe.com/apis/hermes`
- Sandbox URL: `https://api-preprod.phonepe.com/apis/hermes/pg/v1`
- Payment Initiate: `/pg/v1/pay`
- Status Check: `/pg/v1/status/{merchantId}/{transactionId}`

### Signature Algorithm
```
Base64(payload) + "/pg/v1/pay" + saltKey → SHA256 → checksum###saltIndex
```

---

## Key Features

✅ White-labeled (No PhonePe branding visible)
✅ Automatic callback verification
✅ Support for all UPI apps (PhonePe, GPay, BHIM, Paytm, etc.)
✅ No manual UTR entry required
✅ Server-side signature generation
✅ Secure payment flow

---

## Files to Modify

### Backend
- `/app/backend/server.py` - Add PhonePe integration, remove UTR code
- `/app/backend/requirements.txt` - Add any new dependencies

### Frontend
- `/app/frontend/src/pages/CheckoutPage.jsx` - Remove UTR flow, add auto-redirect
- `/app/frontend/src/lib/upi-utils.js` - Update payment initiation logic

---

## Notes
- All payments will be processed through PhonePe gateway
- Users will see only UPI app logos (PhonePe, GPay, BHIM, etc.)
- No PhonePe branding or mention in the UI
- Callback URL must be publicly accessible for PhonePe to send status
