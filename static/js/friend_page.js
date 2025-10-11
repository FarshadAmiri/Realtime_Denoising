/**
 * Friend page JavaScript for listening to streams and recordings
 */

let webrtcClient = null;
let isListening = false;
let presenceSocket = null;

document.addEventListener('DOMContentLoaded', () => {
    initializePresenceWebSocket();
    checkStreamStatus();
    loadRecordings();
    setupEventListeners();
    
    // Poll stream status every 3 seconds as backup
    setInterval(checkStreamStatus, 3000);
});

function initializePresenceWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/presence/`;
    
    presenceSocket = new WebSocket(wsUrl);
    
    presenceSocket.onopen = () => {
        console.log('Friend page: Presence WebSocket connected');
    };
    
    presenceSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Listen for streaming status updates of the friend we're viewing
        if (data.type === 'streaming_status' && data.username === friendUsername) {
            console.log(`Friend ${friendUsername} streaming status changed: ${data.is_streaming}`);
            checkStreamStatus(); // Immediately update status
        }
    };
    
    presenceSocket.onerror = (error) => {
        console.error('Friend page WebSocket error:', error);
    };
    
    presenceSocket.onclose = () => {
        console.log('Friend page: Presence WebSocket closed');
        // Reconnect after 5 seconds
        setTimeout(initializePresenceWebSocket, 5000);
    };
}

function setupEventListeners() {
    const listenBtn = document.getElementById('listen-btn');
    const stopListenBtn = document.getElementById('stop-listen-btn');
    
    if (listenBtn) {
        listenBtn.addEventListener('click', startListening);
    }
    
    if (stopListenBtn) {
        stopListenBtn.addEventListener('click', stopListening);
    }
}

async function checkStreamStatus() {
    try {
        const response = await fetch(`/api/stream/status/${friendUsername}/`);
        const data = await response.json();
        
        const statusDiv = document.getElementById('stream-status');
        const livePlayerContainer = document.getElementById('live-player-container');
        const notStreamingMessage = document.getElementById('not-streaming-message');
        
        if (data.is_streaming) {
            statusDiv.textContent = `${friendUsername} is currently streaming!`;
            statusDiv.style.color = '#2ecc71';
            livePlayerContainer.style.display = 'block';
            notStreamingMessage.style.display = 'none';
        } else {
            statusDiv.textContent = `${friendUsername} is not currently streaming.`;
            statusDiv.style.color = '#95a5a6';
            livePlayerContainer.style.display = 'none';
            notStreamingMessage.style.display = 'block';
            
            // If we were listening, stop
            if (isListening) {
                stopListening();
            }
        }
    } catch (error) {
        console.error('Error checking stream status:', error);
    }
}

async function startListening() {
    try {
        const audioElement = document.getElementById('live-audio');
        
        webrtcClient = new WebRTCClient();
        await webrtcClient.startListening(friendUsername, audioElement);
        
        isListening = true;
        document.getElementById('listen-btn').style.display = 'none';
        document.getElementById('stop-listen-btn').style.display = 'block';
        
        console.log('Started listening to stream');
        
    } catch (error) {
        console.error('Error starting listening:', error);
        // Retry automatically if stream not yet ready
        if (/Stream not yet ready|processed audio track not initialized/i.test(error.message)) {
            console.log('Retrying listener in 2s...');
            setTimeout(startListening, 2000);
            return;
        }
        alert('Failed to start listening: ' + error.message);
    }
}

function stopListening() {
    if (webrtcClient) {
        webrtcClient.stopListening();
        webrtcClient = null;
    }
    
    isListening = false;
    
    const listenBtn = document.getElementById('listen-btn');
    const stopListenBtn = document.getElementById('stop-listen-btn');
    
    if (listenBtn && stopListenBtn) {
        listenBtn.style.display = 'block';
        stopListenBtn.style.display = 'none';
    }
    
    console.log('Stopped listening to stream');
}

async function loadRecordings() {
    try {
        const response = await fetch(`/api/recordings/${friendUsername}/`);
        
        if (!response.ok) {
            throw new Error('Failed to load recordings');
        }
        
        const recordings = await response.json();
        displayRecordings(recordings);
        
    } catch (error) {
        console.error('Error loading recordings:', error);
        document.getElementById('recordings-list').innerHTML = 
            '<p>Failed to load recordings.</p>';
    }
}

function displayRecordings(recordings) {
    const recordingsList = document.getElementById('recordings-list');
    
    if (recordings.length === 0) {
        recordingsList.innerHTML = '<p>No recordings yet.</p>';
        return;
    }
    
    recordingsList.innerHTML = recordings.map(recording => {
        const date = new Date(recording.created_at);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        
        return `
            <div class="recording-item">
                <h3>${recording.title || 'Untitled Recording'}</h3>
                <div class="recording-meta">
                    Recorded: ${dateStr}
                    ${recording.duration ? ` • Duration: ${Math.round(recording.duration)}s` : ''}
                </div>
                ${recording.file_url ? `
                    <audio controls>
                        <source src="${recording.file_url}" type="audio/wav">
                        Your browser does not support the audio element.
                    </audio>
                ` : '<p>Recording file not available</p>'}
            </div>
        `;
    }).join('');
}
