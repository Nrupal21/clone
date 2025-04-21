#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###############################################################################
# IMPORTS
###############################################################################
import os
import re
import sys
import time
import json
import uuid
import random
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
import logging
import mimetypes
from bson import ObjectId
from functools import wraps
from logging import FileHandler
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, send_from_directory, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from dotenv import load_dotenv
import atexit
from flask_cors import CORS
import click
import pytz
from urllib.parse import unquote
import montydb
import pymongo
import bcrypt
import math
import jinja2

from config import Config
from models.user import User
from models.song import Song
from models.subscription import Subscription
from models.playlist import Playlist
from models.activity_log import ActivityLog

from routes import auth, songs, admin

###############################################################################
# APPLICATION INITIALIZATION
###############################################################################
app = Flask(__name__, 
    static_folder='static',
    template_folder='templates'
)

###############################################################################
# LOGGING CONFIGURATION
###############################################################################
# Configure application-wide logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

# Suppress Werkzeug (Flask's development server) logging
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.ERROR)

# Suppress Flask development server startup messages
cli = logging.getLogger('flask.cli')
cli.setLevel(logging.ERROR)

# Setup main application logger with custom formatter
app_logger = logging.getLogger('spotify_app')
app_logger.setLevel(getattr(logging, Config.LOG_LEVEL))
file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
app_logger.addHandler(file_handler)

# Setup database logger
db_logger = logging.getLogger('database')
db_logger.setLevel(getattr(logging, Config.LOG_LEVEL))
db_handler = logging.FileHandler(os.path.join(log_dir, 'database.log'))
db_handler.setFormatter(formatter)
db_logger.addHandler(db_handler)

# Configure console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
app_logger.addHandler(console_handler)
db_logger.addHandler(console_handler)

###############################################################################
# FLASK APPLICATION CONFIGURATION
###############################################################################
# Configure app with Config class settings
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = Config.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER

# Initialize the app with Config
Config.init_app(app)

# Apply CORS with environment-specific configuration
if Config.DEBUG:
    CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True}})
else:
    # In production, restrict CORS to specific origins
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'https://example.com').split(',')
    CORS(app, resources={r"/*": {"origins": allowed_origins, "supports_credentials": True}})

###############################################################################
# DATABASE CONFIGURATION
###############################################################################
# Configure database
is_production = os.environ.get("SPOTIFY_ENVIRONMENT", "development") == "production"
app_logger.info(f"Environment: {'production' if is_production else 'development'}")

if is_production:
    # Connect to MongoDB in production
    client = pymongo.MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017/"))
    db = client.get_database("spotify")
    app_logger.info("Connected to MongoDB")
else:
    # Use MontyDB for development/testing
    client = montydb.MontyClient("database")
    db = client.spotify
    app_logger.info("Connected to MontyDB")

# Collections
users_collection = db.users
songs_collection = db.songs
playlists_collection = db.playlists

###############################################################################
# REQUEST HANDLING MIDDLEWARE
###############################################################################
@app.before_request
def before_request():
    """
    Process requests before they are handled by route functions.
    
    This middleware function:
    1. Sets the start time for request timing
    2. Checks if the user's session has timed out
    3. Updates the last activity timestamp for active sessions
    
    Returns:
        Redirect to login page if session has expired, otherwise None
    """
    # Ensure the db variable is accessible
    global db  # Add this line to make sure db is recognized

    # Set the start time for request timing
    request.start_time = datetime.now()
    
    # Check for session timeout
    if session.get('user_id') and session.get('last_activity'):
        inactive_time = datetime.now(timezone.utc).timestamp() - session.get('last_activity')
        max_inactive = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
        
        if inactive_time > max_inactive:
            app_logger.info(f"Session timeout for user {session.get('user_id')}")
            session.clear()
            return redirect(url_for('login_handler'))
        
        # Reset last_activity to prevent constant session updates
        if inactive_time > 60:  # Only update every minute to reduce writes
            session['last_activity'] = datetime.now(timezone.utc).timestamp()

    # Update last active timestamp for logged in users
    if 'user_id' in session:
        user_id = session.get('user_id')
        if db.users.find_one({"_id": ObjectId(user_id)}):
            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_active": datetime.now(timezone.utc)}}
            )

###############################################################################
# RESPONSE MIDDLEWARE SETUP
###############################################################################
@app.after_request
def after_request(response):
    """
    Process responses after they've been generated but before sending to client.
    
    This middleware function:
    1. Logs request details and response time
    2. Adds security headers to all responses
    
    Args:
        response: The Flask response object
        
    Returns:
        Flask response object with added security headers
    """
    # Skip logging for static files
    if not request.path.startswith('/static/'):
        # Calculate response time
        if hasattr(request, 'start_time'):
            duration = datetime.now() - request.start_time
            ms = int(duration.total_seconds() * 1000)
            
            # Log request details
            app_logger.info(f"{request.method} {request.path} {response.status_code} - {ms}ms")
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

###############################################################################
# TEMPLATE CONTEXT PROCESSOR
###############################################################################
@app.context_processor
def inject_user():
    """
    Inject user data into all templates.
    
    This context processor makes user data available to all templates
    automatically by checking the session for a logged in user.
    
    Returns:
        dict: Dictionary with user, current_user and is_admin
    """
    user = None
    is_admin = False
    
    if session.get('user_id'):
        user = User.get_user(session.get('user_id'))
        if user:
            is_admin = user.get('is_admin', False)
            
    return dict(user=user, current_user=user, is_admin=is_admin)

