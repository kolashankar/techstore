import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ShieldCheck, Smartphone, CheckCircle2, Copy, AlertCircle, ArrowLeft, Clock, Info } from 'lucide-react';
import { UPI_CONFIG, generateUpiLink } from '../lib/upi-utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from '@/components/ui/badge';

const CheckoutPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get product from navigation state or fallback to default
  const product = location.state?.product || {
    name: "Demo Premium Access",
    price: 1.00,
    id: "DEMO-001"
  };

  const [step, setStep] = useState(1);
  const [utr, setUtr] = useState('');
  const [paidAmount, setPaidAmount] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [orderData, setOrderData] = useState(null);
  const [isCreatingOrder, setIsCreatingOrder] = useState(true);
  const [timeRemaining, setTimeRemaining] = useState(null);

  // Automatically select tab based on device
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
        setPaidAmount(data.unique_amount.toString());
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

  const handleAppClick = (appId) => {
    if (!orderData) {
      toast.error('Order not ready. Please wait.');
      return;
    }

    // Generate Link with unique amount
    const link = generateUpiLink(
      appId, 
      orderData.unique_amount.toString(), 
      `Payment for ${orderData.order_id}`
    );
    
    // In a real mobile environment, this would open the app
    window.location.href = link;
    
    // Move to verification step
    setTimeout(() => {
        setStep(2);
        toast.info("Enter payment details after completing the transaction", {
            duration: 5000,
        });
    }, 2000);
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    
    if (!utr || utr.length !== 12) {
      toast.error("Please enter a valid 12-digit UTR/Transaction ID");
      return;
    }

    // Validate that UTR contains only numbers
    if (!/^\d{12}$/.test(utr)) {
      toast.error("UTR must contain only numbers");
      return;
    }

    if (!paidAmount || parseFloat(paidAmount) <= 0) {
      toast.error("Please enter the amount you paid");
      return;
    }

    if (!orderData?.order_id) {
      toast.error("Order ID not found. Please refresh and try again.");
      return;
    }

    setIsVerifying(true);
    
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL;
      
      const response = await fetch(`${backendUrl}/api/verify-payment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          order_id: orderData.order_id,
          utr: utr,
          paid_amount: parseFloat(paidAmount)
        })
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle specific error cases
        if (response.status === 400) {
          toast.error(data.detail || "Payment verification failed");
        } else if (response.status === 404) {
          toast.error("Order not found. Please try again.");
        } else {
          toast.error("Failed to verify payment. Please try again.");
        }
        setIsVerifying(false);
        return;
      }

      // Success or Pending Review
      if (data.success) {
        toast.success(data.message || "Payment Verified Successfully!");
        setStep(3);
      } else {
        toast.info(data.message, { duration: 7000 });
        setStep(3);
      }
      setIsVerifying(false);
      
    } catch (error) {
      console.error('Error verifying payment:', error);
      toast.error("Network error. Please check your connection and try again.");
      setIsVerifying(false);
    }
  };

  const copyVpa = (vpa) => {
    navigator.clipboard.writeText(vpa);
    toast.success("UPI ID copied to clipboard");
  };

  const copyAmount = () => {
    if (orderData?.unique_amount) {
      navigator.clipboard.writeText(orderData.unique_amount.toString());
      toast.success("Amount copied to clipboard");
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
              <p className="text-sm text-slate-500">No payment gateway • Direct UPI payment</p>
            </div>
          </div>

          <div className="w-full max-w-md space-y-6">
            
            {/* Unique Amount Card - Prominent Display */}
            {orderData && step !== 3 && (
              <Card className="border-2 border-primary/20 shadow-xl overflow-hidden bg-gradient-to-br from-white to-blue-50/30">
                <div className="bg-primary px-6 py-4 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-blue-100 font-medium uppercase tracking-wider mb-1">Pay Exact Amount</p>
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-bold">₹{Math.floor(orderData.unique_amount)}</span>
                        <span className="text-4xl font-black text-yellow-300">.{(orderData.unique_amount % 1).toFixed(2).slice(2)}</span>
                      </div>
                    </div>
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={copyAmount}
                      className="bg-white/20 hover:bg-white/30 text-white border-white/20"
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
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
            {step !== 3 && (
              <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <Info className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
                <div className="space-y-1 text-sm">
                  <p className="font-semibold text-amber-900">Important: Pay the EXACT amount shown above</p>
                  <p className="text-amber-700">Including the paise (.{orderData ? (orderData.unique_amount % 1).toFixed(2).slice(2) : '00'}). This unique amount helps us automatically verify your payment.</p>
                </div>
              </div>
            )}

            {/* Payment Flow */}
            <Card className="shadow-lg border-slate-200">
              {step === 3 ? (
                <div className="p-8 text-center space-y-4 animate-in-up">
                  <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle2 className="w-8 h-8" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900">Payment Submitted!</h2>
                  <p className="text-slate-600">Your payment has been recorded. We'll verify it automatically within a few moments.</p>
                  <div className="bg-slate-50 p-4 rounded-lg text-left text-xs space-y-1 mt-4">
                    <p><span className="text-slate-600">Order ID:</span> <span className="font-mono font-medium">{orderData?.order_id}</span></p>
                    <p><span className="text-slate-600">UTR:</span> <span className="font-mono font-medium">{utr}</span></p>
                    <p><span className="text-slate-600">Amount:</span> <span className="font-medium">₹{paidAmount}</span></p>
                  </div>
                  <Button className="w-full mt-6" onClick={() => navigate('/')}>
                    Continue Shopping
                  </Button>
                </div>
              ) : (
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <div className="px-6 pt-6">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="mobile">Mobile App</TabsTrigger>
                      <TabsTrigger value="qr">Scan QR</TabsTrigger>
                    </TabsList>
                  </div>

                  <TabsContent value="mobile" className="p-6 space-y-6 mt-0">
                    {step === 1 && (
                      <div className="space-y-4">
                        <div className="text-center mb-6">
                          <h3 className="text-lg font-semibold text-slate-900">Select UPI App</h3>
                          <p className="text-sm text-slate-500">Tap to pay directly on your device</p>
                        </div>
                        
                        <div className="flex flex-col gap-3">
                          {Object.values(UPI_CONFIG).map((app) => (
                            <button
                              key={app.id}
                              onClick={() => handleAppClick(app.id)}
                              data-testid={`upi-app-${app.id}`}
                              className="flex items-center gap-4 p-4 rounded-xl border-2 border-slate-200 hover:border-primary hover:bg-primary/5 transition-all duration-200 group bg-white shadow-sm hover:shadow-md w-full text-left"
                            >
                              <div 
                                className="w-14 h-14 rounded-full flex items-center justify-center text-white shadow-md group-hover:shadow-lg transition-all duration-200 flex-shrink-0"
                                style={{ backgroundColor: app.color }}
                              >
                                <Smartphone className="w-7 h-7 stroke-[2.5]" />
                              </div>
                              <span className="font-semibold text-lg text-slate-800 group-hover:text-slate-900">{app.name}</span>
                            </button>
                          ))}
                        </div>
                        <div className="text-center pt-2">
                          <button 
                            className="text-xs text-primary hover:underline font-medium"
                            onClick={() => setStep(2)}
                          >
                            Already paid? Enter details manually
                          </button>
                        </div>
                      </div>
                    )}

                    {step === 2 && (
                      <div className="animate-in-up space-y-6">
                        <div className="flex items-start gap-4 p-4 bg-blue-50/50 border border-blue-100 rounded-lg">
                          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 shrink-0" />
                          <div className="space-y-1">
                            <p className="text-sm font-medium text-blue-900">Verify Your Payment</p>
                            <p className="text-xs text-blue-700">
                              Enter the exact amount you paid and your transaction ID (UTR) from the payment confirmation.
                            </p>
                          </div>
                        </div>
                        
                        <form onSubmit={handleVerify} className="space-y-4">
                          <div className="space-y-2">
                            <Label htmlFor="paid-amount">Amount Paid (₹)</Label>
                            <Input 
                              id="paid-amount" 
                              type="number"
                              step="0.01"
                              placeholder={orderData?.unique_amount.toString()}
                              value={paidAmount}
                              onChange={(e) => setPaidAmount(e.target.value)}
                              className="h-12 text-lg font-medium"
                            />
                            <p className="text-xs text-slate-500">Enter the exact amount including paise (e.g., {orderData?.unique_amount})</p>
                          </div>
                          
                          <div className="space-y-2">
                            <Label htmlFor="utr">Transaction ID / UTR</Label>
                            <Input 
                              id="utr" 
                              placeholder="Enter 12-digit UTR number" 
                              value={utr}
                              onChange={(e) => setUtr(e.target.value)}
                              className="h-12 text-lg tracking-widest uppercase font-medium placeholder:normal-case placeholder:tracking-normal"
                              maxLength={12}
                            />
                            <p className="text-xs text-slate-500">Found in transaction details (e.g., 302819382910)</p>
                          </div>
                          <Button 
                            type="submit" 
                            className="w-full h-12 text-base shadow-lg shadow-primary/20" 
                            disabled={isVerifying}
                          >
                            {isVerifying ? "Verifying..." : "Verify Payment"}
                          </Button>
                          <Button 
                            type="button" 
                            variant="ghost" 
                            className="w-full"
                            onClick={() => setStep(1)}
                          >
                            Back to Payment Methods
                          </Button>
                        </form>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="qr" className="p-6 space-y-6 mt-0">
                    <div className="text-center space-y-6">
                      <div className="space-y-2">
                        <h3 className="text-lg font-semibold">Scan to Pay</h3>
                        <p className="text-sm text-slate-500">Use any UPI app to scan and pay</p>
                      </div>

                      {orderData && (
                        <div className="bg-white p-6 rounded-xl border-2 border-dashed border-slate-300 inline-block mx-auto">
                          <img 
                            src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa=${UPI_CONFIG.paytm.vpa}&pn=TechStore&am=${orderData.unique_amount}&cu=INR&tn=Order-${orderData.order_id}`}
                            alt="UPI QR Code"
                            className="w-48 h-48"
                            onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YzZjRmNiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM2Mzc1OGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5RUiBDb2RlPC90ZXh0Pjwvc3ZnPg==';
                            }}
                          />
                        </div>
                      )}

                      <div className="bg-slate-50 p-4 rounded-lg space-y-3 text-left">
                        <p className="text-xs font-medium text-slate-500 uppercase">Or pay to UPI ID</p>
                        {Object.values(UPI_CONFIG).map((app) => (
                          <div key={app.id} className="flex items-center justify-between text-sm group">
                            <span className="text-slate-700 font-medium">{app.name}</span>
                            <button 
                              onClick={() => copyVpa(app.vpa)}
                              className="flex items-center gap-2 text-slate-500 hover:text-primary transition-colors"
                            >
                              <span className="font-mono text-xs">{app.vpa}</span>
                              <Copy className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                      <div className="text-center pt-2">
                        <button 
                          className="text-xs text-primary hover:underline font-medium"
                          onClick={() => {
                            setActiveTab("mobile");
                            setStep(2);
                          }}
                        >
                          Already paid? Click here to verify payment
                        </button>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              )}
            </Card>

            {/* Footer Trust */}
            <div className="flex justify-center gap-6 text-slate-400 grayscale opacity-60">
              <span className="font-semibold text-xs">SECURED BY UPI</span>
              <span className="font-semibold text-xs">100% SAFE</span>
              <span className="font-semibold text-xs">AUTO-VERIFIED</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default CheckoutPage;
