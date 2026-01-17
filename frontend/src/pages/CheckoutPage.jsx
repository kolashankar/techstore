import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ShieldCheck, Smartphone, CheckCircle2, AlertCircle, ArrowLeft, Clock, Info, Loader2 } from 'lucide-react';
import { UPI_CONFIG } from '../lib/upi-utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from '@/components/ui/badge';

const CheckoutPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const product = location.state?.product || {
    name: "Demo Premium Access",
    price: 1.00,
    id: "DEMO-001"
  };

  const [isProcessing, setIsProcessing] = useState(false);
  const [orderData, setOrderData] = useState(null);
  const [isCreatingOrder, setIsCreatingOrder] = useState(true);
  const [timeRemaining, setTimeRemaining] = useState(null);

  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  const defaultTab = isMobile ? "mobile" : "qr";
  const [activeTab, setActiveTab] = useState(defaultTab);

  // Create order when component mounts
  useEffect(() => {
    const createOrder = async () => {
      try {
        setIsCreatingOrder(true);
        const backendUrl = process.env.REACT_APP_BACKEND_URL;
        
        // Ensure amount is a valid number
        const amount = typeof product.price === 'number' ? product.price : parseFloat(product.price);
        
        if (isNaN(amount)) {
          throw new Error('Invalid product price');
        }
        
        const payload = {
          product_id: String(product.id),
          product_name: String(product.name),
          amount: amount
        };
        
        console.log('Creating order with payload:', payload);
        
        const response = await fetch(`${backendUrl}/api/orders`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          console.error('Order creation failed:', response.status, errorData);
          throw new Error(errorData.detail || 'Failed to create order');
        }

        const data = await response.json();
        console.log('Order created successfully:', data);
        setOrderData(data);
        setIsCreatingOrder(false);
      } catch (error) {
        console.error('Error creating order:', error);
        toast.error('Failed to create order. Please try again.');
        setIsCreatingOrder(false);
      }
    };

    createOrder();
  }, [product]);

  // Timer countdown for payment window
  useEffect(() => {
    if (!orderData?.payment_window_expires) return;

    const timer = setInterval(() => {
      const expiryTime = new Date(orderData.payment_window_expires);
      const now = new Date();
      const diff = expiryTime - now;

      if (diff <= 0) {
        setTimeRemaining('Expired');
        clearInterval(timer);
      } else {
        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        setTimeRemaining(`${minutes}:${seconds.toString().padStart(2, '0')}`);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [orderData]);

  // Function to initialize Paytm payment
  const initializePaytm = (config) => {
    return new Promise((resolve, reject) => {
      // Remove existing Paytm script if any
      const existingScript = document.getElementById('paytm-checkout-js');
      if (existingScript) {
        existingScript.remove();
      }

      // Create and load Paytm checkout script
      const script = document.createElement('script');
      script.id = 'paytm-checkout-js';
      script.type = 'application/javascript';
      script.crossOrigin = 'anonymous';
      
      // Use staging or production URL based on environment
      script.src = `https://securegw-stage.paytm.in/merchantpgpui/checkoutjs/merchants/${config.mid}.js`;
      
      script.onload = () => {
        console.log('Paytm script loaded successfully');
        resolve();
      };
      
      script.onerror = (error) => {
        console.error('Failed to load Paytm script:', error);
        reject(new Error('Failed to load payment gateway'));
      };
      
      document.body.appendChild(script);
    });
  };

  const handleAppClick = async (appId) => {
    if (!orderData) {
      toast.error('Order not ready. Please wait.');
      return;
    }

    if (isProcessing) {
      return;
    }

    setIsProcessing(true);

    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL;
      
      // Call backend to initiate payment and get transaction token
      const response = await fetch(`${backendUrl}/api/payment/initiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          order_id: orderData.order_id,
          customer_id: `CUST_${orderData.order_id}`,
          customer_email: 'customer@example.com',
          customer_mobile: '9999999999'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Payment initiation failed');
      }

      const paymentData = await response.json();
      
      if (paymentData.success && paymentData.transaction_token) {
        console.log('Payment data received:', paymentData);
        toast.success('Opening Paytm payment...');
        
        // Initialize Paytm checkout
        await initializePaytm({
          mid: paymentData.merchant_id,
          orderId: paymentData.order_id
        });
        
        // Configure Paytm checkout
        const config = {
          root: '',
          flow: 'DEFAULT',
          data: {
            orderId: paymentData.order_id,
            token: paymentData.transaction_token,
            tokenType: 'TXN_TOKEN',
            amount: paymentData.amount.toString()
          },
          merchant: {
            mid: paymentData.merchant_id,
            name: 'TechStore',
            redirect: false
          },
          handler: {
            notifyMerchant: function(eventName, data) {
              console.log('Paytm Event:', eventName, data);
            },
            transactionStatus: function(data) {
              console.log('Payment Status:', data);
              // The callback will handle the redirect
              window.close();
            }
          }
        };

        // Check if Paytm object is available
        if (window.Paytm && window.Paytm.CheckoutJS) {
          window.Paytm.CheckoutJS.init(config).then(function() {
            console.log('Paytm Checkout initialized');
            window.Paytm.CheckoutJS.invoke();
          }).catch(function(error) {
            console.error('Error initializing Paytm:', error);
            toast.error('Failed to open payment page');
            setIsProcessing(false);
          });
        } else {
          throw new Error('Paytm checkout library not loaded');
        }
        
      } else {
        throw new Error('Invalid payment response');
      }
      
    } catch (error) {
      console.error('Error initiating payment:', error);
      toast.error(error.message || 'Failed to initiate payment. Please try again.');
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50 py-8 px-4 sm:px-6 lg:px-8 flex flex-col items-center">
      
      {/* Loading state while creating order */}
      {isCreatingOrder ? (
        <div className="w-full max-w-md mt-20">
          <Card className="p-8 border-slate-200 shadow-xl">
            <div className="flex flex-col items-center justify-center space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              <p className="text-slate-600">Preparing your order...</p>
            </div>
          </Card>
        </div>
      ) : (
        <>
          {/* Header */}
          <div className="w-full max-w-md mb-8 relative">
            <Button 
              variant="ghost" 
              size="sm" 
              className="absolute left-0 top-0 -ml-2 text-slate-500 hover:text-slate-900"
              onClick={() => navigate('/')}
            >
              <ArrowLeft className="w-4 h-4 mr-1" /> Back
            </Button>
            <div className="text-center space-y-2 pt-8">
              <div className="inline-flex items-center justify-center p-3 bg-white rounded-full shadow-md mb-4">
                <ShieldCheck className="w-8 h-8 text-primary" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">Secure Checkout</h1>
              <p className="text-sm text-slate-500">Paytm Payment Gateway • Instant verification</p>
            </div>
          </div>

          <div className="w-full max-w-md space-y-6">
            
            {/* Unique Amount Card */}
            {orderData && (
              <Card className="border-2 border-primary/20 shadow-xl overflow-hidden bg-gradient-to-br from-white to-blue-50/30">
                <div className="bg-primary px-6 py-4 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-blue-100 font-medium uppercase tracking-wider mb-1">Total Amount</p>
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-bold">₹{Math.floor(orderData.unique_amount)}</span>
                        <span className="text-4xl font-black text-yellow-300">.{(orderData.unique_amount % 1).toFixed(2).slice(2)}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <CardContent className="pt-4 pb-5">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-600">Product</span>
                      <span className="font-medium text-slate-900 line-clamp-1 max-w-[200px] text-right">{product.name}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-600">Order ID</span>
                      <Badge variant="outline" className="font-mono text-xs">{orderData.order_id}</Badge>
                    </div>
                    {timeRemaining && (
                      <div className="flex justify-between items-center text-sm pt-2 border-t">
                        <span className="text-slate-600 flex items-center gap-1.5">
                          <Clock className="w-4 h-4" />
                          Time Remaining
                        </span>
                        <span className={`font-bold font-mono ${timeRemaining === 'Expired' ? 'text-red-600' : 'text-green-600'}`}>
                          {timeRemaining}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Important Notice */}
            <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <Info className="w-5 h-5 text-blue-600 mt-0.5 shrink-0" />
              <div className="space-y-1 text-sm">
                <p className="font-semibold text-blue-900">Secure Paytm Payment</p>
                <p className="text-blue-700">Click below to pay via Paytm. Supports UPI, Cards, Net Banking, and Wallets.</p>
              </div>
            </div>

            {/* Payment Button */}
            <Card className="shadow-lg border-slate-200">
              <div className="p-6 space-y-4">
                <div className="text-center">
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">Complete Payment</h3>
                  <p className="text-sm text-slate-500">Pay securely via Paytm Payment Gateway</p>
                </div>
                
                {isProcessing && (
                  <div className="flex items-center justify-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg mb-4">
                    <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                    <div className="text-sm">
                      <p className="font-medium text-blue-900">Opening Paytm...</p>
                      <p className="text-blue-700">Please wait</p>
                    </div>
                  </div>
                )}
                
                <Button
                  onClick={() => handleAppClick('paytm')}
                  disabled={isProcessing || !orderData}
                  className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 shadow-lg hover:shadow-xl transition-all"
                >
                  {isProcessing ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Opening Payment...</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5" />
                      <span>Pay ₹{orderData?.unique_amount?.toFixed(2)} via Paytm</span>
                    </div>
                  )}
                </Button>

                <div className="text-center text-xs text-slate-500 pt-2">
                  <p>Supports UPI, Credit/Debit Cards, Net Banking & Wallets</p>
                </div>
              </div>
            </Card>

            {/* Footer Trust */}
            <div className="flex justify-center gap-6 text-slate-400 grayscale opacity-60">
              <span className="font-semibold text-xs">SECURED BY PAYTM</span>
              <span className="font-semibold text-xs">100% SAFE</span>
              <span className="font-semibold text-xs">INSTANT VERIFY</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default CheckoutPage;
