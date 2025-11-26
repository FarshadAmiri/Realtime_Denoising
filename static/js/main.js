let presenceSocket = null;
let selectedUsername = null;
let isOwnerView = false;
let peerConnection = null;
let localStream = null;
let startTime = null;
let timerInterval = null;
const currentUser = window.CURRENT_USER || ""; // Set from Django template in main.html
let browserAudioProcessing = true; // will be set after cfg JSON is loaded in the next script
const currentOnlineCache = new Map();

// Audio visualizer variables
let audioContext = null;
let analyser = null;
let dataArray = null;
let animationFrameId = null;

// Load selection history from localStorage (persistent across sessions)
let selectionHistory = [];
try {
    const stored = localStorage.getItem('selectionHistory_' + currentUser);
    if (stored) {
        selectionHistory = JSON.parse(stored);
    }
} catch (e) {
    console.warn('Failed to load selection history:', e);
}

function connectPresence() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    presenceSocket = new WebSocket(proto + '//' + location.host + '/ws/presence/');
    presenceSocket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'streaming_status_update') {
            updateSidebarStreaming(data.username, data.is_streaming);
            if (data.username === selectedUsername) {
                updateLivePill({active: data.is_streaming, online: (data.is_streaming ? true : currentOnlineCache.get(data.username) || false)});
                // Update listener controls visibility based on streaming status
                if (!isOwnerView) {
                    updateListenerControlsVisibility(data.is_streaming);
                }
            }
        } else if (data.type === 'online_status_update') {
            currentOnlineCache.set(data.username, data.is_online);
            // If not streaming, update sidebar to show online/offline
            const meta = document.querySelector(`.friend-item[data-username="${data.username}"] .friend-meta`);
            if (meta && !meta.innerHTML.includes('Streaming')) {
                meta.innerHTML = data.is_online ? `<span class="dot online-dot"></span> Online` : `<span class="dot offline-dot"></span> Offline`;
            }
            if (data.username === selectedUsername && !isOwnerView) {
                updateLivePill({active: false, online: data.is_online});
            }
        } else if (data.type === 'stream_ended') {
            // If listener is watching this stream, show message and stop
            console.log('[WebSocket] Stream ended event received:', data.username, 'selectedUsername:', selectedUsername, 'isOwnerView:', isOwnerView, 'peerConnection:', !!peerConnection);
            if (data.username === selectedUsername && !isOwnerView) {
                console.log('[WebSocket] Handling stream end for listener');
                document.getElementById('listen-status').textContent = 'Stream ended. Loading recording...';
                document.getElementById('listen-status').style.color = '#ef4444';
                
                // Stop listening if currently listening
                if (peerConnection) {
                    stopListening();
                }
                
                // Refresh recordings to show the newly saved recording
                // Wait a bit longer to ensure backend has saved the recording
                setTimeout(() => {
                    console.log('[WebSocket] Refreshing recordings after stream end');
                    document.getElementById('listen-status').textContent = '';
                    document.getElementById('listen-status').style.color = '';
                    refreshRecordings();
                }, 2000);
            }
        } else if (data.type === 'recording_saved') {
            // If viewing this user's page, add new recording without refresh
            if (data.username === selectedUsername && data.recording) {
                addRecordingToList(data.recording);
            }
        }
    };
    presenceSocket.onclose = () => setTimeout(connectPresence, 2000);
}

function updateSidebarStreaming(username, isStreaming){
    const meta = document.querySelector(`.friend-item[data-username="${username}"] .friend-meta`);
    if(!meta) return;
    if(isStreaming){ meta.innerHTML = `<span class="dot live-dot"></span> Streaming`; }
    else {
        // fallback to online cache or offline
        const online = currentOnlineCache.get(username) || false;
        meta.innerHTML = online ? `<span class="dot online-dot"></span> Online` : `<span class="dot offline-dot"></span> Offline`;
    }
}

function updateListenerControlsVisibility(isStreaming) {
    const listenBtn = document.getElementById('listen-btn');
    const listenStatus = document.getElementById('listen-status');
    if (isStreaming) {
        listenBtn.style.display = 'inline-block';
        if (listenStatus.textContent.includes('not streaming')) {
            listenStatus.textContent = '';
        }
    } else {
        listenBtn.style.display = 'none';
        if (!peerConnection) {
            listenStatus.textContent = 'User is not currently streaming.';
            listenStatus.style.color = '#6b7280';
            listenStatus.style.fontWeight = 600;
        }
    }
}

function addRecordingToList(recording) {
    const list = document.getElementById('recordings-list');
    const empty = document.getElementById('no-recordings');
    empty.style.display = 'none';
    
    const item = document.createElement('div');
    item.className = 'recording-item';
    const left = document.createElement('div');
    const title = document.createElement('div');
    title.className = 'recording-title';
    title.textContent = recording.title || 'Recording';
    const meta = document.createElement('div');
    meta.className = 'muted';
    meta.textContent = (recording.duration ? `Duration: ${recording.duration}s | ` : '') + (recording.created_at ? new Date(recording.created_at).toLocaleString() : '');
    left.appendChild(title);
    left.appendChild(meta);
    const right = document.createElement('div');
    if (recording.file_url) {
        const audio = document.createElement('audio');
        audio.controls = true;
        audio.preload = 'none';
        const src = document.createElement('source');
        src.src = recording.file_url;
        src.type = 'audio/wav';
        audio.appendChild(src);
        right.appendChild(audio);
    } else {
        right.textContent = 'No file';
        right.className = 'muted';
    }
    item.appendChild(left);
    item.appendChild(right);
    // Insert at the top (newest first)
    list.insertBefore(item, list.firstChild);
}

function updateSidebarTri(username, flags){
    const meta = document.querySelector(`.friend-item[data-username="${username}"] .friend-meta`);
    if(!meta) {
        console.log(`[updateSidebarTri] No meta element found for ${username}`);
        return;
    }
    let newHTML;
    if(flags.active){ 
        newHTML = `<span class="dot live-dot"></span> Streaming`;
    } else if(flags.online){ 
        newHTML = `<span class="dot online-dot"></span> Online`;
    } else { 
        newHTML = `<span class="dot offline-dot"></span> Offline`;
    }
    if (meta.innerHTML !== newHTML) {
        console.log(`[updateSidebarTri] Updating ${username}: active=${flags.active}, online=${flags.online}`);
        meta.innerHTML = newHTML;
    }
}

function updateLivePill(flags){
    const pill = document.getElementById('live-pill');
    if(flags.active){ pill.className = 'pill pill-live'; pill.textContent = 'Streaming ⏺'; }
    else if(flags.online){ pill.className = 'pill pill-online'; pill.textContent = 'Online'; }
    else { pill.className = 'pill pill-off'; pill.textContent = 'Offline'; }
}

