import datetime
from bson.objectid import ObjectId
from models import logs_collection
import logging

logger = logging.getLogger("activity")

class ActivityLog:
    # Action types
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_SIGNUP = "signup"
    ACTION_SONG_PLAY = "song_play"
    ACTION_SONG_LIKE = "song_like"
    ACTION_SONG_UNLIKE = "song_unlike"
    ACTION_PLAYLIST_CREATE = "playlist_create"
    ACTION_PLAYLIST_UPDATE = "playlist_update"
    ACTION_PLAYLIST_DELETE = "playlist_delete"
    ACTION_PLAYLIST_ADD_SONG = "playlist_add_song"
    ACTION_PLAYLIST_REMOVE_SONG = "playlist_remove_song"
    ACTION_PROFILE_UPDATE = "profile_update"
    ACTION_SEARCH = "search"
    
    # Resource types
    RESOURCE_USER = "user"
    RESOURCE_SONG = "song"
    RESOURCE_PLAYLIST = "playlist"
    RESOURCE_SYSTEM = "system"
    
    @staticmethod
    def log_activity(user_id, action_type, resource_type, resource_id=None, details=None):
        """
        Log a user activity
        
        Args:
            user_id (str): ID of the user performing the action
            action_type (str): Type of action (e.g., login, logout, play_song)
            resource_type (str): Type of resource (e.g., user, song, playlist)
            resource_id (str, optional): ID of the resource
            details (dict, optional): Additional details about the action
            
        Returns:
            str: ID of the created log entry
        """
        try:
            # Create log entry
            log_entry = {
                "user_id": user_id,
                "action_type": action_type,
                "resource_type": resource_type,
                "timestamp": datetime.datetime.utcnow(),
                "ip_address": None  # Will be set in the route
            }
            
            # Add optional fields if provided
            if resource_id:
                log_entry["resource_id"] = resource_id
                
            if details:
                log_entry["details"] = details
                
            # Insert log entry
            result = logs_collection.insert_one(log_entry)
            
            if result and result.inserted_id:
                logger.info(f"Activity logged: {action_type} on {resource_type}")
                return str(result.inserted_id)
            else:
                logger.error(f"Failed to log activity: {action_type} on {resource_type}")
                return None
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
            return None
    
    @staticmethod
    def get_user_activity(user_id, limit=20, skip=0, action_types=None):
        """
        Get activity logs for a specific user
        
        Args:
            user_id (str): User ID
            limit (int): Maximum number of logs to return
            skip (int): Number of logs to skip (for pagination)
            action_types (list): Filter logs by action type
            
        Returns:
            list: List of activity logs
        """
        try:
            query = {"user_id": user_id}
            
            # Filter by action types if provided
            if action_types:
                query["action_type"] = {"$in": action_types}
                
            # Get logs
            logs = logs_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
            
            # Convert to list and format
            logs_list = []
            for log in logs:
                log["_id"] = str(log["_id"])
                logs_list.append(log)
                
            return logs_list
        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}")
            return []
    
    @staticmethod
    def get_resource_activity(resource_type, resource_id, limit=20, skip=0):
        """
        Get activity logs for a specific resource
        
        Args:
            resource_type (str): Type of resource
            resource_id (str): Resource ID
            limit (int): Maximum number of logs to return
            skip (int): Number of logs to skip (for pagination)
            
        Returns:
            list: List of activity logs
        """
        try:
            query = {
                "resource_type": resource_type,
                "resource_id": resource_id
            }
            
            # Get logs
            logs = logs_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
            
            # Convert to list and format
            logs_list = []
            for log in logs:
                log["_id"] = str(log["_id"])
                logs_list.append(log)
                
            return logs_list
        except Exception as e:
            logger.error(f"Error getting resource activity: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_activity(limit=20, skip=0, action_types=None):
        """
        Get recent activity logs
        
        Args:
            limit (int): Maximum number of logs to return
            skip (int): Number of logs to skip (for pagination)
            action_types (list): Filter logs by action type
            
        Returns:
            list: List of activity logs
        """
        try:
            query = {}
            
            # Filter by action types if provided
            if action_types:
                query["action_type"] = {"$in": action_types}
                
            # Get logs
            logs = logs_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
            
            # Convert to list and format
            logs_list = []
            for log in logs:
                log["_id"] = str(log["_id"])
                logs_list.append(log)
                
            return logs_list
        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}")
            return [] 