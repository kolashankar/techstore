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
import json
import requests
try:
    import PaytmChecksum
except ImportError:
    from paytmchecksum import PaytmChecksum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Paytm Configuration
PAYTM_ENVIRONMENT = os.environ.get('PAYTM_ENVIRONMENT', 'STAGING')
PAYTM_MID = os.environ.get('PAYTM_MID', 'TESTMERCHANT')
PAYTM_KEY = os.environ.get('PAYTM_KEY', 'TEST_MERCHANT_KEY_1234567890')
PAYTM_WEBSITE = os.environ.get('PAYTM_WEBSITE', 'WEBSTAGING')
PAYTM_INDUSTRY_TYPE = os.environ.get('PAYTM_INDUSTRY_TYPE', 'Retail')
PAYTM_CHANNEL_ID = os.environ.get('PAYTM_CHANNEL_ID', 'WEB')
PAYTM_CALLBACK_URL = os.environ.get('PAYTM_CALLBACK_URL', 'http://localhost:8001/api/payment/callback')

# Paytm API URLs
if PAYTM_ENVIRONMENT == 'STAGING':
    PAYTM_TXN_URL = "https://securegw-stage.paytm.in/theia/api/v1/initiateTransaction"
    PAYTM_STATUS_URL = "https://securegw-stage.paytm.in/order/status"
else:
    PAYTM_TXN_URL = "https://securegw.paytm.in/theia/api/v1/initiateTransaction"
    PAYTM_STATUS_URL = "https://securegw.paytm.in/order/status"

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

# Create the main app
app = FastAPI()

# Create a router
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
    unique_amount: float
    status: str = "pending"  # pending, processing, success, failed, expired
    payment_method: Optional[str] = None  # paytm, card, netbanking, upi
    payment_gateway_txn_id: Optional[str] = None  # Paytm transaction ID
    transaction_token: Optional[str] = None  # Paytm transaction token
    gateway_response: Optional[dict] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    payment_window_expires: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: Optional[datetime] = None

# Payment Gateway Models
class PaymentInitiateRequest(BaseModel):
    order_id: str
    customer_id: str
    customer_email: str
    customer_mobile: str

class PaymentInitiateResponse(BaseModel):
    success: bool
    transaction_token: str
    order_id: str
    merchant_id: str
    amount: float

class PaymentStatusResponse(BaseModel):
    success: bool
    status: str  # SUCCESS, PENDING, FAILED
    transaction_id: str
    order_id: str
    amount: float
    message: str


# ==================== PAYTM HELPER FUNCTIONS ====================