function selectEntry(username, isSelf){
    // Prevent navigation if currently broadcasting
    if (localStream && !isSelf) {
        alert('Please stop your stream before navigating to another page.');
        return;
    }
    
    // Auto-stop listening when switching pages
    if (peerConnection && !isOwnerView) {
        stopListening();
    }
    
    // Update selection history (move to front if exists, otherwise add to front)
    const historyIndex = selectionHistory.indexOf(username);
    if (historyIndex > -1) {
        selectionHistory.splice(historyIndex, 1);
    }
    selectionHistory.unshift(username);
    // Keep only last 50 selections to avoid memory issues
    if (selectionHistory.length > 50) {
        selectionHistory = selectionHistory.slice(0, 50);
    }
    
    // Save to localStorage for persistence across sessions
    try {
        localStorage.setItem('selectionHistory_' + currentUser, JSON.stringify(selectionHistory));
    } catch (e) {
        console.warn('Failed to save selection history:', e);
    }
    
    selectedUsername = username;
    isOwnerView = isSelf;
    
    // Remove active class from all items (including "Your Profile")
    document.querySelectorAll('.friend-item').forEach(i => i.classList.remove('active'));
    
    // Apply active state to selected item (do NOT refresh the list to maintain order during session)
    document.querySelector(`.friend-item[data-username="${username}"]`)?.classList.add('active');
    
    document.getElementById('content-title').textContent = username;
    document.getElementById('content-sub').textContent = isSelf ? 'Manage your stream and recordings' : 'Listen live and browse recordings';
    document.getElementById('owner-controls').style.display = isSelf ? 'block' : 'none';
    document.getElementById('listener-controls').style.display = isSelf ? 'none' : 'block';
    cleanupPeer();
    refreshRecordings();
    // Live pill initial state via REST and update listener controls
    fetch(`/api/stream/status/${encodeURIComponent(username)}/`, { credentials: 'same-origin' })
        .then(r=>r.json()).then(j=>{ 
            currentOnlineCache.set(username, !!j.online); 
            updateLivePill({active: !!j.active, online: !!j.online}); 
            updateSidebarTri(username, {active: !!j.active, online: !!j.online}); 
            // For listener view, hide/show controls based on streaming status
            if (!isSelf) {
                updateListenerControlsVisibility(!!j.active);
            }
        });
}

function cleanupPeer(){
    try{ if(peerConnection){ peerConnection.getSenders().forEach(s=>s.track&&s.track.stop()); peerConnection.close(); } }catch(e){}
    peerConnection=null; localStream=null; stopTimer();
    document.getElementById('remote-audio').style.display='none';
    document.getElementById('listen-status').textContent='';
}

function getCookie(name){
    const m = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : null;
}

async function startStream(){
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const denoiseToggle = document.getElementById('denoise-toggle');
    const denoiseBtn = document.getElementById('denoise-btn');
    const statusEl = document.getElementById('stream-status');
    
    try{
        statusEl.textContent = 'Starting stream...';
        const denoise = denoiseToggle.checked;
        
        const resp = await fetch('/api/stream/start/', {
            method:'POST', 
            headers:{
                'Content-Type':'application/json',
                'X-CSRFToken':getCookie('csrftoken')
            }, 
            body: JSON.stringify({denoise})
        });
        if(!resp.ok) throw new Error('Failed to start stream');
        
        localStream = await navigator.mediaDevices.getUserMedia({
            audio:{
                channelCount:{ideal:1}, 
                sampleRate:{ideal:48000}, 
                echoCancellation:browserAudioProcessing, 
                noiseSuppression:browserAudioProcessing, 
                autoGainControl:browserAudioProcessing
            }, 
            video:false
        });
        
        peerConnection = new RTCPeerConnection({ iceServers:[{urls:'stun:stun.l.google.com:19302'}] });
        localStream.getTracks().forEach(t=>{ 
            const s=peerConnection.addTrack(t, localStream); 
            try{ 
                const p=s.getParameters(); 
                if(!p.encodings)p.encodings=[{}]; 
                p.encodings[0].maxBitrate=192000; 
                s.setParameters(p);
            }catch(e){} 
        });
        
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        await waitForIceGathering(peerConnection);
        
        const offerResp = await fetch('/api/stream/offer/', {
            method:'POST', 
            headers:{
                'Content-Type':'application/json',
                'X-CSRFToken':getCookie('csrftoken')
            }, 
            body: JSON.stringify({ sdp: peerConnection.localDescription.sdp })
        });
        if(!offerResp.ok) throw new Error('Failed to negotiate');
        
        const answer = await offerResp.json();
        await peerConnection.setRemoteDescription({type:'answer', sdp:answer.sdp});
        
        // Update UI - stream started successfully
        if(startBtn) startBtn.style.display = 'none';
        if(stopBtn) stopBtn.style.display = 'inline-block';
        
        // Show sound wave and start real-time visualizer
        const soundWave = document.getElementById('sound-wave');
        if(soundWave) soundWave.style.display = 'flex';
        startAudioVisualizer(localStream);
        
        // Hide denoise button and show status label
        if(denoiseBtn) denoiseBtn.style.display = 'none';
        const denoiseStatus = document.getElementById('denoise-status');
        if(denoiseStatus) {
            const isDenoiseOn = denoiseToggle && denoiseToggle.checked;
            denoiseStatus.textContent = isDenoiseOn ? '✓ Denoise: ON' : '✗ Denoise: OFF';
            denoiseStatus.style.background = isDenoiseOn ? '#10b981' : '#6b7280';
            denoiseStatus.style.display = 'inline-block';
        }
        
        statusEl.textContent = 'Streaming...';
        startTimer();
        
    }catch(e){ 
        statusEl.textContent = 'Error: ' + e.message;
        
        // Reset UI on error
        if(startBtn) startBtn.style.display = 'inline-flex';
        if(stopBtn) stopBtn.style.display = 'none';
        const soundWave = document.getElementById('sound-wave');
        if(soundWave) soundWave.style.display = 'none';
        stopAudioVisualizer();
        
        // Hide denoise status and show button again
        const denoiseStatus = document.getElementById('denoise-status');
        if(denoiseStatus) denoiseStatus.style.display = 'none';
        if(denoiseBtn) denoiseBtn.style.display = 'inline-block';
        
        if(denoiseToggle) denoiseToggle.disabled = false;
        if(denoiseBtn) denoiseBtn.disabled = false;
        
        // Clean up on error
        if(peerConnection) {
            try { peerConnection.close(); } catch(err) {}
            peerConnection = null;
        }
        if(localStream) {
            try { localStream.getTracks().forEach(t => t.stop()); } catch(err) {}
            localStream = null;
        }
    }
}

