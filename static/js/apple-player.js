/**
 * Apple Music-inspired Music Player
 * Handles audio playback, controls, and UI updates for the music player
 */

document.addEventListener('DOMContentLoaded', function() {
    // Player Elements
    const audioPlayer = document.getElementById('audioPlayer');
    const playerBar = document.getElementById('playerBar');
    const playPauseButton = document.getElementById('playPauseButton');
    const playPauseIcon = document.getElementById('playPauseIcon');
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    const progressHandle = document.getElementById('progressHandle');
    const currentTimeElement = document.getElementById('currentTime');
    const songDurationElement = document.getElementById('songDuration');
    const volumeBar = document.getElementById('volumeBar');
    const volumeLevel = document.getElementById('volumeLevel');
    const volumeHandle = document.getElementById('volumeHandle');
    const volumeIcon = document.getElementById('volumeIcon');
    const currentSongTitle = document.getElementById('currentSongTitle');
    const currentSongArtist = document.getElementById('currentSongArtist');
    const currentSongCover = document.getElementById('currentSongCover');
    const likeButton = document.getElementById('likeButton');
    const shuffleButton = document.getElementById('shuffleButton');
    const repeatButton = document.getElementById('repeatButton');
    
    // State Management
    let currentSongId = null;
    let isPlaying = false;
    let volume = 0.7;
    let currentPlaylist = [];
    let currentPlaylistIndex = 0;
    let shuffle = false;
    let repeat = 'none'; // 'none', 'all', 'one'
    
    // Initialize player
    initPlayer();
    
    /**
     * Initialize player state, event listeners and check for cached song
     */
    function initPlayer() {
        // Set initial volume
        if (audioPlayer) {
            audioPlayer.volume = volume;
            updateVolumeUI();
        }
        
        // Restore previous state if any
        const storedSongId = localStorage.getItem('currentSongId');
        const storedTime = localStorage.getItem('songTime');
        
        if (storedSongId) {
            currentSongId = storedSongId;
            updateSongInfoUI(storedSongId);
            
            if (storedTime && audioPlayer) {
                audioPlayer.currentTime = parseFloat(storedTime);
            }
        }
        
        // Add event listeners
        attachEventListeners();
        
        // Find all song play buttons on the page and attach listeners
        document.querySelectorAll('.play-song-btn, .song-row').forEach(el => {
            el.addEventListener('click', function(e) {
                if (e.target.closest('.song-action')) {
                    return; // Don't trigger play if clicking an action button
                }
                
                const songId = this.getAttribute('data-song-id');
                if (songId) {
                    playSong(songId);
                }
            });
        });
    }
    
    /**
     * Attach event listeners to player controls
     */
    function attachEventListeners() {
        if (playPauseButton) {
            playPauseButton.addEventListener('click', togglePlayPause);
        }
        
        if (prevButton) {
            prevButton.addEventListener('click', playPrevious);
        }
        
        if (nextButton) {
            nextButton.addEventListener('click', playNext);
        }
        
        if (audioPlayer) {
            audioPlayer.addEventListener('timeupdate', updateProgress);
            audioPlayer.addEventListener('loadedmetadata', updateDuration);
            audioPlayer.addEventListener('ended', handleSongEnd);
            audioPlayer.addEventListener('error', handleAudioError);
        }
        
        if (progressBar) {
            progressBar.addEventListener('click', seek);
        }
        
        if (volumeBar) {
            volumeBar.addEventListener('click', changeVolume);
        }
        
        if (volumeIcon) {
            volumeIcon.addEventListener('click', toggleMute);
        }
        
        if (likeButton) {
            likeButton.addEventListener('click', toggleLikeSong);
        }
        
        if (shuffleButton) {
            shuffleButton.addEventListener('click', toggleShuffle);
        }
        
        if (repeatButton) {
            repeatButton.addEventListener('click', toggleRepeat);
        }
    }
    
    /**
     * Play a song by ID
     * @param {string} songId - The ID of the song to play
     */
    function playSong(songId) {
        if (!songId) return;
        
        if (currentSongId === songId && isPlaying) {
            // Already playing this song
            return;
        }
        
        if (currentSongId !== songId) {
            // New song
            currentSongId = songId;
            
            // Show loading state
            updateLoadingState(true);
            
            // Clear audio source
            if (audioPlayer) {
                audioPlayer.src = '';
                
                // Fetch and play the audio file
                fetch(`/play/${songId}`)
                    .then(response => {
                        if (!response.ok) {
                            if (response.status === 404) {
                                throw new Error('Audio file not found');
                            } else {
                                throw new Error(`Server error: ${response.status}`);
                            }
                        }
                        return response.blob();
                    })
                    .then(blob => {
                        const url = URL.createObjectURL(blob);
                        audioPlayer.src = url;
                        audioPlayer.load();
                        
                        // Update UI with song info
                        updateSongInfoUI(songId);
                        
                        // Save current song ID to local storage
                        localStorage.setItem('currentSongId', songId);
                        
                        // Start playing
                        audioPlayer.play()
                            .then(() => {
                                isPlaying = true;
                                updatePlayPauseUI();
                                updateLoadingState(false);
                            })
                            .catch(error => {
                                console.error('Play error:', error);
                                updateLoadingState(false);
                                showAlert('Error playing audio: ' + error.message);
                            });
                    })
                    .catch(error => {
                        console.error('Fetch error:', error);
                        updateLoadingState(false);
                        showAlert('Error loading audio: ' + error.message);
                    });
            }
        } else {
            // Same song, just resume
            togglePlayPause();
        }
        
        // Update active song in playlist
        updatePlaylistUI(songId);
    }
    
    /**
     * Toggle play/pause
     */
    function togglePlayPause() {
        if (!audioPlayer || !currentSongId) {
            showAlert('No song selected');
            return;
        }
        
        if (isPlaying) {
            audioPlayer.pause();
            isPlaying = false;
        } else {
            audioPlayer.play()
                .then(() => {
                    isPlaying = true;
                })
                .catch(error => {
                    console.error('Error playing audio:', error);
                    showAlert('Error playing audio: ' + error.message);
                });
        }
        
        updatePlayPauseUI();
    }
    
    /**
     * Update the play/pause button icon
     */
    function updatePlayPauseUI() {
        if (playPauseIcon) {
            playPauseIcon.textContent = isPlaying ? 'pause' : 'play_arrow';
        }
    }
    
    /**
     * Update song information in the player UI
     * @param {string} songId - The ID of the song
     */
    function updateSongInfoUI(songId) {
        // Try to find song info from the page elements
        const songElement = document.querySelector(`[data-song-id="${songId}"]`);
        
        if (songElement) {
            // Get data from the element
            const title = songElement.getAttribute('data-title') || 'Unknown Title';
            const artist = songElement.getAttribute('data-artist') || 'Unknown Artist';
            const cover = songElement.getAttribute('data-cover') || '/static/img/default-cover.jpg';
            const isLiked = songElement.getAttribute('data-liked') === 'true';
            
            // Update player UI
            if (currentSongTitle) currentSongTitle.textContent = title;
            if (currentSongArtist) currentSongArtist.textContent = artist;
            if (currentSongCover) currentSongCover.src = cover;
            updateLikeButtonUI(isLiked);
            
            // Show player bar
            if (playerBar) playerBar.classList.add('active');
        } else {
            // If element not found, try fetching from API
            fetch(`/api/song/${songId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' && data.song) {
                        const song = data.song;
                        if (currentSongTitle) currentSongTitle.textContent = song.title || 'Unknown Title';
                        if (currentSongArtist) currentSongArtist.textContent = song.artist || 'Unknown Artist';
                        
                        if (currentSongCover) {
                            const coverPath = song.image_path || '/static/img/default-cover.jpg';
                            currentSongCover.src = coverPath.startsWith('/') ? coverPath : `/static/${coverPath}`;
                        }
                        
                        updateLikeButtonUI(song.is_liked || false);
                        
                        if (playerBar) playerBar.classList.add('active');
                    } else {
                        throw new Error('Song data not available');
                    }
                })
                .catch(error => {
                    console.error('Error fetching song info:', error);
                    // Use defaults
                    if (currentSongTitle) currentSongTitle.textContent = 'Unknown Title';
                    if (currentSongArtist) currentSongArtist.textContent = 'Unknown Artist';
                    if (currentSongCover) currentSongCover.src = '/static/img/default-cover.jpg';
                });
        }
    }
    
    /**
     * Update loading state with visual feedback
     */
    function updateLoadingState(isLoading) {
        if (playPauseButton) {
            if (isLoading) {
                playPauseButton.classList.add('loading');
            } else {
                playPauseButton.classList.remove('loading');
            }
        }
    }
    
    /**
     * Update progress bar during playback
     */
    function updateProgress() {
        if (!audioPlayer) return;
        
        const currentTime = audioPlayer.currentTime;
        const duration = audioPlayer.duration || 0;
        
        // Update progress bar
        if (progressFill && progressHandle) {
            const progressPercent = (currentTime / duration) * 100;
            progressFill.style.width = `${progressPercent}%`;
            progressHandle.style.left = `${progressPercent}%`;
        }
        
        // Update time display
        if (currentTimeElement) {
            currentTimeElement.textContent = formatTime(currentTime);
        }
        
        // Store current time for resuming later
        localStorage.setItem('songTime', currentTime.toString());
    }
    
    /**
     * Update duration on song load
     */
    function updateDuration() {
        if (!audioPlayer || !songDurationElement) return;
        
        const duration = audioPlayer.duration || 0;
        songDurationElement.textContent = formatTime(duration);
    }
    
    /**
     * Format seconds to mm:ss format
     * @param {number} seconds - Seconds to format
     * @returns {string} Formatted time string
     */
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }
    
    /**
     * Seek to position in audio
     * @param {Event} e - Click event on progress bar
     */
    function seek(e) {
        if (!audioPlayer || !progressBar || !audioPlayer.duration) return;
        
        const rect = progressBar.getBoundingClientRect();
        const pos = (e.clientX - rect.left) / rect.width;
        audioPlayer.currentTime = pos * audioPlayer.duration;
    }
    
    /**
     * Change volume level
     * @param {Event} e - Click event on volume bar
     */
    function changeVolume(e) {
        if (!audioPlayer || !volumeBar) return;
        
        const rect = volumeBar.getBoundingClientRect();
        const pos = (e.clientX - rect.left) / rect.width;
        volume = Math.max(0, Math.min(1, pos));
        audioPlayer.volume = volume;
        updateVolumeUI();
    }
    
    /**
     * Update volume UI elements
     */
    function updateVolumeUI() {
        if (volumeLevel) volumeLevel.style.width = `${volume * 100}%`;
        if (volumeHandle) volumeHandle.style.left = `${volume * 100}%`;
        
        // Update volume icon
        if (volumeIcon) {
            if (volume === 0) {
                volumeIcon.textContent = 'volume_off';
            } else if (volume < 0.5) {
                volumeIcon.textContent = 'volume_down';
            } else {
                volumeIcon.textContent = 'volume_up';
            }
        }
    }
    
    /**
     * Toggle mute/unmute
     */
    function toggleMute() {
        if (!audioPlayer) return;
        
        if (audioPlayer.volume > 0) {
            // Store current volume before muting
            volume = audioPlayer.volume;
            audioPlayer.volume = 0;
        } else {
            // Unmute to previous volume or default
            audioPlayer.volume = volume > 0 ? volume : 0.7;
        }
        
        updateVolumeUI();
    }
    
    /**
     * Play previous song in playlist
     */
    function playPrevious() {
        if (currentPlaylist.length <= 1) return;
        
        // Check if we're at the beginning of the song (< 3 seconds)
        if (audioPlayer && audioPlayer.currentTime > 3) {
            // If more than 3 seconds in, restart current song
            audioPlayer.currentTime = 0;
            return;
        }
        
        if (shuffle) {
            // Play random song if shuffle is on
            const randomIndex = Math.floor(Math.random() * currentPlaylist.length);
            const songId = currentPlaylist[randomIndex];
            playSong(songId);
        } else {
            // Play previous song in playlist
            currentPlaylistIndex = (currentPlaylistIndex - 1 + currentPlaylist.length) % currentPlaylist.length;
            const songId = currentPlaylist[currentPlaylistIndex];
            playSong(songId);
        }
    }
    
    /**
     * Play next song in playlist
     */
    function playNext() {
        if (currentPlaylist.length <= 1) return;
        
        if (shuffle) {
            // Play random song if shuffle is on
            const randomIndex = Math.floor(Math.random() * currentPlaylist.length);
            const songId = currentPlaylist[randomIndex];
            playSong(songId);
        } else {
            // Play next song in playlist
            currentPlaylistIndex = (currentPlaylistIndex + 1) % currentPlaylist.length;
            const songId = currentPlaylist[currentPlaylistIndex];
            playSong(songId);
        }
    }
    
    /**
     * Handle song end behavior
     */
    function handleSongEnd() {
        if (repeat === 'one') {
            // Repeat current song
            if (audioPlayer) {
                audioPlayer.currentTime = 0;
                audioPlayer.play()
                    .catch(error => console.error('Error repeating song:', error));
            }
        } else if (repeat === 'all' || currentPlaylist.length > 0) {
            // Play next song
            playNext();
        } else {
            // Stop playing
            isPlaying = false;
            updatePlayPauseUI();
        }
    }
    
    /**
     * Handle audio element errors
     * @param {Event} e - Error event
     */
    function handleAudioError(e) {
        console.error('Audio error:', e);
        
        // Show user-friendly error message
        let errorMessage = 'Error playing audio';
        if (e.target && e.target.error) {
            switch (e.target.error.code) {
                case e.target.error.MEDIA_ERR_ABORTED:
                    errorMessage = 'Playback aborted';
                    break;
                case e.target.error.MEDIA_ERR_NETWORK:
                    errorMessage = 'Network error during playback';
                    break;
                case e.target.error.MEDIA_ERR_DECODE:
                    errorMessage = 'Audio decoding error';
                    break;
                case e.target.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                    errorMessage = 'Audio format not supported';
                    break;
            }
        }
        
        showAlert(errorMessage);
        
        // Reset playing state
        isPlaying = false;
        updatePlayPauseUI();
    }
    
    /**
     * Toggle like status for current song
     */
    function toggleLikeSong() {
        if (!currentSongId) return;
        
        // Check if user is logged in
        const isLoggedIn = document.body.classList.contains('user-logged-in') || 
                         !!document.querySelector('.user-profile-mini');
        
        if (!isLoggedIn) {
            showAlert('Please log in to like songs');
            return;
        }
        
        // Toggle like via API
        fetch(`/like-song/${currentSongId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Toggle like status in UI
                const isNowLiked = likeButton.classList.contains('active') ? false : true;
                updateLikeButtonUI(isNowLiked);
                
                // Update song element in the list if present
                const songElement = document.querySelector(`[data-song-id="${currentSongId}"]`);
                if (songElement) {
                    songElement.setAttribute('data-liked', isNowLiked ? 'true' : 'false');
                    
                    // Update any like icons in the list
                    const listLikeIcon = songElement.querySelector('.song-like-icon');
                    if (listLikeIcon) {
                        listLikeIcon.textContent = isNowLiked ? 'favorite' : 'favorite_border';
                    }
                }
            } else {
                throw new Error(data.message || 'Failed to update like status');
            }
        })
        .catch(error => {
            console.error('Error toggling like:', error);
            showAlert('Error: ' + error.message);
        });
    }
    
    /**
     * Update like button UI state
     * @param {boolean} isLiked - Whether song is liked
     */
    function updateLikeButtonUI(isLiked) {
        if (!likeButton) return;
        
        if (isLiked) {
            likeButton.innerHTML = '<i class="material-icons-round">favorite</i>';
            likeButton.classList.add('active');
        } else {
            likeButton.innerHTML = '<i class="material-icons-round">favorite_border</i>';
            likeButton.classList.remove('active');
        }
    }
    
    /**
     * Toggle shuffle mode
     */
    function toggleShuffle() {
        if (!shuffleButton) return;
        
        shuffle = !shuffle;
        
        if (shuffle) {
            shuffleButton.classList.add('active');
        } else {
            shuffleButton.classList.remove('active');
        }
    }
    
    /**
     * Toggle repeat mode (none -> all -> one)
     */
    function toggleRepeat() {
        if (!repeatButton) return;
        
        // Cycle through repeat modes
        switch (repeat) {
            case 'none':
                repeat = 'all';
                repeatButton.classList.add('active');
                repeatButton.innerHTML = '<i class="material-icons-round">repeat</i>';
                break;
            case 'all':
                repeat = 'one';
                repeatButton.classList.add('active');
                repeatButton.innerHTML = '<i class="material-icons-round">repeat_one</i>';
                break;
            case 'one':
                repeat = 'none';
                repeatButton.classList.remove('active');
                repeatButton.innerHTML = '<i class="material-icons-round">repeat</i>';
                break;
        }
    }
    
    /**
     * Update playlist UI to highlight current song
     * @param {string} songId - Currently playing song ID
     */
    function updatePlaylistUI(songId) {
        // Remove active class from all songs
        document.querySelectorAll('.song-row').forEach(row => {
            row.classList.remove('active');
        });
        
        // Add active class to current song
        const activeSong = document.querySelector(`.song-row[data-song-id="${songId}"]`);
        if (activeSong) {
            activeSong.classList.add('active');
            
            // Update playlist if needed
            if (currentPlaylist.length === 0) {
                // Build playlist from visible songs
                const songRows = document.querySelectorAll('.song-row[data-song-id]');
                currentPlaylist = Array.from(songRows).map(row => row.getAttribute('data-song-id'));
                currentPlaylistIndex = currentPlaylist.indexOf(songId);
            }
        }
    }
    
    /**
     * Show an alert toast message
     * @param {string} message - Message to show
     * @param {string} type - Toast type (error, success, info)
     */
    function showAlert(message, type = 'error') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="material-icons-round">${type === 'error' ? 'error' : type === 'success' ? 'check_circle' : 'info'}</i>
            </div>
            <div class="toast-content">${message}</div>
            <button class="toast-close">
                <i class="material-icons-round">close</i>
            </button>
        `;
        
        // Add to container
        toastContainer.appendChild(toast);
        
        // Add close handler
        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                toast.classList.add('toast-hide');
                setTimeout(() => toast.remove(), 300);
            });
        }
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.classList.add('toast-hide');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
}); 