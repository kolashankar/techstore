export const UPI_CONFIG = {
  gpay: {
    id: "gpay",
    name: "Google Pay",
    vpa: "kolashankar113@oksbi",
    color: "#ffffff", // White background for logo
    package: "com.google.android.apps.nbu.paisa.user",
    scheme: "gpay",
    logo: "https://upload.wikimedia.org/wikipedia/commons/f/f2/Google_Pay_Logo.svg"
  },
  phonepe: {
    id: "phonepe",
    name: "PhonePe",
    vpa: "8688009537@ibl", 
    color: "#5F259F", // Purple
    package: "com.phonepe.app",
    scheme: "phonepe",
    logo: "https://upload.wikimedia.org/wikipedia/commons/7/71/PhonePe_Logo.svg"
  },
  paytm: {
    id: "paytm",
    name: "Paytm",
    vpa: "8688009537@ptsbi",
    color: "#ffffff", // White
    package: "net.one97.paytm",
    scheme: "paytm",
    logo: "https://upload.wikimedia.org/wikipedia/commons/2/24/Paytm_Logo_%28standalone%29.svg"
  },
  bhim: {
    id: "bhim",
    name: "BHIM",
    vpa: "8688009537@bhim",
    color: "#ffffff", // White
    package: "in.org.npci.upiapp",
    scheme: "bhim",
    logo: "https://upload.wikimedia.org/wikipedia/commons/d/d1/BHIM_SVG_Logo.svg"
  }
};

export const generateUpiLink = (appId, amount, transactionNote = "Order Payment") => {
  const config = UPI_CONFIG[appId];
  if (!config) return null;

  const params = new URLSearchParams({
    pa: config.vpa,
    pn: "Merchant",
    am: amount,
    cu: "INR",
    tn: transactionNote,
  });

  const baseParams = params.toString();
  const isAndroid = /Android/i.test(navigator.userAgent);
  const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);

  // Android Specific Intent (Forces specific app)
  if (isAndroid && config.package) {
    return `intent://pay?${baseParams}#Intent;scheme=upi;package=${config.package};end;`;
  }

  // iOS Specific Scheme (Forces specific app if installed)
  if (isIOS && config.scheme) {
    // Note: iOS schemes vary. 
    // GPay: gpay://upi/pay?
    // PhonePe: phonepe://upi/pay?
    // Paytm: paytm://upi/pay?
    
    // Check specific known schemes
    if (appId === 'gpay') return `gpay://upi/pay?${baseParams}`;
    if (appId === 'phonepe') return `phonepe://upi/pay?${baseParams}`;
    if (appId === 'paytm') return `paytm://upi/pay?${baseParams}`;
    if (appId === 'bhim') return `bhim://upi/pay?${baseParams}`;
  }

  // Fallback to generic UPI intent (Let OS choose)
  return `upi://pay?${baseParams}`;
};
