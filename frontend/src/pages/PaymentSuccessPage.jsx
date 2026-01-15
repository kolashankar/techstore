import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, Package, ArrowRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const PaymentSuccessPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('order_id');
  
  const [orderData, setOrderData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchOrderDetails = async () => {
      if (!orderId) {
        setIsLoading(false);
        return;
      }

      try {
        const backendUrl = process.env.REACT_APP_BACKEND_URL;
        const response = await fetch(`${backendUrl}/api/orders/${orderId}`);
        
        if (response.ok) {
          const data = await response.json();
          setOrderData(data);
        }
      } catch (error) {
        console.error('Error fetching order:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchOrderDetails();
  }, [orderId]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-green-50/30 to-slate-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-8 text-center">
          <Loader2 className="w-12 h-12 text-green-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Verifying your payment...</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-green-50/30 to-slate-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-2xl border-green-200">
        <CardContent className="p-8 text-center space-y-6">
          {/* Success Icon */}
          <div className="relative">
            <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
              <CheckCircle2 className="w-10 h-10" strokeWidth={2.5} />
            </div>
            <div className="absolute inset-0 bg-green-400 rounded-full blur-2xl opacity-20 animate-pulse"></div>
          </div>

          {/* Success Message */}
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-slate-900">Payment Successful!</h1>
            <p className="text-slate-600">Your order has been confirmed and verified</p>
          </div>

          {/* Order Details */}
          {orderData && (
            <div className="bg-slate-50 p-5 rounded-lg space-y-3 text-left border border-slate-200">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">Order ID</span>
                <Badge variant="outline" className="font-mono text-xs">{orderData.order_id}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">Product</span>
                <span className="text-sm font-medium text-slate-900 max-w-[200px] text-right line-clamp-1">
                  {orderData.product_name}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t">
                <span className="text-sm text-slate-600">Amount Paid</span>
                <span className="text-lg font-bold text-green-600">₹{orderData.unique_amount}</span>
              </div>
              {orderData.payment_method && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Payment Method</span>
                  <span className="text-sm font-medium text-slate-900 uppercase">{orderData.payment_method}</span>
                </div>
              )}
            </div>
          )}

          {/* What's Next */}
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 text-left">
            <div className="flex items-start gap-3">
              <Package className="w-5 h-5 text-blue-600 mt-0.5 shrink-0" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-blue-900">What's Next?</p>
                <p className="text-xs text-blue-700">
                  You'll receive a confirmation email shortly with your order details and delivery information.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3 pt-2">
            <Button 
              className="w-full h-12 text-base shadow-lg shadow-primary/20" 
              onClick={() => navigate('/')}
            >
              Continue Shopping
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
            <Button 
              variant="outline" 
              className="w-full"
              onClick={() => navigate('/orders')}
            >
              View My Orders
            </Button>
          </div>

          {/* Trust Badge */}
          <div className="pt-4 border-t">
            <p className="text-xs text-slate-500">
              <CheckCircle2 className="w-3 h-3 inline mr-1 text-green-600" />
              Payment verified and secured
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentSuccessPage;
