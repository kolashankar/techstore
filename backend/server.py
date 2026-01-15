from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import re
import random


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
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
    base_amount: float  # Original product price
    unique_amount: float  # Unique amount with decimals for verification
    status: str = "pending"  # pending, verified, expired, failed
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    payment_window_expires: datetime  # When payment window closes
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: Optional[datetime] = None
    confidence_score: Optional[float] = None  # Matching confidence (0-100)

# Payment Models
class PaymentVerification(BaseModel):
    order_id: str
    utr: str
    paid_amount: float  # Amount user actually paid
    
    @validator('utr')
    def validate_utr(cls, v):
        # Remove spaces and convert to string
        utr_str = str(v).strip().replace(" ", "")
        
        # Check if it's numeric and 12 digits
        if not re.match(r'^\d{12}$', utr_str):
            raise ValueError('UTR must be exactly 12 digits')
        
        return utr_str

class Payment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    utr: str
    order_id: str
    amount: float
    status: str  # verified, duplicate, invalid, pending_review
    confidence_score: float  # 0-100
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False

class PaymentResponse(BaseModel):
    success: bool
    message: str
    order_id: str
    utr: str
    confidence_score: Optional[float] = None
    verified_at: Optional[str] = None

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# ==================== ORDER ENDPOINTS ====================

def generate_unique_amount(base_amount: float) -> float:
    """
    Generate a unique payment amount by adding random paise
    Example: 499 -> 499.17, 499.42, etc.
    """
    # Generate random paise between 1 and 99
    random_paise = random.randint(1, 99) / 100.0
    unique_amount = base_amount + random_paise
    return round(unique_amount, 2)

@api_router.post("/orders", response_model=Order)
async def create_order(order_input: OrderCreate, request: Request):
    """Create a new order with unique payment amount"""
    try:
        order_dict = order_input.model_dump()
        
        # Generate unique amount
        base_amount = order_dict['amount']
        unique_amount = generate_unique_amount(base_amount)
        
        # Set payment window (30 minutes from now)
        payment_window_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        # Get user agent and IP from request
        user_agent = order_dict.get('user_agent') or request.headers.get('user-agent', 'Unknown')
        ip_address = order_dict.get('ip_address') or request.client.host
        
        # Create order object
        order_obj = Order(
            product_id=order_dict['product_id'],
            product_name=order_dict['product_name'],
            base_amount=base_amount,
            unique_amount=unique_amount,
            user_agent=user_agent,
            ip_address=ip_address,
            payment_window_expires=payment_window_expires
        )
        
        # Convert to dict and serialize datetime to ISO string for MongoDB
        doc = order_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['payment_window_expires'] = doc['payment_window_expires'].isoformat()
        
        # Insert into database
        await db.orders.insert_one(doc)
        
        logger.info(f"Order created: {order_obj.order_id} - Unique Amount: ₹{unique_amount}")
        return order_obj
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """Get order details by order_id"""
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Convert ISO string timestamps back to datetime objects
    if isinstance(order.get('created_at'), str):
        order['created_at'] = datetime.fromisoformat(order['created_at'])
    if isinstance(order.get('payment_window_expires'), str):
        order['payment_window_expires'] = datetime.fromisoformat(order['payment_window_expires'])
    if order.get('verified_at') and isinstance(order['verified_at'], str):
        order['verified_at'] = datetime.fromisoformat(order['verified_at'])
    
    return order

# ==================== SMART PAYMENT VERIFICATION ====================

def calculate_confidence_score(order: dict, payment: PaymentVerification, request: Request) -> float:
    """
    Calculate confidence score for payment matching
    Returns: 0-100 score
    """
    score = 0.0
    
    # 1. Exact Amount Match (50 points)
    if abs(payment.paid_amount - order['unique_amount']) < 0.01:
        score += 50
    else:
        # No points if amount doesn't match
        return 0
    
    # 2. Time Window Check (30 points)
    payment_window_expires = order['payment_window_expires']
    if isinstance(payment_window_expires, str):
        payment_window_expires = datetime.fromisoformat(payment_window_expires)
    
    current_time = datetime.now(timezone.utc)
    if current_time <= payment_window_expires:
        # Within time window - full points
        score += 30
    else:
        # Slightly outside window - reduced points based on how late
        time_diff = (current_time - payment_window_expires).total_seconds() / 60  # minutes
        if time_diff <= 5:  # Within 5 mins of expiry
            score += 20
        elif time_diff <= 15:  # Within 15 mins
            score += 10
        # else: 0 points for too late
    
    # 3. Session Match - User Agent (10 points)
    request_user_agent = request.headers.get('user-agent', '')
    if order.get('user_agent') and request_user_agent:
        if order['user_agent'] == request_user_agent:
            score += 10
        elif order['user_agent'][:50] == request_user_agent[:50]:  # Partial match
            score += 5
    
    # 4. Session Match - IP Address (10 points)
    request_ip = request.client.host
    if order.get('ip_address') and request_ip:
        if order['ip_address'] == request_ip:
            score += 10
        elif order['ip_address'].split('.')[0:2] == request_ip.split('.')[0:2]:  # Same subnet
            score += 5
    
    return min(score, 100)  # Cap at 100

