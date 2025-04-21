import os
import requests
import json
import random
from models.song import Song
from urllib.parse import urlparse

class OpenSourceSongFetcher:
    # Sample open source music sources
    JAMENDO_API = "https://api.jamendo.com/v3.0"
    FREE_MUSIC_ARCHIVE_API = "https://freemusicarchive.org/api"
    
    def __init__(self, static_folder):
        self.static_folder = static_folder
        self.base_songs_path = os.path.join(static_folder, 'songs')

    def download_file(self, url, destination):
        """Download a file from URL to destination"""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return destination

    def add_public_domain_song(self, title, artist, mood, audio_url, image_url=None):
        """Add a public domain song to the collection"""
        # Create mood directory if doesn't exist
        mood_dir = f"{mood}_(mood)"
        song_dir = os.path.join(self.base_songs_path, mood_dir)
        os.makedirs(song_dir, exist_ok=True)

        # Download audio file
        audio_filename = os.path.basename(urlparse(audio_url).path)
        if not audio_filename.endswith(('.mp3', '.wav')):
            audio_filename += '.mp3'
        audio_path = os.path.join(song_dir, audio_filename)
        self.download_file(audio_url, audio_path)

        # Download image if provided
        image_filename = None
        if image_url:
            image_filename = os.path.basename(urlparse(image_url).path)
            if not image_filename.endswith(('.jpg', '.jpeg', '.png')):
                image_filename += '.jpg'
            image_path = os.path.join(song_dir, image_filename)
            self.download_file(image_url, image_path)

        # Add to database using existing Song model
        return Song.add_song(
            title=title,
            artist=artist,
            mood=mood,
            file_path=os.path.join(mood_dir, audio_filename),
            image_path=os.path.join(mood_dir, image_filename) if image_filename else None
        )