async function stopStream(){
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const denoiseToggle = document.getElementById('denoise-toggle');
    const denoiseBtn = document.getElementById('denoise-btn');
    const statusEl = document.getElementById('stream-status');
    
    // Prevent double-clicking
    if(stopBtn && stopBtn.disabled) {
        console.log('Stop button already disabled, ignoring click');
        return;
    }
    if(stopBtn) stopBtn.disabled = true;
    
    // Function to reset UI
    function resetUI(message) {
        console.log('Resetting UI:', message);
        if(startBtn) startBtn.style.display = 'inline-flex';
        if(stopBtn) {
            stopBtn.style.display = 'none';
            stopBtn.disabled = false;
        }
        
        // Hide sound wave animation and stop visualizer
        const soundWave = document.getElementById('sound-wave');
        if(soundWave) soundWave.style.display = 'none';
        stopAudioVisualizer();
        
        // Hide denoise status and show button again
        const denoiseStatus = document.getElementById('denoise-status');
        if(denoiseStatus) denoiseStatus.style.display = 'none';
        if(denoiseBtn) denoiseBtn.style.display = 'inline-block';
        
        if(denoiseToggle) denoiseToggle.disabled = false;
        if(denoiseBtn) denoiseBtn.disabled = false;
        
        // Reset stop-timer after save is complete
        const stopTimerEl = document.getElementById('stop-timer');
        if(stopTimerEl) stopTimerEl.textContent = '00:00';
        
        if(statusEl) statusEl.textContent = message || 'Stream stopped.';
    }
    
    try{
        console.log('[stopStream] Starting stop process...');
        if(statusEl) statusEl.textContent = 'Stopping stream...';
        
        // Cleanup peer connection and streams FIRST
        console.log('[stopStream] Cleaning up peer connection and streams...');
        if(peerConnection){
            try{ 
                peerConnection.getSenders().forEach(s => {
                    if(s.track) s.track.stop();
                });
                peerConnection.close(); 
            }catch(e){
                console.error('[stopStream] Error closing peer connection:', e);
            }
        }
        
        if(localStream){
            try{
                localStream.getTracks().forEach(track => track.stop());
            }catch(e){
                console.error('[stopStream] Error stopping tracks:', e);
            }
        }
        
        peerConnection = null;
        localStream = null;
        stopTimer();
        console.log('[stopStream] Cleanup complete');
        
        // Send stop request with timeout
        console.log('[stopStream] Sending stop request to backend...');
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        try {
            const resp = await fetch('/api/stream/stop/', {
                method: 'POST', 
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }, 
                body: JSON.stringify({}),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            console.log('[stopStream] Stop response status:', resp.status);
            if(!resp.ok){
                const errorText = await resp.text();
                console.error('[stopStream] Stop failed:', errorText);
                // Don't throw - just log and continue with UI update
            } else {
                console.log('[stopStream] Backend acknowledged stop successfully');
            }
        } catch(fetchError) {
            clearTimeout(timeoutId);
            if(fetchError.name === 'AbortError') {
                console.warn('[stopStream] Stop request timed out - continuing with UI update');
            } else {
                console.error('[stopStream] Fetch error:', fetchError);
            }
            // Don't throw - continue with UI update
        }
        
        console.log('[stopStream] Resetting UI...');
        resetUI('Stream stopped.');
        
        console.log('[stopStream] Refreshing recordings...');
        try {
            await refreshRecordings();
            console.log('[stopStream] Recordings refreshed successfully');
        } catch(refreshError) {
            console.error('[stopStream] Failed to refresh recordings:', refreshError);
            // Don't fail the whole operation if refresh fails
        }
        
        console.log('[stopStream] Stop process complete!');
        
    }catch(e){ 
        console.error('[stopStream] Error in stopStream:', e);
        resetUI('Error: ' + e.message);
    }
}

async function startListening(){
    try{
        document.getElementById('listen-status').textContent='Connecting...';
        document.getElementById('listen-btn').style.display='none';
        document.getElementById('stop-listen-btn').style.display='inline-block';
        peerConnection = new RTCPeerConnection({ iceServers:[{urls:'stun:stun.l.google.com:19302'}] });
        const remoteAudio = document.getElementById('remote-audio');
        peerConnection.addEventListener('track', (ev)=>{ if(remoteAudio.srcObject!==ev.streams[0]){ remoteAudio.srcObject = ev.streams[0]; remoteAudio.style.display='block'; const p=remoteAudio.play(); if(p&&p.catch) p.catch(()=>{});} });
        peerConnection.addTransceiver('audio', { direction:'recvonly' });
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        await waitForIceGathering(peerConnection);
        const resp = await fetch(`/api/stream/listener/${encodeURIComponent(selectedUsername)}/offer/`, {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: JSON.stringify({ sdp: peerConnection.localDescription.sdp })});
        if(!resp.ok) throw new Error('Failed to negotiate listen connection');
        const answer = await resp.json();
        await peerConnection.setRemoteDescription({ type:'answer', sdp: answer.sdp });
        document.getElementById('listen-status').textContent='Listening to live stream...';
    }catch(e){ document.getElementById('listen-status').textContent='Error: '+e.message; }
}

function stopListening(){ cleanupPeer(); document.getElementById('listen-btn').style.display='inline-block'; document.getElementById('stop-listen-btn').style.display='none'; }

function waitForIceGathering(pc) { 
    return new Promise(res => { 
        if (pc.iceGatheringState === 'complete') {
            res(); 
        } else { 
            // Set a timeout to resolve after 3 seconds even if ICE gathering isn't complete
            const timeout = setTimeout(() => {
                console.log('[ICE] Gathering timeout reached (3s), proceeding anyway');
                pc.removeEventListener('icegatheringstatechange', fn);
                res();
            }, 3000);
            
            const fn = () => { 
                if (pc.iceGatheringState === 'complete') { 
                    clearTimeout(timeout);
                    pc.removeEventListener('icegatheringstatechange', fn); 
                    res(); 
                } 
            }; 
            pc.addEventListener('icegatheringstatechange', fn);
        } 
    }); 
}

function startTimer(){ 
    startTime=Date.now(); 
    timerInterval=setInterval(()=>{ 
        const el=Math.floor((Date.now()-startTime)/1000); 
        const m=String(Math.floor(el/60)).padStart(2,'0'); 
        const s=String(el%60).padStart(2,'0'); 
        const timeStr = `${m}:${s}`;
        const stopTimerEl = document.getElementById('stop-timer');
        if(stopTimerEl) stopTimerEl.textContent = timeStr;
    }, 1000); 
}

function stopTimer(){ 
    if(timerInterval){ 
        clearInterval(timerInterval); 
        timerInterval=null; 
    } 
    // Don't reset the stop-timer here - keep it showing the recorded time
    // It will be reset in resetUI() after file saves
}

// Audio visualizer functions
function startAudioVisualizer(stream) {
    try {
        // Create audio context and analyser
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        
        // Configure analyser
        analyser.fftSize = 128; // Larger size for 45 bars (gives 64 frequency bins)
        analyser.smoothingTimeConstant = 0.8;
        source.connect(analyser);
        
        const bufferLength = analyser.frequencyBinCount;
        dataArray = new Uint8Array(bufferLength);
        
        // Start animation loop
        animateVisualizer();
    } catch (e) {
        console.error('Failed to start audio visualizer:', e);
    }
}

function animateVisualizer() {
    animationFrameId = requestAnimationFrame(animateVisualizer);
    
    if (!analyser || !dataArray) return;
    
    // Get frequency data
    analyser.getByteFrequencyData(dataArray);
    
    // Update the 45 bars
    const bars = document.querySelectorAll('.sound-wave .bar');
    if (bars.length !== 45) return;
    
    // Map frequency data to 45 bars (we have more data points than bars)
    const dataPerBar = Math.floor(dataArray.length / 45);
    
    bars.forEach((bar, i) => {
        // Get average for this bar's frequency range
        let sum = 0;
        const start = i * dataPerBar;
        const end = start + dataPerBar;
        for (let j = start; j < end && j < dataArray.length; j++) {
            sum += dataArray[j];
        }
        const average = sum / dataPerBar;
        
        // Normalize to 0-1 range (0-255 -> 0-1)
        const normalizedHeight = average / 255;
        
        // Set minimum height of 0.2 so bars are always visible
        const height = Math.max(0.2, normalizedHeight);
        
        // Apply scale transform
        bar.style.transform = `scaleY(${height})`;
    });
}

function stopAudioVisualizer() {
    // Stop animation
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }
    
    // Close audio context
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    
    analyser = null;
    dataArray = null;
    
    // Reset bars to default state
    const bars = document.querySelectorAll('.sound-wave .bar');
    bars.forEach(bar => {
        bar.style.transform = 'scaleY(0.3)';
    });
}