###############################################################################
# HELPER FUNCTIONS
###############################################################################
def allowed_file(filename, allowed_extensions=None):
    """
    Check if an uploaded file has an allowed extension.
    
    Args:
        filename (str): The name of the file to check
        allowed_extensions (set, optional): Set of allowed extensions. Defaults to None.
        
    Returns:
        bool: True if the file has an allowed extension, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = {'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'png', 'jpg', 'jpeg', 'gif'}
        
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

###############################################################################
# USER AUTHENTICATION HELPER FUNCTIONS
###############################################################################
def get_current_user():
    """
    Get the current logged-in user for use in route handlers.
    
    This function retrieves the current user's data from the database
    based on the user_id stored in the session.
    
    Returns:
        dict: User object or None if not logged in
    """
    if not session.get('user_id'):
        return None
    
    user = User.get_user(session.get('user_id'))
    if not user and session.get('user_id'):
        # User was deleted or doesn't exist
        app_logger.warning(f"User {session.get('user_id')} not found in database")
        session.clear()
    
    return user

###############################################################################
# AUTHORIZATION DECORATORS
###############################################################################
def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login_handler'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login_handler'))
        
        user = User.get_by_id(session['user_id'])
        if not user or not user.get('is_admin', False):
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('home'))
            
        return f(*args, **kwargs)
    return decorated_function

###############################################################################
# BLUEPRINT REGISTRATION
###############################################################################
# Register authentication routes
app.route('/signup', methods=['POST'])(auth.signup_user)
app.route('/login', methods=['POST'])(auth.login)
# Register song-related routes
app.register_blueprint(songs.songs, url_prefix='/songs')
# Register admin routes
app.register_blueprint(admin.admin, url_prefix='/admin')

###############################################################################
# AUTHENTICATION PAGE ROUTES
###############################################################################
@app.route('/signup', methods=['GET'])
def signup_page():
    """
    Render the signup page or redirect to index if already logged in.
    
    This route handles GET requests to the signup page and checks if
    the user is already logged in before rendering the template.
    
    Returns:
        str: Rendered HTML template or redirect response
    """
    if session.get('user_id'):
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/login', methods=['GET'])
def login_page():
    """
    Render the login page or redirect to appropriate dashboard based on user role.
    
    This route handles GET requests to the login page and redirects logged-in
    users to either the admin dashboard or main index page based on their role.
    
    Returns:
        str: Rendered HTML template or redirect response
    """
    if session.get('user_id'):
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout the current user."""
    user_id = session.get('user_id')
    
    if user_id:
        # Log the logout activity
        ActivityLog.log_activity(
            user_id=user_id,
            action_type=ActivityLog.ACTION_LOGOUT,
            resource_type=ActivityLog.RESOURCE_USER,
            resource_id=user_id,
            details={"ip_address": request.remote_addr}
        )
        
        # Clear session
    session.clear()
        
    # Redirect to login page
    flash('You have been logged out.', 'info')
    return redirect(url_for('login_handler'))

###############################################################################
# TEST DATA MANAGEMENT ROUTES
###############################################################################
@app.route("/add-test-songs", methods=['GET', 'POST'])
def add_test_songs():
    """
    Add test songs to the database for development and testing.
    
    This route:
    1. Checks if the request is authorized
    2. Imports test song data from a JSON file
    3. Creates song objects in the database
    
    Returns:
        Response: JSON result of the operation
    """
    # Security check - only allow in development mode with correct token
    if not Config.DEBUG:
        return jsonify({"error": "Not available in production mode"}), 403
        
    token = request.args.get('token')
    if token != Config.SECRET_KEY[:8]:
        return jsonify({"error": "Invalid token"}), 403
    
    if request.method == 'POST':
        try:
            # Load test song data
            with open('test_songs.json', 'r') as f:
                songs_data = json.load(f)
            
            # Track results
            results = {
                "success": 0,
                "failed": 0,
                "songs": []
            }
            
            # Process each song
            for song_data in songs_data:
                try:
                    # Create the song object
                    song = Song.create(
                        title=song_data.get('title', 'Unknown'),
                        artist=song_data.get('artist', 'Unknown'),
                        album=song_data.get('album', 'Single'),
                        mood=song_data.get('mood', 'Happy'),
                        audio_file=song_data.get('audio_file', ''),
                        image_path=song_data.get('image_path', '')
                    )
                    
                    # Track successful creation
                    if song and song.get('_id'):
                        results["success"] += 1
                        results["songs"].append({
                            "id": str(song.get('_id')),
                            "title": song.get('title')
                        })
                    else:
                        results["failed"] += 1
                        
                except Exception as e:
                    app_logger.error(f"Error adding test song: {str(e)}")
                    results["failed"] += 1
            
            return jsonify(results)
            
        except Exception as e:
            app_logger.error(f"Error in add_test_songs: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    # For GET requests, show a form to trigger the import
    return '''
        <form method="post">
            <h1>Import Test Songs</h1>
            <p>This will import test songs from test_songs.json</p>
            <button type="submit">Import Now</button>
        </form>
    '''

###############################################################################
# MAIN APPLICATION ROUTES
###############################################################################
@app.route("/")
def home():
    """
    Render the home page with featured and recommended songs.
    
    This route:
    1. Fetches songs from the database grouped by mood
    2. Gets user-specific recommendations if logged in
    3. Renders the home page template with song data
    
    Returns:
        Response: Rendered home page
    """
    user = None
    is_admin = False
    
    if session.get('user_id'):
        # Get user data if logged in
        user = User.get_user(session.get('user_id'))
        if user is None:
            is_admin = False  # Default value if user is not found
        else:
            is_admin = user.get('is_admin', False)  # Safely access is_admin if user exists
        session['is_admin'] = is_admin

    # Get all songs using the Song model - convert to list to avoid TypeError
    all_songs = list(Song.get_songs())
    songs_by_mood = {}
    
    # Get trending songs (most played) - convert to list to avoid TypeError
    trending_songs = list(Song.get_songs(sort_by='plays', limit=12))
    
    # Group songs by mood using dictionary comprehension
    for song in all_songs:
        mood = song.get('mood', 'Other')
        if mood not in songs_by_mood:
            songs_by_mood[mood] = []
        songs_by_mood[mood].append(song)
    
    return render_template('index.html', 
                         user=user,
                         is_admin=is_admin,
                         songs_by_mood=songs_by_mood,
                         trending_songs=trending_songs,
                         all_songs=all_songs)

###############################################################################
# SEARCH FUNCTIONALITY
###############################################################################
@app.route("/search")
def search():
    """
    Search for songs, artists, and playlists.
    
    This route handles search functionality across the application,
    supporting search by query parameters for various content types.
        
    Returns:
        Response: Rendered search results template with found items
    """
    query = request.args.get('q', '')
    mood = request.args.get('mood', '')
    page = request.args.get('page', 1, type=int)
    
    # Default values
    results = {
        'songs': [],
        'artists': [],
        'playlists': []
    }
    
    # Get current user for template rendering
    user_id = session.get('user_id')
    user = get_current_user() if user_id else None
    
    # If no search query and no mood filter, return empty results
    if not query and not mood:
        return render_template('search.html', 
                              results=results, 
                              query='', 
                              page=1, 
                              total=0,
                              user=user)
    
    # Get songs matching query
    songs = Song.search(query) if query else []
    
    # Apply mood filter if provided
    if mood and songs:
        songs = [song for song in songs if song.get('mood') == mood]
    elif mood and not query:
        # If only mood filter is provided
        songs = Song.get_songs(mood=mood)
    
    # Count total songs for pagination
    total_songs = len(songs)
    
    # Calculate pagination values
    per_page = getattr(Config, 'SONGS_PER_PAGE', 20)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Paginate results
    paginated_songs = songs[start_idx:end_idx] if songs else []
    
    # Prepare results
    results['songs'] = paginated_songs
    
    # Get user's liked songs if logged in
    liked_song_ids = []
    if user_id:
        liked_song_ids = Song.get_liked_song_ids(user_id)
    
    # Get unique artists from search results
    artists = {}
    for song in songs:
        artist_name = song.get('artist')
        if artist_name and artist_name not in artists:
            artists[artist_name] = {
                'name': artist_name,
                'song_count': 1
            }
        elif artist_name:
            artists[artist_name]['song_count'] += 1
    
    results['artists'] = list(artists.values())
    
    # Calculate total pages for pagination
    total_pages = (total_songs + per_page - 1) // per_page
    
    # Prepare pagination info
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total_songs,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }
    
    # Log search activity if user is logged in
    if user_id:
        ActivityLog.log_activity(
            user_id=user_id,
            action_type=ActivityLog.ACTION_SEARCH,
            resource_type=ActivityLog.RESOURCE_SYSTEM,
            details={
                "query": query,
                "mood": mood,
                "results_count": total_songs
            }
        )
    
    return render_template(
        'search.html',
        results=results,
        query=query,
        mood=mood,
        pagination=pagination,
        user=user,
        liked_song_ids=liked_song_ids
    )

