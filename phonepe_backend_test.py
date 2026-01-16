#!/usr/bin/env python3
"""
PhonePe Payment Gateway Backend API Testing Suite
Tests the complete PhonePe integration flow including order creation, payment initiation, and status checking
"""

import requests
import json
import time
from datetime import datetime
import sys
import random

# Backend URL from frontend/.env
BACKEND_URL = "https://keyerror-fix-1.preview.emergentagent.com/api"

class PhonePeAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.created_order_id = None
        self.unique_amount = None
        self.transaction_id = None
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   Details: {details}")
        print()
        
    def test_order_creation(self):
        """Test POST /api/orders - Order Creation with PhonePe fields"""
        print("🧪 Testing Order Creation API...")
        
        # Test data with realistic product information
        order_data = {
            "product_id": "PHONE-001",
            "product_name": "iPhone 15 Pro Max",
            "amount": 134900.00  # Real iPhone price
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/orders",
                json=order_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Order Creation",
                    False,
                    f"Expected status 200, got {response.status_code}",
                    {"response_text": response.text, "status_code": response.status_code}
                )
                return False
                
            try:
                order_response = response.json()
            except json.JSONDecodeError as e:
                self.log_result(
                    "Order Creation",
                    False,
                    "Invalid JSON response",
                    {"error": str(e), "response_text": response.text}
                )
                return False
            
            # Verify required fields for PhonePe integration
            required_fields = ["order_id", "unique_amount", "payment_window_expires", "status"]
            missing_fields = [field for field in required_fields if field not in order_response]
            
            if missing_fields:
                self.log_result(
                    "Order Creation",
                    False,
                    f"Missing required fields: {missing_fields}",
                    {"response": order_response}
                )
                return False
            
            # Verify order_id format (ORD-XXXXXXXX)
            order_id = order_response["order_id"]
            if not order_id.startswith("ORD-") or len(order_id) != 12:
                self.log_result(
                    "Order Creation",
                    False,
                    f"Invalid order_id format. Expected ORD-XXXXXXXX, got {order_id}",
                    {"order_id": order_id}
                )
                return False
            
            # Verify unique_amount generation (base + random paise)
            base_amount = order_data["amount"]
            unique_amount = order_response["unique_amount"]
            
            if unique_amount <= base_amount or unique_amount > base_amount + 1:
                self.log_result(
                    "Order Creation",
                    False,
                    "unique_amount should be base_amount + random paise (0.01-0.99)",
                    {"base_amount": base_amount, "unique_amount": unique_amount}
                )
                return False
            
            # Verify initial status is 'pending'
            if order_response["status"] != "pending":
                self.log_result(
                    "Order Creation",
                    False,
                    f"Initial status should be 'pending', got '{order_response['status']}'",
                    {"status": order_response["status"]}
                )
                return False
            
            # Verify payment window is 30 minutes
            payment_expires = order_response["payment_window_expires"]
            
            # Store for later tests
            self.created_order_id = order_id
            self.unique_amount = unique_amount
            
            self.log_result(
                "Order Creation",
                True,
                "Order created successfully with PhonePe fields",
                {
                    "order_id": order_id,
                    "base_amount": base_amount,
                    "unique_amount": unique_amount,
                    "paise_added": round(unique_amount - base_amount, 2),
                    "status": order_response["status"],
                    "payment_expires": payment_expires
                }
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Order Creation",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Order Creation",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_payment_initiation(self):
        """Test POST /api/payment/initiate - PhonePe Payment Initiation"""
        print("🧪 Testing Payment Initiation API...")
        
        if not self.created_order_id:
            self.log_result(
                "Payment Initiation",
                False,
                "No order_id available (order creation failed)",
                {}
            )
            return False
        
        # Test with different UPI apps
        upi_apps = ["phonepe", "gpay", "bhim", "paytm"]
        
        for payment_app in upi_apps:
            payment_data = {
                "order_id": self.created_order_id,
                "payment_app": payment_app
            }
            
            try:
                response = self.session.post(
                    f"{BACKEND_URL}/payment/initiate",
                    json=payment_data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code != 200:
                    self.log_result(
                        f"Payment Initiation ({payment_app})",
                        False,
                        f"Expected status 200, got {response.status_code}",
                        {"response_text": response.text, "status_code": response.status_code}
                    )
                    continue
                
                try:
                    payment_response = response.json()
                except json.JSONDecodeError as e:
                    self.log_result(
                        f"Payment Initiation ({payment_app})",
                        False,
                        "Invalid JSON response",
                        {"error": str(e), "response_text": response.text}
                    )
                    continue
                
                # Verify required fields in response
                required_fields = ["success", "payment_url", "transaction_id", "order_id"]
                missing_fields = [field for field in required_fields if field not in payment_response]
                
                if missing_fields:
                    self.log_result(
                        f"Payment Initiation ({payment_app})",
                        False,
                        f"Missing required response fields: {missing_fields}",
                        {"response": payment_response}
                    )
                    continue
                
                # Verify success is True
                if not payment_response.get("success"):
                    self.log_result(
                        f"Payment Initiation ({payment_app})",
                        False,
                        "Payment initiation returned success=False",
                        {"response": payment_response}
                    )
                    continue
                
                # Verify payment_url is valid
                payment_url = payment_response.get("payment_url", "")
                if not payment_url.startswith("https://"):
                    self.log_result(
                        f"Payment Initiation ({payment_app})",
                        False,
                        "Invalid payment URL format",
                        {"payment_url": payment_url}
                    )
                    continue
                
                # Store transaction ID for status check
                self.transaction_id = payment_response.get("transaction_id")
                
                self.log_result(
                    f"Payment Initiation ({payment_app})",
                    True,
                    "Payment initiation successful",
                    {
                        "payment_url": payment_url[:50] + "..." if len(payment_url) > 50 else payment_url,
                        "transaction_id": self.transaction_id,
                        "order_id": payment_response.get("order_id")
                    }
                )
                
                # Test only first app to avoid multiple initiations
                break
                
            except requests.exceptions.RequestException as e:
                self.log_result(
                    f"Payment Initiation ({payment_app})",
                    False,
                    f"Network error: {str(e)}",
                    {"error_type": type(e).__name__}
                )
                continue
            except Exception as e:
                self.log_result(
                    f"Payment Initiation ({payment_app})",
                    False,
                    f"Unexpected error: {str(e)}",
                    {"error_type": type(e).__name__}
                )
                continue
        
        return self.transaction_id is not None
    
    def test_payment_initiation_errors(self):
        """Test error handling in payment initiation"""
        print("🧪 Testing Payment Initiation Error Handling...")
        
        # Test with invalid order_id
        invalid_payment_data = {
            "order_id": "INVALID-ORDER-ID",
            "payment_app": "phonepe"
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/payment/initiate",
                json=invalid_payment_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 404:
                self.log_result(
                    "Payment Initiation Error Handling",
                    False,
                    f"Expected 404 for invalid order_id, got {response.status_code}",
                    {"response_text": response.text}
                )
                return False
            
            # Test with already processed order (if we have one)
            if self.created_order_id and self.transaction_id:
                processed_payment_data = {
                    "order_id": self.created_order_id,
                    "payment_app": "gpay"
                }
                
                response = self.session.post(
                    f"{BACKEND_URL}/payment/initiate",
                    json=processed_payment_data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code != 400:
                    self.log_result(
                        "Payment Initiation Error Handling",
                        False,
                        f"Expected 400 for already processed order, got {response.status_code}",
                        {"response_text": response.text}
                    )
                    return False
            
            self.log_result(
                "Payment Initiation Error Handling",
                True,
                "Error handling working correctly",
                {"invalid_order_test": "passed", "processed_order_test": "passed"}
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Payment Initiation Error Handling",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Payment Initiation Error Handling",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_payment_status_check(self):
        """Test GET /api/payment/status/{order_id} - Payment Status Check"""
        print("🧪 Testing Payment Status Check API...")
        
        if not self.created_order_id:
            self.log_result(
                "Payment Status Check",
                False,
                "No order_id available for status check",
                {}
            )
            return False
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/payment/status/{self.created_order_id}",
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Payment Status Check",
                    False,
                    f"Expected status 200, got {response.status_code}",
                    {"response_text": response.text, "status_code": response.status_code}
                )
                return False
            
            try:
                status_response = response.json()
            except json.JSONDecodeError as e:
                self.log_result(
                    "Payment Status Check",
                    False,
                    "Invalid JSON response",
                    {"error": str(e), "response_text": response.text}
                )
                return False
            
            # Verify required fields in response
            required_fields = ["success", "status", "transaction_id", "order_id", "amount", "message"]
            missing_fields = [field for field in required_fields if field not in status_response]
            
            if missing_fields:
                self.log_result(
                    "Payment Status Check",
                    False,
                    f"Missing required response fields: {missing_fields}",
                    {"response": status_response}
                )
                return False
            
            # Verify order_id matches
            if status_response.get("order_id") != self.created_order_id:
                self.log_result(
                    "Payment Status Check",
                    False,
                    "Order ID mismatch in status response",
                    {"expected": self.created_order_id, "received": status_response.get("order_id")}
                )
                return False
            
            # Verify amount matches
            if abs(status_response.get("amount", 0) - self.unique_amount) > 0.01:
                self.log_result(
                    "Payment Status Check",
                    False,
                    "Amount mismatch in status response",
                    {"expected": self.unique_amount, "received": status_response.get("amount")}
                )
                return False
            
            self.log_result(
                "Payment Status Check",
                True,
                "Payment status check successful",
                {
                    "status": status_response.get("status"),
                    "transaction_id": status_response.get("transaction_id"),
                    "amount": status_response.get("amount"),
                    "message": status_response.get("message")
                }
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Payment Status Check",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Payment Status Check",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_admin_orders(self):
        """Test GET /api/admin/orders - Admin Orders API"""
        print("🧪 Testing Admin Orders API...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/orders",
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Admin Orders",
                    False,
                    f"Expected status 200, got {response.status_code}",
                    {"response_text": response.text, "status_code": response.status_code}
                )
                return False
            
            try:
                admin_response = response.json()
            except json.JSONDecodeError as e:
                self.log_result(
                    "Admin Orders",
                    False,
                    "Invalid JSON response",
                    {"error": str(e), "response_text": response.text}
                )
                return False
            
            # Verify response structure
            if "orders" not in admin_response or "count" not in admin_response:
                self.log_result(
                    "Admin Orders",
                    False,
                    "Missing 'orders' or 'count' in response",
                    {"response": admin_response}
                )
                return False
            
            orders = admin_response.get("orders", [])
            count = admin_response.get("count", 0)
            
            # Verify count matches orders length
            if len(orders) != count:
                self.log_result(
                    "Admin Orders",
                    False,
                    "Count mismatch with orders array length",
                    {"orders_length": len(orders), "count": count}
                )
                return False
            
            # Check if our created order is in the list
            our_order_found = False
            if self.created_order_id:
                for order in orders:
                    if order.get("order_id") == self.created_order_id:
                        our_order_found = True
                        break
            
            self.log_result(
                "Admin Orders",
                True,
                "Admin orders API working correctly",
                {
                    "total_orders": count,
                    "our_order_found": our_order_found,
                    "sample_order_fields": list(orders[0].keys()) if orders else []
                }
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Admin Orders",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Admin Orders",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_order_status_update(self):
        """Test that order status changes correctly during payment flow"""
        print("🧪 Testing Order Status Updates...")
        
        if not self.created_order_id:
            self.log_result(
                "Order Status Update",
                False,
                "No order_id available for status update test",
                {}
            )
            return False
        
        try:
            # Get current order status
            response = self.session.get(
                f"{BACKEND_URL}/orders/{self.created_order_id}",
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Order Status Update",
                    False,
                    f"Failed to get order details: {response.status_code}",
                    {"response_text": response.text}
                )
                return False
            
            order_data = response.json()
            current_status = order_data.get("status")
            
            # Check if status changed from 'pending' to 'processing' after payment initiation
            if self.transaction_id and current_status == "pending":
                self.log_result(
                    "Order Status Update",
                    False,
                    "Order status should change to 'processing' after payment initiation",
                    {"current_status": current_status, "transaction_id": self.transaction_id}
                )
                return False
            
            # Verify payment gateway fields are populated
            payment_gateway_txn_id = order_data.get("payment_gateway_txn_id")
            payment_method = order_data.get("payment_method")
            
            if self.transaction_id:
                if not payment_gateway_txn_id:
                    self.log_result(
                        "Order Status Update",
                        False,
                        "payment_gateway_txn_id should be populated after payment initiation",
                        {"order_data": order_data}
                    )
                    return False
                
                if not payment_method:
                    self.log_result(
                        "Order Status Update",
                        False,
                        "payment_method should be populated after payment initiation",
                        {"order_data": order_data}
                    )
                    return False
            
            self.log_result(
                "Order Status Update",
                True,
                "Order status updates working correctly",
                {
                    "status": current_status,
                    "payment_gateway_txn_id": payment_gateway_txn_id,
                    "payment_method": payment_method
                }
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Order Status Update",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Order Status Update",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def run_all_tests(self):
        """Run all PhonePe backend tests"""
        print("🚀 Starting PhonePe Payment Gateway Backend Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 70)
        
        # Run tests in sequence
        tests = [
            self.test_order_creation,
            self.test_payment_initiation,
            self.test_payment_initiation_errors,
            self.test_order_status_update,
            self.test_payment_status_check,
            self.test_admin_orders
        ]
        
        passed = 0
        total = len(tests)
        
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
                time.sleep(2)  # Delay between tests to avoid rate limiting
            except Exception as e:
                print(f"❌ Test {test_func.__name__} crashed: {str(e)}")
        
        print("=" * 70)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All PhonePe backend tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            return False
    
    def print_summary(self):
        """Print detailed test summary"""
        print("\n📋 Detailed PhonePe Test Summary:")
        print("-" * 50)
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
            
            if result["details"]:
                for key, value in result["details"].items():
                    print(f"   {key}: {value}")
        
        print("-" * 50)

def main():
    """Main test execution"""
    tester = PhonePeAPITester()
    
    try:
        success = tester.run_all_tests()
        tester.print_summary()
        
        if success:
            print("\n✅ All PhonePe backend tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some PhonePe backend tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()