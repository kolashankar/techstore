from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import random
import hashlib
import base64
import json
import requests


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging FIRST before any routes or functions use it
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# PhonePe Configuration
PHONEPE_MERCHANT_ID = os.environ.get('PHONEPE_MERCHANT_ID', 'M23HX1NJIDUCT_2601152130')
PHONEPE_SALT_KEY = os.environ.get('PHONEPE_SALT_KEY', 'YTM3YjQwMjEtNGE5Yy00ZTA2LTg5Y2QtYzJjNDM5ZjA3N2Zh')
PHONEPE_SALT_INDEX = int(os.environ.get('PHONEPE_SALT_INDEX', '1'))
PHONEPE_ENV = os.environ.get('PHONEPE_ENV', 'production')  # 'production' or 'sandbox'

# PhonePe API URLs
if PHONEPE_ENV == 'sandbox':
    PHONEPE_BASE_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox"
else:
    PHONEPE_BASE_URL = "https://api.phonepe.com/apis/pg"

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

# Create the main app without a prefix
app = FastAPI()

# Create a router WITHOUT prefix initially
router = APIRouter()


# ==================== MODELS ====================

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Order Models
class OrderCreate(BaseModel):
    product_id: str
    product_name: str
    amount: float
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = Field(default_factory=lambda: "ORD-" + str(uuid.uuid4())[:8].upper())
    product_id: str
    product_name: str
    base_amount: float
    unique_amount: float  # We'll keep this for amount tracking
    status: str = "pending"  # pending, success, failed, expired
    payment_method: Optional[str] = None  # phonepe, gpay, bhim, paytm, etc.
    payment_gateway_txn_id: Optional[str] = None  # PhonePe transaction ID
    gateway_response: Optional[dict] = None  # Store full gateway response
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    payment_window_expires: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: Optional[datetime] = None

# Payment Gateway Models
class PaymentInitiateRequest(BaseModel):
    order_id: str
    payment_app: str  # phonepe, gpay, bhim, paytm, etc.

class PaymentInitiateResponse(BaseModel):
    success: bool
    payment_url: str
    transaction_id: str
    order_id: str

class PaymentStatusResponse(BaseModel):
    success: bool
    status: str  # PAYMENT_SUCCESS, PAYMENT_PENDING, PAYMENT_FAILED
    transaction_id: str
    order_id: str
    amount: float
    message: str


# ==================== PHONEPE HELPER FUNCTIONS ====================

def generate_phonepe_checksum(payload_base64: str, endpoint: str) -> str:
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

def verify_phonepe_callback_checksum(response_base64: str, received_checksum: str) -> bool:
    """Verify checksum from PhonePe callback"""
    try:
        expected_string = response_base64 + PHONEPE_SALT_KEY
        expected_hash = hashlib.sha256(expected_string.encode()).hexdigest()
        expected_checksum = expected_hash + "###" + str(PHONEPE_SALT_INDEX)
        return expected_checksum == received_checksum
    except Exception as e:
        logger.error(f"Checksum verification error: {str(e)}")
        return False


# ==================== BASIC ROUTES ====================

@router.get("/")
async def root():
    return {"message": "Payment Gateway API"}

@router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks


# ==================== ORDER ENDPOINTS ====================

def generate_unique_amount(base_amount: float) -> float:
    """Generate a unique payment amount by adding random paise"""
    random_paise = random.randint(1, 99) / 100.0
    unique_amount = base_amount + random_paise
    return round(unique_amount, 2)

@router.post("/orders", response_model=Order)
async def create_order(order_input: OrderCreate, request: Request):
    """Create a new order"""
    try:
        order_dict = order_input.model_dump()
        
        base_amount = order_dict['amount']
        unique_amount = generate_unique_amount(base_amount)
        
        payment_window_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        user_agent = order_dict.get('user_agent') or request.headers.get('user-agent', 'Unknown')
        ip_address = order_dict.get('ip_address') or request.client.host
        
        order_obj = Order(
            product_id=order_dict['product_id'],
            product_name=order_dict['product_name'],
            base_amount=base_amount,
            unique_amount=unique_amount,
            user_agent=user_agent,
            ip_address=ip_address,
            payment_window_expires=payment_window_expires
        )
        
        doc = order_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['payment_window_expires'] = doc['payment_window_expires'].isoformat()
        
        await db.orders.insert_one(doc)
        
        logger.info(f"Order created: {order_obj.order_id} - Amount: ₹{unique_amount}")
        return order_obj
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """Get order details by order_id"""
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if isinstance(order.get('created_at'), str):
        order['created_at'] = datetime.fromisoformat(order['created_at'])
    if isinstance(order.get('payment_window_expires'), str):
        order['payment_window_expires'] = datetime.fromisoformat(order['payment_window_expires'])
    if order.get('verified_at') and isinstance(order['verified_at'], str):
        order['verified_at'] = datetime.fromisoformat(order['verified_at'])
    
    return order