@api_router.post("/verify-payment", response_model=PaymentResponse)
async def verify_payment(payment: PaymentVerification, request: Request):
    """
    Smart payment verification with auto-matching
    - Checks exact amount match
    - Validates time window
    - Matches session data
    - Returns confidence score
    """
    try:
        # 1. Check if order exists
        order = await db.orders.find_one({"order_id": payment.order_id}, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # 2. Check if order is already verified
        if order['status'] == 'verified':
            raise HTTPException(
                status_code=400, 
                detail="This order has already been verified with a payment"
            )
        
        # 3. Check if UTR already exists (CRITICAL: Prevent duplicate UTR usage)
        existing_payment = await db.payments.find_one({"utr": payment.utr}, {"_id": 0})
        
        if existing_payment:
            logger.warning(f"Duplicate UTR attempt: {payment.utr} for order {payment.order_id}")
            
            # Store failed attempt
            failed_payment = Payment(
                utr=payment.utr,
                order_id=payment.order_id,
                amount=payment.paid_amount,
                status="duplicate",
                confidence_score=0,
                verified=False
            )
            
            doc = failed_payment.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.payments.insert_one(doc)
            
            raise HTTPException(
                status_code=400,
                detail=f"This UTR has already been used for another payment. Each UTR can only be used once."
            )
        
        # 4. Calculate confidence score
        confidence_score = calculate_confidence_score(order, payment, request)
        
        logger.info(f"Payment verification - Order: {payment.order_id}, Confidence: {confidence_score}%")
        
        # 5. Determine verification status based on confidence
        if confidence_score >= 90:
            # High confidence - Auto-approve
            status = "verified"
            verified = True
            verified_at = datetime.now(timezone.utc)
            message = "Payment verified successfully! Your order has been confirmed."
            
            # Update order status
            await db.orders.update_one(
                {"order_id": payment.order_id},
                {
                    "$set": {
                        "status": "verified",
                        "verified_at": verified_at.isoformat(),
                        "confidence_score": confidence_score
                    }
                }
            )
            
        elif confidence_score >= 50:
            # Medium confidence - Pending review
            status = "pending_review"
            verified = False
            verified_at = None
            message = "Payment received! Your payment is being reviewed and will be confirmed shortly."
            
            # Update order status
            await db.orders.update_one(
                {"order_id": payment.order_id},
                {
                    "$set": {
                        "status": "pending_review",
                        "confidence_score": confidence_score
                    }
                }
            )
            
        else:
            # Low confidence - Reject
            status = "invalid"
            verified = False
            verified_at = None
            message = "Payment verification failed. Please check the amount and try again, or contact support."
            
            # Update order status
            await db.orders.update_one(
                {"order_id": payment.order_id},
                {
                    "$set": {
                        "status": "failed",
                        "confidence_score": confidence_score
                    }
                }
            )
        
        # 6. Store payment record
        payment_record = Payment(
            utr=payment.utr,
            order_id=payment.order_id,
            amount=payment.paid_amount,
            status=status,
            confidence_score=confidence_score,
            verified=verified
        )
        
        payment_doc = payment_record.model_dump()
        payment_doc['created_at'] = payment_doc['created_at'].isoformat()
        await db.payments.insert_one(payment_doc)
        
        logger.info(f"Payment {status} - Order: {payment.order_id}, UTR: {payment.utr}, Score: {confidence_score}%")
        
        return PaymentResponse(
            success=verified,
            message=message,
            order_id=payment.order_id,
            utr=payment.utr,
            confidence_score=confidence_score,
            verified_at=verified_at.isoformat() if verified_at else None
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        # UTR validation error
        logger.error(f"UTR validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while verifying payment. Please try again."
        )

# ==================== ADMIN ENDPOINTS (Optional - for future use) ====================

@api_router.get("/admin/pending-reviews")
async def get_pending_reviews():
    """Get all payments pending manual review"""
    orders = await db.orders.find(
        {"status": "pending_review"}, 
        {"_id": 0}
    ).to_list(1000)
    
    # Convert ISO strings back to datetime
    for order in orders:
        if isinstance(order.get('created_at'), str):
            order['created_at'] = datetime.fromisoformat(order['created_at'])
        if isinstance(order.get('payment_window_expires'), str):
            order['payment_window_expires'] = datetime.fromisoformat(order['payment_window_expires'])
    
    return {"pending_reviews": orders, "count": len(orders)}

@api_router.post("/admin/approve-payment/{order_id}")
async def admin_approve_payment(order_id: str):
    """Manually approve a payment (admin endpoint)"""
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order['status'] == 'verified':
        raise HTTPException(status_code=400, detail="Order already verified")
    
    verified_at = datetime.now(timezone.utc)
    
    # Update order
    await db.orders.update_one(
        {"order_id": order_id},
        {
            "$set": {
                "status": "verified",
                "verified_at": verified_at.isoformat()
            }
        }
    )
    
    # Update payment record
    await db.payments.update_one(
        {"order_id": order_id},
        {
            "$set": {
                "status": "verified",
                "verified": True
            }
        }
    )
    
    logger.info(f"Admin approved payment for order: {order_id}")
    
    return {"success": True, "message": "Payment approved successfully", "order_id": order_id}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
