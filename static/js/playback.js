/**
 * Playback Controls - Handles the playback bar UI and functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    /**************************************************************************
     * DOM ELEMENTS AND STATE VARIABLES
     **************************************************************************/
    // Get DOM elements
    const audioPlayer = document.getElementById('audioPlayer');
    const playButton = document.querySelector('.play-button');
    const backButton = document.querySelector('.back-button');
    const rewindButton = document.querySelector('.rewind-button');
    const forwardButton = document.querySelector('.forward-button');
    const skipButton = document.querySelector('.skip-button');
    const progressSlider = document.querySelector('.progress-slider');
    const progressHandle = document.querySelector('.progress-handle');
    const currentTimeDisplay = document.querySelector('.current-time');
    const totalTimeDisplay = document.querySelector('.total-time');
    const playIcon = playButton?.querySelector('.play-icon');
    const pauseIcon = playButton?.querySelector('.pause-icon');
    const playPauseButton = document.getElementById('playPauseButton');
    const playPauseIcon = document.getElementById('playPauseIcon');
    const volumeButton = document.querySelector('.volume-button');
    const volumeSlider = document.querySelector('.volume-slider');
    const volumeHandle = document.querySelector('.volume-handle');
    const trackImage = document.querySelector('.track-info .track-image');
    
    // Topbar player elements
    const topPlayPauseButton = document.getElementById('topPlayPauseButton');
    const topPlayPauseIcon = document.getElementById('topPlayPauseIcon');
    const topPrevButton = document.getElementById('topPrevButton');
    const topNextButton = document.getElementById('topNextButton');
    const topShuffleButton = document.getElementById('topShuffleButton');
    const topRepeatButton = document.getElementById('topRepeatButton');
    const topCurrentSongTitle = document.getElementById('topCurrentSongTitle');
    const topCurrentSongArtist = document.getElementById('topCurrentSongArtist');
    
    // Play states
    let isPlaying = false;
    let currentSongId = null;
    let currentSongData = null;
    let playlist = []; // Keeps track of playlist for next/previous functionality
    let currentPlaylistIndex = -1;
    let isMuted = false;
    let previousVolume = 0.7; // Store previous volume for mute toggle
    let isShuffled = false;
    let repeatMode = 'none'; // none, one, all
    let originalPlaylist = []; // Keep track of original order for shuffle
    
    /**************************************************************************
     * AUDIO PLAYER INITIALIZATION
     **************************************************************************/
    // Initialize audio player
    if (audioPlayer) {
        // Set initial volume
        audioPlayer.volume = 0.7;
        updateVolumeUI(audioPlayer.volume);
        
        // Hide default controls (we're using our custom controls)
        audioPlayer.controls = false;
        
        // Event listeners for audio player
        audioPlayer.addEventListener('timeupdate', updateProgress);
        audioPlayer.addEventListener('loadedmetadata', function() {
            totalTimeDisplay.textContent = formatTime(audioPlayer.duration);
        });
        audioPlayer.addEventListener('ended', handleSongEnd);
        audioPlayer.addEventListener('play', function() {
            isPlaying = true;
            updatePlayButtonUI();
        });
        audioPlayer.addEventListener('pause', function() {
            isPlaying = false;
            updatePlayButtonUI();
        });
        audioPlayer.addEventListener('volumechange', function() {
            // Update volume UI when volume changes
            updateVolumeUI(audioPlayer.volume);
        });
        audioPlayer.addEventListener('error', function(e) {
            console.error('Audio player error:', e);
            // Show error notification
            showNotification('Error playing the song. Please try again.');
        });
    }
    
    /**************************************************************************
     * PROGRESS BAR INTERACTIONS
     **************************************************************************/
    // Initialize progress bar interactions
    if (progressSlider) {
        // Click to seek
        progressSlider.addEventListener('click', function(e) {
            if (!audioPlayer.src) return;
            
            const rect = progressSlider.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            audioPlayer.currentTime = pos * audioPlayer.duration;
        });
        
        // Drag to seek
        let isDragging = false;
        
        progressSlider.addEventListener('mousedown', function(e) {
            isDragging = true;
            seekToPosition(e);
        });
        
        document.addEventListener('mousemove', function(e) {
            if (isDragging) seekToPosition(e);
        });
        
        document.addEventListener('mouseup', function() {
            isDragging = false;
        });
        
        function seekToPosition(e) {
            if (!audioPlayer.src || !audioPlayer.duration) return;
            
            const rect = progressSlider.getBoundingClientRect();
            let pos = (e.clientX - rect.left) / rect.width;
            
            // Clamp position between 0 and 1
            pos = Math.max(0, Math.min(1, pos));
            
            // Update the position visually
            progressSlider.style.setProperty('--progress', `${pos * 100}%`);
            if (progressHandle) {
                progressHandle.style.left = `${pos * 100}%`;
            }
            
            // Update time display
            currentTimeDisplay.textContent = formatTime(pos * audioPlayer.duration);
            
            // Only set actual time on mouseup to prevent constant seeking
            if (!isDragging) {
                audioPlayer.currentTime = pos * audioPlayer.duration;
            }
        }
    }
    
    /**************************************************************************
     * PLAYBACK CONTROL BUTTONS
     **************************************************************************/
    // Play/Pause button functionality
    if (playButton) {
        playButton.addEventListener('click', function() {
            togglePlayPause();
        });
    }
    
    // Key press controls
    document.addEventListener('keydown', function(e) {
        // Space to play/pause
        if (e.code === 'Space' && !isInputFocused()) {
            e.preventDefault(); // Prevent page scrolling
            togglePlayPause();
        }
        // Left arrow to rewind
        else if (e.code === 'ArrowLeft' && !isInputFocused()) {
            audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 10);
        }
        // Right arrow to fast forward
        else if (e.code === 'ArrowRight' && !isInputFocused()) {
            audioPlayer.currentTime = Math.min(audioPlayer.duration, audioPlayer.currentTime + 10);
        }
        // Up arrow to increase volume
        else if (e.code === 'ArrowUp' && !isInputFocused()) {
            const newVolume = Math.min(1, audioPlayer.volume + 0.1);
            setVolume(newVolume);
        }
        // Down arrow to decrease volume
        else if (e.code === 'ArrowDown' && !isInputFocused()) {
            const newVolume = Math.max(0, audioPlayer.volume - 0.1);
            setVolume(newVolume);
        }
        // M key to mute/unmute
        else if (e.code === 'KeyM' && !isInputFocused()) {
            toggleMute();
        }
    });
    
    // Volume button functionality (mute/unmute)
    if (volumeButton) {
        volumeButton.addEventListener('click', function() {
            toggleMute();
        });
    }
    
    // Volume slider functionality
    if (volumeSlider) {
        // Set initial volume UI
        updateVolumeUI(audioPlayer.volume);
        
        // Click to change volume
        volumeSlider.addEventListener('click', function(e) {
            const rect = volumeSlider.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            setVolume(pos);
        });
        
        // Drag to change volume
        let isDraggingVolume = false;
        
        volumeSlider.addEventListener('mousedown', function(e) {
            isDraggingVolume = true;
            adjustVolume(e);
        });
        
        document.addEventListener('mousemove', function(e) {
            if (isDraggingVolume) adjustVolume(e);
        });
        
        document.addEventListener('mouseup', function() {
            isDraggingVolume = false;
        });
        
        function adjustVolume(e) {
            const rect = volumeSlider.getBoundingClientRect();
            let pos = (e.clientX - rect.left) / rect.width;
            pos = Math.max(0, Math.min(1, pos));
            setVolume(pos);
        }
    }
    
    // Check if an input element is focused
    function isInputFocused() {
        const activeElement = document.activeElement;
        return activeElement.tagName === 'INPUT' || 
               activeElement.tagName === 'TEXTAREA' || 
               activeElement.isContentEditable;
    }
    
    // Rewind button functionality (10 seconds back)
    if (rewindButton) {
        rewindButton.addEventListener('click', function() {
            if (audioPlayer.src) {
                audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 10);
            }
        });
    }
    
    // Forward button functionality (10 seconds forward)
    if (forwardButton) {
        forwardButton.addEventListener('click', function() {
            if (audioPlayer.src) {
                audioPlayer.currentTime = Math.min(audioPlayer.duration, audioPlayer.currentTime + 10);
            }
        });
    }
    
    // Back button functionality (previous song)
    if (backButton) {
        backButton.addEventListener('click', function() {
            playPreviousSong();
        });
    }
    
    // Skip button functionality (next song)
    if (skipButton) {
        skipButton.addEventListener('click', function() {
            playNextSong();
        });
    }
    
    /**************************************************************************
     * UI UPDATE FUNCTIONS
     **************************************************************************/
    // Update the progress bar
    function updateProgress() {
        if (progressSlider && audioPlayer.duration && !isDragging) {
            const progress = (audioPlayer.currentTime / audioPlayer.duration);
            progressSlider.style.setProperty('--progress', `${progress * 100}%`);
            if (progressHandle) {
                progressHandle.style.left = `${progress * 100}%`;
            }
            currentTimeDisplay.textContent = formatTime(audioPlayer.currentTime);
        }
    }
    
    // Format time as MM:SS
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds === Infinity) return '0:00';
        
        seconds = Math.floor(seconds);
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    /**************************************************************************
     * PLAYBACK CONTROL FUNCTIONS
     **************************************************************************/
    // Toggle play/pause
    function togglePlayPause() {
        if (!audioPlayer.src) {
            // If no song loaded, try to play first song in list
            const firstSongButton = document.querySelector('.play-button[data-song-url]');
            if (firstSongButton) {
                const songId = firstSongButton.dataset.songId;
                const songUrl = firstSongButton.dataset.songUrl;
                
                if (songUrl) {
                    playSong(songId);
                    return;
                }
            }
            
            // If no songs found, show message
            showNotification('No songs available to play');
            return;
        }
        
        if (isPlaying) {
            audioPlayer.pause();
        } else {
            const playPromise = audioPlayer.play();
            
            // Handle promise rejection
            if (playPromise !== undefined) {
                playPromise.catch(error => {
                    console.error('Playback failed:', error);
                    showNotification('Playback failed. Click again to retry.');
                });
            }
        }
    }
    
    // Handle song end
    function handleSongEnd() {
        isPlaying = false;
        updatePlayButtonUI();
        
        // Play next song automatically
        playNextSong();
    }
    
    // Update play button icon based on state
    function updatePlayButtonUI() {
        if (!playButton || !playIcon || !pauseIcon) return;
        
        if (isPlaying) {
            playIcon.classList.add('hidden');
            pauseIcon.classList.remove('hidden');
            playButton.querySelector('.button-label').textContent = 'Pause';
        } else {
            playIcon.classList.remove('hidden');
            pauseIcon.classList.add('hidden');
            playButton.querySelector('.button-label').textContent = 'Play';
        }
    }
    
    // Update the UI to show currently playing song
    function updateNowPlayingUI(songData = null) {
        if (!songData) return;
        
        // Highlight the current song in any track list
        document.querySelectorAll('.track-row.playing').forEach(row => {
            row.classList.remove('playing');
        });
        
        const currentRow = document.querySelector(`.track-row[data-song-id="${currentSongId}"]`);
        if (currentRow) {
            currentRow.classList.add('playing');
        }
        
        // Update song info in player bar if we have the data
        if (songData.title) {
            // If we have track info elements, update them
            const trackTitle = document.querySelector('.track-title');
            const trackArtist = document.querySelector('.track-artist');
            
            if (trackTitle) trackTitle.textContent = songData.title;
            if (trackArtist) trackArtist.textContent = songData.artist || 'Unknown Artist';
            
            // Update track image if available
            if (trackImage && songData.imageUrl) {
                trackImage.src = songData.imageUrl;
            } else if (trackImage) {
                // Try to find image from the song element
                const songElement = document.querySelector(`.track-row[data-song-id="${currentSongId}"]`);
                if (songElement) {
                    const img = songElement.querySelector('.track-image img');
                    if (img && img.src) {
                        trackImage.src = img.src;
                    }
                }
            }
        }
    }
    
    // Toggle mute/unmute
    function toggleMute() {
        if (!audioPlayer) return;
        
        if (!isMuted) {
            // Store current volume before muting
            previousVolume = audioPlayer.volume > 0 ? audioPlayer.volume : 0.7;
            audioPlayer.volume = 0;
            isMuted = true;
        } else {
            // Restore previous volume
            audioPlayer.volume = previousVolume;
            isMuted = false;
        }
        
        // Update volume UI
        updateVolumeUI(audioPlayer.volume);
    }
    
    // Set volume and update UI
    function setVolume(volume) {
        if (!audioPlayer) return;
        
        // Clamp volume between 0 and 1
        volume = Math.max(0, Math.min(1, volume));
        
        // Set audio player volume
        audioPlayer.volume = volume;
        
        // Update muted state
        isMuted = volume === 0;
        
        // Store volume for mute toggle if not muted
        if (!isMuted) {
            previousVolume = volume;
        }
        
        // Update volume UI
        updateVolumeUI(volume);
    }
    
    // Update volume UI elements
    function updateVolumeUI(volume) {
        if (!volumeSlider || !volumeHandle || !volumeButton) return;
        
        // Update volume slider visual state
        volumeSlider.style.setProperty('--volume', `${volume * 100}%`);
        if (volumeHandle) {
            volumeHandle.style.left = `${volume * 100}%`;
        }
        
        // Update volume button icon based on volume level
        const volumeIcon = volumeButton.querySelector('.material-icons');
        if (!volumeIcon) return;
        
        if (volume === 0) {
            volumeIcon.textContent = 'volume_off';
        } else if (volume < 0.5) {
            volumeIcon.textContent = 'volume_down';
        } else {
            volumeIcon.textContent = 'volume_up';
        }
    }
    
    /**************************************************************************
     * SONG PLAYBACK FUNCTIONS
     **************************************************************************/
    // Play a song
    function playSong(songId) {
        // Show loading indicator while song loads
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        
        // Fetch song details and URL
        fetch(`/song/${songId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Song not found');
                }
                return response.json();
            })
            .then(data => {
                // Set audio source
                if (audioPlayer) {
                    audioPlayer.src = data.audio_url;
                    audioPlayer.load();
                    
                    // Play once loaded
                    audioPlayer.play()
                        .then(() => {
                            isPlaying = true;
                            
                            // Update the UI with song details in both places
                            if (currentSongTitle) currentSongTitle.textContent = data.title;
                            if (currentSongArtist) currentSongArtist.textContent = data.artist;
                            if (currentSongCover) currentSongCover.src = data.cover_image_url;
                            
                            // Update topbar player info
                            if (topCurrentSongTitle) topCurrentSongTitle.textContent = data.title;
                            if (topCurrentSongArtist) topCurrentSongArtist.textContent = data.artist;
                            
                            // Update play/pause icons on both players
                            if (playPauseIcon) playPauseIcon.textContent = 'pause';
                            if (topPlayPauseIcon) topPlayPauseIcon.textContent = 'pause';
                            
                            // Hide loading indicator
                            if (loadingIndicator) {
                                loadingIndicator.style.display = 'none';
                            }
                            
                            // Make sure player bar is visible
                            if (nowPlayingBar) {
                                nowPlayingBar.style.display = 'flex';
                                nowPlayingBar.style.visibility = 'visible';
                                nowPlayingBar.style.opacity = '1';
                            }
                            
                            // Update current song id
                            currentSongId = songId;
                            
                            // Check if like button should be active based on user's liked songs
                            checkIfSongIsLiked(songId);
                            
                            // Log play to history if user is signed in
                            logSongPlay(songId);
                            
                            // Update document title with song info
                            document.title = `${data.title} - ${data.artist} | Spotify`;
                        })
                        .catch(error => {
                            console.error('Error playing audio:', error);
                            if (loadingIndicator) {
                                loadingIndicator.style.display = 'none';
                            }
                            alert('Error playing the song. Please try again.');
                        });
                }
            })
            .catch(error => {
                console.error('Error fetching song:', error);
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                alert('Error loading the song. Please try again.');
            });
    }
    
    // Log play to server
    function logPlay(songId) {
        if (!songId) return;
        
        // For demo purposes, just log to console
        console.log(`Logging play for song ID: ${songId}`);
        
        // In a real application, you would make an API call here
        // fetch('/api/songs/log-play', { 
        //     method: 'POST', 
        //     body: JSON.stringify({ songId }),
        //     headers: { 'Content-Type': 'application/json' }
        // });
    }
    
    /**************************************************************************
     * PLAYLIST NAVIGATION FUNCTIONS
     **************************************************************************/
    // Play next song - integration with existing playlist functionality
    function playNextSong() {
        // Check if we have a playlist and we're not at the end
        if (playlist.length > 0 && currentPlaylistIndex < playlist.length - 1) {
            currentPlaylistIndex++;
            const nextSong = playlist[currentPlaylistIndex];
            playSong(nextSong.id);
            return;
        }
        
        // Otherwise, try to find any next song button in the DOM
        const currentSongElement = document.querySelector(`.track-row[data-song-id="${currentSongId}"]`);
        if (currentSongElement) {
            const nextRow = currentSongElement.nextElementSibling;
            if (nextRow && nextRow.classList.contains('track-row')) {
                const nextButton = nextRow.querySelector('.play-button');
                if (nextButton) {
                    const songId = nextButton.dataset.songId;
                    const songUrl = nextButton.dataset.songUrl;
                    
                    if (songUrl) {
                        playSong(songId);
                        return;
                    }
                }
            }
        }
        
        // If we couldn't find a next song, just log a message
        console.log('No next song available');
    }
    
    // Play previous song - integration with existing playlist functionality
    function playPreviousSong() {
        // Check if we have a playlist and we're not at the beginning
        if (playlist.length > 0 && currentPlaylistIndex > 0) {
            currentPlaylistIndex--;
            const prevSong = playlist[currentPlaylistIndex];
            playSong(prevSong.id);
            return;
        }
        
        // Otherwise, try to find any previous song button in the DOM
        const currentSongElement = document.querySelector(`.track-row[data-song-id="${currentSongId}"]`);
        if (currentSongElement) {
            const prevRow = currentSongElement.previousElementSibling;
            if (prevRow && prevRow.classList.contains('track-row')) {
                const prevButton = prevRow.querySelector('.play-button');
                if (prevButton) {
                    const songId = prevButton.dataset.songId;
                    const songUrl = prevButton.dataset.songUrl;
                    
                    if (songUrl) {
                        playSong(songId);
                        return;
                    }
                }
            }
        }
        
        // If we couldn't find a previous song, just log a message
        console.log('No previous song available');
    }
    
    // Update the playlist index based on current song ID
    function updatePlaylistIndex(songId) {
        if (!songId || playlist.length === 0) return;
        
        for (let i = 0; i < playlist.length; i++) {
            if (playlist[i].id === songId) {
                currentPlaylistIndex = i;
                return;
            }
        }
    }
    
    /**************************************************************************
     * PLAYLIST BUILDING FUNCTIONS
     **************************************************************************/
    // Build the playlist from DOM elements
    function buildPlaylistFromDOM() {
        playlist = [];
        const playButtons = document.querySelectorAll('.play-button[data-song-url]');
        
        playButtons.forEach(button => {
            const songId = button.dataset.songId;
            const songUrl = button.dataset.songUrl;
            
            if (songId && songUrl) {
                // Try to get song data from the DOM
                const row = button.closest('.track-row');
                let songData = null;
                
                if (row) {
                    const titleElement = row.querySelector('.track-title');
                    const artistElement = row.querySelector('.track-artist');
                    
                    if (titleElement && artistElement) {
                        songData = {
                            title: titleElement.textContent.trim(),
                            artist: artistElement.textContent.trim()
                        };
                    }
                }
                
                playlist.push({
                    id: songId,
                    url: songUrl,
                    data: songData
                });
            }
        });
        
        console.log(`Built playlist with ${playlist.length} songs`);
    }
    
    /**************************************************************************
     * UTILITY FUNCTIONS
     **************************************************************************/
    // Show notification
    function showNotification(message, duration = 3000) {
        // Check if notification container exists
        let notificationContainer = document.querySelector('.notification-container');
        if (!notificationContainer) {
            // Create notification container if it doesn't exist
            notificationContainer = document.createElement('div');
            notificationContainer.classList.add('notification-container');
            document.body.appendChild(notificationContainer);
            
            // Style the notification container
            notificationContainer.style.position = 'fixed';
            notificationContainer.style.bottom = '100px';
            notificationContainer.style.left = '50%';
            notificationContainer.style.transform = 'translateX(-50%)';
            notificationContainer.style.zIndex = '9999';
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.classList.add('notification');
        notification.textContent = message;
        
        // Style the notification
        notification.style.background = 'rgba(0, 0, 0, 0.8)';
        notification.style.color = 'white';
        notification.style.padding = '12px 24px';
        notification.style.borderRadius = '24px';
        notification.style.marginBottom = '8px';
        notification.style.transition = 'opacity 0.3s ease';
        
        // Add to container
        notificationContainer.appendChild(notification);
        
        // Remove after duration
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                notificationContainer.removeChild(notification);
                
                // Remove container if empty
                if (notificationContainer.children.length === 0) {
                    document.body.removeChild(notificationContainer);
                }
            }, 300);
        }, duration);
    }
    
    /**************************************************************************
     * INITIALIZATION FUNCTIONS
     **************************************************************************/
    // Initialize play buttons
    function initializePlayButtons() {
        const allPlayButtons = document.querySelectorAll('.play-button[data-song-url]');
        allPlayButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                
                const songId = this.dataset.songId;
                const songUrl = this.dataset.songUrl;
                
                // Get song data from the DOM
                let songData = null;
                const row = this.closest('.track-row');
                
                if (row) {
                    const titleElement = row.querySelector('.track-title');
                    const artistElement = row.querySelector('.track-artist');
                    
                    if (titleElement && artistElement) {
                        songData = {
                            title: titleElement.textContent.trim(),
                            artist: artistElement.textContent.trim()
                        };
                    }
                }
                
                // If it's the currently playing song, toggle play/pause
                if (songId === currentSongId) {
                    togglePlayPause();
                } else {
                    // Otherwise play the new song
                    playSong(songId);
                }
            });
        });
        
        // Build the playlist
        buildPlaylistFromDOM();
    }
    
    // Initialize
    initializePlayButtons();
    
    /**************************************************************************
     * PUBLIC API
     **************************************************************************/
    // Public API
    window.PlayerControls = {
        play: function(songId) {
            playSong(songId);
        },
        pause: function() {
            if (isPlaying) {
                audioPlayer.pause();
            }
        },
        togglePlayPause: togglePlayPause,
        next: playNextSong,
        previous: playPreviousSong,
        seekTo: function(seconds) {
            if (audioPlayer.src) {
                audioPlayer.currentTime = Math.max(0, Math.min(audioPlayer.duration, seconds));
            }
        },
        getCurrentSongId: function() {
            return currentSongId;
        },
        isPlaying: function() {
            return isPlaying;
        },
        getDuration: function() {
            return audioPlayer.duration;
        },
        getCurrentTime: function() {
            return audioPlayer.currentTime;
        },
        setVolume: function(volume) {
            setVolume(volume);
        },
        toggleMute: function() {
            toggleMute();
        },
        updateVolumeUI: updateVolumeUI
    };

    /**************************************************************************
     * ADDITIONAL EVENT LISTENERS
     **************************************************************************/
    playPauseButton.addEventListener('click', function() {
        if (isPlaying) {
            // Pause the song
            // Add your audio pause logic here
            playPauseIcon.textContent = '▶'; // Change icon to play
        } else {
            // Play the song
            // Add your audio play logic here
            playPauseIcon.textContent = '❚❚'; // Change icon to pause
        }
        isPlaying = !isPlaying; // Toggle play state
    });

    // Add this function to ensure playbar visibility
    function enforcePlaybarVisibility() {
        const nowPlayingBar = document.querySelector('.now-playing-bar');
        if (nowPlayingBar) {
            nowPlayingBar.style.position = 'fixed';
            nowPlayingBar.style.bottom = '0';
            nowPlayingBar.style.left = '0';
            nowPlayingBar.style.right = '0';
            nowPlayingBar.style.zIndex = '9999';
            nowPlayingBar.style.display = 'flex';
            nowPlayingBar.style.visibility = 'visible';
            nowPlayingBar.style.opacity = '1';
        }
    }

    // Call initially
    enforcePlaybarVisibility();

    // Call again after a short delay to ensure it takes effect
    setTimeout(enforcePlaybarVisibility, 500);

    // Call when window is resized
    window.addEventListener('resize', enforcePlaybarVisibility);

    // Call when content is dynamically updated
    const mainContent = document.querySelector('.content');
    if (mainContent) {
        // Use MutationObserver to detect content changes
        const observer = new MutationObserver(enforcePlaybarVisibility);
        observer.observe(mainContent, { 
            childList: true, 
            subtree: true 
        });
    }

    // Function to update current song info in both UI locations
    function updateCurrentSongInfo(title, artist, coverUrl) {
        // Update main player
        if (topCurrentSongTitle) topCurrentSongTitle.textContent = title || 'No song playing';
        if (topCurrentSongArtist) topCurrentSongArtist.textContent = artist || '-';
    }

    // Function to update play/pause icons in both UI locations
    function updatePlayPauseIcons(isPlaying) {
        // Update main player
        if (topPlayPauseIcon) {
            topPlayPauseIcon.textContent = isPlaying ? 'pause' : 'play_arrow';
        }
    }

    // Topbar Play/Pause button event listener
    if (topPlayPauseButton) {
        topPlayPauseButton.addEventListener('click', togglePlayPause);
    }

    // Toggle play/pause function
    function togglePlayPause() {
        if (!audioPlayer) return;
        
        if (audioPlayer.paused) {
            if (audioPlayer.src) {
                audioPlayer.play()
                    .then(() => {
                        isPlaying = true;
                        updatePlayPauseIcons(true);
                    })
                    .catch(err => {
                        console.error('Error playing audio:', err);
                    });
            } else {
                // No song loaded
                alert('Please select a song to play first');
            }
        } else {
            audioPlayer.pause();
            isPlaying = false;
            updatePlayPauseIcons(false);
        }
    }

    // Topbar Previous button event listener
    if (topPrevButton) {
        topPrevButton.addEventListener('click', playPreviousSong);
    }

    // Topbar Next button event listener
    if (topNextButton) {
        topNextButton.addEventListener('click', playNextSong);
    }

    // Topbar Shuffle button event listener
    if (topShuffleButton) {
        topShuffleButton.addEventListener('click', toggleShuffle);
    }

    // Function to toggle shuffle mode
    function toggleShuffle() {
        isShuffled = !isShuffled;
        
        // Update UI for both controls
        if (topShuffleButton) {
            topShuffleButton.classList.toggle('active', isShuffled);
        }
        
        // Implement shuffle logic
        if (isShuffled) {
            // Save original order if not already saved
            if (originalPlaylist.length === 0) {
                originalPlaylist = [...playlist];
            }
            
            // Fisher-Yates shuffle algorithm
            let currentIndex = playlist.length;
            let randomIndex, temporaryValue;
            
            // Preserve the current song
            const currentSong = playlist[currentPlaylistIndex];
            
            // Shuffle the playlist
            while (currentIndex !== 0) {
                randomIndex = Math.floor(Math.random() * currentIndex);
                currentIndex--;
                
                temporaryValue = playlist[currentIndex];
                playlist[currentIndex] = playlist[randomIndex];
                playlist[randomIndex] = temporaryValue;
            }
            
            // Find the current song in the shuffled playlist and update currentPlaylistIndex
            currentPlaylistIndex = playlist.findIndex(song => song.id === currentSong.id);
        } else {
            // Restore original order
            if (originalPlaylist.length > 0) {
                const currentSong = playlist[currentPlaylistIndex];
                playlist = [...originalPlaylist];
                currentPlaylistIndex = playlist.findIndex(song => song.id === currentSong.id);
                originalPlaylist = [];
            }
        }
    }

    // Topbar Repeat button event listener
    if (topRepeatButton) {
        topRepeatButton.addEventListener('click', toggleRepeat);
    }

    // Function to toggle repeat mode
    function toggleRepeat() {
        // Cycle through repeat modes: none -> all -> one -> none
        switch (repeatMode) {
            case 'none':
                repeatMode = 'all';
                break;
            case 'all':
                repeatMode = 'one';
                break;
            case 'one':
                repeatMode = 'none';
                break;
        }
        
        // Update UI for both controls
        if (topRepeatButton) {
            topRepeatButton.classList.toggle('active', repeatMode !== 'none');
            if (repeatMode === 'one') {
                topRepeatButton.innerHTML = '<i class="material-icons-round">repeat_one</i>';
            } else {
                topRepeatButton.innerHTML = '<i class="material-icons-round">repeat</i>';
            }
        }
        
        // Update audio element's loop property
        if (audioPlayer) {
            audioPlayer.loop = (repeatMode === 'one');
        }
    }

    // Ensure both playbar versions are synced on initial load
    function syncPlayerUIState() {
        // Sync play/pause button state
        updatePlayPauseIcons(isPlaying);
        
        // Sync shuffle button state
        if (topShuffleButton) {
            topShuffleButton.classList.toggle('active', isShuffled);
        }
        
        // Sync repeat button state
        if (topRepeatButton) {
            const isRepeatActive = repeatMode !== 'none';
            topRepeatButton.classList.toggle('active', isRepeatActive);
            
            if (repeatMode === 'one') {
                topRepeatButton.innerHTML = '<i class="material-icons-round">repeat_one</i>';
            } else {
                topRepeatButton.innerHTML = '<i class="material-icons-round">repeat</i>';
            }
        }
    }

    // Call on initial load
    syncPlayerUIState();

    console.log('Trying to get element:', document.getElementById('yourElementId'));
}); 