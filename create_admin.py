from models.user import User
from pymongo import MongoClient
from config import Config
import bcrypt
import datetime
import logging

# Connect to the database
try:
    client = MongoClient(Config.MONGODB_URI, 
                       serverSelectionTimeoutMS=5000,
                       connectTimeoutMS=10000,
                       socketTimeoutMS=30000)
    
    db = client[Config.DATABASE_NAME]
    users_collection = db['users']
    print("Connected to database")
except Exception as e:
    print(f"Error connecting to database: {e}")
    exit(1)

# Create admin user with desired credentials
admin_username = "admin"
admin_name = "Admin User"
admin_email = "admin@example.com"
admin_password = "AdminPassword123!"

# Check if admin already exists
existing_admin = users_collection.find_one({"username": admin_username})
if existing_admin:
    print(f"User with username {admin_username} already exists")
    exit(0)

# Create admin user document
try:
    # Hash password
    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt(12))
    
    # Create user document
    admin_data = {
        "username": admin_username,
        "name": admin_name,
        "email": admin_email,
        "password": hashed_password,
        "is_admin": True,  # This is the key field that grants admin privileges
        "created_at": datetime.datetime.utcnow(),
        "last_login": None,
        "liked_songs": [],
        "playlists": []
    }
    
    # Insert user into database
    result = users_collection.insert_one(admin_data)
    user_id = result.inserted_id
    
    if user_id:
        print(f"Admin user created successfully with ID: {user_id}")
        print(f"Username: {admin_username}")
        print(f"Password: {admin_password}")
    else:
        print("Failed to create admin user")
        
except Exception as e:
    print(f"Error creating admin user: {e}") 