async function refreshRecordings(){
    console.log('[refreshRecordings] Starting to refresh recordings list...');
    const list = document.getElementById('recordings-list');
    const empty = document.getElementById('no-recordings');
    
    if(!list || !empty) {
        console.warn('[refreshRecordings] Required DOM elements not found');
        return;
    }
    
    list.innerHTML=''; 
    empty.style.display='none';
    
    if(!selectedUsername){
        // ensure selection; default to current user
        selectedUsername = currentUser;
    }
    
    console.log('[refreshRecordings] Fetching recordings for:', selectedUsername);
    const url = `/api/recordings/${encodeURIComponent(selectedUsername)}/`;
    
    try {
        // Add timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout
        
        const resp = await fetch(url, { 
            credentials: 'same-origin',
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        console.log('[refreshRecordings] Response status:', resp.status);
        
        if(!resp.ok){ 
            empty.textContent='Unable to load recordings'; 
            empty.style.display='block'; 
            console.error('[refreshRecordings] Fetch failed', resp.status); 
            return; 
        }
        
        const data = await resp.json();
        const recs = Array.isArray(data) ? data : (data.results || []);
        console.log('[refreshRecordings] Received', recs.length, 'recordings');
        
        if(!recs.length){ 
            empty.style.display='block'; 
            console.log('[refreshRecordings] No recordings to display');
            return; 
        }
        
        for(const r of recs){
            const item = document.createElement('div'); item.className='recording-item'; item.dataset.recordingId = r.id;
            
            // Action buttons for owner's recordings (positioned absolutely in top-right)
            if(r.owner_username === currentUser){
                const actions = document.createElement('div'); actions.className='recording-actions';
                const deleteBtn = document.createElement('button'); deleteBtn.className='recording-action-btn delete'; deleteBtn.innerHTML='❌'; deleteBtn.title='Delete'; deleteBtn.onclick = () => showDeleteModal(r.id, r.title);
                actions.appendChild(deleteBtn);
                item.appendChild(actions);
            }
            
            const left = document.createElement('div');
            const titleWrapper = document.createElement('div'); titleWrapper.className='recording-title-wrapper';
            const title = document.createElement('div'); title.className='recording-title'; title.textContent = r.title || 'Recording';
            
            // Add double-click to rename for owner's recordings
            if(r.owner_username === currentUser){
                title.style.cursor = 'pointer';
                title.title = 'Double-click to rename';
                title.ondblclick = () => startRenameRecording(r.id, item);
            }
            
            const meta = document.createElement('div'); meta.className='muted'; meta.textContent = (r.duration?`Duration: ${r.duration}s | `:'') + (r.created_at? new Date(r.created_at).toLocaleString() : '');
            titleWrapper.appendChild(title); titleWrapper.appendChild(meta);
            left.appendChild(titleWrapper);
            
            const right = document.createElement('div');
            if(r.file_url){ const audio = document.createElement('audio'); audio.controls=true; audio.preload='none'; audio.dataset.recordingId=r.id; const src=document.createElement('source'); src.src=r.file_url; src.type='audio/wav'; audio.appendChild(src); right.appendChild(audio); } else { right.textContent='No file'; right.className='muted'; }
            item.appendChild(left); item.appendChild(right); list.appendChild(item);
        }
        console.log('[refreshRecordings] Successfully rendered', recs.length, 'recordings');
        
    } catch(err) {
        console.error('[refreshRecordings] Error:', err);
        if(err.name === 'AbortError') {
            empty.textContent='Request timed out - please try again';
        } else {
            empty.textContent='Unable to load recordings';
        }
        empty.style.display='block';
    }
}

// Recording management functions
function showDeleteModal(recordingId, recordingTitle) {
    console.log('[showDeleteModal] Showing delete modal for:', recordingId, recordingTitle);
    
    // Check if any audio element with this recording is currently playing
    const audioElements = document.querySelectorAll(`audio[data-recording-id="${recordingId}"]`);
    for(const audio of audioElements) {
        if(!audio.paused) {
            showModernAlert('⚠️', 'Cannot Delete', 'This recording is currently playing. Please stop it before deleting.');
            console.warn('[showDeleteModal] Recording is playing, cannot delete');
            return;
        }
    }
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'delete-modal-overlay';
    
    const modal = document.createElement('div');
    modal.className = 'delete-modal';
    
    modal.innerHTML = `
        <div class="delete-modal-header">
            <div class="delete-modal-icon">🗑️</div>
            <h3 class="delete-modal-title">Delete Recording</h3>
        </div>
        <div class="delete-modal-body">
            Are you sure you want to delete <span class="delete-modal-recording-name">"${recordingTitle}"</span>? This action cannot be undone.
        </div>
        <div class="delete-modal-actions">
            <button class="delete-modal-btn cancel">Cancel</button>
            <button class="delete-modal-btn delete">Delete</button>
        </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Cancel button
    const cancelBtn = modal.querySelector('.cancel');
    cancelBtn.onclick = () => {
        overlay.remove();
        console.log('[showDeleteModal] User cancelled deletion');
    };
    
    // Delete button
    const deleteBtn = modal.querySelector('.delete');
    deleteBtn.onclick = () => {
        overlay.remove();
        deleteRecording(recordingId);
    };
    
    // Click outside to close
    overlay.onclick = (e) => {
        if(e.target === overlay) {
            overlay.remove();
            console.log('[showDeleteModal] User clicked outside, cancelled deletion');
        }
    };
}

async function deleteRecording(recordingId) {
    console.log('[deleteRecording] Deleting recording:', recordingId);
    
    try {
        const resp = await fetch(`/api/recordings/${recordingId}/delete/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
            credentials: 'same-origin',
        });
        
        console.log('[deleteRecording] Response status:', resp.status);
        
        if(resp.ok) {
            console.log('[deleteRecording] Successfully deleted recording');
            // Remove the item from DOM
            const item = document.querySelector(`.recording-item[data-recording-id="${recordingId}"]`);
            if(item) {
                item.remove();
                console.log('[deleteRecording] Removed item from DOM');
            }
            // Check if list is now empty
            const list = document.getElementById('recordings-list');
            if(!list.querySelector('.recording-item')) {
                document.getElementById('no-recordings').style.display = 'block';
                console.log('[deleteRecording] No recordings left, showing empty message');
            }
        } else {
            const data = await resp.json();
            showModernAlert('❌', 'Delete Failed', `Failed to delete recording: ${data.error || 'Unknown error'}`);
            console.error('[deleteRecording] Delete failed:', data);
        }
    } catch(err) {
        console.error('[deleteRecording] Error:', err);
        showModernAlert('❌', 'Error', 'Failed to delete recording. Please try again.');
    }
}