# ==================== PHONEPE PAYMENT GATEWAY ENDPOINTS ====================

@router.post("/payment/initiate", response_model=PaymentInitiateResponse)
async def initiate_payment(payment_request: PaymentInitiateRequest, request: Request):
    """
    Initiate payment with PhonePe gateway
    Returns payment URL for redirect
    """
    try:
        # 1. Get order details
        order = await db.orders.find_one({"order_id": payment_request.order_id}, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order['status'] != 'pending':
            raise HTTPException(status_code=400, detail=f"Order already {order['status']}")
        
        # 2. Generate unique transaction ID
        merchant_transaction_id = f"MT{int(datetime.now().timestamp() * 1000)}"
        
        # 3. Prepare PhonePe payload
        amount_in_paise = int(order['unique_amount'] * 100)  # Convert to paise
        
        # Construct callback URL
        callback_url = f"{BACKEND_URL}/api/payment/callback"
        
        payload_data = {
            "merchantId": PHONEPE_MERCHANT_ID,
            "merchantTransactionId": merchant_transaction_id,
            "merchantUserId": f"USER_{order['order_id']}",
            "amount": amount_in_paise,
            "redirectUrl": callback_url,
            "redirectMode": "POST",
            "callbackUrl": callback_url,
            "mobileNumber": "9999999999",  # Optional
            "paymentInstrument": {
                "type": "PAY_PAGE"
            }
        }
        
        # 4. Generate base64 payload
        payload_json = json.dumps(payload_data)
        payload_base64 = base64.b64encode(payload_json.encode()).decode()
        
        # 5. Generate checksum
        endpoint = "/pg/v1/pay"
        checksum = generate_phonepe_checksum(payload_base64, endpoint)
        
        # 6. Make API call to PhonePe
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": checksum
        }
        
        api_payload = {
            "request": payload_base64
        }
        
        phonepe_url = f"{PHONEPE_BASE_URL}{endpoint}"
        
        logger.info(f"Initiating PhonePe payment for order {payment_request.order_id}")
        logger.info(f"PhonePe URL: {phonepe_url}")
        
        response = requests.post(phonepe_url, json=api_payload, headers=headers, timeout=30)
        response_data = response.json()
        
        logger.info(f"PhonePe response: {response_data}")
        
        if not response_data.get('success'):
            error_msg = response_data.get('message', 'Payment initiation failed')
            logger.error(f"PhonePe error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 7. Extract payment URL
        payment_url = response_data['data']['instrumentResponse']['redirectInfo']['url']
        
        # 8. Update order with transaction details
        await db.orders.update_one(
            {"order_id": payment_request.order_id},
            {
                "$set": {
                    "payment_gateway_txn_id": merchant_transaction_id,
                    "payment_method": payment_request.payment_app,
                    "status": "processing"
                }
            }
        )
        
        logger.info(f"Payment initiated: Order {payment_request.order_id}, Txn {merchant_transaction_id}")
        
        return PaymentInitiateResponse(
            success=True,
            payment_url=payment_url,
            transaction_id=merchant_transaction_id,
            order_id=payment_request.order_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating payment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment initiation failed: {str(e)}")


@router.post("/payment/callback")
async def payment_callback(request: Request):
    """
    Handle PhonePe payment callback
    This endpoint receives POST data from PhonePe after payment
    """
    try:
        # Get form data or JSON based on PhonePe's response format
        try:
            form_data = await request.form()
            response_base64 = form_data.get('response')
            checksum = form_data.get('checksum')
        except:
            body = await request.json()
            response_base64 = body.get('response')
            checksum = body.get('checksum')
        
        if not response_base64:
            logger.error("No response data in callback")
            raise HTTPException(status_code=400, detail="Invalid callback data")
        
        # Verify checksum
        if not verify_phonepe_callback_checksum(response_base64, checksum):
            logger.error("Checksum verification failed")
            raise HTTPException(status_code=400, detail="Invalid checksum")
        
        # Decode response
        response_json = base64.b64decode(response_base64).decode()
        response_data = json.loads(response_json)
        
        logger.info(f"PhonePe callback received: {response_data}")
        
        merchant_transaction_id = response_data.get('data', {}).get('merchantTransactionId')
        
        if not merchant_transaction_id:
            logger.error("No transaction ID in callback")
            raise HTTPException(status_code=400, detail="Invalid transaction data")
        
        # Find order by transaction ID
        order = await db.orders.find_one({"payment_gateway_txn_id": merchant_transaction_id}, {"_id": 0})
        
        if not order:
            logger.error(f"Order not found for transaction: {merchant_transaction_id}")
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check payment status
        payment_status = response_data.get('code')
        
        if payment_status == 'PAYMENT_SUCCESS':
            # Update order as verified
            verified_at = datetime.now(timezone.utc)
            
            await db.orders.update_one(
                {"payment_gateway_txn_id": merchant_transaction_id},
                {
                    "$set": {
                        "status": "success",
                        "verified_at": verified_at.isoformat(),
                        "gateway_response": response_data
                    }
                }
            )
            
            logger.info(f"Payment successful: {merchant_transaction_id}")
            
            # Redirect to success page
            frontend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:3000').replace(':8001', ':3000')
            return RedirectResponse(url=f"{frontend_url}/payment-success?order_id={order['order_id']}")
        
        else:
            # Payment failed or pending
            await db.orders.update_one(
                {"payment_gateway_txn_id": merchant_transaction_id},
                {
                    "$set": {
                        "status": "failed",
                        "gateway_response": response_data
                    }
                }
            )
            
            logger.warning(f"Payment failed: {merchant_transaction_id}, Status: {payment_status}")
            
            # Redirect to failure page
            frontend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:3000').replace(':8001', ':3000')
            return RedirectResponse(url=f"{frontend_url}/payment-failed?order_id={order['order_id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Callback processing failed: {str(e)}")


@router.get("/payment/status/{order_id}", response_model=PaymentStatusResponse)
async def check_payment_status(order_id: str):
    """
    Check payment status by order_id
    Makes a server-to-server call to PhonePe to verify transaction status
    """
    try:
        # 1. Get order
        order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        merchant_transaction_id = order.get('payment_gateway_txn_id')
        
        if not merchant_transaction_id:
            # Order not yet initiated with payment gateway
            return PaymentStatusResponse(
                success=False,
                status="PENDING",
                transaction_id="",
                order_id=order_id,
                amount=order['unique_amount'],
                message="Payment not initiated"
            )
        
        # 2. Generate checksum for status check
        endpoint = f"/pg/v1/status/{PHONEPE_MERCHANT_ID}/{merchant_transaction_id}"
        string_to_hash = endpoint + PHONEPE_SALT_KEY
        sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
        checksum = sha256_hash + "###" + str(PHONEPE_SALT_INDEX)
        
        # 3. Make status check API call
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": checksum,
            "X-MERCHANT-ID": PHONEPE_MERCHANT_ID
        }
        
        status_url = f"{PHONEPE_BASE_URL}{endpoint}"
        
        response = requests.get(status_url, headers=headers, timeout=30)
        response_data = response.json()
        
        logger.info(f"PhonePe status check: {response_data}")
        
        if response_data.get('success'):
            payment_status = response_data.get('code')
            
            # Update order status based on PhonePe response
            if payment_status == 'PAYMENT_SUCCESS' and order['status'] != 'success':
                verified_at = datetime.now(timezone.utc)
                
                await db.orders.update_one(
                    {"order_id": order_id},
                    {
                        "$set": {
                            "status": "success",
                            "verified_at": verified_at.isoformat(),
                            "gateway_response": response_data
                        }
                    }
                )
                
                return PaymentStatusResponse(
                    success=True,
                    status="PAYMENT_SUCCESS",
                    transaction_id=merchant_transaction_id,
                    order_id=order_id,
                    amount=order['unique_amount'],
                    message="Payment completed successfully"
                )
            
            elif payment_status == 'PAYMENT_PENDING':
                return PaymentStatusResponse(
                    success=False,
                    status="PAYMENT_PENDING",
                    transaction_id=merchant_transaction_id,
                    order_id=order_id,
                    amount=order['unique_amount'],
                    message="Payment is being processed"
                )
            
            else:
                # PAYMENT_FAILED or other status
                if order['status'] != 'failed':
                    await db.orders.update_one(
                        {"order_id": order_id},
                        {"$set": {"status": "failed", "gateway_response": response_data}}
                    )
                
                return PaymentStatusResponse(
                    success=False,
                    status="PAYMENT_FAILED",
                    transaction_id=merchant_transaction_id,
                    order_id=order_id,
                    amount=order['unique_amount'],
                    message="Payment failed"
                )
        else:
            raise HTTPException(status_code=400, detail="Failed to check payment status")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking payment status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/orders")
async def get_all_orders():
    """Get all orders (admin endpoint)"""
    orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for order in orders:
        if isinstance(order.get('created_at'), str):
            order['created_at'] = datetime.fromisoformat(order['created_at'])
        if isinstance(order.get('payment_window_expires'), str):
            order['payment_window_expires'] = datetime.fromisoformat(order['payment_window_expires'])
        if order.get('verified_at') and isinstance(order['verified_at'], str):
            order['verified_at'] = datetime.fromisoformat(order['verified_at'])
    
    return {"orders": orders, "count": len(orders)}


# Include the router in the main app TWICE
app.include_router(router, prefix="/api")
app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
