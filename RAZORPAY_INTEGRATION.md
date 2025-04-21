# Razorpay Integration for Spotify Clone

This document outlines how to use the Razorpay payment integration in the Spotify Clone application.

## Setup

1. **Sign up for a Razorpay account**: 
   - Go to [Razorpay](https://razorpay.com/) and create an account
   - Once approved, obtain your API keys from the dashboard

2. **Set environment variables**:
   ```bash
   # For Windows PowerShell
   $env:RAZORPAY_KEY_ID="rzp_test_your_key_id" 
   $env:RAZORPAY_KEY_SECRET="your_key_secret"
   
   # For Unix/Linux
   export RAZORPAY_KEY_ID="rzp_test_your_key_id"
   export RAZORPAY_KEY_SECRET="your_key_secret"
   ```

3. **Install dependencies**:
   ```bash
   pip install razorpay setuptools
   ```

## How It Works

The Razorpay integration in this application follows this flow:

1. **User selects a subscription plan**: 
   - In the subscription page (`/subscription`), the user selects a plan and clicks the "Get Plan" button
   - This triggers the `showPaymentModal()` function in JavaScript

2. **Order creation**:
   - The frontend makes a request to `/subscription/create-order/<plan_type>` endpoint
   - The backend creates a Razorpay order and returns the order ID

3. **Payment checkout**:
   - Razorpay's checkout form opens, allowing the user to select a payment method
   - User completes the payment

4. **Payment verification**:
   - After payment, Razorpay provides payment details to the callback function
   - The frontend sends these details to `/subscription/process-payment`
   - The backend verifies the payment signature using Razorpay's API
   - If valid, the user's subscription is updated in the database

5. **Subscription management**:
   - Subscription details are stored in the user's profile
   - The user can cancel their subscription at any time via `/subscription/cancel`

## Key Files

- `app.py`: Contains the main routes for subscription management
- `models/payment.py`: Defines the Payment model for storing transaction records
- `templates/subscription.html`: Contains the UI for subscription plans
- `static/js/script.js`: Contains the JavaScript for handling Razorpay checkout
- `test_razorpay.py`: A standalone test server for testing Razorpay integration

## Testing

For testing purposes, use Razorpay's test cards:

- **Test Card Number**: 4111 1111 1111 1111
- **Expiry**: Any future date
- **CVV**: Any 3-digit number
- **Name**: Any name

You can use the `test_razorpay.py` script to quickly test the integration:

```bash
python test_razorpay.py
```

## Troubleshooting

1. **Authentication Error**: Make sure your API keys are correctly set in environment variables

2. **Payment Verification Failed**: Check that you're using the correct key pairs (test/live) consistently

3. **Order Creation Fails**: Verify that the currency and amount are valid (amount should be in smallest currency unit, e.g., paise for INR)

4. **Missing Dependencies**: Ensure you have installed both `razorpay` and `setuptools` packages

## Production Considerations

1. **Use Live Keys**: Replace test keys with live keys for production

2. **Store Transaction Records**: Use the Payment model to keep track of all transactions

3. **Implement Webhooks**: For better reliability, configure Razorpay webhooks

4. **Handle Failed Payments**: Implement proper error handling and user feedback

5. **Secure Environment Variables**: Do not hardcode keys, use environment variables or a secure vault 