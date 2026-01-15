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
        
        const response = await fetch(`${backendUrl}/api/orders`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            product_id: product.id,
            product_name: product.name,
            amount: product.price
          })
        });

        if (!response.ok) {
          throw new Error('Failed to create order');
        }

        const data = await response.json();
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
      
      // Call backend to initiate payment
      const response = await fetch(`${backendUrl}/api/payment/initiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          order_id: orderData.order_id,
          payment_app: appId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Payment initiation failed');
      }

      const paymentData = await response.json();
      
      if (paymentData.success && paymentData.payment_url) {
        toast.success('Redirecting to payment...');
        
        // Redirect to PhonePe payment page
        setTimeout(() => {
          window.location.href = paymentData.payment_url;
        }, 500);
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
              <p className="text-sm text-slate-500">Direct UPI payment • Instant verification</p>
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
                <p className="font-semibold text-blue-900">Instant Payment Verification</p>
                <p className="text-blue-700">Select your preferred UPI app below. You'll be redirected to complete the payment securely.</p>
              </div>
            </div>

            {/* Payment Selection */}
            <Card className="shadow-lg border-slate-200">
              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <div className="px-6 pt-6">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="mobile">UPI Apps</TabsTrigger>
                    <TabsTrigger value="qr">QR Code</TabsTrigger>
                  </TabsList>
                </div>

                <TabsContent value="mobile" className="p-6 space-y-6 mt-0">
                  <div className="space-y-4">
                    <div className="text-center mb-6">
                      <h3 className="text-lg font-semibold text-slate-900">Select UPI App</h3>
                      <p className="text-sm text-slate-500">Choose your preferred payment app</p>
                    </div>
                    
                    {isProcessing && (
                      <div className="flex items-center justify-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg mb-4">
                        <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                        <div className="text-sm">
                          <p className="font-medium text-blue-900">Processing payment...</p>
                          <p className="text-blue-700">Please wait while we redirect you</p>
                        </div>
                      </div>
                    )}
                    
                    <div className="flex flex-col gap-3">
                      {Object.values(UPI_CONFIG).map((app) => (
                        <button
                          key={app.id}
                          onClick={() => handleAppClick(app.id)}
                          disabled={isProcessing}
                          data-testid={`upi-app-${app.id}`}
                          className="flex items-center gap-4 p-4 rounded-xl border-2 border-slate-200 hover:border-primary hover:bg-primary/5 transition-all duration-200 group bg-white shadow-sm hover:shadow-md w-full text-left disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <div 
                            className="w-14 h-14 rounded-full flex items-center justify-center shadow-md group-hover:shadow-lg transition-all duration-200 flex-shrink-0 overflow-hidden"
                            style={{ backgroundColor: app.logo ? '#ffffff' : app.color }}
                          >
                            {app.logo ? (
                              <img src={app.logo} alt={app.name} className="w-full h-full object-contain p-2" />
                            ) : (
                              <Smartphone className="w-7 h-7 stroke-[2.5] text-white" />
                            )}
                          </div>
                          <span className="font-semibold text-lg text-slate-800 group-hover:text-slate-900">{app.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="qr" className="p-6 space-y-6 mt-0">
                  <div className="text-center space-y-6">
                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold">Coming Soon</h3>
                      <p className="text-sm text-slate-500">QR code payment will be available shortly</p>
                    </div>

                    <div className="bg-slate-100 p-8 rounded-xl">
                      <AlertCircle className="w-16 h-16 text-slate-400 mx-auto" />
                    </div>

                    <p className="text-sm text-slate-600">
                      Please use the "UPI Apps" tab to complete your payment
                    </p>
                  </div>
                </TabsContent>
              </Tabs>
            </Card>

            {/* Footer Trust */}
            <div className="flex justify-center gap-6 text-slate-400 grayscale opacity-60">
              <span className="font-semibold text-xs">SECURED BY UPI</span>
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
