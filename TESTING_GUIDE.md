# Testing Guide for Streaming Fixes

## Prerequisites

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

2. **Setup Database:**
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Create Test Users:**
```bash
python manage.py createsuperuser --username alice --email alice@test.com
python manage.py createsuperuser --username bob --email bob@test.com
```

4. **Start Redis (Optional but Recommended):**
```bash
# On Ubuntu/Debian:
sudo service redis-server start

# Or with Docker:
docker run -p 6379:6379 redis:latest

# Or use in-memory mode:
export CHANNEL_BACKEND=inmemory
```

5. **Run Server:**
```bash
# Development server with Daphne (required for WebSockets)
daphne -b 0.0.0.0 -p 8000 fc25_denoise.asgi:application

# Or with manage.py (may not support WebSockets properly)
python manage.py runserver
```

## Test Scenarios

### Test 1: Basic Streaming and Timer
**Objective:** Verify streaming starts and timer updates correctly.

**Steps:**
1. Login as `alice`
2. Click "Start Streaming" button
3. Grant microphone permissions when prompted
4. Observe the timer starts at 00:00
5. Wait and verify timer updates every second (00:01, 00:02, etc.)
6. Open browser console (F12) and check for timer logs:
   ```
   [Timer] Starting stream timer at ...
   [Timer] Updated duration: 00:01 (1s)
   [Timer] Updated duration: 00:02 (2s)
   ```

**Expected Results:**
- ✅ Timer updates every second
- ✅ Console shows timer logs
- ✅ "Stop Streaming" button appears
- ✅ Red pulsing dot appears in sidebar

### Test 2: Page Reload Cleanup
**Objective:** Verify stream stops when page is reloaded.

**Steps:**
1. Login as `alice` and start streaming
2. Wait 5 seconds (verify timer is at 00:05)
3. Reload the page (F5 or Ctrl+R)
4. Check that streaming is NOT active after reload
5. Check Django logs for cleanup messages

**Expected Results:**
- ✅ Stream stops on reload
- ✅ Timer resets to 00:00
- ✅ "Start Streaming" button visible (not "Stop")
- ✅ Logs show: "Closed streaming session ... for user alice"

### Test 3: Recording Saved
**Objective:** Verify denoised audio is saved to file.

**Steps:**
1. Login as `alice` and start streaming
2. Speak or play audio into microphone for 10-15 seconds
3. Click "Stop Streaming"
4. Check the `streamed_audios/` directory:
   ```bash
   ls -lh streamed_audios/
   ```
5. Verify a WAV file exists: `alice_{session_id}.wav`
6. Check Django logs for:
   ```
   Saved recording to .../streamed_audios/alice_....wav (duration: X.XXs)
   Created StreamRecording #X for user alice
   ```
7. Login as `bob`, add `alice` as friend
8. Visit alice's page and check "Previous Recordings" section
9. Verify recording appears and can be played

**Expected Results:**
- ✅ WAV file created in `streamed_audios/`
- ✅ File size > 0 bytes
- ✅ Recording appears in database
- ✅ Recording playable on friend page

### Test 4: Real-time Status Updates
**Objective:** Verify friends see streaming status instantly.

**Steps:**
1. Login as `alice` in Browser Window 1
2. Login as `bob` in Browser Window 2 (incognito/private mode)
3. Make alice and bob friends (send/accept friend request)
4. In Window 2 (bob): Navigate to main page, see alice in friends list
5. In Window 1 (alice): Click "Start Streaming"
6. In Window 2 (bob): Observe alice's status changes to "Streaming" within 1-2 seconds
7. In Window 1 (alice): Click "Stop Streaming"
8. In Window 2 (bob): Observe alice's status changes to "Offline" immediately

**Expected Results:**
- ✅ Status changes appear within 1-2 seconds
- ✅ Console shows WebSocket messages:
  ```
  Friend alice streaming status changed: true
  Friend alice streaming status changed: false
  ```

### Test 5: Listening to Stream
**Objective:** Verify friends can listen to live streams.