function showModernAlert(icon, title, message) {
    const overlay = document.createElement('div');
    overlay.className = 'delete-modal-overlay';
    
    const modal = document.createElement('div');
    modal.className = 'delete-modal';
    
    modal.innerHTML = `
        <div class="delete-modal-header">
            <div class="delete-modal-icon">${icon}</div>
            <h3 class="delete-modal-title">${title}</h3>
        </div>
        <div class="delete-modal-body">${message}</div>
        <div class="delete-modal-actions">
            <button class="delete-modal-btn cancel" style="width: 100%;">OK</button>
        </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    const okBtn = modal.querySelector('.cancel');
    okBtn.onclick = () => overlay.remove();
    overlay.onclick = (e) => {
        if(e.target === overlay) overlay.remove();
    };
}

function startRenameRecording(recordingId, item) {
    console.log('[startRenameRecording] Starting rename for recording:', recordingId);
    
    const titleElement = item.querySelector('.recording-title');
    const currentTitle = titleElement.textContent;
    const actionsDiv = item.querySelector('.recording-actions');
    
    // Hide action buttons
    if(actionsDiv) actionsDiv.style.display = 'none';
    
    // Store original title element
    const originalTitle = titleElement.cloneNode(true);
    
    // Create rename input container
    const renameContainer = document.createElement('div');
    renameContainer.style.display = 'flex';
    renameContainer.style.gap = '0.6rem';
    renameContainer.style.alignItems = 'center';
    
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'recording-rename-input';
    input.value = currentTitle;
    input.maxLength = 255;
    input.style.flex = '1';
    
    const saveBtn = document.createElement('button');
    saveBtn.className = 'recording-rename-inline-btn save';
    saveBtn.innerHTML = '✓';
    saveBtn.title = 'Save (Enter)';
    saveBtn.onclick = () => saveRename(recordingId, input.value, renameContainer, actionsDiv, originalTitle, item);
    
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'recording-rename-inline-btn cancel';
    cancelBtn.innerHTML = '✕';
    cancelBtn.title = 'Cancel (Esc)';
    cancelBtn.onclick = () => cancelRename(recordingId, renameContainer, actionsDiv, originalTitle, item);
    
    renameContainer.appendChild(input);
    renameContainer.appendChild(saveBtn);
    renameContainer.appendChild(cancelBtn);
    
    // Replace title with input
    titleElement.replaceWith(renameContainer);
    
    // Focus input and select all text
    input.focus();
    input.select();
    
    // Allow Enter key to save, Escape to cancel
    input.addEventListener('keydown', (e) => {
        if(e.key === 'Enter') {
            e.preventDefault();
            saveBtn.click();
        } else if(e.key === 'Escape') {
            e.preventDefault();
            cancelBtn.click();
        }
    });
}

function cancelRename(recordingId, renameContainer, actionsDiv, originalTitle, item) {
    console.log('[cancelRename] Cancelling rename operation');
    
    // Restore original title and re-attach double-click event
    const newTitleElement = originalTitle.cloneNode(true);
    newTitleElement.style.cursor = 'pointer';
    newTitleElement.title = 'Double-click to rename';
    newTitleElement.ondblclick = () => startRenameRecording(recordingId, item);
    
    renameContainer.replaceWith(newTitleElement);
    if(actionsDiv) actionsDiv.style.display = 'flex';
}

async function saveRename(recordingId, newTitle, renameContainer, actionsDiv, originalTitle, item) {
    console.log('[saveRename] Attempting to rename recording:', recordingId, 'to:', newTitle);
    
    newTitle = newTitle.trim();
    if(!newTitle) {
        showModernAlert('⚠️', 'Empty Title', 'Recording title cannot be empty');
        return;
    }
    
    try {
        const resp = await fetch(`/api/recordings/${recordingId}/rename/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            credentials: 'same-origin',
            body: JSON.stringify({ title: newTitle }),
        });
        
        console.log('[saveRename] Response status:', resp.status);
        
        if(resp.ok) {
            const data = await resp.json();
            // Create new title element with updated text and re-attach event listener
            const newTitleElement = originalTitle.cloneNode(false);
            newTitleElement.textContent = data.title;
            newTitleElement.style.cursor = 'pointer';
            newTitleElement.title = 'Double-click to rename';
            newTitleElement.ondblclick = () => startRenameRecording(recordingId, item);
            
            renameContainer.replaceWith(newTitleElement);
            if(actionsDiv) actionsDiv.style.display = 'flex';
            console.log('[saveRename] Successfully renamed recording to:', data.title);
        } else {
            const data = await resp.json();
            showModernAlert('❌', 'Rename Failed', `Failed to rename recording: ${data.error || 'Unknown error'}`);
            console.error('[saveRename] Rename failed:', data);
        }
    } catch(err) {
        console.error('[saveRename] Error:', err);
        showModernAlert('❌', 'Error', 'Failed to rename recording. Please try again.');
    }
}

// Search and requests
const searchInput = null; // will get by id on load
async function refreshRequests(){ const r=await fetch('/api/friends/requests/', { credentials: 'same-origin' }); if(!r.ok){ console.error('Requests fetch failed', r.status); return; } const j=await r.json(); const box=document.getElementById('requests'); box.innerHTML=''; if(!(j.received?.length||j.sent?.length)){ box.innerHTML='<div class="empty">No pending requests</div>'; return; } (j.received||[]).forEach(u=>{ const el=document.createElement('div'); el.className='req'; el.innerHTML=`<div>${u}</div><div><button class="btn btn-success" style="padding:0.35rem 0.75rem;" onclick="actReq('accept','${u}')">Accept</button> <button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="actReq('reject','${u}')">Reject</button></div>`; box.appendChild(el); }); (j.sent||[]).forEach(u=>{ const el=document.createElement('div'); el.className='req'; el.innerHTML=`<div>${u}<div class="muted" style="font-size:0.75rem;margin-top:0.15rem;">Request Sent</div></div><div><button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="undoReq('${u}')">Undo Request</button></div>`; box.appendChild(el); }); }

async function actReq(action, username){ const ep = action==='accept' ? '/api/friends/accept/' : '/api/friends/reject/'; await fetch(ep,{method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: JSON.stringify({ username })}); refreshRequests(); refreshFriendsList(); }

async function doSearch(q){ const r=await fetch(`/api/users/search/?q=${encodeURIComponent(q)}`, { credentials: 'same-origin' }); if(!r.ok){ console.error('Search fetch failed', r.status); return; } const j=await r.json(); const list=document.getElementById('search-results'); list.innerHTML=''; if(!(j.results||[]).length){ list.innerHTML='<div class="empty">No users found</div>'; return; } j.results.forEach(it=>{ const row=document.createElement('div'); row.className='req'; row.innerHTML=`<div>${it.username}${it.friendship_status === 'sent_pending' ? '<div class="muted" style="font-size:0.75rem;margin-top:0.15rem;">Request Sent</div>' : ''}</div><div>${renderSearchActions(it)}</div>`; list.appendChild(row); }); }

function renderSearchActions(it){ 
    if(it.friendship_status === 'sent_pending') return '<button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="undoReq(\''+it.username+'\')">Undo Request</button>'; 
    if(it.friendship_status === 'sent_accepted' || it.friendship_status === 'received_accepted') return '<span class="muted" style="color:#10b981;font-weight:600;"><span style="font-size:1.1em;">✓</span> Already Friends</span>'; 
    if(it.friendship_status.startsWith('received_')) return `<button class="btn btn-success" style="padding:0.35rem 0.75rem;" onclick="actReq('accept','${it.username}')">Accept</button> <button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="actReq('reject','${it.username}')">Reject</button>`; 
    return `<button class="btn btn-primary" style="padding:0.35rem 0.75rem;" onclick="sendReq('${it.username}')">Add</button>`; 
}

async function sendReq(username){ await fetch('/api/friends/request/',{method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: JSON.stringify({ username })}); doSearch(document.getElementById('search-input').value || ''); refreshRequests(); }

async function undoReq(username){ 
    await fetch('/api/friends/undo/',{method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: JSON.stringify({ username })}); 
    const searchVal = document.getElementById('search-input').value || '';
    if(searchVal) doSearch(searchVal); 
    refreshRequests(); 
}

