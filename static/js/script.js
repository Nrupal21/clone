console.log('Spotify Clone Application - JavaScript Initialized');

//################################################
// GLOBAL VARIABLES
//################################################
let songs = [];
let currFolder;
let currentSong;
let currentSongId;

//################################################
// UTILITY FUNCTIONS
//################################################
/**
 * Convert seconds to MM:SS format
 * @param {number} seconds - Time in seconds
 * @returns {string} Formatted time string
 */
function secondsToMinutesSeconds(seconds) {
    if (isNaN(seconds) || seconds < 0) {
        return "00:00";
    }

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    const formattedMinutes = String(minutes).padStart(2, '0');
    const formattedSeconds = String(remainingSeconds).padStart(2, '0');

    return `${formattedMinutes}:${formattedSeconds}`;
}

/**
 * Format time function (alternative format)
 * @param {number} seconds - Time in seconds
 * @returns {string} Formatted time string
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

//################################################
// SONG LOADING FUNCTIONS
//################################################
/**
 * Fetch songs from a folder
 * @param {string} folder - Folder path to get songs from
 * @returns {Promise<Array>} Array of song paths
 */
async function getSongs(folder) {
    try {
    currFolder = folder;
        const response = await fetch(`/${folder}/`);
        if (!response.ok) {
            throw new Error(`Failed to fetch songs: ${response.status} ${response.statusText}`);
        }
        
        const responseText = await response.text();
        const div = document.createElement("div");
        div.innerHTML = responseText;
        const anchors = div.getElementsByTagName("a");
        songs = [];
        
        for (let index = 0; index < anchors.length; index++) {
            const element = anchors[index];
        if (element.href.endsWith(".mp3")) {
                songs.push(element.href.split(`/${folder}/`)[1]);
            }
        }
        
        // Show all the songs in the playlist
        updatePlaylist(songs);
        
        return songs;
    } catch (error) {
        console.error("Error fetching songs:", error);
        return [];
    }
}

/**
 * Update the playlist UI with song list
 * @param {Array} songList - List of songs to display
 */
function updatePlaylist(songList) {
    const songUL = document.querySelector(".songList")?.getElementsByTagName("ul")[0];
    if (!songUL) return;
    
        songUL.innerHTML = "";
    
    for (const song of songList) {
        const formattedSongName = song.replaceAll("%20", " ");
        
        songUL.innerHTML += `
            <li>
                <img class="invert" width="34" src="img/music.svg" alt="">
                            <div class="info">
                    <div>${formattedSongName}</div>
                    <div>Artist</div>
                            </div>
                            <div class="playnow">
                                <span>Play Now</span>
                                <img class="invert" src="img/play.svg" alt="">
                </div>
            </li>
        `;
    }

    // Attach an event listener to each song
    const songItems = document.querySelector(".songList")?.getElementsByTagName("li");
    if (songItems) {
        Array.from(songItems).forEach(item => {
            item.addEventListener("click", () => {
                const songName = item.querySelector(".info").firstElementChild.innerHTML.trim();
                playMusic(songName);
            });
        });
    }
}

/**
 * Display albums on the page
 */
async function displayAlbums() {
    console.log("Displaying albums");
    try {
        const response = await fetch(`/songs/`);
        if (!response.ok) {
            throw new Error(`Failed to fetch albums: ${response.status} ${response.statusText}`);
        }
        
        const responseText = await response.text();
        const div = document.createElement("div");
        div.innerHTML = responseText;
        const anchors = div.getElementsByTagName("a");
        const cardContainer = document.querySelector(".cardContainer");
        
        if (!cardContainer) return;
        
        const albums = Array.from(anchors)
            .filter(e => e.href.includes("/songs") && !e.href.includes(".htaccess"));
            
        for (let index = 0; index < albums.length; index++) {
            const album = albums[index];
            const folder = album.href.split("/").slice(-2)[0];
            
                try {
            // Get the metadata of the folder
                const metaResponse = await fetch(`/songs/${folder}/info.json`);
                if (!metaResponse.ok) {
                    console.warn(`No info.json found for ${folder}`);
                    continue;
                }
                
                const albumInfo = await metaResponse.json();
                
                cardContainer.innerHTML += `
                    <div data-folder="${folder}" class="card">
            <div class="play">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                    xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 20V4L19 12L5 20Z" stroke="#141B34" fill="#000" stroke-width="1.5"
                        stroke-linejoin="round" />
                </svg>
            </div>
                        <img src="/songs/${folder}/cover.jpg" alt="${albumInfo.title}">
                        <h2>${albumInfo.title}</h2>
                        <p>${albumInfo.description || ''}</p>
                    </div>
                `;
                } catch (error) {
                    console.error(`Error loading info for folder ${folder}:`, error);
            }
        }

        // Load the playlist when a card is clicked
        const cards = document.getElementsByClassName("card");
        Array.from(cards).forEach(card => {
            card.addEventListener("click", async () => {
                console.log("Fetching songs from folder:", card.dataset.folder);
                const folderSongs = await getSongs(`songs/${card.dataset.folder}`);
                
                if (folderSongs && folderSongs.length > 0) {
                    playMusic(folderSongs[0], false);
                } else {
                    console.warn("No songs found in folder");
                }
            });
        });
    } catch (error) {
        console.error("Error displaying albums:", error);
    }
}