**Steps:**
1. Login as `alice` in Browser Window 1 and start streaming
2. Login as `bob` in Browser Window 2
3. In Window 2: Click on `alice` in friends list
4. Verify "alice is currently streaming!" message appears
5. Click "Start Listening" button
6. Verify audio element appears and plays audio
7. In Window 1 (alice): Speak into microphone
8. In Window 2 (bob): Verify you hear the denoised audio

**Expected Results:**
- ✅ Live audio plays in browser
- ✅ Audio is denoised (less background noise)
- ✅ Latency < 3 seconds
- ✅ Audio quality is clear

### Test 6: WebSocket Disconnect Cleanup
**Objective:** Verify stream stops when WebSocket disconnects.

**Steps:**
1. Login as `alice` and start streaming
2. Open browser DevTools → Network tab
3. Find the WebSocket connection (`ws://localhost:8000/ws/presence/`)
4. Close the WebSocket connection manually (or close browser)
5. Check Django logs for cleanup

**Expected Results:**
- ✅ Logs show: "Closed streaming session ... for disconnected user alice"
- ✅ Database: `ActiveStream` entry deleted
- ✅ Database: User `is_streaming` set to `False`

### Test 7: Redis Channel Layer
**Objective:** Verify Redis is being used for channel layer.

**Steps:**
1. Ensure Redis is running on port 6379
2. Start Django server
3. Login and start streaming
4. Check Django logs for:
   ```
   Sending streaming_status_update via channel layer for user alice (is_streaming=True)
   Channel layer notification sent for user alice
   PresenceConsumer received streaming_status_update: alice is_streaming=True
   Sent streaming_status to WebSocket client for alice
   ```
5. Alternatively, use Redis CLI to monitor activity:
   ```bash
   redis-cli monitor
   ```

**Expected Results:**
- ✅ Redis commands appear in monitor
- ✅ Django logs show channel layer activity
- ✅ No "InMemoryChannelLayer" warnings (unless using CHANNEL_BACKEND=inmemory)

## Debugging

### Timer Not Updating
1. Open browser console
2. Check for error messages
3. Verify `stream-duration` element exists in DOM
4. Check console for "[Timer]" log messages

### Recording Not Saved
1. Check Django logs for errors
2. Verify `streamed_audios/` directory exists and is writable
3. Check for DeepFilterNet model initialization errors
4. Verify `soundfile` is installed: `pip list | grep soundfile`

### WebSocket Issues
1. Check browser console for WebSocket connection errors
2. Verify Daphne is running (not runserver)
3. Check firewall/proxy settings
4. Verify `channels` and `channels-redis` are installed

### Audio Quality Issues
1. Check microphone quality and settings
2. Adjust DeepFilterNet parameters in `dfn2.py`
3. Check for console errors during processing
4. Verify CPU/GPU is sufficient for real-time processing

## Performance Monitoring

### Check CPU Usage
```bash
top -p $(pgrep -f "daphne")
```

### Check Memory Usage
```bash
ps aux | grep daphne
```

### Check Recording File Sizes
```bash
du -h streamed_audios/
```

### Monitor WebSocket Connections
```bash
netstat -an | grep :8000
```

## Troubleshooting

### Issue: "No module named 'av'"
**Solution:** Install PyAV:
```bash
pip install av
```

### Issue: "aiortc is not installed"
**Solution:**
```bash
pip install --upgrade pip setuptools wheel
pip install av aiortc
```

### Issue: Redis connection failed
**Solution:** Either start Redis or use in-memory mode:
```bash
export CHANNEL_BACKEND=inmemory
```

### Issue: Microphone permission denied
**Solution:**
- Check browser permissions
- Use HTTPS (required for getUserMedia in production)
- Try different browser

### Issue: No audio in recording
**Solution:**
- Verify microphone is working
- Check audio levels in OS settings
- Test with different audio input source

## Success Criteria

All tests pass if:
- ✅ Timer updates in real-time
- ✅ Streams stop on page reload/close
- ✅ Audio files saved to `streamed_audios/`
- ✅ Recordings appear in database and are playable
- ✅ Status updates appear within 1-2 seconds
- ✅ Friends can listen to live streams
- ✅ WebSocket disconnect triggers cleanup
- ✅ Redis logs show channel layer activity (if using Redis)
