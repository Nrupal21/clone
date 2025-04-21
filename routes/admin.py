from flask import Blueprint, render_template, jsonify, session, redirect, url_for, current_app, request
from werkzeug.utils import secure_filename
from functools import wraps
import logging
import time
import os
import requests
import json
import uuid
from datetime import datetime
from models.user import User
from models.song import Song
from utils.song_fetcher import OpenSourceSongFetcher
from bson import ObjectId
from models.subscription import Subscription

admin = Blueprint('admin', __name__)

# Set up logging for admin actions
logger = logging.getLogger('admin_actions')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs/admin_activity.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

#################################################
# Authentication Decorators
#################################################
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # More comprehensive admin check
        if not session.get('user_id') or not session.get('is_admin'):
            logger.warning(f"Unauthorized admin access attempt: {request.remote_addr}")
            return redirect(url_for('login_page'))
            
        # Additional security: verify admin status from database
        try:
            user = User.get_user(session.get('user_id'))
            if not user or not user.get('is_admin'):
                logger.warning(f"User {session.get('user_id')} with invalid admin status tried to access admin area")
                session.clear()  # Clear session on suspicious activity
                return redirect(url_for('login_page'))
        except Exception as e:
            logger.error(f"Error verifying admin status: {str(e)}")
            return jsonify({"message": "Server error, please try again"}), 500
            
        # Log admin activity
        logger.info(f"Admin action: {request.endpoint} by user {session.get('user_id')} from IP {request.remote_addr}")
        return f(*args, **kwargs)
    return decorated_function

#################################################
# Admin Dashboard
#################################################
@admin.route('/dashboard')
@admin_required
def dashboard():
    try:
        # Get all users
        users = User.get_users(filter_query={"is_admin": False})
        
        # Get all songs grouped by mood
        songs_by_mood = {}
        all_songs = Song.get_songs(use_cache=False)
        
        # Sort songs by creation date
        all_songs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        for song in all_songs:
            mood = song.get('mood', 'Other')
            if mood not in songs_by_mood:
                songs_by_mood[mood] = []
            
            # Set default cover image if none exists
            if not song.get('image_path') or song.get('image_path') == 'None' or song.get('image_path') is None:
                song['image_path'] = 'img/default-cover.jpg'
                
            songs_by_mood[mood].append(song)
            
        # Get subscription stats
        subscription_counts = Subscription.get_subscription_counts()
        
        # Get system stats
        stats = {
            "user_count": len(users),
            "song_count": len(all_songs),
            "mood_count": len(songs_by_mood),
            "premium_count": subscription_counts["premium"],
            "free_count": subscription_counts["free"],
            "expired_count": subscription_counts["expired"]
        }
        
        logger.info(f"Admin dashboard loaded with {len(all_songs)} songs")

        return render_template('admin.html', 
            users=users, 
            songs_by_mood=songs_by_mood,
            stats=stats
        )
    except Exception as e:
        logger.error(f"Error in admin dashboard: {str(e)}")
        return render_template('error.html', error="An error occurred while loading the dashboard"), 500