def generate_transaction_token(order_id: str, amount: float, customer_id: str, customer_mobile: str) -> dict:
    """
    Generate Paytm transaction token for payment initiation
    Returns: dict with success status and token or error message
    """
    try:
        # Generate unique transaction ID
        txn_id = f"TXN{int(datetime.now().timestamp() * 1000)}"
        
        # Prepare request parameters
        paytm_params = {
            "body": {
                "requestType": "Payment",
                "mid": PAYTM_MID,
                "websiteName": PAYTM_WEBSITE,
                "orderId": order_id,
                "txnAmount": {
                    "value": str(amount),
                    "currency": "INR"
                },
                "userInfo": {
                    "custId": customer_id,
                    "mobile": customer_mobile
                },
                "callbackUrl": PAYTM_CALLBACK_URL
            },
            "head": {
                "signature": ""
            }
        }
        
        # Generate checksum
        checksum = PaytmChecksum.generateSignature(
            json.dumps(paytm_params["body"]), 
            PAYTM_KEY
        )
        paytm_params["head"]["signature"] = checksum
        
        # Make API call to Paytm
        headers = {
            "Content-Type": "application/json"
        }
        
        url = f"{PAYTM_TXN_URL}?mid={PAYTM_MID}&orderId={order_id}"
        
        logger.info(f"Initiating Paytm transaction for order {order_id}")
        logger.info(f"Paytm URL: {url}")
        
        response = requests.post(url, json=paytm_params, headers=headers, timeout=30)
        response_data = response.json()
        
        logger.info(f"Paytm token response: {response_data}")
        
        if response_data.get("body", {}).get("resultInfo", {}).get("resultStatus") == "S":
            # Success - extract token
            token = response_data["body"]["txnToken"]
            return {
                "success": True,
                "token": token,
                "txn_id": txn_id,
                "order_id": order_id
            }
        else:
            # Failed
            error_msg = response_data.get("body", {}).get("resultInfo", {}).get("resultMsg", "Token generation failed")
            logger.error(f"Paytm token error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
    except Exception as e:
        logger.exception(f"Error generating transaction token: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def verify_paytm_checksum(paytm_params: dict, checksum: str) -> bool:
    """Verify Paytm callback checksum"""
    try:
        return PaytmChecksum.verifySignature(paytm_params, PAYTM_KEY, checksum)
    except Exception as e:
        logger.error(f"Checksum verification error: {str(e)}")
        return False


def get_payment_status_from_paytm(order_id: str) -> dict:
    """
    Get payment status from Paytm
    Returns: dict with payment status information
    """
    try:
        # Prepare request parameters
        paytm_params = {
            "body": {
                "mid": PAYTM_MID,
                "orderId": order_id
            },
            "head": {
                "signature": ""
            }
        }
        
        # Generate checksum
        checksum = PaytmChecksum.generateSignature(
            json.dumps(paytm_params["body"]), 
            PAYTM_KEY
        )
        paytm_params["head"]["signature"] = checksum
        
        # Make API call
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(PAYTM_STATUS_URL, json=paytm_params, headers=headers, timeout=30)
        response_data = response.json()
        
        logger.info(f"Paytm status response: {response_data}")
        
        return {
            "success": True,
            "data": response_data
        }
        
    except Exception as e:
        logger.exception(f"Error checking payment status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ==================== BASIC ROUTES ====================

@router.get("/")
async def root():
    return {"message": "Paytm Payment Gateway API"}

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


# ==================== PAYTM PAYMENT GATEWAY ENDPOINTS ====================

@router.post("/payment/initiate", response_model=PaymentInitiateResponse)
async def initiate_payment(payment_request: PaymentInitiateRequest, request: Request):
    """
    Initiate payment with Paytm gateway
    Returns transaction token for frontend to open Paytm payment page
    """
    try:
        # 1. Get order details
        order = await db.orders.find_one({"order_id": payment_request.order_id}, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order['status'] not in ['pending', 'processing']:
            raise HTTPException(status_code=400, detail=f"Order already {order['status']}")
        
        # 2. Generate transaction token from Paytm
        token_response = generate_transaction_token(
            order_id=payment_request.order_id,
            amount=order['unique_amount'],
            customer_id=payment_request.customer_id,
            customer_mobile=payment_request.customer_mobile
        )
        
        if not token_response["success"]:
            error_msg = token_response.get("error", "Failed to generate transaction token")
            logger.error(f"Paytm token error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 3. Update order with transaction details
        txn_id = token_response["txn_id"]
        token = token_response["token"]
        
        await db.orders.update_one(
            {"order_id": payment_request.order_id},
            {
                "$set": {
                    "payment_gateway_txn_id": txn_id,
                    "transaction_token": token,
                    "status": "processing"
                }
            }
        )
        
        logger.info(f"Payment initiated: Order {payment_request.order_id}, Token generated")
        
        return PaymentInitiateResponse(
            success=True,
            transaction_token=token,
            order_id=payment_request.order_id,
            merchant_id=PAYTM_MID,
            amount=order['unique_amount']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating payment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment initiation failed: {str(e)}")


@router.post("/payment/callback")
async def payment_callback(request: Request):
    """
    Handle Paytm payment callback
    This endpoint receives POST data from Paytm after payment
    """
    try:
        # Get form data from Paytm callback
        form_data = await request.form()
        paytm_params = dict(form_data)
        
        logger.info(f"Paytm callback received: {paytm_params}")
        
        # Extract checksum
        checksum = paytm_params.pop('CHECKSUMHASH', None)
        
        if not checksum:
            logger.error("No checksum in callback")
            raise HTTPException(status_code=400, detail="Invalid callback data")
        
        # Verify checksum
        if not verify_paytm_checksum(paytm_params, checksum):
            logger.error("Checksum verification failed")
            raise HTTPException(status_code=400, detail="Invalid checksum")
        
        # Extract order details
        order_id = paytm_params.get('ORDERID')
        txn_id = paytm_params.get('TXNID')
        status = paytm_params.get('STATUS')
        resp_code = paytm_params.get('RESPCODE')
        resp_msg = paytm_params.get('RESPMSG')
        
        if not order_id:
            logger.error("No order ID in callback")
            raise HTTPException(status_code=400, detail="Invalid transaction data")
        
        # Find order
        order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
        
        if not order:
            logger.error(f"Order not found for: {order_id}")
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check payment status
        if status == 'TXN_SUCCESS':
            # Payment successful
            verified_at = datetime.now(timezone.utc)
            
            await db.orders.update_one(
                {"order_id": order_id},
                {
                    "$set": {
                        "status": "success",
                        "verified_at": verified_at.isoformat(),
                        "payment_gateway_txn_id": txn_id,
                        "gateway_response": paytm_params
                    }
                }
            )
            
            logger.info(f"Payment successful: {order_id}")
            
            # Redirect to success page
            frontend_url = BACKEND_URL.replace(':8001', ':3000').replace('api.', '')
            return RedirectResponse(url=f"{frontend_url}/payment-success?order_id={order_id}")
        
        else:
            # Payment failed
            await db.orders.update_one(
                {"order_id": order_id},
                {
                    "$set": {
                        "status": "failed",
                        "gateway_response": paytm_params
                    }
                }
            )
            
            logger.warning(f"Payment failed: {order_id}, Status: {status}, Msg: {resp_msg}")
            
            # Redirect to failure page
            frontend_url = BACKEND_URL.replace(':8001', ':3000').replace('api.', '')
            return RedirectResponse(url=f"{frontend_url}/payment-failed?order_id={order_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Callback processing failed: {str(e)}")


@router.get("/payment/status/{order_id}", response_model=PaymentStatusResponse)
async def check_payment_status(order_id: str):
    """
    Check payment status by order_id
    Makes a server-to-server call to Paytm to verify transaction status
    """
    try:
        # 1. Get order from database
        order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # 2. Check with Paytm
        paytm_response = get_payment_status_from_paytm(order_id)
        
        if not paytm_response["success"]:
            # Return local status if Paytm check fails
            return PaymentStatusResponse(
                success=order['status'] == 'success',
                status=order['status'].upper(),
                transaction_id=order.get('payment_gateway_txn_id', ''),
                order_id=order_id,
                amount=order['unique_amount'],
                message=f"Payment status: {order['status']}"
            )
        
        # 3. Parse Paytm response
        response_data = paytm_response["data"]
        result_status = response_data.get("body", {}).get("resultInfo", {}).get("resultStatus")
        
        if result_status == "TXN_SUCCESS":
            # Update order if not already marked as success
            if order['status'] != 'success':
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
                status="SUCCESS",
                transaction_id=order.get('payment_gateway_txn_id', ''),
                order_id=order_id,
                amount=order['unique_amount'],
                message="Payment completed successfully"
            )
        
        elif result_status == "TXN_FAILURE":
            # Update order status
            if order['status'] != 'failed':
                await db.orders.update_one(
                    {"order_id": order_id},
                    {"$set": {"status": "failed", "gateway_response": response_data}}
                )
            
            return PaymentStatusResponse(
                success=False,
                status="FAILED",
                transaction_id=order.get('payment_gateway_txn_id', ''),
                order_id=order_id,
                amount=order['unique_amount'],
                message="Payment failed"
            )
        
        else:
            # Pending or other status
            return PaymentStatusResponse(
                success=False,
                status="PENDING",
                transaction_id=order.get('payment_gateway_txn_id', ''),
                order_id=order_id,
                amount=order['unique_amount'],
                message="Payment is being processed"
            )
        
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


# Include the router in the main app
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
