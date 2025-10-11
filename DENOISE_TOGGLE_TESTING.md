# Denoise Toggle Feature - Testing Guide

## Overview
This document describes how to test the new denoise toggle feature that allows users to disable denoising and stream raw microphone audio.

## Feature Description
- **Purpose**: Allow users to toggle denoising on/off before starting a stream to test if audio/timer issues are related to the DeepFilterNet processing
- **UI Location**: Checkbox appears in the sidebar header, above the "Start Streaming" button
- **Default State**: Denoising is enabled by default (checkbox checked)
- **Behavior**: Toggle disappears once streaming starts and reappears when streaming stops

## UI States

### Before Streaming
![Before Streaming](https://github.com/user-attachments/assets/44e032d4-cb62-464c-a18b-b0d62ec79e99)
- ✅ "Enable Denoising" checkbox is visible
- ✅ Checkbox is checked by default
- ✅ "Start Streaming" button is visible
- ✅ User can toggle the checkbox on/off

### During Streaming
![During Streaming](https://github.com/user-attachments/assets/b112bcf1-4f05-4bbb-b053-91a071500b68)
- ✅ "Enable Denoising" checkbox is hidden
- ✅ "Stop Streaming" button is visible with timer
- ✅ "Streaming now" indicator is shown

## Technical Implementation

### Frontend Changes
1. **main.html** - Added checkbox UI element
2. **main.js** - Added denoise state tracking and toggle visibility logic
3. **webrtc_client.js** - Pass denoise flag to backend in WebRTC offer
4. **style.css** - Added styling for denoise toggle

### Backend Changes
1. **streams/views.py**:
   - `start_stream()` - Accept and log denoise parameter
   - `webrtc_offer()` - Store denoise flag in session

2. **streams/webrtc_handler.py**:
   - `WebRTCSession.__init__()` - Added `denoise_enabled` parameter
   - `create_session()` - Accept denoise flag
   - Audio processing loop - Conditionally apply denoising based on flag

## Testing Steps

### Manual Testing

#### Test 1: UI Visibility (Before Streaming)
1. Login to the application
2. Navigate to the main page
3. **Expected**: See "Enable Denoising" checkbox above "Start Streaming" button
4. **Expected**: Checkbox should be checked by default

#### Test 2: Toggle Functionality
1. Uncheck the "Enable Denoising" checkbox
2. Check it again
3. **Expected**: Checkbox toggles between checked/unchecked states smoothly

#### Test 3: Streaming with Denoising Enabled (Default)
1. Ensure "Enable Denoising" is checked
2. Click "Start Streaming"
3. **Expected**: 
   - Checkbox disappears
   - "Stop Streaming" button appears with timer (00:00, 00:01, 00:02, etc.)
   - "Streaming now" indicator appears
   - Backend logs show: `denoise_enabled=True`
   - Audio is processed through DeepFilterNet2

#### Test 4: Streaming with Denoising Disabled (Raw Mode)
1. Uncheck "Enable Denoising"
2. Click "Start Streaming"
3. **Expected**:
   - Checkbox disappears
   - "Stop Streaming" button appears with timer
   - "Streaming now" indicator appears
   - Backend logs show: `denoise_enabled=False`
   - Console logs show: `Bypassing denoising (raw mode)`
   - Raw microphone audio is streamed to listeners

#### Test 5: Stop Streaming
1. While streaming, click "Stop Streaming"
2. **Expected**:
   - "Enable Denoising" checkbox reappears
   - "Start Streaming" button reappears
   - Timer resets to 00:00
   - Streaming indicator disappears

#### Test 6: Timer Functionality
1. Start streaming (with or without denoising)
2. Observe the timer for 30 seconds
3. **Expected**:
   - Timer updates every second: 00:00 → 00:01 → 00:02 → ... → 00:30
   - Timer does NOT get stuck at 00:00

#### Test 7: Listener Test (With Denoising)
1. User A: Enable denoising, start streaming
2. User B (friend): Navigate to User A's page, click "Start Listening"
3. **Expected**:
   - User B hears User A's audio with noise reduction applied
   - Audio is clear and denoised

#### Test 8: Listener Test (Without Denoising - Raw Mode)
1. User A: Disable denoising, start streaming
2. User B (friend): Navigate to User A's page, click "Start Listening"
3. **Expected**:
   - User B hears User A's raw microphone audio
   - No denoising applied (may have background noise)
   - Audio arrives quickly without processing delay

### Debugging Issues

#### If Timer Stuck at 00:00
- Check browser console for JavaScript errors
- Verify `streamStartedAt` is being set in `startStreamTimer()`
- Check if `updateStreamDuration()` is being called every second

#### If Listeners Can't Hear Audio
1. **With Denoising Enabled**: Issue may be in DeepFilterNet processing
2. **With Denoising Disabled**: Issue is likely WebRTC/network related, not denoising

#### If Checkbox Doesn't Appear
- Check browser console for errors
- Verify CSS is loaded correctly
- Check `denoise-toggle-container` element is in the DOM

#### If Toggle Doesn't Disappear During Streaming
- Check `updateStreamingUI()` is being called after streaming starts
- Verify `isStreaming` or `serverStreaming` flags are set correctly

## Expected Backend Logs

### With Denoising Enabled
```
Starting stream for user testuser with denoise=True
Created session xxx-xxx-xxx for testuser with denoise_enabled=True
[Session xxx-xxx-xxx] Applied denoising
```

### With Denoising Disabled
```
Starting stream for user testuser with denoise=False
Created session xxx-xxx-xxx for testuser with denoise_enabled=False
[Session xxx-xxx-xxx] Bypassing denoising (raw mode)
```

## Code Review Checklist
- [x] Frontend passes denoise flag to backend
- [x] Backend receives and stores denoise flag
- [x] WebRTC session conditionally applies denoising
- [x] UI toggle appears before streaming
- [x] UI toggle disappears during streaming
- [x] UI toggle reappears after streaming stops
- [x] Default state is denoising enabled
- [x] CSS styling is consistent with existing UI
- [x] No JavaScript errors in console
- [x] No Python errors in backend logs

## Known Limitations
- Denoise setting cannot be changed during an active stream (must stop and restart)
- Setting is not persisted (resets to enabled on page reload)

## Future Enhancements (Optional)
- Persist denoise preference in user settings
- Allow changing denoise setting during streaming (requires session recreation)
- Add tooltip explaining what "Enable Denoising" does
- Show visual indicator of current mode while streaming