#################################################
# User Management
#################################################
@admin.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        # Make sure admin can't delete themselves
        if user_id == session.get('user_id'):
            return jsonify({"message": "Cannot delete your own admin account"}), 403
            
        # Get user before deletion for logging
        user = User.get_user(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404
            
        # Prevent deletion of other admins
        if user.get('is_admin'):
            logger.warning(f"Admin {session.get('user_id')} attempted to delete another admin: {user_id}")
            return jsonify({"message": "Cannot delete other admin accounts"}), 403
            
        # Delete user
        result = User.users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            return jsonify({"message": "User not found or already deleted"}), 404
            
        # Log successful deletion
        logger.info(f"Admin {session.get('user_id')} deleted user: {user_id} ({user.get('email')})")
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({"message": f"Error deleting user: {str(e)}"}), 500

#################################################
# Song Management
#################################################
@admin.route('/songs/<song_id>', methods=['DELETE'])
@admin_required
def delete_song(song_id):
    try:
        # Get song before deletion for logging
        song = Song.get_song(song_id)
        if not song:
            logger.warning(f"Admin attempted to delete non-existent song: {song_id}")
            return jsonify({"message": "Song not found"}), 404
            
        # Log the song info before deleting
        song_title = song.get('title', 'Unknown')
        song_artist = song.get('artist', 'Unknown')
        song_mood = song.get('mood', 'Unknown')
        logger.info(f"Attempting to delete song: {song_id} ({song_title} by {song_artist})")
            
        # Use Song model's delete method for proper cleanup
        delete_result = Song.delete_song(song_id)
        if delete_result:
            # Log successful deletion
            logger.info(f"Admin {session.get('user_id')} successfully deleted song: {song_id} ({song_title} by {song_artist})")
            return jsonify({"message": "Song deleted successfully", "success": True}), 200
        else:
            logger.error(f"Failed to delete song {song_id} ({song_title})")
            return jsonify({"message": "Song could not be deleted", "success": False}), 500
    except Exception as e:
        logger.error(f"Error deleting song {song_id}: {str(e)}")
        return jsonify({"message": f"Error deleting song: {str(e)}"}), 500

@admin.route('/upload-song', methods=['POST'])
@admin_required
def upload_song():
    try:
        if 'audioFile' not in request.files:
            return jsonify({"message": "No audio file provided"}), 400
            
        audio_file = request.files['audioFile']
        if audio_file.filename == '':
            return jsonify({"message": "No audio file selected"}), 400
            
        # Validate form data
        title = request.form.get('title', '').strip()
        artist = request.form.get('artist', '').strip()
        mood = request.form.get('mood', '').strip()
        
        if not all([title, artist, mood]):
            return jsonify({"message": "Missing required fields"}), 400
            
        if mood not in Song.MOODS:
            return jsonify({"message": f"Invalid mood. Valid options: {', '.join(Song.MOODS)}"}), 400

        # Create unique filenames
        unique_id = str(uuid.uuid4())
        audio_filename = secure_filename(f"{unique_id}_{audio_file.filename}")
        mood_dir = f"{mood}_(mood)"
        
        # Handle cover image
        image_path = None
        if 'coverImage' in request.files and request.files['coverImage'].filename:
            cover_image = request.files['coverImage']
            image_filename = secure_filename(f"cover_{unique_id}_{cover_image.filename}")
            image_path = os.path.join('songs', mood_dir, image_filename)
            
            # Save cover image
            os.makedirs(os.path.join(current_app.static_folder, 'songs', mood_dir), exist_ok=True)
            cover_image.save(os.path.join(current_app.static_folder, image_path))

        # Save audio file
        audio_path = os.path.join('songs', mood_dir, audio_filename)
        os.makedirs(os.path.join(current_app.static_folder, 'songs', mood_dir), exist_ok=True)
        audio_file.save(os.path.join(current_app.static_folder, audio_path))
        
        # Add song to database
        song_id = Song.add_song(
            title=title,
            artist=artist,
            mood=mood,
            file_path=audio_path,
            image_path=image_path if image_path else 'img/default-cover.jpg'
        )
        
        # Log the upload
        logger.info(f"Admin {session.get('user_id')} uploaded song: {title} by {artist}")
        
        return jsonify({
            "message": "Song uploaded successfully",
            "song_id": str(song_id)
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading song: {str(e)}")
        # Clean up files if database insert fails
        try:
            if 'audio_path' in locals():
                os.remove(os.path.join(current_app.static_folder, audio_path))
            if 'image_path' in locals() and image_path:
                os.remove(os.path.join(current_app.static_folder, image_path))
        except Exception:
            pass  # File cleanup is best effort
        return jsonify({"message": f"Error uploading song: {str(e)}"}), 500

#################################################
# Open Source Song Integration
#################################################
@admin.route('/fetch-open-source-songs', methods=['POST'])
@admin_required
def fetch_open_source_songs():
    try:
        fetcher = OpenSourceSongFetcher(current_app.static_folder)
        added_songs = []
        errors = []
        
        # Get desired mood from request
        mood = request.json.get('mood', 'Chill')
        if mood not in Song.MOODS:
            return jsonify({"message": f"Invalid mood. Valid options: {', '.join(Song.MOODS)}"}), 400
            
        # Fetch songs from external API (Free Music Archive)
        try:
            # API endpoints can change, this is just an example
            api_url = "https://freemusicarchive.org/api/get/curators.json?api_key=EXAMPLE_KEY"
            
            # In reality, you would make an actual API call here
            # response = requests.get(api_url, timeout=10)
            # if response.status_code != 200:
            #     raise Exception(f"API returned status code {response.status_code}")
            # api_songs = response.json().get('songs', [])
            
            # Instead, here's a simulated API response
            api_songs = [
                {
                    "title": "Dreams",
                    "artist": "Benjamin Tissot",
                    "mood": mood,
                    "audio_url": "https://www.bensound.com/bensound-music/bensound-dreams.mp3",
                    "image_url": "https://www.bensound.com/bensound-img/dreams.jpg"
                },
                {
                    "title": "Energy",
                    "artist": "Benjamin Tissot",
                    "mood": mood,
                    "audio_url": "https://www.bensound.com/bensound-music/bensound-energy.mp3",
                    "image_url": "https://www.bensound.com/bensound-img/energy.jpg"
                },
                {
                    "title": "Happy Rock",
                    "artist": "Benjamin Tissot",
                    "mood": mood,
                    "audio_url": "https://www.bensound.com/bensound-music/bensound-happyrock.mp3",
                    "image_url": "https://www.bensound.com/bensound-img/happyrock.jpg"
                }
            ]
            
        except Exception as e:
            logger.error(f"Error fetching songs from API: {str(e)}")
            return jsonify({"message": f"Error accessing music API: {str(e)}"}), 500

        start_time = time.time()
        
        # Track progress for frontend
        total_songs = len(api_songs)
        current_song = 0
        
        # Process each song
        for song in api_songs:
            current_song += 1
            try:
                # Validate required fields
                if not all([song.get("title"), song.get("artist"), song.get("audio_url")]):
                    errors.append(f"Missing required fields for song: {song.get('title', 'Unknown')}")
                    continue
                    
                # Use the fetcher to download and add the song
                song_id = fetcher.add_public_domain_song(
                    title=song["title"],
                    artist=song["artist"],
                    mood=song["mood"],
                    audio_url=song["audio_url"],
                    image_url=song.get("image_url")
                )
                
                added_songs.append({
                    "title": song["title"],
                    "artist": song["artist"],
                    "id": song_id,
                    "mood": song["mood"]
                })
                
                # Log successful addition
                logger.info(f"Admin {session.get('user_id')} added public domain song: {song['title']} by {song['artist']}")
                
            except Exception as e:
                error_msg = f"Error adding song {song.get('title', 'Unknown')}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
                
        # Calculate processing time
        elapsed_time = time.time() - start_time

        return jsonify({
            "message": f"Added {len(added_songs)} out of {total_songs} open source songs in {elapsed_time:.2f}s",
            "songs": added_songs,
            "errors": errors if errors else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error in open source song fetch: {str(e)}")
        return jsonify({"message": f"Error fetching songs: {str(e)}"}), 500