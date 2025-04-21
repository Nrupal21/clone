"""
Simple Flask app to test Razorpay integration
"""
from flask import Flask, render_template, jsonify, request
import os
import razorpay

app = Flask(__name__)

# Razorpay configuration
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_CZC1QWjEumx4L2')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'JPy31sLQQqqxUo9q5WJUntgP')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.route('/')
def index():
    """Home page with Razorpay payment button"""
    return render_template('test_payment.html', 
                          razorpay_key_id=RAZORPAY_KEY_ID)

@app.route('/create-order', methods=['POST'])
def create_order():
    """Create a Razorpay order"""
    try:
        # Create order data
        amount = 100 * 100  # Rs. 100 in paise
        currency = 'INR'
        
        # Create order payload
        order_payload = {
            'amount': amount,
            'currency': currency,
            'receipt': 'test_receipt',
            'payment_capture': 1  # Auto-capture payment
        }
        
        # Create the order
        order = razorpay_client.order.create(data=order_payload)
        
        print(f"Created order: {order}")
        
        # Return order information to client
        return jsonify({
            'id': order['id'],
            'amount': amount,
            'currency': currency
        })
        
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return jsonify({"error": f"Failed to create order: {str(e)}"}), 500

@app.route('/process-payment', methods=['POST'])
def process_payment():
    """Process Razorpay payment verification"""
    try:
        # Get the payment data from request
        payment_data = request.json
        
        if not payment_data:
            return jsonify({"success": False, "error": "No payment data received"}), 400
        
        # Extract payment details
        razorpay_payment_id = payment_data.get('razorpay_payment_id')
        razorpay_order_id = payment_data.get('razorpay_order_id')
        razorpay_signature = payment_data.get('razorpay_signature')
        
        # Create params_dict for signature verification
        params_dict = {
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_signature': razorpay_signature
        }
        
        # Verify the payment signature
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        print("Payment verified successfully")
        return jsonify({"success": True, "message": "Payment processed successfully"})
        
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        return jsonify({"success": False, "error": f"Error processing payment: {str(e)}"}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create test_payment.html template
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Razorpay Test Payment</title>
        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    </head>
    <body>
        <h1>Razorpay Test Payment</h1>
        <button id="pay-button">Pay Now</button>
        
        <script>
            document.getElementById('pay-button').addEventListener('click', function() {
                // Create order
                fetch('/create-order', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                        return;
                    }
                    
                    // Configure Razorpay
                    const options = {
                        key: '{{ razorpay_key_id }}', 
                        amount: data.amount,
                        currency: data.currency,
                        name: 'Test Company',
                        description: 'Test Payment',
                        order_id: data.id,
                        handler: function(response) {
                            // Process payment
                            processPayment(response);
                        },
                        prefill: {
                            name: 'Test User',
                            email: 'test@example.com',
                            contact: '9999999999'
                        },
                        theme: {
                            color: '#3399cc'
                        }
                    };
                    
                    // Open Razorpay
                    const rzp = new Razorpay(options);
                    rzp.open();
                })
                .catch(error => {
                    console.error('Error creating order:', error);
                    alert('Error creating order');
                });
            });
            
            function processPayment(response) {
                fetch('/process-payment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_signature: response.razorpay_signature
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Payment successful!');
                    } else {
                        alert(data.error || 'Payment verification failed');
                    }
                })
                .catch(error => {
                    console.error('Error processing payment:', error);
                    alert('Error processing payment');
                });
            }
        </script>
    </body>
    </html>
    """
    
    # Write template to file
    with open('templates/test_payment.html', 'w') as f:
        f.write(template)
    
    print("Starting Razorpay test server...")
    app.run(debug=True) 