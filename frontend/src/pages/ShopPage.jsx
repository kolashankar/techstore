import React from 'react';
import { ShoppingBag, Star, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const PRODUCTS = [
  {
    id: 1,
    name: "Premium Wireless Headphones",
    price: 2499,
    rating: 4.8,
    image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
    tag: "Best Seller"
  },
  {
    id: 2,
    name: "Smart Fitness Watch",
    price: 1999,
    rating: 4.5,
    image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
    tag: "New Arrival"
  },
  {
    id: 3,
    name: "Ergonomic Office Chair",
    price: 4999,
    rating: 4.9,
    image: "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
    tag: "Premium"
  },
  {
    id: 4,
    name: "Minimalist Mechanical Keyboard",
    price: 3499,
    rating: 4.7,
    image: "https://images.unsplash.com/photo-1587829741301-dc798b91a05c?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
    tag: "Popular"
  }
];

const ShopPage = () => {
  const navigate = useNavigate();

  const handleBuy = (product) => {
    // Navigate to checkout with product details
    navigate('/checkout', { state: { product } });
  };

  return (
    <div className="min-h-screen bg-slate-50/50">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div className="container flex h-16 items-center justify-between px-4 sm:px-8 max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            <div className="bg-primary/10 p-2 rounded-full">
                <ShoppingBag className="h-5 w-5 text-primary" />
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">TechStore</span>
          </div>
          <Button variant="ghost" size="sm" className="hidden sm:flex">
            Sign In
          </Button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-slate-900 text-white py-16 px-4 sm:px-8">
        <div className="max-w-7xl mx-auto flex flex-col items-center text-center space-y-6">
           <Badge variant="outline" className="text-blue-200 border-blue-500/30 bg-blue-500/10 px-4 py-1">
             Summer Sale Live Now
           </Badge>
           <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight">
             Future Tech, <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">Available Today</span>
           </h1>
           <p className="text-slate-400 max-w-2xl text-lg">
             Upgrade your lifestyle with our curated collection of premium gadgets. 
             Secure payments via UPI for instant processing.
           </p>
        </div>
      </section>

      {/* Product Grid */}
      <main className="container py-12 px-4 sm:px-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {PRODUCTS.map((product) => (
            <Card key={product.id} className="group overflow-hidden border-slate-200 hover:shadow-xl transition-all duration-300">
              <div className="relative aspect-square overflow-hidden bg-slate-100">
                <img 
                  src={product.image} 
                  alt={product.name}
                  className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
                <div className="absolute top-3 left-3">
                   <Badge className="bg-white/90 text-slate-900 hover:bg-white shadow-sm backdrop-blur-sm">
                     {product.tag}
                   </Badge>
                </div>
              </div>
              
              <CardContent className="pt-6">
                <div className="flex justify-between items-start mb-2">
                   <h3 className="font-semibold text-lg text-slate-900 line-clamp-1">{product.name}</h3>
                </div>
                <div className="flex items-center gap-1 text-amber-500 text-sm mb-4">
                   <Star className="w-4 h-4 fill-current" />
                   <span className="text-slate-600 font-medium">{product.rating}</span>
                </div>
                <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold text-slate-900">₹{product.price}</span>
                    <span className="text-sm text-slate-400 line-through">₹{product.price + 1000}</span>
                </div>
              </CardContent>

              <CardFooter className="pb-6">
                <Button 
                  onClick={() => handleBuy(product)}
                  className="w-full gap-2 group-hover:bg-primary/90 transition-colors"
                >
                  Buy Now <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-50 border-t border-slate-200 py-12 mt-12">
        <div className="container max-w-7xl mx-auto px-4 text-center text-slate-500">
            <p className="mb-4 text-sm">© 2024 TechStore Demo. All rights reserved.</p>
            <div className="flex justify-center gap-6 text-xs font-medium">
                <a href="#" className="hover:text-slate-900">Privacy Policy</a>
                <a href="#" className="hover:text-slate-900">Terms of Service</a>
                <a href="#" className="hover:text-slate-900">Contact Support</a>
            </div>
        </div>
      </footer>
    </div>
  );
};

export default ShopPage;
