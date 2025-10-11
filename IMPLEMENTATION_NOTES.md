# Denoise Toggle Implementation Notes

## Problem Statement
The user reported two main issues:
1. Timer stuck at 00:00 during streaming
2. Friends cannot hear audio (start listening doesn't work)

To diagnose whether these issues are related to DeepFilterNet denoising or other system components, a toggle was requested to enable/disable denoising before starting a stream.

## Solution Architecture

### Flow Diagram
```
User Interface (Checkbox)
    ↓ (checked/unchecked)
main.js (denoiseEnabled variable)
    ↓ (on Start Streaming)
webrtc_client.js (passes in startBroadcast)
    ↓ (WebRTC offer)
streams/views.py start_stream() (receives denoise flag)
    ↓ (creates session)
webrtc_handler.py WebRTCSession (stores denoise_enabled)
    ↓ (audio frame processing)
Conditional: if denoise_enabled → DeepFilterNet2 → listeners
            else → raw audio → listeners
```

## Key Implementation Points

### 1. State Management (Frontend)
```javascript
let denoiseEnabled = true; // Global state, default enabled
```
- Tracked in `main.js`
- Updated by checkbox change event
- Passed to `startBroadcast()` and `/api/stream/start/`

### 2. UI Toggle Visibility
The toggle visibility is controlled by `updateStreamingUI()`:
- **Before streaming**: `denoiseToggleContainer.style.display = 'block'`
- **During streaming**: `denoiseToggleContainer.style.display = 'none'`
- **After streaming**: `denoiseToggleContainer.style.display = 'block'`

This ensures users cannot change the setting mid-stream.

### 3. Backend Session Management
```python
class WebRTCSession:
    def __init__(self, session_id: str, username: str, denoise_enabled: bool = True):
        self.denoise_enabled = denoise_enabled
        # ...
```
- Denoise flag stored at session level
- Cannot be changed during active stream
- Resets to default (enabled) for new sessions

### 4. Audio Processing Logic
```python
if self.denoise_enabled:
    processed_audio = await self.processor.process_frame(audio_mono)
    print(f"[Session {self.session_id}] Applied denoising")
else:
    processed_audio = audio_mono  # Pass-through
    print(f"[Session {self.session_id}] Bypassing denoising (raw mode)")
```
- Simple if/else branching
- Minimal performance overhead
- Clear logging for debugging

## Design Decisions

### Why Hide Toggle During Streaming?
- **Prevents confusion**: User clearly sees the setting was applied
- **Prevents mid-stream changes**: Changing denoise settings requires session recreation
- **UI clarity**: Reduces clutter during active streaming
- **Consistent with requirement**: Problem statement specified "after streaming starts, this button disappears"

### Why Default to Enabled?
- **Production use case**: Most users want denoising
- **Testing is opt-out**: User explicitly disables for testing
- **Safe default**: Doesn't break existing behavior

### Why Not Persist Setting?
- **Testing focus**: This is for debugging, not a permanent user preference
- **Simpler implementation**: No database changes needed
- **Explicit choice**: User consciously selects mode each session

## Testing Strategy

### Unit Testing (Not Implemented)
Could add:
- Test denoise flag propagation from frontend to backend
- Test conditional audio processing logic
- Test UI visibility changes

### Manual Testing Required
1. **Timer test with denoise ON**: Verify timer counts up correctly
2. **Timer test with denoise OFF**: Verify timer counts up correctly
3. **Listener test with denoise ON**: Verify audio is heard and denoised
4. **Listener test with denoise OFF**: Verify raw audio is heard
5. **UI test**: Verify toggle appears/disappears correctly

### Debugging Approach
By testing both modes, user can determine:
- If timer works in both modes → timer is fine, original report may be incorrect
- If timer fails in both modes → timer issue is not denoise-related
- If listeners hear audio in raw mode but not denoised mode → DeepFilterNet issue
- If listeners don't hear audio in either mode → WebRTC/network issue

## Potential Issues & Mitigations

### Issue 1: Audio Quality in Raw Mode
**Problem**: Raw audio may have noise/echo  
**Mitigation**: This is expected; it's for testing only

### Issue 2: Latency Difference
**Problem**: Raw mode may have different latency than denoised mode  
**Mitigation**: Document this behavior; testing is about functionality, not performance

### Issue 3: User Forgets to Re-enable
**Problem**: User leaves denoise disabled accidentally  
**Mitigation**: Default is enabled; resets on page reload

## Performance Considerations

### With Denoising Enabled (Default)
- CPU: High (DeepFilterNet2 processing)
- Latency: Higher (model inference time)
- Audio Quality: Better (noise removed)

### With Denoising Disabled (Raw Mode)
- CPU: Low (no processing)
- Latency: Lower (direct pass-through)
- Audio Quality: Raw (background noise present)

## Future Enhancements (Out of Scope)

1. **Persistent Setting**: Store in user profile
2. **Mid-stream Toggle**: Allow changing during active stream
3. **Multiple Denoise Levels**: Light/Medium/Heavy/Off
4. **Visual Indicator**: Show denoise status while streaming
5. **Per-listener Setting**: Each listener chooses their own denoise level

## Related Code

### Frontend Files
- `frontend/templates/frontend/main.html`: UI element
- `static/js/main.js`: State management and UI logic
- `static/js/webrtc_client.js`: Pass flag to backend
- `static/css/style.css`: Toggle styling

### Backend Files
- `streams/views.py`: API endpoints handling
- `streams/webrtc_handler.py`: Audio processing logic

### Documentation
- `DENOISE_TOGGLE_TESTING.md`: Comprehensive testing guide
- `IMPLEMENTATION_NOTES.md`: This file

## Conclusion

This implementation provides a **minimal, surgical change** to enable diagnostic testing:
- ✅ Small code footprint (~100 lines changed)
- ✅ No breaking changes to existing functionality
- ✅ Clear separation between denoise/raw modes
- ✅ Comprehensive logging for debugging
- ✅ User-friendly UI that matches existing design

The feature successfully addresses the user's request to test whether the reported issues (timer, listening) are related to denoising or other system components.