###############################################################################
# SESSION MANAGEMENT
###############################################################################
@app.route('/extend-session', methods=['POST'])
def extend_session():
    """
    Endpoint to extend the user's session when they're active.
    
    This route updates the last_activity timestamp in the session
    to prevent timeout for active users.
    
    Returns:
        Response: JSON response with status message
    """
    if session.get('user_id'):
        session['last_activity'] = datetime.now(timezone.utc).timestamp()
        return jsonify({"message": "Session extended"}), 200
    return jsonify({"message": "No active session"}), 401

###############################################################################
# MONITORING AND HEALTH CHECK
###############################################################################
@app.route("/health")
def health_check():
    # Check if the database is connected
    try:
        # Ping the database
        db.command('ping')
        db_status = "connected"
    except Exception as e:
        app.logger.error(f"Database connection error: {str(e)}")
        db_status = "disconnected"
    
    # Basic application status
    status = {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "version": "1.0.0"
    }
    
    # Return JSON response with appropriate status code
    return jsonify(status), 200 if status["status"] == "healthy" else 503

###############################################################################
# USER PROFILE ROUTES
###############################################################################
@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    user_id = session.get('user_id')
    
    # Get user data
    user = User.get_by_id(user_id)
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login_handler'))
    
    # Get user's playlists
    playlists = Playlist.get_user_playlists(user_id)
    
    # Get user's liked songs
    liked_songs = Song.get_liked_songs(user_id)
    
    # Render profile page
    return render_template('profile.html', user=user, playlists=playlists, liked_songs=liked_songs)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile page."""
    user_id = session.get('user_id')
    
    # Get user data
    user = User.get_by_id(user_id)
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login_handler'))
    
    if request.method == 'POST':
            # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
            
            # Update user data
        updated = User.update(user_id, name=name, email=email)
        
        if updated:
            flash('Profile updated successfully.', 'success')
        else:
            flash('Error updating profile.', 'error')
        
        return redirect(url_for('profile'))
    
    # Render edit profile page
    return render_template('edit_profile.html', user=user)

@app.route('/profile/activity')
@login_required
def user_activity():
    """Display user activity history."""
    user_id = session.get('user_id')
    
    # Get current user
    user = User.get_by_id(user_id)
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login_handler'))
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    skip = (page - 1) * per_page
    
    # Get user activity logs
    activity_logs = ActivityLog.get_user_activity(
        user_id=user_id,
        limit=per_page,
        skip=skip
    )
    
    # Add additional context to logs
    for log in activity_logs:
        # Add resource details based on type
        if log['resource_type'] == ActivityLog.RESOURCE_SONG and log.get('resource_id'):
            song = Song.get_by_id(log['resource_id'])
            if song:
                log['resource_name'] = song.get('title')
        elif log['resource_type'] == ActivityLog.RESOURCE_PLAYLIST and log.get('resource_id'):
            playlist = Playlist.get_by_id(log['resource_id'])
            if playlist:
                log['resource_name'] = playlist.get('name')
    
    # Total count for pagination
    total_count = logs_collection.count_documents({"user_id": user_id})
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template(
        'activity.html',
        user=user,
        activity_logs=activity_logs,
        page=page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

###############################################################################
# USER LIBRARY ROUTES
###############################################################################
@app.route('/library')
@login_required
def library():
    user_id = session.get('user_id')
    
    # Get user's liked songs
    liked_songs = Song.get_liked_songs(user_id)
    
    # Get user's playlists
    playlists = Playlist.get_user_playlists(user_id)
    
    return render_template('library.html', 
                          liked_songs=liked_songs,
                          playlists=playlists)

@app.route('/like-song/<song_id>', methods=['POST'])
@login_required
def like_song(song_id):
    user_id = session.get('user_id')
    
    # Toggle like status
    success = Song.toggle_like(song_id, user_id)
    
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Failed to update like status"}), 400

@app.route('/playlist/<playlist_id>')
def view_playlist(playlist_id):
    # Get playlist details
    playlist = Playlist.get_by_id(playlist_id)
    
    if not playlist:
        flash('Playlist not found', 'error')
        return redirect(url_for('home'))
    
    # Check if user is authorized to view this playlist
    user_id = session.get('user_id')
    if playlist.get('is_private', False) and str(playlist.get('user_id')) != user_id:
        flash('You do not have permission to view this playlist', 'error')
        return redirect(url_for('home'))
    
    # Get songs in playlist
    songs = Playlist.get_songs(playlist_id)
    
    return render_template('playlist.html', playlist=playlist, songs=songs)

@app.route('/playlist/new', methods=['GET', 'POST'])
@login_required
def create_playlist():
    """Create a new playlist."""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description', '')
        is_private = request.form.get('is_private') == 'on'
        
        # Validate title
        if not title:
            flash('Please provide a title for your playlist.', 'error')
            return render_template('create_playlist.html')
        
        # Create playlist
        try:
            playlist_id = Playlist.create(
                title=title,
                description=description,
                user_id=user_id,
                is_private=is_private
            )
            
            if playlist_id:
                # Log the playlist creation
                ActivityLog.log_activity(
                    user_id=user_id,
                    action_type=ActivityLog.ACTION_PLAYLIST_CREATE,
                    resource_type=ActivityLog.RESOURCE_PLAYLIST,
                    resource_id=playlist_id,
                    details={
                        "title": title,
                        "description": description,
                        "is_private": is_private
                    }
                )
                
                flash('Playlist created successfully!', 'success')
                return redirect(url_for('view_playlist', playlist_id=playlist_id))
            else:
                flash('Error creating playlist.', 'error')
        except Exception as e:
            app_logger.error(f"Error creating playlist: {e}")
            flash('An error occurred while creating your playlist.', 'error')
        
    # Render playlist creation form
    return render_template('create_playlist.html')

@app.route('/add-to-playlist/<song_id>/<playlist_id>', methods=['POST'])
@login_required
def add_to_playlist(song_id, playlist_id):
    # Check if user owns this playlist
    user_id = session.get('user_id')
    playlist = Playlist.get_by_id(playlist_id)
    
    if not playlist:
        return jsonify({"status": "error", "message": "Playlist not found"}), 404
    
    if str(playlist.get('user_id')) != user_id:
        return jsonify({"status": "error", "message": "Not authorized"}), 403
    
    # Add song to playlist
    success = Playlist.add_song(playlist_id, song_id)
    
    if success:
        # Log the activity
        song = Song.get_by_id(song_id)
        song_title = song.get('title', 'Unknown') if song else 'Unknown'
        
        ActivityLog.log_activity(
            user_id=user_id,
            action_type=ActivityLog.ACTION_PLAYLIST_ADD_SONG,
            resource_type=ActivityLog.RESOURCE_PLAYLIST,
            resource_id=playlist_id,
            details={
                "song_id": song_id,
                "song_title": song_title,
                "playlist_name": playlist.get('name', 'Unknown')
            }
        )
        
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Failed to add song to playlist"}), 400

###############################################################################
# SONG DEBUGGING ROUTES
###############################################################################
@app.route('/debug/song/<song_id>')
def debug_song(song_id):
    """Route for debugging a specific song details"""
    # Only allow in development mode
    if not app.config['DEBUG']:
        abort(404)
        
    song = Song.get_by_id(song_id)
    return jsonify(song)

@app.route('/debug/audio-test/<song_id>')
def debug_audio_file(song_id):
    """Debug route to test audio file access directly."""
    if not session.get('user_id'):
        return jsonify({"error": "Authentication required"}), 401
        
    try:
        # Only admins can access this route
        user = User.get_by_id(session.get('user_id'))
        if not user or not user.get('is_admin'):
            return jsonify({"error": "Admin access required"}), 403
            
        song = Song.get_by_id(song_id)
        if not song:
            return jsonify({"error": "Song not found"}), 404
            
        file_path = song.get('file_path')
        if not file_path:
            return jsonify({"error": "No file path in song data"}), 404
            
        # Check all possible paths
        possible_paths = [
            file_path,
            os.path.join("static", file_path),
            os.path.join(Config.UPLOAD_FOLDER, os.path.basename(file_path)),
            os.path.join("static", "songs", song.get('mood', '') + "_(mood)", os.path.basename(file_path))
        ]
        
        valid_paths = []
        for path in possible_paths:
            if os.path.exists(path):
                size = os.path.getsize(path)
                valid_paths.append({
                    "path": path,
                    "size": size,
                    "size_human": f"{size / 1024:.2f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB"
                })
                
        # Check mood directory for match in info.json
        if song.get('mood'):
            mood_dir = f"{song['mood']}_(mood)"
            info_path = os.path.join("static", "songs", mood_dir, "info.json")
            
            if os.path.exists(info_path):
                with open(info_path, 'r') as f:
                    try:
                        info = json.load(f)
                        for song_info in info.get("songs", []):
                            if song_info.get("title") == song.get("title") and song_info.get("artist") == song.get("artist"):
                                mood_file_path = os.path.join("static", "songs", mood_dir, song_info.get("filename"))
                                if os.path.exists(mood_file_path):
                                    size = os.path.getsize(mood_file_path)
                                    valid_paths.append({
                                        "path": mood_file_path,
                                        "source": "info.json match",
                                        "size": size,
                                        "size_human": f"{size / 1024:.2f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB"
                                    })
                    except json.JSONDecodeError:
                        pass
                        
        return jsonify({
            "song": song,
            "file_path": file_path,
            "valid_paths": valid_paths,
            "possible_paths": possible_paths,
            "direct_access_url": url_for('play_song', song_id=song_id, _external=True)
        })
        
    except Exception as e:
        app_logger.error(f"Error in debug_audio_file: {str(e)}")
        return jsonify({"error": str(e)}), 500

###############################################################################
# MEDIA FILE SERVING ROUTES
###############################################################################
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Route to serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/audio/<path:filename>')
def audio_file(filename):
    """Route to serve audio files with proper headers"""
    response = send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), filename)
    response.headers['Accept-Ranges'] = 'bytes'
    return response

###############################################################################
# SONG MANAGEMENT ROUTES
###############################################################################
@app.route('/songs/<song_id>')
def song_detail(song_id):
    """Route to display song details"""
    song = Song.get_song(song_id)
    
    if not song:
        flash('Song not found', 'error')
        return redirect(url_for('home'))
        
    # Get related songs (same mood)
    related_songs = Song.get_songs(mood=song.get('mood', 'Unknown'), limit=5)
    
    # Remove current song from related
    related_songs = [s for s in related_songs if str(s.get('_id')) != song_id]
    
    # Get current user for like status
    user_id = session.get('user_id')
    if user_id:
        user_likes = Song.get_liked_song_ids(user_id)
        for s in related_songs:
            s['is_liked'] = str(s.get('_id')) in user_likes
        song['is_liked'] = str(song.get('_id')) in user_likes
    
    return render_template('song_detail.html', song=song, related_songs=related_songs)

@app.route('/mood/<mood_name>')
def mood_songs(mood_name):
    """Route to display songs by mood"""
    # URL decode the mood name
    mood_name = unquote(mood_name)
    
    # Get songs for this mood
    songs = Song.get_songs(mood=mood_name)
    
    # Get current user for like status
    user_id = session.get('user_id')
    if user_id:
        user_likes = Song.get_liked_song_ids(user_id)
        for song in songs:
            song['is_liked'] = str(song.get('_id')) in user_likes
    
    return render_template('mood.html', mood=mood_name, songs=songs)

@app.route('/admin/songs/delete/<song_id>', methods=['POST'])
def admin_delete_song(song_id):
    """Delete song."""
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_handler'))
    
    # Get user data
    user = User.get_by_id(user_id)
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login_handler'))
    
    # Check if user is admin
    if not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('home'))
    
    # Delete song
    try:
        Song.delete_song(song_id)
        flash('Song deleted.', 'success')
    except Exception as e:
        app_logger.error(f"Error deleting song: {e}")
        flash('Error deleting song.', 'error')
    
    # Redirect to manage songs page
    return redirect(url_for('manage_songs'))

#################################################
# UTILITY FUNCTIONS
#################################################
def serialize_objectid(obj):
    """Convert MongoDB ObjectIDs to strings in a dictionary"""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if isinstance(obj[key], ObjectId):
                obj[key] = str(obj[key])
            elif isinstance(obj[key], (dict, list)):
                obj[key] = serialize_objectid(obj[key])
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = serialize_objectid(item)
    return obj

def format_timestamp(timestamp):
    """Format a timestamp for display"""
    if isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return timestamp

#################################################
# AUTHENTICATION ROUTES
#################################################
@app.route('/signup', methods=['GET', 'POST'])
def signup_handler():
    """
    Handle user signup requests.
    
    This route:
    1. For GET requests: Renders the signup form
    2. For POST requests: Processes new user registration
    
    Returns:
        str: Rendered HTML template or redirect response
    """
    # Handle user registration
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        
        # Basic validation
        if not all([name, email, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('signup_handler'))
            
        # Check if email already exists
        if db.users.find_one({"email": email}):
            flash('Email already registered', 'error')
            return redirect(url_for('signup_handler'))
            
        # Check if username already exists (if provided)
        if username and db.users.find_one({"username": username}):
            flash('Username already taken', 'error')
            return redirect(url_for('signup_handler'))
            
        # Generate username if not provided
        if not username:
            # Create a username from the name (lowercase, no spaces)
            username = name.lower().replace(" ", "")
            
            # Check if username exists, append numbers if needed
            base_username = username
            count = 1
            while db.users.find_one({"username": username}):
                username = f"{base_username}{count}"
                count += 1
            
        # Create new user
        hashed_password = generate_password_hash(password)
        user_data = {
            "name": name,
            "username": username,
            "email": email,
            "password": hashed_password,
            "created_at": datetime.now(timezone.utc),
            "last_active": datetime.now(timezone.utc),
            "is_admin": False,
            "liked_songs": [],
            "playlists": []
        }
        
        result = db.users.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Log in the user
        session['user_id'] = user_id
        flash('Account created successfully!', 'success')
        return redirect(url_for('home'))
    
    # For GET requests
    if session.get('user_id'):
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login_handler():
    """
    Handle user login requests.
    
    This route:
    1. For GET requests: Renders the login form
    2. For POST requests: Authenticates user credentials
    
    Returns:
        str: Rendered HTML template or redirect response
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email and password are provided
        if not email or not password:
            flash('Please provide email and password.', 'error')
            return render_template('login.html')
        
        # Check if user exists
        user = User.get_by_email(email)
        if not user:
            flash('Invalid email or password.', 'error')
            return render_template('login.html')
        
        # Check if password is correct
        if not check_password_hash(user['password'], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')
        
        # Set user ID in session
        user_id = str(user['_id'])
        session['user_id'] = user_id
        
        # Log the login activity
        ActivityLog.log_activity(
            user_id=user_id,
            action_type=ActivityLog.ACTION_LOGIN,
            resource_type=ActivityLog.RESOURCE_USER,
            resource_id=user_id,
            details={"ip_address": request.remote_addr}
        )
        
        # Check if user is admin and set the session variable
        is_admin = user.get('is_admin', False)
        session['is_admin'] = is_admin
        
        # Redirect to appropriate dashboard
        if is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))
    
    # For GET requests
    if session.get('user_id'):
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))
    
    # Render login page
    return render_template('login.html')

