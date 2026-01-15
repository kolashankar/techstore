import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ShopPage from './pages/ShopPage';
import CheckoutPage from './pages/CheckoutPage';
import PaymentSuccessPage from './pages/PaymentSuccessPage';
import PaymentFailedPage from './pages/PaymentFailedPage';
import { Toaster } from './components/ui/sonner';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary">
        <Routes>
          <Route path="/" element={<ShopPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/payment-success" element={<PaymentSuccessPage />} />
          <Route path="/payment-failed" element={<PaymentFailedPage />} />
        </Routes>
        <Toaster />
      </div>
    </Router>
  );
}

export default App;
