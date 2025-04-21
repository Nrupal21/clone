from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from config import Config

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
    payments_collection = db['payments']
    print("Connected to database for payments collection")
except Exception as e:
    print(f"Error connecting to database from payment model: {e}")
    # Use a mock collection when database is not available
    class MockCollection:
        def find_one(self, *args, **kwargs):
            print("WARNING: Using mock collection. No database connection.")
            return None
            
        def find(self, *args, **kwargs):
            print("WARNING: Using mock collection. No database connection.")
            return []
            
        def insert_one(self, *args, **kwargs):
            print("WARNING: Using mock collection. No database connection.")
            class MockResult:
                @property
                def inserted_id(self):
                    return "mock_id"
            return MockResult()
            
        def update_one(self, *args, **kwargs):
            print("WARNING: Using mock collection. No database connection.")
            class MockResult:
                @property
                def matched_count(self):
                    return 0
                @property
                def modified_count(self):
                    return 0
            return MockResult()
            
        def delete_one(self, *args, **kwargs):
            print("WARNING: Using mock collection. No database connection.")
            class MockResult:
                @property
                def deleted_count(self):
                    return 0
            return MockResult()
            
        def count_documents(self, *args, **kwargs):
            print("WARNING: Using mock collection. No database connection.")
            return 0
    
    payments_collection = MockCollection()

class Payment:
    """Model for handling payment records"""
    
    @staticmethod
    def create(user_id, payment_id, order_id, plan_type, amount, currency="USD", status="completed"):
        """
        Create a new payment record
        Returns: ID of the created payment or None if failed
        """
        try:
            payment = {
                "user_id": ObjectId(user_id),
                "payment_id": payment_id,
                "order_id": order_id,
                "plan_type": plan_type,
                "amount": amount,
                "currency": currency,
                "status": status,
                "created_at": datetime.utcnow()
            }
            
            result = payments_collection.insert_one(payment)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating payment record: {e}")
            return None
    
    @staticmethod
    def get_by_id(payment_id):
        """
        Get a payment record by ID
        Returns: Payment object or None
        """
        try:
            payment = payments_collection.find_one({"_id": ObjectId(payment_id)})
            if payment:
                payment['_id'] = str(payment['_id'])
                payment['user_id'] = str(payment['user_id'])
            return payment
        except Exception as e:
            print(f"Error getting payment by ID: {e}")
            return None
    
    @staticmethod
    def get_by_user(user_id, limit=10):
        """
        Get payment records for a user
        Returns: List of payment objects
        """
        try:
            payments = list(payments_collection.find(
                {"user_id": ObjectId(user_id)}
            ).sort("created_at", -1).limit(limit))
            
            # Convert ObjectIds to strings
            for payment in payments:
                payment['_id'] = str(payment['_id'])
                payment['user_id'] = str(payment['user_id'])
                
            return payments
        except Exception as e:
            print(f"Error getting payments for user: {e}")
            return []
    
    @staticmethod
    def get_by_payment_id(payment_id):
        """
        Get a payment record by Razorpay payment ID
        Returns: Payment object or None
        """
        try:
            payment = payments_collection.find_one({"payment_id": payment_id})
            if payment:
                payment['_id'] = str(payment['_id'])
                payment['user_id'] = str(payment['user_id'])
            return payment
        except Exception as e:
            print(f"Error getting payment by payment ID: {e}")
            return None 