async function refreshFriendsList(){
    const r=await fetch('/api/friends/list/', { credentials: 'same-origin' }); if(!r.ok){ console.error('Friends list fetch failed', r.status); return; } const j=await r.json(); 
    
    // Sort friends based on selection history (most recently selected first)
    const friends = j.friends || [];
    friends.sort((a, b) => {
        const aIndex = selectionHistory.indexOf(a.username);
        const bIndex = selectionHistory.indexOf(b.username);
        
        // If both in history, sort by history order
        if (aIndex !== -1 && bIndex !== -1) {
            return aIndex - bIndex;
        }
        // If only a in history, a comes first
        if (aIndex !== -1) return -1;
        // If only b in history, b comes first
        if (bIndex !== -1) return 1;
        // Neither in history, keep original order (or alphabetically)
        return a.username.localeCompare(b.username);
    });
    
    const box=document.getElementById('friends-list'); 
    box.innerHTML='';
    
    friends.forEach(f=>{
        currentOnlineCache.set(f.username, !!f.is_online);
        const d=document.createElement('div'); d.className='friend-item'; d.dataset.username=f.username;
        let statusHTML = '';
        if(f.is_streaming){ statusHTML = `<span class="dot live-dot"></span> Streaming`; }
        else if(f.is_online){ statusHTML = `<span class="dot online-dot"></span> Online`; }
        else { statusHTML = `<span class="dot offline-dot"></span> Offline`; }
        // Add (friend) label for admins viewing all users
        const friendLabel = (f.is_friend !== undefined && f.is_friend) ? ' <span style="color:#777;font-size:0.9rem;">(friend)</span>' : '';
        d.innerHTML=`<div class=\"friend-info\" onclick=\"selectEntry('${f.username}', false)\"><div class=\"friend-name\">${f.username}${friendLabel}</div><div class=\"friend-meta\">${statusHTML}</div></div><div style=\"position: relative;\"><button class=\"friend-options-btn\" onclick=\"event.stopPropagation(); toggleFriendMenu('${f.username}')\">⋮</button><div class=\"friend-options-menu\" id=\"friend-menu-${f.username}\"><div class=\"friend-options-menu-item danger\" onclick=\"event.stopPropagation(); showUnfriendModal('${f.username}')\">Unfriend</div></div></div>`; 
        box.appendChild(d);
    });
}

let streamingFilterActive = false;

function toggleStreamingFilter() {
    const filterBtn = document.getElementById('streaming-filter-btn');
    streamingFilterActive = !streamingFilterActive;
    
    if (streamingFilterActive) {
        filterBtn.classList.add('active');
    } else {
        filterBtn.classList.remove('active');
    }
    
    // Apply filter
    filterFriendsList();
}

function filterFriendsList() {
    const searchInput = document.getElementById('sidebar-search');
    const query = searchInput.value.toLowerCase().trim();
    const friendItems = document.querySelectorAll('.friend-item:not(.you-item)');
    
    friendItems.forEach(item => {
        const username = item.dataset.username.toLowerCase();
        const meta = item.querySelector('.friend-meta');
        const isStreaming = meta && meta.innerHTML.includes('Streaming');
        
        // Check search query match
        const matchesSearch = username.includes(query);
        
        // Check streaming filter
        const matchesStreamingFilter = !streamingFilterActive || isStreaming;
        
        // Show item only if it matches both filters
        if (matchesSearch && matchesStreamingFilter) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

let unfriendTargetUsername = null;

function showUnfriendModal(username) {
    unfriendTargetUsername = username;
    document.getElementById('unfriend-username').textContent = username;
    document.getElementById('unfriend-modal').classList.add('active');
}

function closeUnfriendModal() {
    document.getElementById('unfriend-modal').classList.remove('active');
    unfriendTargetUsername = null;
}

function showAlertModal(type, title, message) {
    const modal = document.getElementById('alert-modal');
    const icon = document.getElementById('alert-icon');
    const titleEl = document.getElementById('alert-title');
    const messageEl = document.getElementById('alert-message');
    const btn = document.getElementById('alert-btn');
    
    // Set icon based on type
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    icon.textContent = icons[type] || icons.info;
    icon.className = `alert-icon ${type}`;
    
    // Set content
    titleEl.textContent = title;
    messageEl.textContent = message;
    
    // Set button style
    btn.className = `alert-btn ${type}`;
    
    // Show modal
    modal.classList.add('active');
}

function closeAlertModal() {
    document.getElementById('alert-modal').classList.remove('active');
}

async function confirmUnfriend() {
    if (!unfriendTargetUsername) return;
    const username = unfriendTargetUsername;
    try {
        const resp = await fetch('/api/friends/unfriend/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ username: username })
        });
        const data = await resp.json();
        closeUnfriendModal();
        
        if (!resp.ok) {
            // Show error alert
            if (resp.status === 400 && data.error) {
                showAlertModal('error', 'Cannot Unfriend', data.error);
            } else {
                showAlertModal('error', 'Failed to Unfriend', data.error || 'An error occurred while trying to unfriend this user.');
            }
            return;
        }
        
        // Show success alert
        showAlertModal('success', 'Unfriended Successfully', `You have unfriended ${username}.`);
        
        // If viewing the unfriended user's page, switch back to self
        if (selectedUsername === username) {
            selectEntry(currentUser, true);
        }
        refreshFriendsList();
    } catch (e) {
        closeUnfriendModal();
        showAlertModal('error', 'Error', 'An unexpected error occurred: ' + e.message);
    }
}

function toggleFriendMenu(username) {
    const menu = document.getElementById('friend-menu-' + username);
    const isActive = menu.classList.contains('active');
    
    // Close all other menus first
    document.querySelectorAll('.friend-options-menu').forEach(m => m.classList.remove('active'));
    
    // Toggle current menu
    if (!isActive) {
        menu.classList.add('active');
    }
}

// Close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.friend-options-btn') && !e.target.closest('.friend-options-menu')) {
        document.querySelectorAll('.friend-options-menu').forEach(m => m.classList.remove('active'));
    }
});

// Initialize
// Read config now that cfg element exists
try { browserAudioProcessing = JSON.parse(document.getElementById('cfg').textContent).browserAudioProcessing; } catch (e) { /* keep default */ }
connectPresence();
document.getElementById('search-input').addEventListener('input', (e)=>{ const q=e.target.value.trim(); if(q.length<1){ document.getElementById('search-results').innerHTML=''; return;} doSearch(q); });
refreshRequests();
refreshFriendsList();
// Select self by default
selectEntry(currentUser, true);
// Refresh initial live dots (self + friends) via REST
fetch(`/api/stream/status/${encodeURIComponent(currentUser)}/`, { credentials: 'same-origin' })
    .then(r=>r.json()).then(j=>{ currentOnlineCache.set(currentUser, !!j.online); updateSidebarTri(currentUser, {active: !!j.active, online: !!j.online}); });

// Unload safety: stop stream if open
window.addEventListener('beforeunload', ()=>{ if(isOwnerView && localStream){ navigator.sendBeacon('/api/stream/stop/', JSON.stringify({})); } });

// Open friends modal on navbar Friends click
window.addEventListener('toggleFriendsPanel', ()=>{
    openFriendsModal();
});

function openFriendsModal() {
    document.getElementById('friends-modal').classList.add('active');
    // Refresh data when modal opens
    refreshRequests();
}

function closeFriendsModal() {
    document.getElementById('friends-modal').classList.remove('active');
    // Clear search when closing
    document.getElementById('search-input').value = '';
    document.getElementById('search-results').innerHTML = '';
}

// Denoise toggle button logic
function toggleDenoise(){
    const cb = document.getElementById('denoise-toggle');
    const btn = document.getElementById('denoise-btn');
    if (document.getElementById('start-btn').style.display === 'none') return; // already streaming
    cb.checked = !cb.checked;
    if(cb.checked){
        btn.classList.remove('toggle-off');
        btn.classList.add('toggle-on');
        btn.textContent = 'Denoise: ON';
    } else {
        btn.classList.remove('toggle-on');
        btn.classList.add('toggle-off');
        btn.textContent = 'Denoise: OFF';
    }
}