#######################
# AUTHENTICATION ROUTES
#######################
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    """Register page."""
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if all fields are provided
        if not name or not email or not password or not confirm_password:
            flash('Please fill out all required fields.', 'error')
            return render_template('signup.html')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        
        # Username is optional, but if provided, check if it already exists
        if username and User.get_by_username(username):
            flash('Username already exists.', 'error')
            return render_template('signup.html')
        
        # Check if email already exists
        if User.get_by_email(email):
            flash('Email already exists.', 'error')
            return render_template('signup.html')
        
        # Create user
        user = User.create(username, name, email, password)
        if not user:
            flash('Error creating user.', 'error')
            return render_template('signup.html')
        
        # Set user ID in session
        session['user_id'] = user['_id']
        
        # Redirect to home page
        return redirect(url_for('home'))
    
    # If user is already logged in, redirect to home page
    if session.get('user_id'):
        return redirect(url_for('home'))
    
    # Render register page
    return render_template('signup.html')

#######################
# SONG MANAGEMENT ROUTES
#######################
@app.route('/songs')
def list_songs():
    """List songs."""
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_handler'))
    
    # Get user data
    user = User.get_by_id(user_id)
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login_handler'))
    
    # Get songs
    songs = Song.get_songs()
    
    # Render songs page
    return render_template('songs.html', user=user, songs=songs)

