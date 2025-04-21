import os
import logging
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from pymongo import MongoClient
from config import Config

#################################################
# Logging Configuration
#################################################
# Setup subscription model logger
subscription_logger = logging.getLogger('subscription_model')
subscription_logger.setLevel(logging.INFO)
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
handler = logging.FileHandler(os.path.join(log_dir, 'subscription.log'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
subscription_logger.addHandler(handler)

#################################################
# Database Connection
#################################################
try:
    # Check if we're using MontyDB
    if Config.MONGODB_URI.startswith("monty://"):
        from montydb import MontyClient
        client = MontyClient(Config.MONGODB_URI.replace("monty://", ""))
    else:
        from pymongo import MongoClient
        client = MongoClient(Config.MONGODB_URI, 
                           serverSelectionTimeoutMS=5000,
                           connectTimeoutMS=10000,
                           socketTimeoutMS=30000)
    
    db = client[Config.DATABASE_NAME]
    subscriptions_collection = db['subscriptions']
    subscription_logger.info("Connected to database for subscriptions collection")
except Exception as e:
    subscription_logger.error(f"Error connecting to database from subscription model: {e}")
    # Use a mock collection when database is not available
    class MockCollection:
        def find_one(self, *args, **kwargs):
            subscription_logger.warning("Using mock collection. No database connection.")
            return None
            
        def find(self, *args, **kwargs):
            subscription_logger.warning("Using mock collection. No database connection.")
            return []
            
        def insert_one(self, *args, **kwargs):
            subscription_logger.warning("Using mock collection. No database connection.")
            class MockResult:
                @property
                def inserted_id(self):
                    return "mock_id"
            return MockResult()
            
        def update_one(self, *args, **kwargs):
            subscription_logger.warning("Using mock collection. No database connection.")
            class MockResult:
                @property
                def matched_count(self):
                    return 0
            return MockResult()
            
        def delete_one(self, *args, **kwargs):
            subscription_logger.warning("Using mock collection. No database connection.")
            return None
            
        def count_documents(self, *args, **kwargs):
            subscription_logger.warning("Using mock collection. No database connection.")
            return 0
    
    subscriptions_collection = MockCollection()

#################################################
# International Pricing Configuration
#################################################
# Currency symbols by region
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€", 
    "GBP": "£",
    "INR": "₹",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
    "BRL": "R$",
    "MXN": "Mex$",
    "SGD": "S$",
    "HKD": "HK$",
    "RUB": "₽",
    "SEK": "kr",
    "CHF": "Fr",
    "ZAR": "R"
}

# International pricing by region (with appropriate pricing based on purchasing power)
INTERNATIONAL_PRICING = {
    # North America
    "US": {"code": "USD", "free": 0, "basic": 4.99, "premium": 9.99, "family": 14.99, "student": 4.99},
    "CA": {"code": "CAD", "free": 0, "basic": 6.49, "premium": 12.99, "family": 19.99, "student": 6.49},
    "MX": {"code": "MXN", "free": 0, "basic": 99, "premium": 199, "family": 299, "student": 99},
    
    # Europe
    "GB": {"code": "GBP", "free": 0, "basic": 3.99, "premium": 7.99, "family": 12.99, "student": 3.99},
    "DE": {"code": "EUR", "free": 0, "basic": 4.49, "premium": 8.99, "family": 13.99, "student": 4.49},
    "FR": {"code": "EUR", "free": 0, "basic": 4.49, "premium": 8.99, "family": 13.99, "student": 4.49},
    "IT": {"code": "EUR", "free": 0, "basic": 4.49, "premium": 8.99, "family": 13.99, "student": 4.49},
    "ES": {"code": "EUR", "free": 0, "basic": 4.49, "premium": 8.99, "family": 13.99, "student": 4.49},
    "SE": {"code": "SEK", "free": 0, "basic": 45, "premium": 95, "family": 145, "student": 45},
    "CH": {"code": "CHF", "free": 0, "basic": 4.50, "premium": 9.90, "family": 15.90, "student": 4.50},
    
    # Asia Pacific
    "JP": {"code": "JPY", "free": 0, "basic": 680, "premium": 980, "family": 1480, "student": 480},
    "AU": {"code": "AUD", "free": 0, "basic": 5.99, "premium": 11.99, "family": 17.99, "student": 5.99},
    "SG": {"code": "SGD", "free": 0, "basic": 6.90, "premium": 12.90, "family": 19.90, "student": 6.90},
    "HK": {"code": "HKD", "free": 0, "basic": 38, "premium": 78, "family": 118, "student": 38},
    "IN": {"code": "INR", "free": 0, "basic": 99, "premium": 199, "family": 299, "student": 49},
    
    # South America
    "BR": {"code": "BRL", "free": 0, "basic": 14.90, "premium": 29.90, "family": 44.90, "student": 14.90},
    
    # Africa
    "ZA": {"code": "ZAR", "free": 0, "basic": 49.99, "premium": 89.99, "family": 139.99, "student": 49.99},
    
    # Default (USD)
    "DEFAULT": {"code": "USD", "free": 0, "basic": 4.99, "premium": 9.99, "family": 14.99, "student": 4.99}
}

class Subscription:
    """Handles subscription management for users"""
    
    # Define subscription plan types
    PLAN_FREE = "free"
    PLAN_BASIC = "basic"
    PLAN_PREMIUM = "premium"
    PLAN_FAMILY = "family"
    PLAN_STUDENT = "student"
    
    # Define subscription features by plan
    PLAN_FEATURES = {
        PLAN_FREE: {
            "name": "Free",
            "price": 0,
            "billing_cycle": "forever",
            "description": "Limited streaming with ads",
            "features": [
                "Stream songs with ads",
                "Limited skips",
                "Standard audio quality",
                "Limited library access"
            ],
            "razorpay_plan_id": None
        },
        PLAN_BASIC: {
            "name": "Basic",
            "price": 4.99,
            "billing_cycle": "monthly",
            "description": "Ad-free listening with basic features",
            "features": [
                "Ad-free streaming",
                "Limited skips",
                "Standard audio quality",
                "Basic library access",
                "Mobile streaming"
            ],
            "razorpay_plan_id": "plan_basic"
        },
        PLAN_PREMIUM: {
            "name": "Premium",
            "price": 9.99,
            "billing_cycle": "monthly",
            "description": "Full streaming experience without limitations",
            "features": [
                "Ad-free streaming",
                "Unlimited skips",
                "High quality audio",
                "Full library access",
                "Offline listening",
                "Multi-device streaming"
            ],
            "razorpay_plan_id": "plan_premium"
        },
        PLAN_FAMILY: {
            "name": "Family",
            "price": 14.99,
            "billing_cycle": "monthly",
            "description": "Premium features for up to 6 family members",
            "features": [
                "All premium features",
                "Up to 6 accounts",
                "Parental controls",
                "Shared playlists",
                "Individual recommendations",
                "Family mix playlists"
            ],
            "razorpay_plan_id": "plan_family"
        },
        PLAN_STUDENT: {
            "name": "Student",
            "price": 4.99,
            "billing_cycle": "monthly",
            "description": "Premium plan for verified students",
            "features": [
                "All premium features",
                "50% student discount",
                "Student verification required",
                "Valid for 12 months",
                "Renewable with verification"
            ],
            "razorpay_plan_id": "plan_student"
        }
    }
    
    # Razorpay subscription durations (in days)
    SUBSCRIPTION_DURATIONS = {
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365,
        "forever": None
    }
    
    subscriptions_collection = subscriptions_collection
    
    #################################################
    # Subscription Creation and Management
    #################################################
    @staticmethod
    def create_subscription(user_id, plan_type=PLAN_FREE):
        """
        Create a new subscription for a user
        
        Args:
            user_id: ID of the user
            plan_type: Type of subscription plan (default: free)
            
        Returns:
            dict: The created subscription document or None if error
        """
        # Validate plan type
        if plan_type not in Subscription.PLAN_FEATURES:
            subscription_logger.error(f"Invalid plan type: {plan_type}")
            return None
        
        # Check if user already has a subscription
        existing = subscriptions_collection.find_one({"user_id": user_id})
        if existing:
            subscription_logger.warning(f"User {user_id} already has a subscription")
            return existing
        
        # Set expiry date based on billing cycle
        billing_cycle = Subscription.PLAN_FEATURES[plan_type].get("billing_cycle", "forever")
        duration_days = Subscription.SUBSCRIPTION_DURATIONS.get(billing_cycle)
        
        expiry_date = None
        if duration_days is not None:
            expiry_date = datetime.utcnow() + timedelta(days=duration_days)
        
        # Create subscription document
        subscription = {
            "user_id": user_id,
            "plan_type": plan_type,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "expiry_date": expiry_date,
            "is_active": True,
            "payment_status": "completed" if plan_type == Subscription.PLAN_FREE else "pending",
            "razorpay_subscription_id": None,
            "razorpay_customer_id": None,
            "billing_cycle": billing_cycle
        }
        
        try:
            result = subscriptions_collection.insert_one(subscription)
            subscription["_id"] = str(result.inserted_id)
            subscription_logger.info(f"Subscription created for user {user_id}: {plan_type}")
            return subscription
        except Exception as e:
            subscription_logger.error(f"Error creating subscription: {str(e)}")
            return None
    
    @staticmethod
    def get_user_subscription(user_id):
        """
        Get subscription details for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            dict: The subscription document or None if not found
        """
        try:
            subscription = subscriptions_collection.find_one({"user_id": user_id})
            if subscription:
                subscription["_id"] = str(subscription["_id"])
                
                # Check if paid subscription is expired
                if subscription["plan_type"] != Subscription.PLAN_FREE and subscription["expiry_date"]:
                    if datetime.utcnow() > subscription["expiry_date"]:
                        # Downgrade to free if expired
                        subscription["is_active"] = False
                        subscriptions_collection.update_one(
                            {"_id": ObjectId(subscription["_id"])},
                            {"$set": {"is_active": False}}
                        )
                        subscription_logger.info(f"Paid subscription expired for user {user_id}")
            return subscription
        except Exception as e:
            subscription_logger.error(f"Error getting subscription: {str(e)}")
            return None
    
    @staticmethod
    def upgrade_subscription(user_id, plan_type, payment_id=None, razorpay_data=None):
        """
        Upgrade a user's subscription to a paid plan
        
        Args:
            user_id: ID of the user
            plan_type: Type of subscription plan to upgrade to
            payment_id: Optional payment transaction ID
            razorpay_data: Optional Razorpay subscription data
            
        Returns:
            dict: The updated subscription document or None if error
        """
        # Validate plan type
        if plan_type not in Subscription.PLAN_FEATURES:
            subscription_logger.error(f"Invalid plan type: {plan_type}")
            return None
            
        try:
            subscription = subscriptions_collection.find_one({"user_id": user_id})
            
            if not subscription:
                # Create new subscription if none exists
                return Subscription.create_subscription(user_id, plan_type)
            
            # Set expiry date based on billing cycle
            billing_cycle = Subscription.PLAN_FEATURES[plan_type].get("billing_cycle", "forever")
            duration_days = Subscription.SUBSCRIPTION_DURATIONS.get(billing_cycle)
            
            expiry_date = None
            if duration_days is not None:
                expiry_date = datetime.utcnow() + timedelta(days=duration_days)
            
            # Prepare update data
            update_data = {
                "plan_type": plan_type,
                "updated_at": datetime.utcnow(),
                "expiry_date": expiry_date,
                "is_active": True,
                "payment_status": "completed",
                "billing_cycle": billing_cycle
            }
            
            # Add payment details if provided
            if payment_id:
                update_data["payment_id"] = payment_id
                
            # Add Razorpay details if provided
            if razorpay_data:
                update_data["razorpay_subscription_id"] = razorpay_data.get("subscription_id")
                update_data["razorpay_customer_id"] = razorpay_data.get("customer_id")
            
            # Update existing subscription
            subscriptions_collection.update_one(
                {"_id": subscription["_id"]},
                {"$set": update_data}
            )
            
            subscription_logger.info(f"Subscription upgraded to {plan_type} for user {user_id}")
            subscription = subscriptions_collection.find_one({"user_id": user_id})
            subscription["_id"] = str(subscription["_id"])
            return subscription
        except Exception as e:
            subscription_logger.error(f"Error upgrading subscription: {str(e)}")
            return None
    
    @staticmethod
    def cancel_subscription(user_id):
        """
        Cancel a user's paid subscription
        
        Args:
            user_id: ID of the user
            
        Returns:
            bool: Success status
        """
        try:
            subscription = subscriptions_collection.find_one({"user_id": user_id})
            
            if not subscription:
                subscription_logger.warning(f"No subscription found for user {user_id}")
                return False
            
            # Don't allow canceling free plan, just downgrade paid plan to free
            if subscription["plan_type"] != Subscription.PLAN_FREE:
                # If we have a Razorpay subscription, we should cancel it with their API
                razorpay_subscription_id = subscription.get("razorpay_subscription_id")
                if razorpay_subscription_id:
                    # In a real implementation, you would call Razorpay API to cancel
                    subscription_logger.info(f"Would cancel Razorpay subscription {razorpay_subscription_id} for user {user_id}")
                
                subscriptions_collection.update_one(
                    {"_id": subscription["_id"]},
                    {"$set": {
                        "plan_type": Subscription.PLAN_FREE,
                        "updated_at": datetime.utcnow(),
                        "expiry_date": None,
                        "payment_status": "completed",
                        "billing_cycle": "forever"
                    }}
                )
                subscription_logger.info(f"Paid subscription cancelled for user {user_id}")
                return True
            else:
                subscription_logger.info(f"User {user_id} is already on free plan")
                return True
        except Exception as e:
            subscription_logger.error(f"Error cancelling subscription: {str(e)}")
            return False
    
    #################################################
    # Razorpay Integration
    #################################################
    @staticmethod
    def create_razorpay_order(user_id, plan_type):
        """
        Create a Razorpay order for subscription payment
        
        Args:
            user_id: ID of the user
            plan_type: Type of subscription plan
            
        Returns:
            dict: Razorpay order details or None if error
        """
        try:
            # Validate plan type
            if plan_type not in Subscription.PLAN_FEATURES:
                subscription_logger.error(f"Invalid plan type: {plan_type}")
                return None
                
            # Get plan details
            plan = Subscription.PLAN_FEATURES[plan_type]
            
            # In a real implementation, this would call the Razorpay API
            # For now, we'll simulate a successful order creation
            order_id = f"order_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}"
            
            order_details = {
                "id": order_id,
                "amount": int(plan["price"] * 100),  # Amount in smallest currency unit (e.g., cents)
                "currency": "USD",
                "receipt": f"receipt_{user_id}_{plan_type}",
                "plan_type": plan_type
            }
            
            subscription_logger.info(f"Created Razorpay order for user {user_id}, plan {plan_type}")
            return order_details
            
        except Exception as e:
            subscription_logger.error(f"Error creating Razorpay order: {str(e)}")
            return None
            
    @staticmethod
    def verify_razorpay_payment(payment_data):
        """
        Verify a Razorpay payment
        
        Args:
            payment_data: Payment data from Razorpay callback
            
        Returns:
            bool: True if payment is valid, False otherwise
        """
        try:
            # In a real implementation, this would validate the signature and payment
            # For now, we'll simulate a successful verification
            return True
        except Exception as e:
            subscription_logger.error(f"Error verifying Razorpay payment: {str(e)}")
            return False
    
    #################################################
    # Admin Functions
    #################################################
    @staticmethod
    def get_all_subscriptions(skip=0, limit=100):
        """
        Get all subscriptions for admin panel
        
        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            list: List of subscription documents
        """
        try:
            subscriptions = list(subscriptions_collection.find().skip(skip).limit(limit))
            for subscription in subscriptions:
                subscription["_id"] = str(subscription["_id"])
            return subscriptions
        except Exception as e:
            subscription_logger.error(f"Error getting all subscriptions: {str(e)}")
            return []
    
    @staticmethod
    def get_subscription_counts():
        """
        Get count of subscriptions by plan type
        
        Returns:
            dict: Counts for different subscription types
        """
        try:
            total = subscriptions_collection.count_documents({})
            
            counts = {}
            for plan_type in Subscription.PLAN_FEATURES:
                if plan_type == Subscription.PLAN_FREE:
                    counts[plan_type] = subscriptions_collection.count_documents({"plan_type": plan_type})
                else:
                    active = subscriptions_collection.count_documents({"plan_type": plan_type, "is_active": True})
                    counts[f"{plan_type}_active"] = active
                    expired = subscriptions_collection.count_documents({"plan_type": plan_type, "is_active": False})
                    counts[f"{plan_type}_expired"] = expired
            
            counts["total"] = total
            return counts
        except Exception as e:
            subscription_logger.error(f"Error getting subscription counts: {str(e)}")
            return {"total": 0}
    
    @staticmethod
    def initialize_subscriptions():
        """
        Create indexes and ensure all users have at least free subscriptions
        """
        try:
            # Create indexes
            subscriptions_collection.create_index("user_id", unique=True)
            subscriptions_collection.create_index("plan_type")
            subscriptions_collection.create_index("expiry_date")
            subscriptions_collection.create_index("razorpay_subscription_id")
            
            subscription_logger.info("Subscription indexes created")
            return True
        except Exception as e:
            subscription_logger.error(f"Error initializing subscriptions: {str(e)}")
            return False

    @staticmethod
    def get_country_code_from_ip(ip_address=None):
        """
        Get country code from IP address
        
        Args:
            ip_address: Optional IP address to use (if None, uses requestor's IP)
            
        Returns:
            str: Two-letter country code (ISO 3166-1 alpha-2)
        """
        # Use a default country code if IP detection fails
        default_country = "US"
        
        try:
            # If no IP is provided, this is handled when using Flask request in the view
            if not ip_address:
                return default_country
            
            # Simplified for now - using external API or geolocation library would go here
            # In a production app, you'd want to use a service like ipinfo.io, MaxMind, etc.
            # Or parse existing GeoIP database files
            
            # For demo purposes only - not actual IP detection
            if ip_address.startswith('192.168.'):
                return "US"
            elif ip_address.startswith('10.'):
                return "GB"  
            elif ip_address.startswith('172.'):
                return "DE"
            return default_country
            
        except Exception as e:
            subscription_logger.error(f"Error detecting country from IP: {str(e)}")
            return default_country

    @staticmethod
    def get_pricing_for_country(country_code):
        """
        Get pricing information for a specific country
        
        Args:
            country_code: Two-letter country code (ISO 3166-1 alpha-2)
            
        Returns:
            dict: Pricing information for the country
        """
        country_code = country_code.upper() if country_code else "DEFAULT"
        
        # Get country-specific pricing or use default
        pricing = INTERNATIONAL_PRICING.get(country_code, INTERNATIONAL_PRICING["DEFAULT"])
        currency_code = pricing["code"]
        currency_symbol = CURRENCY_SYMBOLS.get(currency_code, "$")
        
        return {
            "country_code": country_code,
            "currency_code": currency_code,
            "currency_symbol": currency_symbol,
            "free": pricing["free"],
            "basic": pricing["basic"],
            "premium": pricing["premium"],
            "family": pricing["family"],
            "student": pricing["student"]
        }

    @staticmethod
    def get_subscription_with_local_pricing(user_id, country_code=None):
        """
        Get subscription with local pricing for a user
        
        Args:
            user_id: ID of the user
            country_code: Optional country code override
            
        Returns:
            dict: Subscription with local pricing information
        """
        # Get user's subscription
        subscription = Subscription.get_user_subscription(user_id)
        
        # Get country pricing
        pricing = Subscription.get_pricing_for_country(country_code)
        
        # Update plan features with local pricing
        updated_features = {}
        for plan_type, features in Subscription.PLAN_FEATURES.items():
            plan_features = features.copy()
            plan_features["price"] = pricing.get(plan_type, features["price"])
            plan_features["currency_symbol"] = pricing["currency_symbol"]
            plan_features["currency_code"] = pricing["currency_code"]
            updated_features[plan_type] = plan_features
        
        return {
            "subscription": subscription,
            "plans": updated_features,
            "country_code": pricing["country_code"],
            "currency_code": pricing["currency_code"],
            "currency_symbol": pricing["currency_symbol"]
        } 