/**
 * Main page JavaScript for friend list and streaming
 */

let webrtcClient = null;
let presenceSocket = null;
let isStreaming = false; // local session actively broadcasting
let serverStreaming = false; // backend-reported streaming flag
let streamingIndicatorEl = null;
let streamingStatusTextEl = null;
let streamDurationEl = null;
let streamTimerInterval = null;
let streamStartedAt = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializePresenceWebSocket();
    loadFriends();
    loadFriendRequests();
    setupEventListeners();
    // Poll own status in case page refreshed while streaming
    setInterval(syncOwnStreamingStatus, 8000);
    
    // Add beforeunload handler to stop streaming on page close/reload
    window.addEventListener('beforeunload', handlePageUnload);
});

function setupEventListeners() {
    const startBtn = document.getElementById('start-stream-btn');
    const stopBtn = document.getElementById('stop-stream-btn');
    const searchInput = document.getElementById('search-input');
    streamDurationEl = document.getElementById('stream-duration');

    // Create/locate streaming indicator
    streamingIndicatorEl = document.getElementById('streaming-indicator');
    if (!streamingIndicatorEl) {
        const header = document.querySelector('.sidebar-header');
        if (header) {
            streamingIndicatorEl = document.createElement('div');
            streamingIndicatorEl.id = 'streaming-indicator';
            streamingIndicatorEl.style.display = 'none';
            streamingIndicatorEl.className = 'streaming-indicator';
            streamingIndicatorEl.innerHTML = '<span class="dot"></span><span id="streaming-status-text">Streaming now</span>';
            header.appendChild(streamingIndicatorEl);
        }
    }
    streamingStatusTextEl = document.getElementById('streaming-status-text');

    startBtn.addEventListener('click', startStreaming);
    stopBtn.addEventListener('click', stopStreaming);
    
    // Search functionality
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        
        if (query.length > 0) {
            searchTimeout = setTimeout(() => searchUsers(query), 300);
        } else {
            document.getElementById('search-results').classList.remove('show');
        }
    });

    updateStreamingUI();
}

function initializePresenceWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/presence/`;
    
    presenceSocket = new WebSocket(wsUrl);
    
    presenceSocket.onopen = () => {
        console.log('Presence WebSocket connected');
    };
    
    presenceSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'friends_status') {
            updateFriendsStatus(data.friends);
        } else if (data.type === 'streaming_status') {
            updateFriendStatus(data.username, data.is_streaming);
        }
    };
    
    presenceSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    presenceSocket.onclose = () => {
        console.log('Presence WebSocket closed');
        // Reconnect after 5 seconds
        setTimeout(initializePresenceWebSocket, 5000);
    };
}

async function loadFriends() {
    try {
        const response = await fetch('/api/friends/', {
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        const data = await response.json();
        displayFriends(data.friends);
    } catch (error) {
        console.error('Error loading friends:', error);
    }
}

function startStreamTimer() {
    // Ensure we have the element reference
    if (!streamDurationEl) {
        streamDurationEl = document.getElementById('stream-duration');
    }
    if (!streamDurationEl) {
        console.error('stream-duration element not found!');
        return;
    }
    
    streamStartedAt = Date.now();
    console.log('[Timer] Starting stream timer at', new Date(streamStartedAt).toISOString());
    updateStreamDuration();
    if (streamTimerInterval) {
        clearInterval(streamTimerInterval);
    }
    streamTimerInterval = setInterval(updateStreamDuration, 1000);
}

function updateStreamDuration() {
    if (!streamDurationEl) {
        streamDurationEl = document.getElementById('stream-duration');
    }
    if (!streamDurationEl || streamStartedAt === null) {
        return;
    }
    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - streamStartedAt) / 1000));
    const formattedTime = formatDuration(elapsedSeconds);
    streamDurationEl.textContent = formattedTime;
    console.log(`[Timer] Updated duration: ${formattedTime} (${elapsedSeconds}s)`);
}

function stopStreamTimer() {
    if (streamTimerInterval) {
        clearInterval(streamTimerInterval);
        streamTimerInterval = null;
    }
    streamStartedAt = null;
    if (streamDurationEl) {
        streamDurationEl.textContent = '00:00';
    }
}

function formatDuration(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const parts = [];
    if (hours > 0) {
        parts.push(hours.toString().padStart(2, '0'));
    }
    parts.push(minutes.toString().padStart(2, '0'));
    parts.push(seconds.toString().padStart(2, '0'));
    return parts.join(':');
}

function displayFriends(friends) {
    const friendsList = document.getElementById('friends-list');
    
    if (friends.length === 0) {
        friendsList.innerHTML = '<p style="color: #95a5a6;">No friends yet. Search and add some!</p>';
        return;
    }
    
    friendsList.innerHTML = friends.map(friend => `
        <div class="friend-item" data-username="${friend.username}" onclick="goToFriendPage('${friend.username}')">
            <div class="friend-name">${friend.username}</div>
            <div class="friend-status ${friend.is_streaming ? 'streaming' : ''}" id="status-${friend.username}">
                ${friend.is_streaming ? 'Streaming' : 'Offline'}
            </div>
        </div>
    `).join('');
}

function updateFriendsStatus(friends) {
    friends.forEach(friend => {
        updateFriendStatus(friend.username, friend.is_streaming);
    });
}

function updateFriendStatus(username, isStreamingRemote) {
    const statusElement = document.getElementById(`status-${username}`);
    if (statusElement) {
        statusElement.textContent = isStreamingRemote ? 'Streaming' : 'Offline';
        statusElement.classList.toggle('streaming', isStreamingRemote);
    }

    // If this refers to the current user, treat it as backend status update
    if (username === usernameGlobalSafe()) {
        const changed = serverStreaming !== isStreamingRemote;
        serverStreaming = isStreamingRemote;
        if (!serverStreaming && isStreaming) {
            // Backend reports stream stopped; align local state
            isStreaming = false;
            stopStreamTimer();
        }
        if (changed) {
            updateStreamingUI();
        }
    }
}

function usernameGlobalSafe() { return typeof username !== 'undefined' ? username : null; }

async function syncOwnStreamingStatus() {
    const me = usernameGlobalSafe();
    if (!me) return;
    try {
        const resp = await fetch(`/api/stream/status/${me}/`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (typeof data.is_streaming === 'boolean') {
            const backendStatus = data.is_streaming;
            if (!backendStatus && (isStreaming || serverStreaming)) {
                isStreaming = false;
                serverStreaming = false;
                stopStreamTimer();
                updateStreamingUI();
            } else if (backendStatus !== serverStreaming) {
                serverStreaming = backendStatus;
                updateStreamingUI();
            }
        }
    } catch (e) { /* ignore transient */ }
}

function goToFriendPage(username) {
    window.location.href = `/friend/${username}/`;
}

async function searchUsers(query) {
    try {
        const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        const data = await response.json();
        displaySearchResults(data.users);
    } catch (error) {
        console.error('Error searching users:', error);
    }
}

function displaySearchResults(users) {
    const resultsContainer = document.getElementById('search-results');
    
    if (users.length === 0) {
        resultsContainer.innerHTML = '<div class="search-result-item">No users found</div>';
    } else {
        resultsContainer.innerHTML = users.map(user => `
            <div class="search-result-item">
                <span>${user.username}</span>
                <button class="btn btn-sm btn-primary" onclick="sendFriendRequest('${user.username}')">Add Friend</button>
            </div>
        `).join('');
    }
    
    resultsContainer.classList.add('show');
}

async function sendFriendRequest(username) {
    try {
        const response = await fetch('/api/friend-request/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ username })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Friend request sent!');
            document.getElementById('search-results').classList.remove('show');
            document.getElementById('search-input').value = '';
        } else {
            alert(data.error || 'Failed to send friend request');
        }
    } catch (error) {
        console.error('Error sending friend request:', error);
        alert('Failed to send friend request');
    }
}

async function loadFriendRequests() {
    try {
        const response = await fetch('/api/friend-requests/pending/', {
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        const data = await response.json();
        displayFriendRequests(data.received);
    } catch (error) {
        console.error('Error loading friend requests:', error);
    }
}

function displayFriendRequests(requests) {
    const requestsList = document.getElementById('friend-requests-list');
    
    if (requests.length === 0) {
        requestsList.innerHTML = '<p style="color: #95a5a6;">No pending requests</p>';
        return;
    }
    
    requestsList.innerHTML = requests.map(req => `
        <div class="friend-request-item">
            <div><strong>${req.from_user}</strong> wants to be friends</div>
            <div class="request-actions">
                <button class="btn btn-sm btn-success" onclick="respondToRequest(${req.id}, 'accept')">Accept</button>
                <button class="btn btn-sm btn-danger" onclick="respondToRequest(${req.id}, 'reject')">Reject</button>
            </div>
        </div>
    `).join('');
}

async function respondToRequest(requestId, action) {
    try {
        const response = await fetch(`/api/friend-request/${requestId}/respond/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ action })
        });
        
        if (response.ok) {
            loadFriendRequests();
            loadFriends();
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to respond to request');
        }
    } catch (error) {
        console.error('Error responding to request:', error);
        alert('Failed to respond to request');
    }
}