//################################################
// PLAYBACK FUNCTIONS
//################################################
/**
 * Play a song from the current folder
 * @param {string} track - Song filename to play
 * @param {boolean} [autoplay=true] - Whether to start playing automatically
 */
function playMusic(track, autoplay = true) {
    try {
        // Initialize audio player if not already
        if (!currentSong) {
            currentSong = new Audio();
        }
        
        // Update the audio source
        const songUrl = `/${currFolder}/${track}`;
        console.log(`Playing: ${songUrl}`);
        
        currentSong.src = songUrl;
        
        // Update UI
        document.querySelector(".songinfo").innerHTML = track;
        document.querySelector(".songtime").innerHTML = "00:00 / 00:00";
        
        if (autoplay) {
            const playPromise = currentSong.play();
            
            // Handle asynchronous playback
            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        console.log("Playback started successfully");
                        document.getElementById("play").src = "img/pause.svg";
                    })
                    .catch(err => {
                        console.error("Error starting playback:", err);
                        document.getElementById("play").src = "img/play.svg";
                        alert("Failed to play the song. Please try again.");
                    });
            }
        }
        
        // Update playlist UI to highlight current song
        const songItems = document.querySelectorAll(".songList li");
        songItems.forEach(item => {
            const songName = item.querySelector(".info").firstElementChild.innerHTML.trim();
            if (songName === track) {
                item.classList.add("playing");
            } else {
                item.classList.remove("playing");
            }
        });
        
    } catch (error) {
        console.error("Error in playMusic:", error);
    }
}

/**
 * Play the next song in the playlist
 */
function playNextSong() {
    if (!songs || songs.length === 0 || !currentSong) {
        console.warn("No songs available to play next");
        return;
    }
    
    // Find current song index
    const currentIndex = songs.indexOf(currentSong.src.split("/").slice(-1)[0]);
    
    if (currentIndex === -1) {
        console.warn("Current song not found in playlist");
        return;
    }
    
    // Play next song or loop back to first
    const nextIndex = (currentIndex + 1) % songs.length;
    playMusic(songs[nextIndex]);
}

/**
 * Play the previous song in the playlist
 */
function playPreviousSong() {
    if (!songs || songs.length === 0 || !currentSong) {
        console.warn("No songs available to play previous");
        return;
    }
    
    // Find current song index
    const currentIndex = songs.indexOf(currentSong.src.split("/").slice(-1)[0]);
    
    if (currentIndex === -1) {
        console.warn("Current song not found in playlist");
        return;
    }
    
    // Go to previous song or loop to the last if at beginning
    const prevIndex = (currentIndex - 1 + songs.length) % songs.length;
    playMusic(songs[prevIndex]);
}

//################################################
// UI INTERACTION FUNCTIONS
//################################################
/**
 * Initialize UI interactions for the application
 */
function initializeUIInteractions() {
    // User dropdown functionality
    initializeDropdowns();
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize scrolling behavior
    initializeScroll();
    
    // Initialize buttons
    initializeButtons();
    
    // Delayed initialization for any dynamic content
    setTimeout(function() {
        initializePlayButtons();
        initializeDeleteButtons();
    }, 500);
}

/**
 * Initialize dropdowns for user profiles
 */
function initializeDropdowns() {
    const userProfile = document.querySelector('.sidebar .user-profile');
    const userDropdown = document.querySelector('.sidebar .user-dropdown');
    const topbarUserProfile = document.querySelector('.topbar-user-profile');
    const topbarDropdown = document.querySelector('.topbar .user-dropdown');
    
    // Initialize sidebar dropdown toggles
    if (userProfile && userDropdown) {
        userProfile.addEventListener('click', function(e) {
            e.stopPropagation();
            userDropdown.classList.toggle('active');
            
            // Close topbar dropdown if open
            if (topbarDropdown && topbarDropdown.classList.contains('active')) {
                topbarDropdown.classList.remove('active');
            }
        });
    }
    
    // Initialize topbar dropdown toggles
    if (topbarUserProfile && topbarDropdown) {
        topbarUserProfile.addEventListener('click', function(e) {
            e.stopPropagation();
            topbarDropdown.classList.toggle('active');
            
            // Close sidebar dropdown if open
            if (userDropdown && userDropdown.classList.contains('active')) {
                userDropdown.classList.remove('active');
            }
        });
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function() {
        if (userDropdown && userDropdown.classList.contains('active')) {
            userDropdown.classList.remove('active');
        }
        if (topbarDropdown && topbarDropdown.classList.contains('active')) {
            topbarDropdown.classList.remove('active');
        }
    });
}

/**
 * Initialize search functionality
 */
function initializeSearch() {
    const searchInput = document.querySelector('.search-input');
    const clearSearchBtn = document.querySelector('.clear-search-btn');
    
    if (searchInput && clearSearchBtn) {
        // Add event listener for input changes to show/hide clear button
        searchInput.addEventListener('input', function() {
            clearSearchBtn.style.opacity = this.value.length > 0 ? '1' : '0';
        });
        
        // Focus the search input when clicking on the search container
        const searchContainer = document.querySelector('.search-container');
        if (searchContainer) {
            searchContainer.addEventListener('click', function(e) {
                if (e.target === this) {
                    searchInput.focus();
                }
            });
    }
    
    // Clear search button functionality
        clearSearchBtn.addEventListener('click', function() {
            searchInput.value = '';
            searchInput.focus();
            this.style.opacity = '0';
        });
    
    // Form submission enhancement
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            if (searchInput.value.trim() === '') {
                e.preventDefault(); // Prevent empty search submission
            }
        });
        }
    }
    }
    