// Heartbeat to mark user online
function sendHeartbeat(){
    fetch('/api/presence/heartbeat/', { method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: '{}' }).catch(()=>{});
}
sendHeartbeat();
setInterval(sendHeartbeat, 15000);

// Periodic friend status refresh every 10 seconds
async function refreshFriendStatuses() {
    try {
        console.log('[Status Refresh] Starting status refresh...');
        
        // Refresh friends list to get latest online/streaming status
        const r = await fetch('/api/friends/list/', { credentials: 'same-origin' });
        if (!r.ok) {
            console.error('[Status Refresh] Friends list fetch failed:', r.status);
            return;
        }
        const j = await r.json();
        console.log('[Status Refresh] Got friends data:', j);
        
        (j.friends || []).forEach(f => {
            const wasOnline = currentOnlineCache.get(f.username);
            currentOnlineCache.set(f.username, !!f.is_online);
            // Update sidebar status for each friend
            updateSidebarTri(f.username, {active: !!f.is_streaming, online: !!f.is_online});
            if (wasOnline !== !!f.is_online) {
                console.log(`[Status Refresh] ${f.username} changed: ${wasOnline} -> ${f.is_online}`);
            }
        });
        
        // Also refresh current user's own status
        const selfStatus = await fetch(`/api/stream/status/${encodeURIComponent(currentUser)}/`, { credentials: 'same-origin' });
        if (selfStatus.ok) {
            const selfData = await selfStatus.json();
            const wasOnline = currentOnlineCache.get(currentUser);
            currentOnlineCache.set(currentUser, !!selfData.online);
            updateSidebarTri(currentUser, {active: !!selfData.active, online: !!selfData.online});
            if (wasOnline !== !!selfData.online) {
                console.log(`[Status Refresh] Self status changed: ${wasOnline} -> ${selfData.online}`);
            }
        }
        
        // If viewing someone's page, update their live pill too
        if (selectedUsername) {
            const userStatus = await fetch(`/api/stream/status/${encodeURIComponent(selectedUsername)}/`, { credentials: 'same-origin' });
            if (userStatus.ok) {
                const userData = await userStatus.json();
                currentOnlineCache.set(selectedUsername, !!userData.online);
                updateLivePill({active: !!userData.active, online: !!userData.online});
                if (!isOwnerView) {
                    updateListenerControlsVisibility(!!userData.active);
                }
            }
        }
        
        console.log('[Status Refresh] Refresh complete');
    } catch (e) {
        console.error('[Status Refresh] Error during refresh:', e);
    }
}

// Start periodic refresh every 10 seconds
console.log('[Status Refresh] Starting periodic refresh (every 10s)');
setInterval(refreshFriendStatuses, 10000);
// Also run once immediately after 2 seconds to get initial state
setTimeout(refreshFriendStatuses, 2000);

// ===== Denoise File Modal Functions =====
function openDenoiseModal() {
    document.getElementById('denoise-modal').classList.add('active');
    refreshDenoiseFilesList();
}

function closeDenoiseModal() {
    document.getElementById('denoise-modal').classList.remove('active');
    clearFileInput();
    document.getElementById('upload-status').textContent = '';
}

// File input handling
function clearFileInput(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const fileInput = document.getElementById('audio-file-input');
    fileInput.value = '';
    updateFileInputUI();
}

function updateFileInputUI() {
    const fileInput = document.getElementById('audio-file-input');
    const wrapper = document.getElementById('file-input-wrapper');
    const mainText = document.getElementById('file-input-main');
    const subText = document.getElementById('file-input-sub');
    const clearBtn = document.getElementById('file-input-clear');
    const icon = wrapper.querySelector('.file-input-icon');
    
    if (fileInput.files && fileInput.files[0]) {
        const file = fileInput.files[0];
        const fileName = file.name;
        const fileSize = (file.size / (1024 * 1024)).toFixed(2); // MB
        
        wrapper.classList.add('has-file');
        mainText.textContent = fileName;
        subText.textContent = `${fileSize} MB`;
        clearBtn.style.display = 'block';
        icon.textContent = '🎵';
    } else {
        wrapper.classList.remove('has-file');
        mainText.textContent = 'Choose an audio file';
        subText.textContent = 'WAV, MP3, FLAC, OGG, M4A';
        clearBtn.style.display = 'none';
        icon.textContent = '📁';
    }
}

// Listen for file selection
document.getElementById('audio-file-input').addEventListener('change', updateFileInputUI);

/* Commented out - refreshDenoiseFilesList is now in modal-tabs-new.js with waveform visualization
async function refreshDenoiseFilesList() {
    try {
        const resp = await fetch('/api/denoise/files/', { credentials: 'same-origin' });
        if (!resp.ok) {
            console.error('Failed to fetch denoise files');
            return;
        }
        const data = await resp.json();
        const list = document.getElementById('denoise-files-list');
        
        if (!data.files || data.files.length === 0) {
            list.innerHTML = '<div class="empty">No files yet</div>';
            return;
        }
        
        list.innerHTML = '';
        data.files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'recording-item';
            item.style.flexDirection = 'column';
            item.style.alignItems = 'stretch';
            item.style.gap = '0.75rem';
            item.style.padding = '1rem';
            
            const header = document.createElement('div');
            header.style.width = '100%';
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            header.style.marginBottom = '0.5rem';
            
            const leftHeader = document.createElement('div');
            leftHeader.style.display = 'flex';
            leftHeader.style.flexDirection = 'column';
            leftHeader.style.gap = '0.25rem';
            leftHeader.style.flex = '1';
            
            const fileName = document.createElement('div');
            fileName.className = 'recording-title';
            fileName.textContent = file.original_filename;
            
            const uploadDate = document.createElement('div');
            uploadDate.className = 'muted';
            uploadDate.style.fontSize = '0.85rem';
            uploadDate.textContent = new Date(file.uploaded_at).toLocaleString();
            
            leftHeader.appendChild(fileName);
            leftHeader.appendChild(uploadDate);
            
            // Delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn-delete-file';
            deleteBtn.innerHTML = '<span>❌</span>';
            deleteBtn.onclick = () => deleteDenoiseFile(file.id, file.original_filename);
            deleteBtn.style.marginLeft = '1rem';
            deleteBtn.style.flexShrink = '0';
            
            header.appendChild(leftHeader);
            header.appendChild(deleteBtn);
            
            const filesRow = document.createElement('div');
            filesRow.style.width = '100%';
            filesRow.style.display = 'flex';
            filesRow.style.gap = '1.5rem';
            filesRow.style.alignItems = 'flex-start';
            filesRow.style.flexWrap = 'wrap';
            
            // Original file
            const originalBox = document.createElement('div');
            originalBox.style.flex = '1 1 250px';
            originalBox.style.minWidth = '250px';
            originalBox.style.maxWidth = '350px';
            const originalLabel = document.createElement('div');
            originalLabel.className = 'muted';
            originalLabel.style.fontSize = '0.8rem';
            originalLabel.style.marginBottom = '0.25rem';
            originalLabel.textContent = '📁 Original';
            const originalAudio = document.createElement('audio');
            originalAudio.controls = true;
            originalAudio.preload = 'none';
            originalAudio.style.width = '100%';
            const originalSrc = document.createElement('source');
            originalSrc.src = file.original_file_url;
            originalSrc.type = 'audio/wav';
            originalAudio.appendChild(originalSrc);
            originalBox.appendChild(originalLabel);
            originalBox.appendChild(originalAudio);
            
            // Denoised file
            const denoisedBox = document.createElement('div');
            denoisedBox.style.flex = '1 1 250px';
            denoisedBox.style.minWidth = '250px';
            denoisedBox.style.maxWidth = '350px';
            const denoisedLabel = document.createElement('div');
            denoisedLabel.className = 'muted';
            denoisedLabel.style.fontSize = '0.8rem';
            denoisedLabel.style.marginBottom = '0.25rem';
            denoisedLabel.textContent = '✨ Denoised';
            
            if (file.status === 'completed' && file.denoised_file_url) {
                const denoisedAudio = document.createElement('audio');
                denoisedAudio.controls = true;
                denoisedAudio.preload = 'none';
                denoisedAudio.style.width = '100%';
                const denoisedSrc = document.createElement('source');
                denoisedSrc.src = file.denoised_file_url;
                denoisedSrc.type = 'audio/wav';
                denoisedAudio.appendChild(denoisedSrc);
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(denoisedAudio);
            } else if (file.status === 'processing') {
                const processingMsg = document.createElement('div');
                processingMsg.style.padding = '0.5rem';
                processingMsg.style.background = '#fef3c7';
                processingMsg.style.color = '#92400e';
                processingMsg.style.borderRadius = '6px';
                processingMsg.style.fontSize = '0.9rem';
                processingMsg.textContent = '⏳ In Process...';
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(processingMsg);
            } else if (file.status === 'failed') {
                const errorMsg = document.createElement('div');
                errorMsg.style.padding = '0.5rem';
                errorMsg.style.background = '#fee2e2';
                errorMsg.style.color = '#991b1b';
                errorMsg.style.borderRadius = '6px';
                errorMsg.style.fontSize = '0.9rem';
                errorMsg.textContent = '❌ Failed';
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(errorMsg);
            } else {
                const pendingMsg = document.createElement('div');
                pendingMsg.style.padding = '0.5rem';
                pendingMsg.style.background = '#e0e7ff';
                pendingMsg.style.color = '#3730a3';
                pendingMsg.style.borderRadius = '6px';
                pendingMsg.style.fontSize = '0.9rem';
                pendingMsg.textContent = '⏱️ Pending...';
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(pendingMsg);
            }
            
            filesRow.appendChild(originalBox);
            filesRow.appendChild(denoisedBox);
            
            item.appendChild(header);
            item.appendChild(filesRow);
            list.appendChild(item);
        });
    } catch (e) {
        console.error('Error refreshing denoise files:', e);
    }
}
*/

