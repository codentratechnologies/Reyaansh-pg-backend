# PgAdmin: Payment & Automated Mail System Documentation

This document outlines the end-to-end flow for the automated rent reminder system, calendar invitations, and UPI payment integrations.

## Table of Contents
1. [End-to-End System Flow](#1-end-to-end-system-flow)
2. [API Reference](#2-api-reference)
   - [1. Generate Payment Links API](#1-generate-payment-links-api-get)
   - [2. Trigger Daily Sweep (Cron Job) API](#2-trigger-daily-sweep-cron-job-api-getpost)
   - [3. Send Rent Reminder Email API](#3-send-rent-reminder-email-api-post)
   - [4. Send Calendar Invite API](#4-send-calendar-invite-api-post)
3. [Frontend Implementation Guide](#3-frontend-implementation-guide-nextjsreact)

---

## 1. End-to-End System Flow

The system is designed to be fully automated with zero manual intervention required for monthly rent collection.

1. **Daily Sweep:** Every day at 9:00 AM, a free cron service (like cron-job.org) pings the `/api/trigger-daily-reminders/` endpoint.
2. **Background Processing:** The backend automatically identifies all members whose rent is due *today*.
3. **Automated Emails:** The backend sends a personalized email to those members. The email contains a link to their unique checkout page (e.g., `https://reyaansh-pg.vercel.app/checkout?member_id=-OXYZ123`).
4. **Checkout Page Load:** The member clicks the link and opens the checkout page on their phone. The frontend reads the `member_id` from the URL and hits `/api/generate-payment-link/?member_id=-OXYZ123`.
5. **One-Click Payment:** The backend returns deep links for Google Pay, PhonePe, and Paytm with the member's exact rent amount pre-filled. The user taps "Pay with GPay", their app opens, and they pay.

---

## 2. API Reference

All APIs run entirely in background threads, guaranteeing `< 5ms` response times for your frontend.

### 1. Generate Payment Links API (GET)
Use this API on the Checkout page to generate ready-to-use "One-Click Pay" buttons that open native UPI apps on the user's phone.

**Endpoint:** `GET /api/generate-payment-link/`

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `member_id` | String | **Yes** | The unique Firebase ID of the member. |

**Success Response (200 OK):**
```json
{
    "member_name": "Rahul Sharma",
    "rent_amount": 8000.0,
    "payment_links": {
        "generic_upi": "upi://pay?pa=7359377502@paytm&pn=PgAdmin&am=8000.00&cu=INR&tn=Rent+payment+for+Rahul+Sharma",
        "google_pay": "gpay://upi/pay?pa=7359377502@paytm&pn=PgAdmin&am=8000.00&cu=INR&tn=Rent+payment+for+Rahul+Sharma",
        "phonepe": "phonepe://pay?pa=7359377502@paytm&pn=PgAdmin&am=8000.00&cu=INR&tn=Rent+payment+for+Rahul+Sharma",
        "paytm": "paytmmp://pay?pa=7359377502@paytm&pn=PgAdmin&am=8000.00&cu=INR&tn=Rent+payment+for+Rahul+Sharma"
    }
}
```


### 2. Trigger Daily Sweep (Cron Job) API (GET/POST)
Use this API to trigger the fully automated sweep of the database. It sends emails to anyone whose rent is due today.

**Endpoint:** `GET /api/trigger-daily-reminders/`

**Query Parameters:** None

**Success Response (202 Accepted):**
```json
{
    "message": "Automated sweep initiated in the background.",
    "status": "Running"
}
```
*Note: Set up a free service like cron-job.org to hit this URL every day at 9:00 AM.*


### 3. Send Rent Reminder Email API (POST)
Use this to manually trigger a professional rent reminder email for a specific member without a calendar invite attached.

**Endpoint:** `POST /api/send-rent-email/`

**Body:**
```json
{
    "member_id": "-O123456789",
    "title": "Action Required: Rent Payment Due",
    "description": "This is a polite reminder that your monthly rent is due.",
    "checkout_url": "https://reyaansh-pg.vercel.app/checkout?member_id=-O123456789"
}
```

**Success Response (202 Accepted):**
```json
{
    "message": "Rent reminder email is being processed and sent in the background."
}
```

### 4. Send Calendar Invite API (POST)
Use this when a member first joins. It sends an `.ics` Google Calendar invite that sets up an automatic recurring alarm on the member's phone based on their rent due date.

**Endpoint:** `POST /api/send-calendar-reminder/`

**Body:**
```json
{
    "member_id": "-O123456789",
    "title": "Monthly Rent Due",
    "description": "Please remember to pay your rent! Your timely payment is appreciated.",
    "checkout_url": "https://reyaansh-pg.vercel.app/checkout?member_id=-O123456789"
}
```

**Success Response (202 Accepted):**
```json
{
    "message": "Calendar invite is being processed and sent in the background."
}
```

---

## 3. Frontend Implementation Guide (Next.js/React)

Here is how you should structure your `Checkout.js` page on the frontend to consume the Payment Links API:

```jsx
import { useEffect, useState } from 'react';

export default function CheckoutPage() {
  const [paymentData, setPaymentData] = useState(null);

  useEffect(() => {
    // 1. Get member_id from the URL (e.g. ?member_id=-OXYZ123)
    const urlParams = new URLSearchParams(window.location.search);
    const memberId = urlParams.get('member_id');

    if (memberId) {
      // 2. Fetch the pre-filled payment links from Django
      fetch(`http://your-django-backend.com/api/generate-payment-link/?member_id=${memberId}`)
        .then(res => res.json())
        .then(data => setPaymentData(data));
    }
  }, []);

  if (!paymentData) return <div>Loading...</div>;

  return (
    <div className="checkout-container">
      <h1>Checkout for {paymentData.member_name}</h1>
      <h2>Amount Due: ₹{paymentData.rent_amount}</h2>

      {/* 3. Map the URLs directly to standard HTML buttons */}
      <div className="payment-buttons">
        <a href={paymentData.payment_links.google_pay} className="btn-gpay">
          Pay with GPay
        </a>
        <a href={paymentData.payment_links.phonepe} className="btn-phonepe">
          Pay with PhonePe
        </a>
        <a href={paymentData.payment_links.paytm} className="btn-paytm">
          Pay with Paytm
        </a>
      </div>
    </div>
  );
}
```

### Important Notes on Testing Deep Links
Deep links (`gpay://`, `phonepe://`) will **only** work when clicked from a real mobile device (Android/iOS) that has those apps installed. If you click them on a Desktop PC, your browser will say "Unsupported Link". To test them, open the frontend website on your actual mobile phone!
