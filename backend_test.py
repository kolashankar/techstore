#!/usr/bin/env python3
"""
TechStore Backend API Testing Suite
Tests order creation and payment verification flows
"""

import requests
import json
import time
from datetime import datetime
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://techstore-fix-1.preview.emergentagent.com/api"

class TechStoreAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.created_order_id = None
        self.unique_amount = None
        
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
        """Test POST /api/orders - Order Creation"""
        print("🧪 Testing Order Creation API...")
        
        # Test data as specified in requirements
        order_data = {
            "product_id": "TEST-001",
            "product_name": "Test Product",
            "amount": 499.00
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/orders",
                json=order_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            # Check status code - should be 200, NOT 422
            if response.status_code != 200:
                self.log_result(
                    "Order Creation",
                    False,
                    f"Expected status 200, got {response.status_code}",
                    {"response_text": response.text, "status_code": response.status_code}
                )
                return False
                
            # Parse response
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
            
            # Verify required fields
            required_fields = ["order_id", "unique_amount", "payment_window_expires"]
            missing_fields = [field for field in required_fields if field not in order_response]
            
            if missing_fields:
                self.log_result(
                    "Order Creation",
                    False,
                    f"Missing required fields: {missing_fields}",
                    {"response": order_response}
                )
                return False
            
            # Verify unique_amount is different from base_amount
            base_amount = order_data["amount"]
            unique_amount = order_response["unique_amount"]
            
            if unique_amount == base_amount:
                self.log_result(
                    "Order Creation",
                    False,
                    "unique_amount should be different from base_amount",
                    {"base_amount": base_amount, "unique_amount": unique_amount}
                )
                return False
            
            # Verify unique_amount format (should have paise)
            if unique_amount <= base_amount or unique_amount > base_amount + 1:
                self.log_result(
                    "Order Creation",
                    False,
                    "unique_amount should be base_amount + random paise (0.01-0.99)",
                    {"base_amount": base_amount, "unique_amount": unique_amount}
                )
                return False
            
            # Store for later tests
            self.created_order_id = order_response["order_id"]
            self.unique_amount = unique_amount
            
            self.log_result(
                "Order Creation",
                True,
                "Order created successfully",
                {
                    "order_id": self.created_order_id,
                    "base_amount": base_amount,
                    "unique_amount": unique_amount,
                    "difference": round(unique_amount - base_amount, 2)
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
    
    def test_get_order(self):
        """Test GET /api/orders/{order_id}"""
        print("🧪 Testing Get Order API...")
        
        if not self.created_order_id:
            self.log_result(
                "Get Order",
                False,
                "No order_id available (order creation failed)",
                {}
            )
            return False
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/orders/{self.created_order_id}",
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Get Order",
                    False,
                    f"Expected status 200, got {response.status_code}",
                    {"response_text": response.text, "status_code": response.status_code}
                )
                return False
            
            try:
                order_data = response.json()
            except json.JSONDecodeError as e:
                self.log_result(
                    "Get Order",
                    False,
                    "Invalid JSON response",
                    {"error": str(e), "response_text": response.text}
                )
                return False
            
            # Verify order details
            if order_data.get("order_id") != self.created_order_id:
                self.log_result(
                    "Get Order",
                    False,
                    "Order ID mismatch",
                    {"expected": self.created_order_id, "received": order_data.get("order_id")}
                )
                return False
            
            self.log_result(
                "Get Order",
                True,
                "Order retrieved successfully",
                {
                    "order_id": order_data.get("order_id"),
                    "status": order_data.get("status"),
                    "unique_amount": order_data.get("unique_amount")
                }
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Get Order",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Get Order",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_payment_verification(self):
        """Test POST /api/verify-payment"""
        print("🧪 Testing Payment Verification API...")
        
        if not self.created_order_id or not self.unique_amount:
            self.log_result(
                "Payment Verification",
                False,
                "No order data available (order creation failed)",
                {}
            )
            return False
        
        # Test payment verification
        payment_data = {
            "order_id": self.created_order_id,
            "utr": "123456789012",  # Valid 12-digit UTR
            "paid_amount": self.unique_amount
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/verify-payment",
                json=payment_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code not in [200, 400]:  # 400 might be expected for some validation
                self.log_result(
                    "Payment Verification",
                    False,
                    f"Unexpected status code: {response.status_code}",
                    {"response_text": response.text, "status_code": response.status_code}
                )
                return False
            
            try:
                payment_response = response.json()
            except json.JSONDecodeError as e:
                self.log_result(
                    "Payment Verification",
                    False,
                    "Invalid JSON response",
                    {"error": str(e), "response_text": response.text}
                )
                return False
            
            # Check required fields in response
            required_fields = ["success", "message", "order_id", "utr"]
            missing_fields = [field for field in required_fields if field not in payment_response]
            
            if missing_fields:
                self.log_result(
                    "Payment Verification",
                    False,
                    f"Missing required response fields: {missing_fields}",
                    {"response": payment_response}
                )
                return False
            
            # Verify confidence score is present
            if "confidence_score" not in payment_response:
                self.log_result(
                    "Payment Verification",
                    False,
                    "Missing confidence_score in response",
                    {"response": payment_response}
                )
                return False
            
            # Check if verification logic works
            confidence_score = payment_response.get("confidence_score", 0)
            success = payment_response.get("success", False)
            
            self.log_result(
                "Payment Verification",
                True,
                f"Payment verification completed (confidence: {confidence_score}%, success: {success})",
                {
                    "confidence_score": confidence_score,
                    "success": success,
                    "message": payment_response.get("message"),
                    "order_id": payment_response.get("order_id"),
                    "utr": payment_response.get("utr")
                }
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Payment Verification",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Payment Verification",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_duplicate_utr(self):
        """Test duplicate UTR validation"""
        print("🧪 Testing Duplicate UTR Validation...")
        
        # Create a second order first
        order_data = {
            "product_id": "TEST-002",
            "product_name": "Second Test Product",
            "amount": 299.00
        }
        
        try:
            # Create second order
            response = self.session.post(
                f"{BACKEND_URL}/orders",
                json=order_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Duplicate UTR Test",
                    False,
                    f"Failed to create second order: {response.status_code}",
                    {"response_text": response.text}
                )
                return False
            
            second_order = response.json()
            second_order_id = second_order["order_id"]
            
            # Try to use the same UTR as before
            duplicate_payment_data = {
                "order_id": second_order_id,
                "utr": "123456789012",  # Same UTR as previous test
                "paid_amount": second_order["unique_amount"]
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/verify-payment",
                json=duplicate_payment_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            # Should return 400 for duplicate UTR
            if response.status_code != 400:
                self.log_result(
                    "Duplicate UTR Test",
                    False,
                    f"Expected status 400 for duplicate UTR, got {response.status_code}",
                    {"response_text": response.text, "status_code": response.status_code}
                )
                return False
            
            try:
                error_response = response.json()
            except json.JSONDecodeError:
                error_response = {"detail": response.text}
            
            # Check if error message mentions duplicate UTR
            error_message = error_response.get("detail", "").lower()
            if "utr" not in error_message or "already" not in error_message:
                self.log_result(
                    "Duplicate UTR Test",
                    False,
                    "Error message doesn't properly indicate duplicate UTR",
                    {"error_response": error_response}
                )
                return False
            
            self.log_result(
                "Duplicate UTR Test",
                True,
                "Duplicate UTR properly rejected",
                {"error_message": error_response.get("detail")}
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                "Duplicate UTR Test",
                False,
                f"Network error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
        except Exception as e:
            self.log_result(
                "Duplicate UTR Test",
                False,
                f"Unexpected error: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_utr_validation(self):
        """Test UTR format validation"""
        print("🧪 Testing UTR Format Validation...")
        
        if not self.created_order_id:
            self.log_result(
                "UTR Validation",
                False,
                "No order_id available for UTR validation test",
                {}
            )
            return False
        
        # Test invalid UTR formats
        invalid_utrs = [
            "12345",  # Too short
            "1234567890123",  # Too long
            "12345678901a",  # Contains letter
            "123 456 789 012",  # Contains spaces (should be handled)
        ]
        
        for invalid_utr in invalid_utrs:
            payment_data = {
                "order_id": self.created_order_id,
                "utr": invalid_utr,
                "paid_amount": self.unique_amount
            }
            
            try:
                response = self.session.post(
                    f"{BACKEND_URL}/verify-payment",
                    json=payment_data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                # Should return 400 for invalid UTR
                if response.status_code != 400:
                    self.log_result(
                        "UTR Validation",
                        False,
                        f"Invalid UTR '{invalid_utr}' was accepted (status: {response.status_code})",
                        {"utr": invalid_utr, "response_text": response.text}
                    )
                    return False
                    
            except requests.exceptions.RequestException as e:
                self.log_result(
                    "UTR Validation",
                    False,
                    f"Network error testing UTR '{invalid_utr}': {str(e)}",
                    {"utr": invalid_utr, "error_type": type(e).__name__}
                )
                return False
        
        self.log_result(
            "UTR Validation",
            True,
            "UTR format validation working correctly",
            {"tested_invalid_utrs": invalid_utrs}
        )
        return True
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting TechStore Backend API Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        # Run tests in sequence
        tests = [
            self.test_order_creation,
            self.test_get_order,
            self.test_payment_verification,
            self.test_duplicate_utr,
            self.test_utr_validation
        ]
        
        passed = 0
        total = len(tests)
        
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
                time.sleep(1)  # Small delay between tests
            except Exception as e:
                print(f"❌ Test {test_func.__name__} crashed: {str(e)}")
        
        print("=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            return False
    
    def print_summary(self):
        """Print detailed test summary"""
        print("\n📋 Detailed Test Summary:")
        print("-" * 40)
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
            
            if result["details"]:
                for key, value in result["details"].items():
                    print(f"   {key}: {value}")
        
        print("-" * 40)

def main():
    """Main test execution"""
    tester = TechStoreAPITester()
    
    try:
        success = tester.run_all_tests()
        tester.print_summary()
        
        if success:
            print("\n✅ All backend tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some backend tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()