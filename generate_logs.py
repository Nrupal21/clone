import os
import logging
import random
import time
from datetime import datetime, timedelta

# Setup log directory
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure loggers for different components
def setup_logger(name, log_file, level=logging.INFO):
    """Set up a logger for a specific component"""
    handler = logging.FileHandler(os.path.join(log_dir, log_file))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    for h in logger.handlers:
        logger.removeHandler(h)
    logger.addHandler(handler)
    return logger

# Set up loggers
app_logger = setup_logger('spotify_app', 'app.log')
user_logger = setup_logger('user_activity', 'user.log')
admin_logger = setup_logger('admin_actions', 'admin_activity.log')
playlist_logger = setup_logger('playlist_ops', 'playlist.log')
error_logger = setup_logger('errors', 'error.log', level=logging.ERROR)
security_logger = setup_logger('security', 'security.log')

# Sample data for logs
user_ids = [f"{random.randint(100000, 999999)}" for _ in range(10)]
admin_ids = [f"{random.randint(100000, 999999)}" for _ in range(3)]
song_ids = [f"{random.randint(100000, 999999)}" for _ in range(20)]
playlist_ids = [f"{random.randint(100000, 999999)}" for _ in range(15)]
ip_addresses = ['192.168.1.{}'.format(random.randint(1, 255)) for _ in range(20)]

# User actions
user_actions = [
    "Login successful", 
    "Password changed", 
    "Profile updated",
    "Subscription renewed", 
    "Logout", 
    "Password reset requested",
    "Email verification completed", 
    "Two-factor authentication enabled",
    "Account settings modified"
]

# Admin actions
admin_actions = [
    "User deleted", 
    "Song added", 
    "Song removed", 
    "Subscription modified", 
    "User privileges changed",
    "System settings updated",
    "Database backup initiated",
    "Maintenance mode toggled"
]

# Playlist operations
playlist_ops = [
    "Created new playlist", 
    "Added song to playlist", 
    "Removed song from playlist", 
    "Renamed playlist",
    "Changed playlist visibility", 
    "Deleted playlist",
    "Shared playlist"
]

# Error types
errors = [
    "Database connection failed", 
    "Payment processing error", 
    "Authentication server timeout", 
    "Storage quota exceeded",
    "Invalid file format",
    "Media conversion failed",
    "API rate limit exceeded",
    "Third-party service unavailable"
]

# Security events
security_events = [
    "Multiple failed login attempts", 
    "Password brute force detected", 
    "Suspicious login location", 
    "Account lockout triggered",
    "API token compromised",
    "Unusual data access pattern detected",
    "Session hijacking attempt",
    "Cross-site scripting attempt detected"
]

def generate_app_logs(count=100):
    """Generate application logs"""
    log_levels = [logging.INFO, logging.WARNING, logging.ERROR]
    app_events = [
        "Application started", 
        "Application stopped", 
        "New user registered", 
        "Song upload processed",
        "Payment received", 
        "Email sent", 
        "Cache cleared", 
        "Database backup completed",
        "Background task executed", 
        "API request processed"
    ]
    
    for _ in range(count):
        level = random.choice(log_levels)
        message = random.choice(app_events)
        
        if level == logging.INFO:
            app_logger.info(message)
        elif level == logging.WARNING:
            app_logger.warning(f"{message} with warnings")
        else:
            app_logger.error(f"Failed to {message}")
        
        # Add a small delay for timestamps to be different
        time.sleep(0.01)

def generate_user_logs(count=200):
    """Generate user activity logs"""
    for _ in range(count):
        user_id = random.choice(user_ids)
        action = random.choice(user_actions)
        ip = random.choice(ip_addresses)
        
        user_logger.info(f"User {user_id} - {action} from IP {ip}")
        time.sleep(0.01)

def generate_admin_logs(count=50):
    """Generate admin activity logs"""
    for _ in range(count):
        admin_id = random.choice(admin_ids)
        action = random.choice(admin_actions)
        ip = random.choice(ip_addresses)
        target = random.choice(user_ids) if "User" in action else (
            random.choice(song_ids) if "Song" in action else "system"
        )
        
        admin_logger.info(f"Admin {admin_id} - {action} - Target: {target} from IP {ip}")
        time.sleep(0.01)

def generate_playlist_logs(count=150):
    """Generate playlist operation logs"""
    for _ in range(count):
        user_id = random.choice(user_ids)
        playlist_id = random.choice(playlist_ids)
        action = random.choice(playlist_ops)
        
        if "Added song" in action or "Removed song" in action:
            song_id = random.choice(song_ids)
            playlist_logger.info(f"User {user_id} - {action} {song_id} to playlist {playlist_id}")
        else:
            playlist_logger.info(f"User {user_id} - {action} {playlist_id}")
        
        time.sleep(0.01)

def generate_error_logs(count=30):
    """Generate error logs"""
    for _ in range(count):
        error = random.choice(errors)
        component = random.choice(["database", "auth", "storage", "api", "payment", "media", "cache"])
        
        error_logger.error(f"{error} in {component} component - Code: {random.randint(400, 599)}")
        time.sleep(0.01)

def generate_security_logs(count=40):
    """Generate security logs"""
    for _ in range(count):
        event = random.choice(security_events)
        ip = random.choice(ip_addresses)
        user_id = random.choice(user_ids)
        
        security_logger.warning(f"{event} - User: {user_id} - IP: {ip} - Severity: {random.choice(['Low', 'Medium', 'High', 'Critical'])}")
        time.sleep(0.01)

if __name__ == "__main__":
    print("Generating sample logs...")
    
    # Generate logs for testing
    generate_app_logs(100)
    generate_user_logs(200)
    generate_admin_logs(50)
    generate_playlist_logs(150)
    generate_error_logs(30)
    generate_security_logs(40)
    
    print("Sample logs generated successfully in the logs directory.")
    print("Available log files:")
    for log_file in os.listdir(log_dir):
        if log_file.endswith('.log'):
            log_path = os.path.join(log_dir, log_file)
            size_kb = os.path.getsize(log_path) / 1024
            print(f"- {log_file} ({size_kb:.2f} KB)") 