import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { XCircle, Loader2, AlertTriangle, ArrowLeft, RotateCcw } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const PaymentFailedPage = () => {
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

  const handleRetry = () => {
    if (orderData) {
      navigate('/checkout', { 
        state: { 
          product: {
            id: orderData.product_id,
            name: orderData.product_name,
            price: orderData.base_amount
          }
        } 
      });
    } else {
      navigate('/');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-red-50/30 to-slate-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-8 text-center">
          <Loader2 className="w-12 h-12 text-red-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Checking payment status...</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-red-50/30 to-slate-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-2xl border-red-200">
        <CardContent className="p-8 text-center space-y-6">
          {/* Failure Icon */}
          <div className="relative">
            <div className="w-20 h-20 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <XCircle className="w-10 h-10" strokeWidth={2.5} />
            </div>
            <div className="absolute inset-0 bg-red-400 rounded-full blur-2xl opacity-20"></div>
          </div>

          {/* Failure Message */}
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-slate-900">Payment Failed</h1>
            <p className="text-slate-600">Your payment could not be processed</p>
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
                <span className="text-sm text-slate-600">Amount</span>
                <span className="text-lg font-bold text-slate-900">₹{orderData.unique_amount}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">Status</span>
                <Badge variant="destructive" className="text-xs">Payment Failed</Badge>
              </div>
            </div>
          )}

          {/* Common Reasons */}
          <div className="bg-amber-50 p-4 rounded-lg border border-amber-200 text-left">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
              <div className="space-y-2">
                <p className="text-sm font-semibold text-amber-900">Common reasons for failure:</p>
                <ul className="text-xs text-amber-700 space-y-1 list-disc list-inside">
                  <li>Insufficient balance in account</li>
                  <li>Payment cancelled by user</li>
                  <li>Bank server timeout</li>
                  <li>Incorrect UPI PIN entered</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3 pt-2">
            <Button 
              className="w-full h-12 text-base shadow-lg" 
              onClick={handleRetry}
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
            <Button 
              variant="outline" 
              className="w-full"
              onClick={() => navigate('/')}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Home
            </Button>
          </div>

          {/* Support Info */}
          <div className="pt-4 border-t">
            <p className="text-xs text-slate-500">
              Need help? Contact our support team for assistance
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentFailedPage;