/**
 * Initialize scroll behavior for elements
 */
function initializeScroll() {
    const topbar = document.querySelector('.topbar');
    const content = document.querySelector('.content');
    
    if (content && topbar) {
        content.addEventListener('scroll', function() {
            topbar.classList.toggle('scrolled', this.scrollTop > 10);
        });
    }
    
    // Initialize mood navigation
    const moodLinks = document.querySelectorAll('.mood-link');
    
    if (moodLinks.length > 0) {
        moodLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const mood = this.textContent.trim();
                console.log(`Navigating to mood: ${mood}`);
                
                // Navigate to the mood page
                window.location.href = `/mood/${mood}`;
            });
        });
    }
    }
    
/**
 * Initialize buttons and controls
 */
function initializeButtons() {
    // Initialize upload button
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadModal = document.getElementById('uploadModal');
    const closeModal = document.querySelector('.close-modal');
    
    if (uploadBtn && uploadModal) {
        uploadBtn.addEventListener('click', function() {
            uploadModal.style.display = 'flex';
        });
        
        if (closeModal) {
            closeModal.addEventListener('click', function() {
                uploadModal.style.display = 'none';
            });
        }
        
        window.addEventListener('click', function(e) {
            if (e.target === uploadModal) {
                uploadModal.style.display = 'none';
            }
        });
    }
    
    // Admin link clicks logging
    const adminLinks = document.querySelectorAll('a[href*="admin"]');
    
    if (adminLinks.length > 0) {
        adminLinks.forEach(link => {
            link.addEventListener('click', function() {
                console.log('Admin link clicked:', this.href);
            });
        });
    }
}

/**
 * Initialize play buttons throughout the site
 */
function initializePlayButtons() {
    const playButtons = document.querySelectorAll('.play-song-btn');
    
    if (playButtons.length > 0) {
        playButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                const songId = this.getAttribute('data-song-id');
                if (songId) {
                    // Call the play function with just the ID
                    window.PlayerControls.play(songId);
                }
            });
        });
    }
    
    // Also set up song rows for playback
    const songRows = document.querySelectorAll('.song-row');
    
    if (songRows.length > 0) {
        songRows.forEach(row => {
            row.addEventListener('click', function(e) {
                // Don't trigger if clicked on a button inside the row
                if (e.target.closest('button')) {
                    return;
                }
                
                const songId = this.getAttribute('data-song-id');
                if (songId) {
                    // Call the play function with just the ID
                    window.PlayerControls.play(songId);
                }
            });
        });
    }
}

/**
 * Initialize delete buttons for songs
 */
function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll('.delete-song-btn');
    
    if (deleteButtons.length > 0) {
        deleteButtons.forEach(button => {
            // Clone the button to remove any existing event listeners
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            newButton.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const songId = this.getAttribute('data-song-id');
                const songTitle = this.getAttribute('data-song-title') || 'this song';
                
                if (!songId) {
                    console.error('No song ID found for delete button');
                    return;
                }
                
                if (confirm(`Are you sure you want to delete "${songTitle}"?`)) {
                    deleteSong(songId, this);
                }
            });
        });
    }
}

/**
 * Delete a song via API
 * @param {string} songId - ID of the song to delete
 * @param {HTMLElement} buttonElement - Button element for UI update
 */
