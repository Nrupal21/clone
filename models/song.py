from pymongo import MongoClient
import os
import json
import shutil
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
    songs_collection = db['songs']
    print("Connected to database for songs collection")
except Exception as e:
    print(f"Error connecting to database from song model: {e}")
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
    
    songs_collection = MockCollection()

class Song:
    MOODS = ['Happy', 'Chill', 'Energetic', 'Romantic', 'Focus', 'Angry', 'Dark', 'Bright', 'Funky', 'Love', 'Uplifting']
    
    #################################################
    # Song Creation
    #################################################
    @staticmethod
    def add_song(title, artist, mood, file_path, image_path=None, use_background_image=False):
        """
        Add a new song to the database and update the mood directory info.json
        Returns: ID of the created song or raises an exception
        """
        # Validate inputs
        if not title or not artist or not mood or not file_path:
            raise ValueError("Missing required song fields")
            
        if mood not in Song.MOODS:
            raise ValueError(f"Invalid mood. Must be one of: {', '.join(Song.MOODS)}")
            
        # Normalize paths
        file_path = file_path.replace('\\', '/')
        if file_path.startswith('/'):
            file_path = file_path.lstrip('/')
        
        if image_path:
            image_path = image_path.replace('\\', '/')
            if image_path.startswith('/'):
                image_path = image_path.lstrip('/')
        
        # Create mood directory if it doesn't exist
        mood_dir = f"{mood}_(mood)"
        song_dir = os.path.join("static", "songs", mood_dir)
        os.makedirs(song_dir, exist_ok=True)
        
        # Create song document with additional metadata
        song = {
            "title": title,
            "artist": artist,
            "mood": mood,
            "file_path": file_path,
            "image_path": image_path,
            "use_background_image": use_background_image,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "plays": 0,
            "duration": None  # Could be populated later
        }
        
        # Update info.json in mood directory using a separate method for better separation
        try:
            Song._update_mood_info_json(mood_dir, {
                "title": title,
                "artist": artist,
                "filename": os.path.basename(file_path),
                "image": os.path.basename(image_path) if image_path else "cover.jpg"
            })
        except Exception as e:
            # If info.json update fails, log the error but continue
            print(f"Warning: Failed to update info.json for song {title}: {str(e)}")
        
        # Insert song into database
        try:
            result = songs_collection.insert_one(song)
            return str(result.inserted_id)
        except Exception as e:
            # If database insert fails, clean up the file that was uploaded
            try:
                if os.path.exists(os.path.join("static", file_path)):
                    os.remove(os.path.join("static", file_path))
                if image_path and os.path.exists(os.path.join("static", image_path)):
                    os.remove(os.path.join("static", image_path))
            except Exception:
                pass  # File cleanup is best-effort
            raise Exception(f"Failed to add song to database: {str(e)}")

    #################################################
    # Helper Methods
    #################################################
    @staticmethod
    def _update_mood_info_json(mood_dir, song_info):
        """Helper method to update the info.json file for a mood directory"""
        info_path = os.path.join("static", "songs", mood_dir, "info.json")
        
        # Create a lock file to prevent concurrent updates
        lock_path = f"{info_path}.lock"
        try:
            # Create a basic lock file
            with open(lock_path, 'w') as lock_file:
                lock_file.write(str(datetime.utcnow()))
                
            # Read existing info or create new
            try:
                with open(info_path, 'r') as f:
                    info = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                info = {"songs": []}
            
            # Add the new song and write back
            info["songs"].append(song_info)
            
            # Make a backup before writing
            if os.path.exists(info_path):
                shutil.copy2(info_path, f"{info_path}.bak")
                
            with open(info_path, 'w') as f:
                json.dump(info, f, indent=4)
                
        finally:
            # Always remove the lock file
            if os.path.exists(lock_path):
                os.remove(lock_path)

    #################################################
    # Song Retrieval
    #################################################
    @staticmethod
    def get_songs(limit=100, skip=0, mood=None, artist=None, search=None, sort_by=None, use_cache=True):
        """
        Get songs with optional filtering and pagination
        Returns: List of song objects
        
        Parameters:
        - limit: Maximum number of songs to return
        - skip: Number of songs to skip (for pagination)
        - mood: Filter by mood
        - artist: Filter by artist
        - search: Text search term
        - sort_by: Field to sort by (e.g. 'plays', 'created_at')
        - use_cache: Whether to use cached results (set to False for fresh data)
        """
        try:
            # Build query
            query = {}
            if mood:
                query['mood'] = mood
            if artist:
                query['artist'] = {"$regex": artist, "$options": "i"}
            if search:
                query['$or'] = [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"artist": {"$regex": search, "$options": "i"}},
                    {"mood": {"$regex": search, "$options": "i"}}
                ]
                
            # Determine sort order
            sort_criteria = None
            if sort_by:
                if sort_by == 'plays':
                    sort_criteria = [("plays", -1)]  # Most played first
                elif sort_by == 'created_at':
                    sort_criteria = [("created_at", -1)]  # Newest first
                
            # Get results from database
            cursor = songs_collection.find(query)
            if sort_criteria:
                cursor = cursor.sort(sort_criteria)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            songs = list(cursor)
            
            # Convert ObjectId to string
            for song in songs:
                if '_id' in song:
                    song['_id'] = str(song['_id'])
            
            return songs
        except Exception as e:
            print(f"Error getting songs: {str(e)}")
            # Return empty list instead of failing
            return []

    @staticmethod
    def search(query_text):
        """
        Search for songs matching the given text
        Returns: List of song objects
        
        Parameters:
        - query_text: Text to search for in title, artist and mood
        """
        try:
            # Use get_songs with search parameter
            return Song.get_songs(search=query_text, limit=50)
        except Exception as e:
            print(f"Error searching songs: {str(e)}")
            return []

    @staticmethod
    def _get_songs_by_mood(mood):
        """
        Helper method to get songs from a specific mood directory
        Returns: List of song objects for the mood
        """
        mood_dir = f"{mood}_(mood)"
        info_path = os.path.join("static", "songs", mood_dir, "info.json")
        
        try:
            with open(info_path, 'r') as f:
                info = json.load(f)
                songs = info.get("songs", [])
                
                # Cache song ID lookup to reduce database queries
                song_ids = {}
                db_songs = songs_collection.find({"mood": mood})
                for db_song in db_songs:
                    key = f"{db_song['title']}:{db_song['artist']}"
                    song_ids[key] = str(db_song['_id'])
                
                # Update song information
                for song in songs:
                    song['mood'] = mood
                    
                    # Use cached ID if available
                    song_key = f"{song['title']}:{song['artist']}"
                    if song_key in song_ids:
                        song['_id'] = song_ids[song_key]
                        
                    song['file_path'] = os.path.join(mood_dir, song['filename'])
                    song['image_path'] = os.path.join(mood_dir, song.get('image', 'cover.jpg'))
                
                return songs
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading mood info: {str(e)}")
            return []

    #################################################
    # Song Operations
    #################################################
    @staticmethod
    def get_song(song_id):
        """
        Get a single song by ID
        Returns: Song object or None
        """
        try:
            song = songs_collection.find_one({"_id": ObjectId(song_id)})
            if song:
                song['_id'] = str(song['_id'])
            return song
        except Exception:
            return None

    @staticmethod
    def get_by_id(song_id):
        """
        Alias for get_song method
        Get a single song by ID
        Returns: Song object or None
        """
        return Song.get_song(song_id)

    @staticmethod
    def increment_plays(song_id):
        """
        Increment play count for a song
        Returns: True if successful, False otherwise
        """
        try:
            result = songs_collection.update_one(
                {"_id": ObjectId(song_id)},
                {"$inc": {"plays": 1}}
            )
            return result.modified_count > 0
        except Exception:
            return False
            
    @staticmethod
    def delete_song(song_id):
        """
        Delete a song and its associated files
        Returns: True if successful, False otherwise
        """
        try:
            # Get song details first to have file paths for deletion
            song = Song.get_song(song_id)
            if not song:
                print(f"Song not found for deletion: {song_id}")
                return False
                
            # Delete database entry
            try:
                result = songs_collection.delete_one({"_id": ObjectId(song_id)})
                if result.deleted_count == 0:
                    print(f"No song deleted from database: {song_id}")
                    return False
            except Exception as db_error:
                print(f"Database error deleting song {song_id}: {str(db_error)}")
                return False
                
            # Delete files from filesystem
            deletion_success = True
            try:
                # Check for both relative and absolute paths
                file_paths = [
                    # Try paths relative to current directory
                    os.path.join("static", song['file_path']),
                    # Try absolute paths
                    song['file_path']
                ]
                
                file_deleted = False
                for path in file_paths:
                    if os.path.exists(path):
                        os.remove(path)
                        print(f"Deleted audio file: {path}")
                        file_deleted = True
                        break
                
                if not file_deleted:
                    print(f"Warning: Could not find audio file to delete for song {song_id}")
                    deletion_success = False
                    
                # Try to delete image if it exists
                if song.get('image_path'):
                    image_paths = [
                        os.path.join("static", song['image_path']),
                        song['image_path']
                    ]
                    
                    image_deleted = False
                    for path in image_paths:
                        if os.path.exists(path):
                            os.remove(path)
                            print(f"Deleted image file: {path}")
                            image_deleted = True
                            break
                    
                    if not image_deleted and song.get('image_path') != 'img/default-cover.jpg':
                        print(f"Warning: Could not find image file to delete for song {song_id}")
                
                # Update info.json to remove song
                try:
                    mood_dir = f"{song['mood']}_(mood)"
                    Song._remove_song_from_info_json(mood_dir, song['title'], song['artist'])
                except Exception as json_error:
                    print(f"Warning: Failed to update info.json for song {song_id}: {str(json_error)}")
                    # Continue despite JSON update failure
                    
            except Exception as file_error:
                print(f"Error deleting files for song {song_id}: {str(file_error)}")
                deletion_success = False
                
            # Return success even if file deletion failed but database entry was removed
            return True
            
        except Exception as e:
            print(f"Error in delete_song: {str(e)}")
            return False
            
    @staticmethod
    def _remove_song_from_info_json(mood_dir, title, artist):
        """Helper method to remove a song from the info.json file"""
        info_path = os.path.join("static", "songs", mood_dir, "info.json")
        if not os.path.exists(info_path):
            return
            
        try:
            with open(info_path, 'r') as f:
                info = json.load(f)
                
            # Make a backup
            shutil.copy2(info_path, f"{info_path}.bak")
            
            # Filter out the song to remove
            info["songs"] = [s for s in info["songs"] 
                           if not (s["title"] == title and s["artist"] == artist)]
            
            with open(info_path, 'w') as f:
                json.dump(info, f, indent=4)
        except Exception as e:
            print(f"Error updating info.json: {str(e)}")
            # Try to restore backup if update failed
            if os.path.exists(f"{info_path}.bak"):
                shutil.copy2(f"{info_path}.bak", info_path)

    @staticmethod
    def get_liked_songs(user_id):
        """
        Get all songs liked by a user
        Returns: List of song objects
        
        Parameters:
        - user_id: ID of the user
        """
        try:
            # Get user document
            from models.user import users_collection
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user or 'liked_songs' not in user:
                return []
            
            # Convert ObjectIds to strings
            liked_song_ids = [str(song_id) if isinstance(song_id, ObjectId) else song_id 
                            for song_id in user.get('liked_songs', [])]
            
            # Get song details for all liked songs
            liked_songs = []
            for song_id in liked_song_ids:
                song = Song.get_song(song_id)
                if song:
                    song['is_liked'] = True
                    liked_songs.append(song)
                
            return liked_songs
        except Exception as e:
            print(f"Error getting liked songs: {str(e)}")
            return []

    @staticmethod
    def get_liked_song_ids(user_id):
        """
        Get IDs of all songs liked by a user
        Returns: List of song ID strings
        
        Parameters:
        - user_id: ID of the user
        """
        try:
            # Get user document
            from models.user import users_collection
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user or 'liked_songs' not in user:
                return []
            
            # Convert ObjectIds to strings
            return [str(song_id) if isinstance(song_id, ObjectId) else song_id 
                   for song_id in user.get('liked_songs', [])]
        except Exception as e:
            print(f"Error getting liked song IDs: {str(e)}")
            return []

    @staticmethod
    def toggle_like(song_id, user_id):
        """
        Toggle the liked status of a song for a user
        Returns: True if successful, False otherwise
        
        Parameters:
        - song_id: ID of the song to toggle
        - user_id: ID of the user
        """
        try:
            # Get user document
            from models.user import users_collection
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                return False
            
            # Get current liked songs
            liked_songs = user.get('liked_songs', [])
            
            # Convert to ObjectId if not already
            song_object_id = ObjectId(song_id)
            
            # Check if song is already liked
            if any(str(liked_id) == song_id for liked_id in liked_songs):
                # Remove song from liked songs
                liked_songs = [liked_id for liked_id in liked_songs 
                             if str(liked_id) != song_id]
                action = "$set"
            else:
                # Add song to liked songs
                liked_songs.append(song_object_id)
                action = "$set"
            
            # Update user document
            result = users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {action: {"liked_songs": liked_songs}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error toggling song like: {str(e)}")
            return False

    @staticmethod
    def get_moods():
        """
        Get a list of all available moods
        Returns: List of unique moods
        """
        try:
            # Try to use aggregate for MongoDB
            try:
                mood_pipeline = [
                    {"$group": {"_id": "$mood"}},
                    {"$sort": {"_id": 1}}
                ]
                
                moods = list(songs_collection.aggregate(mood_pipeline))
                return [mood['_id'] for mood in moods if mood['_id']]
            except NotImplementedError:
                # Alternative implementation for MontyDB which doesn't support aggregate
                print("MontyDB detected. Using distinct() instead of aggregate().")
                distinct_moods = songs_collection.distinct("mood")
                return [mood for mood in distinct_moods if mood]
                
        except Exception as e:
            print(f"Error getting moods: {str(e)}")
            # Fall back to predefined moods
            return Song.MOODS

    @staticmethod
    def get_recommendations(user_id, limit=10):
        """
        Get song recommendations for a user based on their liked songs
        Returns: List of recommended songs
        
        Parameters:
        - user_id: ID of the user
        - limit: Maximum number of songs to recommend
        """
        try:
            # Get user's liked songs
            liked_songs = Song.get_liked_songs(user_id)
            
            # If user has no liked songs, return trending songs
            if not liked_songs:
                return Song.get_songs(sort_by='plays', limit=limit)
            
            # Extract moods from liked songs
            liked_moods = {}
            for song in liked_songs:
                mood = song.get('mood')
                if mood:
                    liked_moods[mood] = liked_moods.get(mood, 0) + 1
            
            # Get top 3 moods
            top_moods = sorted(liked_moods.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Get recommendations based on top moods
            recommendations = []
            liked_ids = [song['_id'] for song in liked_songs]
            
            for mood, _ in top_moods:
                # Get songs in this mood that user hasn't liked yet
                mood_songs = Song.get_songs(mood=mood, limit=10)
                for song in mood_songs:
                    if song['_id'] not in liked_ids and len(recommendations) < limit:
                        recommendations.append(song)
            
            # If we don't have enough recommendations, add some trending songs
            if len(recommendations) < limit:
                trending = Song.get_songs(sort_by='plays', limit=limit*2)
                for song in trending:
                    if song['_id'] not in liked_ids and song['_id'] not in [r['_id'] for r in recommendations]:
                        recommendations.append(song)
                        if len(recommendations) >= limit:
                            break
            
            return recommendations[:limit]
        except Exception as e:
            print(f"Error getting recommendations: {str(e)}")
            # Fall back to trending songs
            return Song.get_songs(sort_by='plays', limit=limit)