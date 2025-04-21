import datetime
from bson.objectid import ObjectId
import logging
from models import playlists_collection, songs_collection

logger = logging.getLogger("playlist")

class Playlist:
    @staticmethod
    def create(title, user_id, description="", is_private=False):
        """
        Create a new playlist
        
        Args:
            title (str): The playlist title
            user_id (str): The ID of the user creating the playlist
            description (str): Optional description for the playlist
            is_private (bool): Whether the playlist is private
            
        Returns:
            str: The ID of the created playlist, or None on failure
        """
        try:
            playlist = {
                "name": title,
                "user_id": user_id,
                "description": description,
                "is_private": is_private,
                "songs": [],
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            }
            
            result = playlists_collection.insert_one(playlist)
            if result and result.inserted_id:
                logger.info(f"Created playlist {title} for user {user_id}")
                return str(result.inserted_id)
            else:
                logger.error(f"Failed to create playlist {title}")
                return None
        except Exception as e:
            logger.error(f"Error creating playlist: {str(e)}")
            return None
    
    @staticmethod
    def get_by_id(playlist_id):
        """
        Get a playlist by ID
        
        Args:
            playlist_id (str): The playlist ID
            
        Returns:
            dict: The playlist, or None if not found
        """
        try:
            # Convert string ID to ObjectId if it's a string
            if isinstance(playlist_id, str):
                playlist_id = ObjectId(playlist_id)
                
            playlist = playlists_collection.find_one({"_id": playlist_id})
            if playlist:
                # Convert ObjectID to string for easier JSON serialization
                playlist["_id"] = str(playlist["_id"])
                return playlist
            return None
        except Exception as e:
            logger.error(f"Error getting playlist {playlist_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_user_playlists(user_id):
        """
        Get all playlists for a user
        
        Args:
            user_id (str): The user ID
            
        Returns:
            list: A list of playlists, or empty list on failure
        """
        try:
            playlists = list(playlists_collection.find({"user_id": user_id}))
            
            # Convert ObjectIDs to strings
            for playlist in playlists:
                playlist["_id"] = str(playlist["_id"])
                
            return playlists
        except Exception as e:
            logger.error(f"Error getting playlists for user {user_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_songs(playlist_id):
        """
        Get all songs in a playlist
        
        Args:
            playlist_id (str): The playlist ID
            
        Returns:
            list: A list of songs in the playlist, or empty list on failure
        """
        try:
            # Convert string ID to ObjectId if it's a string
            if isinstance(playlist_id, str):
                playlist_id = ObjectId(playlist_id)
                
            playlist = playlists_collection.find_one({"_id": playlist_id})
            if not playlist:
                return []
                
            song_ids = playlist.get("songs", [])
            if not song_ids:
                return []
                
            # Convert string IDs to ObjectIds
            song_object_ids = [ObjectId(sid) if isinstance(sid, str) else sid for sid in song_ids]
            
            # Fetch all songs in the playlist
            songs = list(songs_collection.find({"_id": {"$in": song_object_ids}}))
            
            # Convert ObjectIDs to strings
            for song in songs:
                song["_id"] = str(song["_id"])
                
            return songs
        except Exception as e:
            logger.error(f"Error getting songs for playlist {playlist_id}: {str(e)}")
            return []
    
    @staticmethod
    def add_song(playlist_id, song_id):
        """
        Add a song to a playlist
        
        Args:
            playlist_id (str): The playlist ID
            song_id (str): The song ID to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert string IDs to ObjectIds
            if isinstance(playlist_id, str):
                playlist_id = ObjectId(playlist_id)
            if isinstance(song_id, str):
                song_id = ObjectId(song_id)
                
            # Check if song exists
            song = songs_collection.find_one({"_id": song_id})
            if not song:
                logger.error(f"Song {song_id} not found")
                return False
                
            # Add song to playlist if not already there
            result = playlists_collection.update_one(
                {"_id": playlist_id, "songs": {"$ne": song_id}},
                {
                    "$push": {"songs": song_id},
                    "$set": {"updated_at": datetime.datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            logger.error(f"Error adding song {song_id} to playlist {playlist_id}: {str(e)}")
            return False
    
    @staticmethod
    def remove_song(playlist_id, song_id):
        """
        Remove a song from a playlist
        
        Args:
            playlist_id (str): The playlist ID
            song_id (str): The song ID to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert string IDs to ObjectIds
            if isinstance(playlist_id, str):
                playlist_id = ObjectId(playlist_id)
            if isinstance(song_id, str):
                song_id = ObjectId(song_id)
                
            # Remove song from playlist
            result = playlists_collection.update_one(
                {"_id": playlist_id},
                {
                    "$pull": {"songs": song_id},
                    "$set": {"updated_at": datetime.datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing song {song_id} from playlist {playlist_id}: {str(e)}")
            return False
    
    @staticmethod
    def update(playlist_id, name=None, description=None, is_private=None):
        """
        Update a playlist's details
        
        Args:
            playlist_id (str): The playlist ID
            name (str, optional): New name for the playlist
            description (str, optional): New description for the playlist
            is_private (bool, optional): New privacy setting
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert string ID to ObjectId
            if isinstance(playlist_id, str):
                playlist_id = ObjectId(playlist_id)
                
            # Build update document
            update_doc = {"updated_at": datetime.datetime.utcnow()}
            if name:
                update_doc["name"] = name
            if description is not None:
                update_doc["description"] = description
            if is_private is not None:
                update_doc["is_private"] = is_private
                
            # Update playlist
            result = playlists_collection.update_one(
                {"_id": playlist_id},
                {"$set": update_doc}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating playlist {playlist_id}: {str(e)}")
            return False
    
    @staticmethod
    def delete(playlist_id):
        """
        Delete a playlist
        
        Args:
            playlist_id (str): The playlist ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert string ID to ObjectId
            if isinstance(playlist_id, str):
                playlist_id = ObjectId(playlist_id)
                
            # Delete playlist
            result = playlists_collection.delete_one({"_id": playlist_id})
            
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting playlist {playlist_id}: {str(e)}")
            return False 