function deleteSong(songId, buttonElement) {
    try {
        fetch(`/songs/${songId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to delete song');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Remove the song card from the UI
                const songCard = buttonElement.closest('.song-card');
                if (songCard) {
                    songCard.remove();
                }
                
                // Show success message
                alert('Song deleted successfully');
            } else {
                alert(data.message || 'Failed to delete song');
            }
        })
        .catch(err => {
            console.error('Error deleting song:', err);
            alert('Error deleting song. Please try again.');
        });
    } catch (error) {
        console.error('Error in delete operation:', error);
        alert('An error occurred while trying to delete the song.');
    }
}

//################################################
// MAIN APPLICATION INITIALIZATION
//################################################
/**
 * Main application initialization function
 */
async function main() {
    try {
        // Set up global audio player
        if (!currentSong) {
            currentSong = new Audio();
            
            // Set up audio event listeners
            setupAudioListeners();
        }
        
        // Initialize UI interactions first
        initializeUIInteractions();

        // Elements may not exist on all pages, use optional chaining
        const play = document.getElementById("play");
        const previous = document.getElementById("previous");
        const next = document.getElementById("next");

        // Get the list of all the songs if on compatible page
        if (document.querySelector(".songList")) {
            const songData = await getSongs("songs/ncs");
            if (songData && songData.length > 0) {
                playMusic(songData[0], false); // Load but don't autoplay first song
            }

    // Display all the albums on the page
            await displayAlbums();
        }

        // Attach an event listener to play, next and previous buttons
        if (play) {
            play.addEventListener("click", togglePlayPause);
        }

        if (previous) {
            previous.addEventListener("click", playPreviousSong);
        }

        if (next) {
            next.addEventListener("click", playNextSong);
        }

        // Set up seekbar interactivity
        setupSeekbar();
        
        // Set up volume controls
        setupVolumeControls();
        
        // Set up mobile UI controls
        setupMobileControls();
        
    } catch (error) {
        console.error("Error in main function:", error);
    }
}

/**
 * Set up audio player event listeners
 */
function setupAudioListeners() {
    if (!currentSong) return;

    // Listen for timeupdate event
    currentSong.addEventListener("timeupdate", () => {
            const songTime = document.querySelector(".songtime");
            const circle = document.querySelector(".circle");
            
            if (songTime) {
                songTime.innerHTML = `${secondsToMinutesSeconds(currentSong.currentTime)} / ${secondsToMinutesSeconds(currentSong.duration)}`;
            }
            
            if (circle && !isNaN(currentSong.duration) && currentSong.duration > 0) {
                circle.style.left = (currentSong.currentTime / currentSong.duration) * 100 + "%";
            }
        });

    // Handle audio errors
    currentSong.addEventListener("error", (e) => {
        console.error("Audio error:", e);
        alert("There was an error playing this song. Please try another one.");
        document.getElementById("play").src = "img/play.svg";
    });
    
    // Handle audio ended
    currentSong.addEventListener("ended", () => {
        playNextSong();
    });
}

/**
 * Toggle play/pause for the current song
 */
function togglePlayPause() {
    if (!currentSong) return;
    
    const playPauseButton = document.getElementById('playPauseButton');
    const playPauseIcon = document.getElementById('playPauseIcon');
    
    if (currentSong.paused) {
        // Play the song
        const playPromise = currentSong.play();
        
        if (playPromise !== undefined) {
            playPromise
                .then(() => {
                    if (playPauseIcon) playPauseIcon.textContent = 'pause';
                })
                .catch(err => {
                    console.error('Error playing song:', err);
                    if (playPauseIcon) playPauseIcon.textContent = 'play_arrow';
                    
                    // Show error message if there's no source
                    if (!currentSong.src) {
                        alert('Please select a song to play first');
                    } else {
                        alert('Error playing the song. Please try another one.');
                }
            });
        }
} else {
        // Pause the song
                currentSong.pause();
        if (playPauseIcon) playPauseIcon.textContent = 'play_arrow';
    }
}

/**
 * Set up seekbar interaction
 */
function setupSeekbar() {
    const progressBar = document.querySelector('.progress-bar');
    const progressHandle = document.querySelector('.progress-handle');
    const progress = document.querySelector('.progress');
    
    if (!progressBar || !progress) return;
    
    let isDragging = false;
    
    progressBar.addEventListener("click", e => {
        if (!currentSong || isNaN(currentSong.duration) || currentSong.duration <= 0) return;
        
        // Calculate percentage based on click position
        const progressBarRect = progressBar.getBoundingClientRect();
        const percent = (e.clientX - progressBarRect.left) / progressBarRect.width * 100;
        
        // Update seek progress position
        progress.style.width = `${percent}%`;
        if (progressHandle) {
            progressHandle.style.left = `${percent}%`;
        }
        
        // Update song position
        currentSong.currentTime = (currentSong.duration * percent) / 100;
    });
    
    // Add drag functionality
    if (progressHandle) {
        progressHandle.addEventListener('mousedown', function(e) {
            isDragging = true;
            progressBar.classList.add('dragging');
            e.preventDefault(); // Prevent text selection
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            const progressBarRect = progressBar.getBoundingClientRect();
            let percent = (e.clientX - progressBarRect.left) / progressBarRect.width;
            percent = Math.max(0, Math.min(1, percent)) * 100;
            
            progress.style.width = `${percent}%`;
            progressHandle.style.left = `${percent}%`;
            
            if (currentSong && !isNaN(currentSong.duration)) {
                // Don't update currentTime until mouse is released to avoid stuttering
                document.querySelector('.current-time').textContent = 
                    formatTime((percent / 100) * currentSong.duration);
            }
        });
        
        document.addEventListener('mouseup', function() {
            if (!isDragging) return;
            
            const progressBarRect = progressBar.getBoundingClientRect();
            const handleStyle = getComputedStyle(progressHandle);
            const handleLeft = parseFloat(handleStyle.left) || 0;
            const percent = handleLeft / progressBarRect.width;
            
            if (currentSong && !isNaN(currentSong.duration)) {
                currentSong.currentTime = percent * currentSong.duration;
            }
            
                isDragging = false;
            progressBar.classList.remove('dragging');
        });
    }
    
    // Update progress bar on timeupdate
    if (currentSong) {
        currentSong.addEventListener('timeupdate', updateProgressBar);
    }
}

/**
 * Update progress bar based on current song time
 */
function updateProgressBar() {
    const progress = document.querySelector('.progress');
        const progressHandle = document.querySelector('.progress-handle');
    const currentTimeDisplay = document.querySelector('.current-time');
    const totalTimeDisplay = document.querySelector('.total-time');
    
    if (!progress || !currentSong || isNaN(currentSong.duration) || currentSong.duration <= 0) return;
    
    const percent = (currentSong.currentTime / currentSong.duration) * 100;
    progress.style.width = `${percent}%`;

        if (progressHandle) {
        progressHandle.style.left = `${percent}%`;
    }
    
    if (currentTimeDisplay) {
        currentTimeDisplay.textContent = formatTime(currentSong.currentTime);
    }
    
    if (totalTimeDisplay && !isNaN(currentSong.duration)) {
        totalTimeDisplay.textContent = formatTime(currentSong.duration);
    }
}

/**
 * Set up volume controls
 */
function setupVolumeControls() {
    // Set up volume slider
    const volumeBar = document.querySelector('.volume-bar');
    const volumeLevel = document.getElementById('volumeLevel');
    const volumeHandle = document.querySelector('.volume-handle');
    const volumeIcon = document.getElementById('volumeIcon');
    
    if (!volumeBar || !volumeLevel) return;
    
    // Set initial volume and handle position
    if (currentSong) {
        volumeLevel.style.width = `${currentSong.volume * 100}%`;
        if (volumeHandle) {
            volumeHandle.style.left = `${currentSong.volume * 100}%`;
        }
    }
    
        let isDragging = false;

    // Click on volume bar
    volumeBar.addEventListener('click', function(e) {
        if (!currentSong) return;
        
        const rect = volumeBar.getBoundingClientRect();
        const volume = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        
        // Update volume
        currentSong.volume = volume;
        volumeLevel.style.width = `${volume * 100}%`;
        
        if (volumeHandle) {
            volumeHandle.style.left = `${volume * 100}%`;
        }
        
        // Update icon
        if (volumeIcon) {
            if (volume === 0) {
                volumeIcon.textContent = 'volume_off';
            } else if (volume < 0.5) {
                volumeIcon.textContent = 'volume_down';
            } else {
                volumeIcon.textContent = 'volume_up';
            }
        }
    });
    
    // Drag functionality for volume handle
    if (volumeHandle) {
        volumeHandle.addEventListener('mousedown', function(e) {
            isDragging = true;
            volumeBar.classList.add('dragging');
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            const rect = volumeBar.getBoundingClientRect();
            const volume = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
            
            if (currentSong) {
                currentSong.volume = volume;
            }
            
            volumeLevel.style.width = `${volume * 100}%`;
            volumeHandle.style.left = `${volume * 100}%`;
            
            // Update icon
            if (volumeIcon) {
                if (volume === 0) {
                    volumeIcon.textContent = 'volume_off';
                } else if (volume < 0.5) {
                    volumeIcon.textContent = 'volume_down';
                } else {
                    volumeIcon.textContent = 'volume_up';
                }
            }
        });
        
        document.addEventListener('mouseup', function() {
            if (isDragging) {
                isDragging = false;
                volumeBar.classList.remove('dragging');
            }
        });
    }
}

/**
 * Setup mobile-specific UI controls
 */
function setupMobileControls() {
    // Handle mobile menu toggling
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.querySelector('.sidebar');
    
    // Create overlay if it doesn't exist
    let overlay = document.querySelector('.mobile-menu-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'mobile-menu-overlay';
        document.body.appendChild(overlay);
    }
    
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('show');
            overlay.classList.toggle('active');
            document.body.classList.toggle('menu-open');
        });
        
        // Close menu when clicking overlay
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('show');
            overlay.classList.remove('active');
            document.body.classList.remove('menu-open');
        });
    }
    
    // Handle portrait/landscape orientation changes
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            // Reset mobile menu when screen gets larger
            if (sidebar) {
                sidebar.classList.remove('show');
            }
            if (overlay) {
                overlay.classList.remove('active');
            }
            document.body.classList.remove('menu-open');
            }
        });
    }

/**
 * Function to play a song in a popup player
 * @param {string} songId - ID of the song to play
 * @param {string} songTitle - Title of the song
 * @param {string} songArtist - Artist of the song
 * @param {string} songCover - Cover image URL
 */
function playSongInPopup(songId, songTitle, songArtist, songCover) {
    const audioPlayer = document.getElementById('audio-player');
    if (!audioPlayer) {
        console.error('Audio player element not found');
        alert('Audio player not available');
        return;
    }
    
    console.log(`Attempting to play song: ${songTitle} (ID: ${songId})`);
    
    // Show loading indicator if available
    const loadingIndicator = document.querySelector('.loading-indicator');
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    
    // Update track info if available
    const trackTitle = document.querySelector('.track-title');
    const trackArtist = document.querySelector('.track-artist');
    const trackImage = document.querySelector('.track-image');
    
    if (trackTitle) trackTitle.textContent = songTitle || 'Unknown Title';
    if (trackArtist) trackArtist.textContent = songArtist || 'Unknown Artist';
    if (trackImage && songCover) trackImage.src = songCover;
    
    // Also update the now-playing bar
    updateNowPlayingBar(songId, songTitle, songArtist, songCover);
    
    // Reset any previous errors
    audioPlayer.removeAttribute('src');
    audioPlayer.load();
    
    // Reset progress bar
    const progress = document.getElementById('progress');
    const progressHandle = document.querySelector('.progress-handle');
    if (progress) progress.style.width = '0%';
    if (progressHandle) progressHandle.style.left = '0%';
    
    // Remove any existing error listeners to avoid duplication
    const oldAudioPlayer = audioPlayer;
    const newAudioPlayer = oldAudioPlayer.cloneNode(false);
    oldAudioPlayer.parentNode.replaceChild(newAudioPlayer, oldAudioPlayer);
    
    // Get the new reference after replacement
    const player = document.getElementById('audio-player');
    
    // Set the current song for other functions to use
    currentSong = player;
    currentSongId = songId;
    
    // Create a retry button in the loading indicator
    const createRetryButton = () => {
        if (loadingIndicator) {
            loadingIndicator.innerHTML = 'Failed to load audio. <button id="retry-audio" style="background: #1db954; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">Retry</button>';
            
            const retryButton = document.getElementById('retry-audio');
            if (retryButton) {
                retryButton.addEventListener('click', () => {
                    loadingIndicator.innerHTML = 'Loading audio...';
                    loadingIndicator.style.display = 'block';
                    playSongInPopup(songId, songTitle, songArtist, songCover);
                });
            }
        }
    };
    
    // Fetch and play the song
    console.log(`Fetching song from: /play/${songId}`);
    
    // Log the request
    const startTime = performance.now();
    
    fetch(`/play/${songId}`)
        .then(response => {
            const endTime = performance.now();
            console.log(`Response received in ${endTime - startTime}ms. Status: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('You need to log in to play songs');
                } else if (response.status === 404) {
                    throw new Error('Song not found or file missing');
                } else if (response.status === 415) {
                    throw new Error('Unsupported audio format');
                } else if (response.status === 500) {
                    throw new Error('Server error: Could not play the song');
        } else {
                    throw new Error(`Error ${response.status}: ${response.statusText}`);
                }
            }
            
            // Look for X-Debug headers
            const debugHeaders = {};
            response.headers.forEach((value, name) => {
                if (name.startsWith('x-debug-')) {
                    debugHeaders[name] = value;
                    console.log(`Debug header: ${name} = ${value}`);
                }
            });
            
            return response.blob();
        })
        .then(blob => {
            // Check if the blob is valid audio data
            console.log(`Received blob of type: ${blob.type}, size: ${blob.size} bytes`);
            if (blob.size === 0) {
                throw new Error('Invalid audio file: Empty response');
            }
            
            // Create a blob URL
            const songUrl = URL.createObjectURL(blob);
            player.src = songUrl;
            
            // Set up audio event listeners after src is set
            player.addEventListener('timeupdate', updateProgressBar);
            
            // Add event listener for audio-specific errors
            const audioErrorHandler = function(e) {
                console.error('Audio element error:', e);
                console.error('Audio error code:', e.target.error ? e.target.error.code : 'unknown');
                console.error('Audio src:', e.target.src);
                
                let errorMessage = 'Error playing audio: ';
                
                if (e.target.error) {
                    switch (e.target.error.code) {
                        case MediaError.MEDIA_ERR_ABORTED:
                            errorMessage += 'Playback aborted';
                            break;
                        case MediaError.MEDIA_ERR_NETWORK:
                            errorMessage += 'Network error';
                            break;
                        case MediaError.MEDIA_ERR_DECODE:
                            errorMessage += 'Audio format not supported or corrupted';
                            break;
                        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
                            errorMessage += 'Audio format not supported by your browser';
                            break;
                        default:
                            errorMessage += 'Unknown error';
                    }
    } else {
                    errorMessage += 'Unknown playback error';
                }
                
                alert(errorMessage);
                player.removeEventListener('error', audioErrorHandler);
                createRetryButton();
            };
            
            player.addEventListener('error', audioErrorHandler);
            
            // Play the song
            console.log('Attempting to play audio...');
            player.play()
                .then(() => {
                    console.log('Playback started successfully');
                    
                    // Update play button icon
                    const playPauseIcon = document.getElementById('playPauseIcon');
                    if (playPauseIcon) playPauseIcon.textContent = 'pause';
                })
                .catch(error => {
                    console.error('Error playing song:', error);
                    
                    // Update play button icon
                    const playPauseIcon = document.getElementById('playPauseIcon');
                    if (playPauseIcon) playPauseIcon.textContent = 'play_arrow';
                    
                    alert('Failed to play the song: ' + (error.message || 'Please try again'));
                    createRetryButton();
                })
                .finally(() => {
                    // Hide loading indicator after a short delay to ensure it's seen
                    if (loadingIndicator) {
                        setTimeout(() => {
                            if (player.paused) {
                                // If still paused, keep the loading indicator or show retry
                                createRetryButton();
                            } else {
                                loadingIndicator.style.display = 'none';
                            }
                        }, 500);
                    }
                });
        })
        .catch(error => {
            console.error('Error fetching song:', error);
            
            // Update play button icon
            const playPauseIcon = document.getElementById('playPauseIcon');
            if (playPauseIcon) playPauseIcon.textContent = 'play_arrow';
            
            alert(error.message || 'Error loading the song. Please try again.');
            if (loadingIndicator) {
                createRetryButton();
        }
    });
}