@app.route('/play/<song_id>')
def play_song(song_id):
    """Play a song."""
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to log in to play songs.', 'error')
        return redirect(url_for('login_handler'))
    
    try:
        # Get song by ID
        app_logger.info(f"Attempting to play song with ID: {song_id}")
        song = Song.get_by_id(song_id)
        
        # Check if song exists
        if not song:
            app_logger.error(f"Song with ID {song_id} not found.")
            return jsonify({"error": "Song not found"}), 404
        
        # Get file path
        file_path = song.get('file_path')
        if not file_path:
            app_logger.error(f"File path for song with ID {song_id} not found.")
            return jsonify({"error": "Song file not found"}), 404
        
        app_logger.info(f"Retrieved file path: {file_path}")
        
        # Check for valid file path formats - try different path combinations
        possible_paths = [
            file_path,  # as stored in database
            os.path.join("static", file_path),  # prepend static folder
            os.path.join(Config.UPLOAD_FOLDER, os.path.basename(file_path)),  # try upload folder
            os.path.join("static", "songs", song.get('mood', '') + "_(mood)", os.path.basename(file_path))  # mood folder path
        ]
        
        # Find first valid path
        valid_path = None
        for path in possible_paths:
            app_logger.info(f"Checking path: {path}")
            if os.path.exists(path):
                valid_path = path
                app_logger.info(f"Found valid file at: {valid_path}")
                break
        
        if not valid_path:
            # Check in mood directory if possible
            if song.get('mood'):
                mood_dir = f"{song['mood']}_(mood)"
                info_path = os.path.join("static", "songs", mood_dir, "info.json")
                
                try:
                    if os.path.exists(info_path):
                        with open(info_path, 'r') as f:
                            info = json.load(f)
                            for song_info in info.get("songs", []):
                                if song_info.get("title") == song.get("title") and song_info.get("artist") == song.get("artist"):
                                    mood_file_path = os.path.join("static", "songs", mood_dir, song_info.get("filename"))
                                    app_logger.info(f"Trying mood info.json file path: {mood_file_path}")
                                    if os.path.exists(mood_file_path):
                                        valid_path = mood_file_path
                                        app_logger.info(f"Found valid file in mood directory: {valid_path}")
                                        break
                except Exception as e:
                    app_logger.error(f"Error checking mood info.json: {str(e)}")
        
        if not valid_path:
            app_logger.error(f"No valid file path found for song. Checked paths: {possible_paths}")
            return jsonify({"error": "Audio file does not exist"}), 404
        
        app_logger.info(f"Playing song from path: {valid_path}")
        
        # Increment play count
        try:
            Song.increment_plays(song_id)
            
            # Log song play activity
            ActivityLog.log_activity(
                user_id=user_id,
                action_type=ActivityLog.ACTION_SONG_PLAY,
                resource_type=ActivityLog.RESOURCE_SONG,
                resource_id=song_id,
                details={
                    "title": song.get('title', 'Unknown'),
                    "artist": song.get('artist', 'Unknown'),
                    "mood": song.get('mood', 'Unknown')
                }
            )
        except Exception as e:
            app_logger.warning(f"Failed to increment play count for song {song_id}: {str(e)}")
        
        # Set appropriate MIME type based on file extension
        _, file_extension = os.path.splitext(valid_path)
        mime_type = 'audio/mpeg'  # default for MP3
        
        if file_extension.lower() == '.wav':
            mime_type = 'audio/wav'
        elif file_extension.lower() == '.ogg':
            mime_type = 'audio/ogg'
        elif file_extension.lower() == '.m4a':
            mime_type = 'audio/mp4'
        
        # Send the file with appropriate headers for streaming
        response = send_file(valid_path, mimetype=mime_type)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache'
        
        return response
    
    except Exception as e:
        app_logger.error(f"Error playing song: {str(e)}")
        app_logger.exception("Full exception traceback:")
        return jsonify({"error": str(e)}), 500

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard page with system overview and statistics."""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        sort_by = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        search_query = request.args.get('q', '')
        
        # Calculate skip value for pagination
        skip = (page - 1) * limit
        
        # Set sort direction
        sort_direction = DESCENDING if order == 'desc' else ASCENDING
        
        # Access MongoDB collections - Make sure we use the global db variable
        users_collection = db.users
        songs_collection = db.songs
        playlists_collection = db.playlists
        
        # Build search query
        query = {}
        if search_query:
            query = {
                "$or": [
                    {"username": {"$regex": f".*{search_query}.*", "$options": "i"}},
                    {"email": {"$regex": f".*{search_query}.*", "$options": "i"}},
                    {"name": {"$regex": f".*{search_query}.*", "$options": "i"}}
                ]
            }
        
        # Get users with pagination and sorting
        users = list(users_collection.find(query).sort(sort_by, sort_direction).skip(skip).limit(limit))
        
        # Get songs with pagination and sorting
        songs_query = {}
        if search_query:
            songs_query = {
                "$or": [
                    {"title": {"$regex": f".*{search_query}.*", "$options": "i"}},
                    {"artist": {"$regex": f".*{search_query}.*", "$options": "i"}},
                    {"mood": {"$regex": f".*{search_query}.*", "$options": "i"}}
                ]
            }
        songs = list(songs_collection.find(songs_query).sort(sort_by, sort_direction).skip(skip).limit(limit))
        
        # Get total counts
        total_users = users_collection.count_documents({})
        total_songs = songs_collection.count_documents({})
        total_playlists = playlists_collection.count_documents({})
        
        # Get distinct mood count
        distinct_moods = songs_collection.distinct("mood", {"mood": {"$exists": True, "$ne": None}})
        mood_count = len(distinct_moods) if distinct_moods else 0
        
        # Get subscription stats
        subscription_counts = Subscription.get_subscription_counts() if 'Subscription' in globals() else {"premium_active": 0, "free": 0, "premium_expired": 0}
        premium_count = subscription_counts.get("premium_active", 0)
        free_count = subscription_counts.get("free", 0)
        expired_count = subscription_counts.get("premium_expired", 0)
        
        # Get recent items
        recent_songs = list(songs_collection.find().sort("created_at", DESCENDING).limit(5))
        recent_users = list(users_collection.find().sort("created_at", DESCENDING).limit(5))
        
        # Get active users in last 7 days
        active_users_cursor = users_collection.find({
            "last_active": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}
        })
        active_count = len(list(active_users_cursor))
        
        # Create stats dictionary
        stats = {
            "user_count": total_users,
            "song_count": total_songs,
            "playlist_count": total_playlists,
            "mood_count": mood_count,
            "premium_count": premium_count,
            "free_count": free_count,
            "expired_count": expired_count,
            "recent_songs": recent_songs,
            "recent_users": recent_users,
            "active_count": active_count
        }
        
        # Prepare pagination info
        pagination = {
            'page': page,
            'per_page': limit,
            'total': total_users,
            'total_pages': max(1, (total_users + limit - 1) // limit),
            'has_prev': page > 1,
            'has_next': page < ((total_users + limit - 1) // limit)
        }
        
        # Render admin dashboard
        return render_template(
            'admin.html', 
            users=users, 
            songs=songs,
            stats=stats,
            pagination=pagination,
            current_sort=sort_by,
            current_order=order,
            search_query=search_query
        )
        
    except Exception as e:
        app_logger.error(f"Error rendering admin dashboard: {str(e)}")
        app_logger.exception("Full exception traceback:")
        
        # Create empty stats for error case
        empty_stats = {
            "user_count": 0,
            "song_count": 0,
            "playlist_count": 0,
            "mood_count": 0,
            "premium_count": 0,
            "free_count": 0,
            "expired_count": 0,
            "recent_songs": [],
            "recent_users": [],
            "active_count": 0
        }
        
        # Default pagination for error case
        default_pagination = {
            'page': page,
            'per_page': limit,
            'total': 0,
            'total_pages': 1,
            'has_prev': False,
            'has_next': False
        }
        
        return render_template(
            'admin.html', 
            error=str(e), 
            users=[], 
            songs=[], 
            stats=empty_stats,
            pagination=default_pagination,
            current_sort=sort_by,
            current_order=order,
            search_query=search_query
        )

@app.route('/admin/subscriptions')
@admin_required
def admin_subscriptions():
    """Alias for subscription management."""
    return redirect(url_for('admin_subscription_management', type='all'))

@app.route('/admin/subscriptions/<type>')
@admin_required
def admin_subscription_management(type='all'):
    """Admin page for subscription management."""
    try:
        # Process subscription type filter
        valid_types = {'all', 'premium', 'free', 'expired'}
        if type not in valid_types:
            type = 'all'
            
        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        plan_type = request.args.get('plan_type', type if type != 'all' else 'all')
        cycle = request.args.get('cycle', 'all')
        sort = request.args.get('sort', 'start_date')
        direction = request.args.get('direction', 'desc')
        
        # Set up filters based on parameters
        filters = {}
        
        # Filter by subscription type
        if plan_type != 'all':
            filters['type'] = plan_type
            
        # Filter by status
        if status != 'all':
            filters['status'] = status
            
        # Filter by billing cycle
        if cycle != 'all':
            filters['billing_cycle'] = cycle
            
        # Get subscription statistics
        stats = Subscription.get_subscription_counts()
        
        # Default values for billing cycle counts if not available
        if 'monthly_count' not in stats:
            stats['monthly_count'] = 0
        if 'yearly_count' not in stats:
            stats['yearly_count'] = 0
        if 'trial_count' not in stats:
            stats['trial_count'] = 0
            
        # Get paginated subscriptions
        per_page = 20
        skip = (page - 1) * per_page
        
        # Set sort direction
        sort_dir = -1 if direction == 'desc' else 1
        
        # Get subscriptions with pagination and filtering
        result = Subscription.get_subscriptions(
            filters=filters,
            sort_by=sort,
            sort_direction=sort_dir,
            limit=per_page,
            skip=skip
        )
        
        subscriptions = result.get('subscriptions', [])
        total_count = result.get('total', 0)
        
        # Set title based on type
        titles = {
            'all': 'All Subscriptions',
            'premium': 'Premium Subscriptions',
            'free': 'Free Tier Users',
            'expired': 'Expired Subscriptions'
        }
        subscriptions_title = titles.get(type, 'Subscriptions')
        
        # Prepare pagination info
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'total_pages': max(1, (total_count + per_page - 1) // per_page),
            'has_prev': page > 1,
            'has_next': page < ((total_count + per_page - 1) // per_page)
        }
        
        # Add format_currency filter for templates
        @app.template_filter('format_currency')
        def format_currency(value):
            if value is None:
                return 'Free'
            return f'${float(value):.2f}'
            
        # Render subscription management page
        return render_template(
            'admin_subscription_management.html',
            subscriptions=subscriptions,
            subscriptions_title=subscriptions_title,
            stats=stats,
            pagination=pagination,
            type=type
        )
        
    except Exception as e:
        app_logger.error(f"Error in admin_subscription_management: {str(e)}")
        flash(f'Error managing subscriptions: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/settings')
@admin_required
def admin_settings():
    """Admin settings page."""
    try:
        # Get log files for the log section
        log_dir = os.path.join(app.root_path, 'logs')
        logs = []
        
        if os.path.exists(log_dir):
            for log_file in os.listdir(log_dir):
                if log_file.endswith('.log'):
                    file_path = os.path.join(log_dir, log_file)
                    size_kb = os.path.getsize(file_path) / 1024
                    size = f"{size_kb:.1f} KB"
                    modified = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    logs.append({
                        'name': log_file,
                        'path': file_path,
                        'size': size,
                        'modified': modified
                    })
            
            # Sort logs by modification time (newest first)
            logs.sort(key=lambda x: x['modified'], reverse=True)
        
        return render_template('admin_settings.html', logs=logs)
    except Exception as e:
        app_logger.error(f"Error in admin_settings: {str(e)}")
        flash(f"Error accessing settings: {str(e)}", 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear-cache', methods=['POST'])
@admin_required
def admin_clear_cache():
    """Clear application cache."""
    try:
        # Log the cache clearing action
        app_logger.info(f"Application cache cleared by admin {session.get('user_id')} from IP {request.remote_addr}")
        
        # Here you would implement actual cache clearing logic
        # This could involve clearing Flask-Caching cache, Redis cache, etc.
        # For now, we'll just simulate success
        
        flash('Application cache cleared successfully.', 'success')
        return redirect(url_for('admin_settings'))
    except Exception as e:
        app_logger.error(f"Error clearing cache: {str(e)}")
        flash(f"Error clearing cache: {str(e)}", 'error')
        return redirect(url_for('admin_settings'))

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin users management page."""
    try:
        # Handle pagination and filtering
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        sort_by = request.args.get('sort', 'created_at')
        sort_direction = request.args.get('order', 'desc')
        search_query = request.args.get('q', '')
        
        # Calculate skip value for pagination
        skip = (page - 1) * limit
        
        # Apply sorting
        sort_direction_value = DESCENDING if sort_direction == 'desc' else 1
        
        # Set up filter query
        user_filter = {}
        if search_query:
            user_filter = {
                '$or': [
                    {'username': {'$regex': search_query, '$options': 'i'}},
                    {'email': {'$regex': search_query, '$options': 'i'}},
                    {'name': {'$regex': search_query, '$options': 'i'}}
                ]
            }
        
        # Get total user count for pagination
        total_users = users_collection.count_documents(user_filter)
        
        # Get paginated users
        users = list(users_collection.find(
            user_filter,
            sort=[(sort_by, sort_direction_value)],
            skip=skip,
            limit=limit
        ))
        
        # Prepare pagination info
        pagination = {
            'page': page,
            'per_page': limit,
            'total': total_users,
            'total_pages': max(1, (total_users + limit - 1) // limit),
            'has_prev': page > 1,
            'has_next': page < ((total_users + limit - 1) // limit)
        }
        
        return render_template(
            'admin_users.html',
            users=users,
            pagination=pagination,
            current_sort=sort_by,
            current_order=sort_direction,
            search_query=search_query
        )
    except Exception as e:
        app_logger.error(f"Error in admin_users: {str(e)}")
        flash(f"Error accessing users: {str(e)}", 'error')
        return redirect(url_for('admin_users'))

@app.route('/admin/add-song')
@admin_required
def admin_add_song():
    """Admin add song page."""
    return render_template('add_song.html')

@app.route('/admin/upload-song', methods=['POST'])
@admin_required
def admin_upload_song():
    """Upload a song to the system."""
    if request.method != 'POST':
        return redirect(url_for('admin_dashboard'))
    
    try:
        title = request.form.get('title')
        artist = request.form.get('artist')
        mood = request.form.get('mood')
        
        if not title or not artist or not mood:
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Check if audio file was uploaded
        if 'audioFile' not in request.files:
            flash('No audio file uploaded', 'error')
            return redirect(url_for('admin_dashboard'))
            
        audio_file = request.files['audioFile']
        
        if audio_file.filename == '':
            flash('No audio file selected', 'error')
            return redirect(url_for('admin_dashboard'))
            
        # Check audio file extension
        if not allowed_file(audio_file.filename, ['mp3', 'wav', 'ogg']):
            flash('Invalid audio file format. Allowed formats: MP3, WAV, OGG', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Process cover image if uploaded
        cover_image_path = None
        if 'coverImage' in request.files:
            cover_image = request.files['coverImage']
            if cover_image.filename != '' and allowed_file(cover_image.filename, ['jpg', 'jpeg', 'png', 'gif']):
                # Generate secure filename and save file
                image_filename = secure_filename(f"{title}-{artist}-cover-{int(time.time())}{os.path.splitext(cover_image.filename)[1]}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'covers', image_filename)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                
                # Save the file
                cover_image.save(image_path)
                cover_image_path = os.path.join('uploads', 'covers', image_filename)
        
        # Save audio file
        audio_filename = secure_filename(f"{title}-{artist}-{int(time.time())}{os.path.splitext(audio_file.filename)[1]}")
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', audio_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        # Save the file
        audio_file.save(audio_path)
        file_path = os.path.join('uploads', 'audio', audio_filename)
        
        # Create song document
        song_data = {
            "title": title,
            "artist": artist,
            "mood": mood,
            "file_path": file_path,
            "image_path": cover_image_path,
            "plays": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Save to database
        result = db.songs.insert_one(song_data)
        song_id = result.inserted_id
        
        flash(f'Song "{title}" by {artist} uploaded successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        app_logger.error(f"Error uploading song: {str(e)}")
        flash(f'Error uploading song: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/songs')
@admin_required
def admin_songs():
    """Manage songs in the admin panel."""
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/promotions')
@admin_required
def admin_promotions():
    """Admin promotions management page."""
    try:
        # You can implement promotions logic here
        # This is a placeholder implementation
        active_promotions = []
        scheduled_promotions = []
        expired_promotions = []
        
        return render_template(
            'admin_promotions.html',
            active_promotions=active_promotions,
            scheduled_promotions=scheduled_promotions,
            expired_promotions=expired_promotions
        )
    except Exception as e:
        app_logger.error(f"Error in admin_promotions: {str(e)}")
        flash(f"Error accessing promotions: {str(e)}", 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/pricing')
@admin_required
def admin_pricing():
    """Admin pricing management page."""
    try:
        # Placeholder implementation
        return render_template('admin_pricing.html')
    except Exception as e:
        app_logger.error(f"Error in admin_pricing: {str(e)}")
        flash(f"Error accessing pricing: {str(e)}", 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """Admin logs view page."""
    try:
        # Get log files
        log_dir = os.path.join(app.root_path, 'logs')
        log_files = []
        
        if os.path.exists(log_dir):
            for log_file in os.listdir(log_dir):
                if log_file.endswith('.log'):
                    file_path = os.path.join(log_dir, log_file)
                    size_kb = os.path.getsize(file_path) / 1024
                    size = f"{size_kb:.1f} KB"
                    modified = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    log_files.append({
                        'name': log_file,
                        'path': file_path,
                        'size': size,
                        'modified': modified
                    })
            
            # Sort logs by modification time (newest first)
            log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return render_template('admin_logs.html', log_files=log_files)
    except Exception as e:
        app_logger.error(f"Error in admin_logs: {str(e)}")
        flash(f"Error accessing logs: {str(e)}", 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/logs/<filename>')
@admin_required
def admin_view_log(filename):
    """View specific log file."""
    try:
        log_dir = os.path.join(app.root_path, 'logs')
        file_path = os.path.join(log_dir, filename)
        
        # Security check - make sure the file is in the logs directory
        if not os.path.exists(file_path) or not filename.endswith('.log'):
            flash('Log file not found.', 'error')
            return redirect(url_for('admin_logs'))
        
        # Get parameters for log viewing
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # Open and read the log file
        with open(file_path, 'r') as f:
            log_contents = f.readlines()
        
        # Count total lines
        total_lines = len(log_contents)
        
        # Calculate pagination
        total_pages = max(1, (total_lines + limit - 1) // limit)
        page = min(max(1, page), total_pages)  # Ensure page is in valid range
        
        # Get the appropriate slice of log lines
        start_line = max(0, total_lines - (page * limit))
        end_line = max(0, total_lines - ((page - 1) * limit))
        current_log_lines = log_contents[start_line:end_line]
        current_log_lines.reverse()  # Show newest entries first
        
        pagination = {
            'page': page, 
            'per_page': limit,
            'total_pages': total_pages,
            'has_prev': page < total_pages,
            'has_next': page > 1
        }
        
        return render_template(
            'admin_logs.html',
            log_files=[], 
            current_log_file=filename,
            log_contents=current_log_lines,
            pagination=pagination,
            total_lines=total_lines
        )
    except Exception as e:
        app_logger.error(f"Error viewing log {filename}: {str(e)}")
        flash(f"Error viewing log: {str(e)}", 'error')
        return redirect(url_for('admin_logs'))

if __name__ == '__main__':
    app.run(debug=True)