// NOTE: refreshDenoiseFilesList is now defined in modal-tabs-new.js with waveform features
// The function above is commented out to avoid overriding the enhanced version

// NOTE: File upload handler moved to modal-tabs.js to avoid duplicate submissions
// The upload-form event listener is now in modal-tabs.js with boost level support
// NOTE: Polling functions also moved to modal-tabs.js to avoid duplicate declarations

// Delete denoise file - show custom modal
let deleteFileId = null;
let deleteFileName = null;

function deleteDenoiseFile(fileId, filename) {
    deleteFileId = fileId;
    deleteFileName = filename;
    document.getElementById('delete-file-name').textContent = filename;
    const modal = document.getElementById('delete-file-modal');
    modal.style.display = ''; // Remove inline style so CSS class can work
    modal.classList.add('active');
}

function closeDeleteFileModal() {
    console.log('[DELETE] Closing modal');
    const modal = document.getElementById('delete-file-modal');
    console.log('[DELETE] Modal before remove active:', modal.className);
    modal.classList.remove('active');
    modal.style.display = 'none';
    console.log('[DELETE] Modal after remove active:', modal.className);
    
    // Clear all file IDs
    deleteFileId = null;
    deleteFileName = null;
    
    // Clear modal-tabs-new.js variables if they exist
    if (typeof window.deleteDenoiseFileId !== 'undefined') window.deleteDenoiseFileId = null;
    if (typeof window.deleteDenoiseFileName !== 'undefined') window.deleteDenoiseFileName = '';
    if (typeof window.deleteVocalFileId !== 'undefined') window.deleteVocalFileId = null;
    if (typeof window.deleteVocalFileName !== 'undefined') window.deleteVocalFileName = '';
    if (typeof window.deleteBoostFileId !== 'undefined') window.deleteBoostFileId = null;
    if (typeof window.deleteBoostFileName !== 'undefined') window.deleteBoostFileName = '';
    if (typeof window.deleteSpeakerFileId !== 'undefined') window.deleteSpeakerFileId = null;
    if (typeof window.deleteSpeakerFileName !== 'undefined') window.deleteSpeakerFileName = '';
    if (typeof window.deleteVoiceCloneFileId !== 'undefined') window.deleteVoiceCloneFileId = null;
    if (typeof window.deleteVoiceCloneFileName !== 'undefined') window.deleteVoiceCloneFileName = '';
    console.log('[DELETE] All variables cleared');
}

async function confirmDeleteFile() {
    console.log('[DELETE] Confirm delete called');
    let fileId = null;
    let deleteUrl = null;
    let refreshFunction = null;
    
    console.log('[DELETE] Checking variables:', {
        denoise: window.deleteDenoiseFileId,
        vocal: window.deleteVocalFileId,
        boost: window.deleteBoostFileId,
        speaker: window.deleteSpeakerFileId,
        voiceclone: window.deleteVoiceCloneFileId,
        fallback: deleteFileId
    });
    
    // Determine which file type is being deleted
    if (window.deleteDenoiseFileId) {
        fileId = window.deleteDenoiseFileId;
        deleteUrl = `/api/denoise/files/${fileId}/delete/`;
        refreshFunction = window.refreshDenoiseFilesList;
    } else if (window.deleteVocalFileId) {
        fileId = window.deleteVocalFileId;
        deleteUrl = `/api/vocal/files/${fileId}/delete/`;
        refreshFunction = window.refreshVocalFilesList;
    } else if (window.deleteBoostFileId) {
        fileId = window.deleteBoostFileId;
        deleteUrl = `/api/boost/files/${fileId}/delete/`;
        refreshFunction = window.refreshBoostFilesList;
    } else if (window.deleteSpeakerFileId) {
        fileId = window.deleteSpeakerFileId;
        deleteUrl = `/api/speaker/files/${fileId}/delete/`;
        refreshFunction = window.refreshSpeakerFilesList;
    } else if (window.deleteVoiceCloneFileId) {
        fileId = window.deleteVoiceCloneFileId;
        deleteUrl = `/api/voiceclone/files/${fileId}/delete/`;
        refreshFunction = window.refreshVoiceCloneFilesList;
    } else if (deleteFileId) {
        // Fallback for old denoise delete
        fileId = deleteFileId;
        deleteUrl = `/api/denoise/files/${fileId}/delete/`;
        refreshFunction = window.refreshDenoiseFilesList;
    }
    
    if (!fileId) return;
    
    try {
        const resp = await fetch(deleteUrl, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        });
        
        if (!resp.ok) {
            const error = await resp.json();
            throw new Error(error.error || 'Failed to delete file');
        }
        
        // Close modal
        closeDeleteFileModal();
        
        // Refresh the appropriate list
        if (refreshFunction) {
            await refreshFunction();
        }
        
    } catch (e) {
        closeDeleteFileModal();
        // Show error in a nicer way
        const statusDiv = document.getElementById('upload-status');
        if (statusDiv) {
            statusDiv.textContent = '❌ Error deleting file: ' + e.message;
            statusDiv.style.color = '#991b1b';
            setTimeout(() => {
                statusDiv.textContent = '';
            }, 5000);
        }
        console.error('Delete error:', e);
    }
}

// Listen for global denoise modal trigger
window.addEventListener('toggleDenoisePanel', openDenoiseModal);