/**
 * Update the now-playing bar with current song info
 * @param {string} songId - ID of the song
 * @param {string} songTitle - Title of the song
 * @param {string} songArtist - Artist of the song
 * @param {string} songCover - Cover image URL
 */
function updateNowPlayingBar(songId, songTitle, songArtist, songCover) {
    // Set the currently playing song ID in global context
    currentSongId = songId;
    
    // Update elements in the now-playing bar
    const playPauseIcon = document.getElementById('playPauseIcon');
    const nowPlayingTitle = document.querySelector('.now-playing-info .track-title');
    const nowPlayingArtist = document.querySelector('.now-playing-info .track-artist');
    const nowPlayingImage = document.querySelector('.now-playing-info .track-image');
    
    if (nowPlayingTitle) nowPlayingTitle.textContent = songTitle || 'Unknown Title';
    if (nowPlayingArtist) nowPlayingArtist.textContent = songArtist || 'Unknown Artist';
    if (nowPlayingImage && songCover) nowPlayingImage.src = songCover;
    
    // Update play button state
    if (playPauseIcon) playPauseIcon.textContent = 'pause';
    
    // Update like button state if the user has liked this song
    const likeButton = document.querySelector('.now-playing-info .like-btn');
    if (likeButton) {
        const likeBtnIcon = likeButton.querySelector('.material-icons-round');
        if (likeBtnIcon) {
            // Check if this song is in the user's liked songs
            // This would require a server check, but for now we'll use a simple toggle
            likeButton.setAttribute('data-song-id', songId);
            
            // Add click handler for the like button if it doesn't exist
            if (!likeButton.hasClickHandler) {
                likeButton.addEventListener('click', function() {
                const songId = this.getAttribute('data-song-id');
                    if (!songId) return;
                    
                    const icon = this.querySelector('.material-icons-round');
                    const isLiked = icon.textContent === 'favorite';
                    
                    // Send like/unlike request to the server
                    fetch(`/like-song/${songId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // Toggle the icon
                            icon.textContent = isLiked ? 'favorite_border' : 'favorite';
                        }
                    })
                    .catch(error => {
                        console.error('Error toggling like status:', error);
            });
        });
                likeButton.hasClickHandler = true;
            }
        }
    }
}

/**
 * Show payment modal with localized pricing
 * @param {string} planType - The type of plan (basic, premium, etc)
 * @param {string} price - Formatted price with currency symbol
 * @param {string} currency - Currency code (USD, EUR, etc)
 */
function showPaymentModal(planType, price, currency) {
    const modal = document.getElementById('payment-modal');
    const selectedPlanName = document.getElementById('selected-plan-name');
    const planNameDisplay = document.getElementById('plan-name-display');
    const planPriceDisplay = document.getElementById('plan-price-display');
    
    if (!modal || !selectedPlanName || !planNameDisplay || !planPriceDisplay) {
        console.error('Payment modal elements not found');
        return;
    }
    
    // Update modal content with plan details
    selectedPlanName.textContent = planType.charAt(0).toUpperCase() + planType.slice(1);
    planNameDisplay.textContent = selectedPlanName.textContent;
    planPriceDisplay.textContent = price;
    
    // Create payment button
    createPaymentButton(planType, currency);
    
    // Show modal
    modal.style.display = 'flex';
}

/**
 * Create payment button for the selected plan
 * @param {string} planType - The type of plan (basic, premium, etc)
 * @param {string} currency - Currency code (USD, EUR, etc)
 */
function createPaymentButton(planType, currency) {
    const paymentButton = document.getElementById('razorpay-button');
    if (!paymentButton) return;
    
    paymentButton.innerHTML = '';
    
    // Create loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'loading-indicator';
    loadingIndicator.innerHTML = 'Preparing payment...';
    paymentButton.appendChild(loadingIndicator);
    
    // Create order from the server
    fetch(`/subscription/create-order/${planType}`, {
        method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        })
        .then(response => {
            if (!response.ok) {
            throw new Error('Failed to create payment order');
                            }
                            return response.json();
                        })
                        .then(data => {
        // Remove loading indicator
        paymentButton.innerHTML = '';
        
        // Create pay button
        const payButton = document.createElement('button');
        payButton.className = 'payment-button';
        payButton.innerHTML = `Pay ${data.currency} ${data.amount/100}`;
        
        payButton.addEventListener('click', () => {
            const options = {
                key: razorpayKeyId, // This should be defined globally in the template
                amount: data.amount,
                currency: data.currency || currency,
                name: "Spotify",
                description: `${planType.charAt(0).toUpperCase() + planType.slice(1)} Plan Subscription`,
                order_id: data.id,
                handler: function(response) {
                    // Process the payment response
                    processPayment(response, planType);
                },
                prefill: {
                    name: userName, // This should be defined globally in the template
                    email: userEmail // This should be defined globally in the template
                },
                theme: {
                    color: "#3f51b5"
                }
            };
            
            // Initialize Razorpay
            try {
                const rzp = new Razorpay(options);
                rzp.open();
            } catch (e) {
                console.error('Error initializing Razorpay:', e);
                alert('Payment gateway unavailable. Please try again later.');
            }
        });
        
        paymentButton.appendChild(payButton);
        })
        .catch(error => {
        console.error('Error creating order:', error);
        paymentButton.innerHTML = `
            <div class="payment-error">
                Unable to process payment at this time. Please try again later.
            </div>
        `;
    });
}

/**
 * Process payment after Razorpay completes
 * @param {Object} response - Razorpay payment response
 * @param {string} planType - The type of plan (basic, premium, etc)
 */
function processPayment(response, planType) {
    // Hide payment modal
    const modal = document.getElementById('payment-modal');
    if (modal) modal.style.display = 'none';
    
    // Send payment data to server for verification
    fetch('/subscription/process-payment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_signature: response.razorpay_signature,
            plan_type: planType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message and reload page
            alert(`Successfully upgraded to ${planType.charAt(0).toUpperCase() + planType.slice(1)} plan!`);
            window.location.reload();
                            } else {
            alert(data.error || 'Payment verification failed. Please contact support.');
        }
    })
    .catch(error => {
        console.error('Payment processing error:', error);
        alert('There was an error processing your payment. Please try again.');
    });
}

// Player Control Functions
function initializePlayer() {
    const progressBar = document.querySelector('.progress-bar');
    const progress = document.querySelector('.progress');
    const progressHandle = document.querySelector('.progress-handle');
    const currentTime = document.querySelector('.current-time');
    const totalTime = document.querySelector('.total-time');
    const playBtn = document.querySelector('.play-btn');
    const volumeBar = document.querySelector('.volume-bar');
    const volumeLevel = document.querySelector('.volume-level');
    const volumeHandle = document.querySelector('.volume-handle');
    
    if (!progressBar || !progress || !currentTime || !totalTime) return;
    
    let audioPlayer = document.getElementById('audio-player');
    let isDraggingProgress = false;
    let isDraggingVolume = false;
    
    // Initialize with saved volume or default to 70%
    const savedVolume = localStorage.getItem('spotifyCloneVolume') || 0.7;
    if (audioPlayer) {
        audioPlayer.volume = savedVolume;
    }
    if (volumeLevel) {
        volumeLevel.style.width = `${savedVolume * 100}%`;
    }
    if (volumeHandle) {
        volumeHandle.style.left = `${savedVolume * 100}%`;
    }
    
    // Play/Pause toggle
    if (playBtn) {
        playBtn.addEventListener('click', () => {
            if (audioPlayer) {
                if (audioPlayer.paused) {
                    audioPlayer.play();
                    playBtn.innerHTML = '<i class="material-icons-round">pause</i>';
                } else {
                    audioPlayer.pause();
                    playBtn.innerHTML = '<i class="material-icons-round">play_arrow</i>';
                    }
                }
            });
    }
    
    // Progress bar click
    if (progressBar) {
        progressBar.addEventListener('mousedown', (e) => {
            if (!audioPlayer) return;
            
            isDraggingProgress = true;
            progressBar.classList.add('dragging');
            updateProgressFromEvent(e);
            
            // Add window-level events for mousemove and mouseup
            window.addEventListener('mousemove', updateProgressDrag);
            window.addEventListener('mouseup', stopProgressDrag);
        });
    }
    
    function updateProgressFromEvent(e) {
        if (!audioPlayer || !progressBar || !progress || !progressHandle) return;
        
        const rect = progressBar.getBoundingClientRect();
        const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
        const percentage = x / rect.width;
        
        // Update progress bar visuals
        progress.style.width = `${percentage * 100}%`;
        progressHandle.style.left = `${percentage * 100}%`;
        
        // Update audio position
        audioPlayer.currentTime = percentage * audioPlayer.duration;
        
        // Update time display
        if (currentTime) {
            currentTime.textContent = formatTime(audioPlayer.currentTime);
        }
    }
    
    function updateProgressDrag(e) {
        if (isDraggingProgress) {
            updateProgressFromEvent(e);
        }
    }
    
    function stopProgressDrag() {
        isDraggingProgress = false;
        if (progressBar) {
            progressBar.classList.remove('dragging');
        }
        window.removeEventListener('mousemove', updateProgressDrag);
        window.removeEventListener('mouseup', stopProgressDrag);
    }
    
    // Volume bar click
    if (volumeBar) {
        volumeBar.addEventListener('mousedown', (e) => {
            isDraggingVolume = true;
            volumeBar.classList.add('dragging');
            updateVolumeFromEvent(e);
            
            // Add window-level events for mousemove and mouseup
            window.addEventListener('mousemove', updateVolumeDrag);
            window.addEventListener('mouseup', stopVolumeDrag);
        });
    }
    
    function updateVolumeFromEvent(e) {
        if (!audioPlayer || !volumeBar || !volumeLevel || !volumeHandle) return;
        
        const rect = volumeBar.getBoundingClientRect();
        const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
        const percentage = x / rect.width;
        
        // Update volume bar visuals
        volumeLevel.style.width = `${percentage * 100}%`;
        volumeHandle.style.left = `${percentage * 100}%`;
        
        // Update audio volume
        audioPlayer.volume = percentage;
        
        // Save to localStorage for persistence
        localStorage.setItem('spotifyCloneVolume', percentage);
    }
    
    function updateVolumeDrag(e) {
        if (isDraggingVolume) {
            updateVolumeFromEvent(e);
        }
    }
    
    function stopVolumeDrag() {
        isDraggingVolume = false;
        if (volumeBar) {
            volumeBar.classList.remove('dragging');
        }
        window.removeEventListener('mousemove', updateVolumeDrag);
        window.removeEventListener('mouseup', stopVolumeDrag);
    }
    
    // Update progress as song plays
    if (audioPlayer) {
        audioPlayer.addEventListener('timeupdate', () => {
            if (!isDraggingProgress && progress && progressHandle) {
                const percentage = audioPlayer.currentTime / audioPlayer.duration;
                progress.style.width = `${percentage * 100}%`;
                progressHandle.style.left = `${percentage * 100}%`;
                
                if (currentTime) {
                    currentTime.textContent = formatTime(audioPlayer.currentTime);
                }
            }
        });
        
        audioPlayer.addEventListener('loadedmetadata', () => {
            if (totalTime) {
                totalTime.textContent = formatTime(audioPlayer.duration);
            }
        });
        
        audioPlayer.addEventListener('ended', () => {
            if (playBtn) {
                playBtn.innerHTML = '<i class="material-icons-round">play_arrow</i>';
            }
            if (progress && progressHandle) {
                progress.style.width = '0%';
                progressHandle.style.left = '0%';
            }
            if (currentTime) {
                currentTime.textContent = '0:00';
            }
        });
    }
}

// Theme Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        // Check for saved theme preference or use device preference
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        // Set initial theme
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        } else if (prefersDark) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
        
        // Toggle theme when button is clicked
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            console.log('Theme switched to:', newTheme);
        });
    } else {
        console.error('Theme toggle button not found');
    }
});

// Run main function when DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
} else {
    main();
}