async function startStreaming() {
    try {
        console.log('[Streaming] Initiating start');
        // 1. Tell backend to mark stream active (session created)
        const response = await fetch('/api/stream/start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to start stream');
        }

        // 2. Optimistic UI update (so user sees immediate feedback)
        isStreaming = true;
        serverStreaming = true;
        updateStreamingUI();

        // 3. Start WebRTC broadcast (might still fail; handle rollback)
        webrtcClient = new WebRTCClient();
        await webrtcClient.startBroadcast();
        console.log('[Streaming] WebRTC broadcast established');

        // 4. Begin timer display
        startStreamTimer();
        
        // 5. Optionally force refresh of own status display
        syncOwnStreamingStatus();
        
    } catch (error) {
        console.error('Error starting stream:', error);
        alert('Failed to start streaming: ' + error.message);
        // Rollback UI if we set streaming optimistically
        if (isStreaming || serverStreaming) {
            isStreaming = false;
            serverStreaming = false;
            updateStreamingUI();
        }
        stopStreamTimer();
        // Inform backend if session was created but we failed after (best effort)
        try { if (webrtcClient) { webrtcClient.stopBroadcast(); } } catch (_) {}
        try {
            await fetch('/api/stream/stop/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
        } catch (_) { /* swallow */ }
    }
}

async function stopStreaming() {
    try {
        // Stop WebRTC
        if (webrtcClient) {
            webrtcClient.stopBroadcast();
            webrtcClient = null;
        }
        
        // Stop stream on server
        const response = await fetch('/api/stream/stop/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        
        if (!response.ok) {
            const data = await response.json();
            console.error('Error stopping stream:', data.error);
        }

        isStreaming = false;
        serverStreaming = false;
        updateStreamingUI();
        stopStreamTimer();
        console.log('Streaming stopped');
        
    } catch (error) {
        console.error('Error stopping stream:', error);
        alert('Failed to stop streaming: ' + error.message);
    }
}

function handlePageUnload(event) {
    // Stop streaming if active when user navigates away or closes page
    if (isStreaming || serverStreaming) {
        // Use navigator.sendBeacon for reliable async request during unload
        const stopUrl = '/api/stream/stop/';
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', csrfToken);
        
        // Try sendBeacon first (best for unload events)
        const beaconSent = navigator.sendBeacon(stopUrl, formData);
        
        if (!beaconSent) {
            // Fallback: synchronous XHR (works but not recommended)
            const xhr = new XMLHttpRequest();
            xhr.open('POST', stopUrl, false); // false = synchronous
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
            try {
                xhr.send(formData);
            } catch (e) {
                console.error('Failed to stop stream on unload:', e);
            }
        }
        
        // Clean up WebRTC locally
        if (webrtcClient) {
            webrtcClient.stopBroadcast();
        }
    }
}

function updateStreamingUI() {
    const startBtn = document.getElementById('start-stream-btn');
    const stopBtn = document.getElementById('stop-stream-btn');
    if (!startBtn || !stopBtn) return;
    const stopLabelEl = stopBtn.querySelector('.stop-label');

    if (isStreaming) {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'flex';
        if (stopLabelEl) stopLabelEl.textContent = 'Stop Streaming';
    } else if (serverStreaming) {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'flex';
        if (stopLabelEl) stopLabelEl.textContent = 'Stop Remote Stream';
        stopStreamTimer();
        if (streamDurationEl) {
            streamDurationEl.textContent = '--:--';
        }
    } else {
        startBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
        if (stopLabelEl) stopLabelEl.textContent = 'Stop Streaming';
        if (!serverStreaming) {
            stopStreamTimer();
        }
    }

    if (streamingIndicatorEl) {
        if (serverStreaming) {
            streamingIndicatorEl.style.display = 'flex';
            if (streamingStatusTextEl) {
                streamingStatusTextEl.textContent = isStreaming ? 'Streaming now' : 'Streaming active on another device';
                streamingStatusTextEl.classList.toggle('status-text-alt', !isStreaming);
            }
        } else {
            streamingIndicatorEl.style.display = 'none';
        }
    }
}
