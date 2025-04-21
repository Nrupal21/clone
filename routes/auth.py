from flask import jsonify, request, flash, redirect, url_for, session, Blueprint, render_template
from models.user import User
from email_validator import validate_email, EmailNotValidError
from functools import wraps
import time
import datetime
from bson.objectid import ObjectId

auth = Blueprint('auth', __name__)

#################################################
# Rate Limiting
#################################################
# Simple in-memory rate limiting (would use Redis or similar in production)
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 15 * 60  # 15 minutes in seconds

def is_rate_limited(ip_address):
    """Check if an IP is rate limited for login attempts"""
    now = time.time()
    
    # Clean up old entries
    for ip in list(login_attempts.keys()):
        if login_attempts[ip]['reset_time'] < now:
            del login_attempts[ip]
    
    if ip_address not in login_attempts:
        login_attempts[ip_address] = {
            'attempts': 0,
            'reset_time': now + LOCKOUT_TIME
        }
        return False
        
    # If lockout period is active
    if login_attempts[ip_address]['attempts'] >= MAX_LOGIN_ATTEMPTS:
        remaining = int(login_attempts[ip_address]['reset_time'] - now)
        if remaining > 0:
            return {'locked': True, 'remaining': remaining}
    
    return False

def record_login_attempt(ip_address, success):
    """Record a login attempt for rate limiting"""
    now = time.time()
    
    if ip_address not in login_attempts:
        login_attempts[ip_address] = {
            'attempts': 0,
            'reset_time': now + LOCKOUT_TIME
        }
    
    if success:
        # Reset on successful login
        login_attempts[ip_address]['attempts'] = 0
    else:
        # Increment attempts on failure
        login_attempts[ip_address]['attempts'] += 1
        # If max attempts reached, set lockout period
        if login_attempts[ip_address]['attempts'] >= MAX_LOGIN_ATTEMPTS:
            login_attempts[ip_address]['reset_time'] = now + LOCKOUT_TIME

#################################################
# User Registration
#################################################
@auth.route('/signup', methods=['GET', 'POST'])
def signup_user():
    if request.method == 'POST':
        # Get client IP for rate limiting
        ip_address = request.remote_addr
        
        # Check if rate limited (reuse login rate limiting)
        rate_limit = is_rate_limited(ip_address)
        if rate_limit and rate_limit.get('locked', False):
            minutes = int(rate_limit['remaining'] / 60)
            seconds = rate_limit['remaining'] % 60
            return jsonify({
                "message": f"Too many attempts. Please try again in {minutes}m {seconds}s."
            }), 429
        
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid request format"}), 400
            
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Enhanced validation
        validation_errors = []
        
        if not name:
            validation_errors.append("Name is required")
        elif len(name) < 2:
            validation_errors.append("Name must be at least 2 characters")
            
        if not email:
            validation_errors.append("Email is required")
        else:
            try:
                validate_email(email, check_deliverability=False)
            except EmailNotValidError as e:
                validation_errors.append(f"Invalid email: {str(e)}")
                
        if not phone:
            validation_errors.append("Phone number is required")
        elif not (phone.isdigit() and 8 <= len(phone) <= 15):
            validation_errors.append("Phone number must contain 8-15 digits")
            
        if not password:
            validation_errors.append("Password is required")
        else:
            # Check password strength
            if len(password) < 8:
                validation_errors.append("Password must be at least 8 characters long")
            if not any(c.isupper() for c in password):
                validation_errors.append("Password must contain at least one uppercase letter")
            if not any(c.islower() for c in password):
                validation_errors.append("Password must contain at least one lowercase letter")
            if not any(c.isdigit() for c in password):
                validation_errors.append("Password must contain at least one number")
            if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
                validation_errors.append("Password must contain at least one special character")
            
        if password != confirm_password:
            validation_errors.append("Passwords do not match")
            
        if validation_errors:
            return render_template('signup.html', errors=validation_errors)

        # User creation is handled by model with password validation
        result = User.create_user(name, email, phone, password)
        
        # Record attempt for rate limiting (success or failure)
        record_login_attempt(ip_address, result[1] == 201)
        
        if result[1] == 201:
            flash('Account created successfully! Please log in.', 'success')
            
            # Set additional security headers
            response = result[0]
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            
            return response
        else:
            # Extract error message from the model's response
            error_data = result[0].get_json()
            error_message = error_data.get("message", "An error occurred during signup")
            
            flash('An error occurred during signup.', 'error')
            return jsonify({"message": error_message}), result[1]

#################################################
# User Authentication
#################################################
@auth.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    # Authenticate user
    result = User.authenticate(email, password)
    if result[1] == 200:  # Authentication successful
        user_data = result[0].get_json()
        # Set session data
        session['user_id'] = user_data['user']['_id']
        session['is_admin'] = user_data['user']['is_admin']
        session['last_activity'] = datetime.datetime.utcnow().timestamp()
        
        # Always redirect to home page
        return redirect(url_for('home'))

    # Return error response if authentication failed
    return result