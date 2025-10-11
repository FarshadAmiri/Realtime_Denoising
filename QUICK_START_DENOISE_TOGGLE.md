# Quick Start: Denoise Toggle Feature

## 🎯 What Is This?
A checkbox that lets you turn audio denoising on/off before starting a stream. Use this to test if your audio or timer issues are caused by the denoising process or something else.

## 🚀 Quick Usage

### Option 1: Normal Streaming (With Denoising)
1. Login to your account
2. Go to main page
3. **Leave checkbox CHECKED** ✅ (default)
4. Click "Start Streaming"
5. **Result**: Your audio is denoised (clean, no background noise)

### Option 2: Testing Mode (Without Denoising)
1. Login to your account  
2. Go to main page
3. **UNCHECK the "Enable Denoising" checkbox** ☐
4. Click "Start Streaming"
5. **Result**: Your raw microphone audio is streamed (may have noise)

## 📋 What to Test

### Test the Timer
**Problem**: Timer stuck at 00:00

**Test Steps**:
1. Start streaming (try both modes)
2. Watch the timer for 30 seconds
3. **Expected**: Timer should count: 00:01, 00:02, 00:03...

**Results**:
- Timer works in BOTH modes → Timer is fixed or working correctly
- Timer stuck in BOTH modes → Timer issue not related to denoising
- Timer works ONLY without denoising → Denoising causes timer issue

### Test Friend Listening
**Problem**: Friends cannot hear you

**Test Steps**:
1. You: Start streaming (try one mode first)
2. Friend: Go to your page, click "Start Listening"
3. Friend: Report if they can hear you

**Results**:
- Audio works in BOTH modes → Audio is working correctly
- Audio fails in BOTH modes → WebRTC/network issue (not denoising)
- Audio works ONLY without denoising → DeepFilterNet processing issue

## 🎨 UI Behavior

### Before Streaming
```
┌─────────────────────────────────┐
│ Welcome, YourName               │
│                                 │
│ ☑ Enable Denoising             │  ← Checkbox visible
│ [Start Streaming]               │
└─────────────────────────────────┘
```

### During Streaming
```
┌─────────────────────────────────┐
│ Welcome, YourName               │
│                                 │
│ [Stop Streaming     00:05]      │  ← No checkbox
│ ● Streaming now                 │
└─────────────────────────────────┘
```

## 🔍 Expected Logs

### Console (Browser)
**With Denoising:**
```
[Streaming] Initiating start with denoise: true
```

**Without Denoising:**
```
[Streaming] Initiating start with denoise: false
```

### Server Logs
**With Denoising:**
```
Starting stream for user X with denoise=True
[Session xxx] Applied denoising
```

**Without Denoising:**
```
Starting stream for user X with denoise=False
[Session xxx] Bypassing denoising (raw mode)
```

## ❓ FAQ

### Q: Which mode should I use normally?
**A**: Keep denoising ENABLED (checked). It makes your audio clearer.

### Q: Why can't I change it during streaming?
**A**: The setting is applied when you start. To change it, stop and restart streaming.

### Q: Will this fix my timer/audio issues?
**A**: This helps **identify** the cause. It doesn't automatically fix issues, but tells you if denoising is the problem.

### Q: What's the difference between the two modes?
**A**: 
- **Enabled**: Audio → DeepFilterNet → Listeners (clean audio, may be slower)
- **Disabled**: Audio → Directly to Listeners (raw audio, faster)

### Q: Does the setting save between sessions?
**A**: No, it resets to ENABLED (checked) each time you reload the page.

## 🐛 Troubleshooting

### Checkbox doesn't appear
- Refresh the page
- Check browser console for errors
- Verify you're logged in

### Checkbox doesn't disappear when streaming
- Check browser console for JavaScript errors
- Verify streaming actually started (timer should count)

### Setting doesn't seem to take effect
- Check server logs for "denoise=True" or "denoise=False"
- Verify streaming started successfully
- Try stopping and restarting

## 📖 More Information
- **Full Testing Guide**: See `DENOISE_TOGGLE_TESTING.md`
- **Technical Details**: See `IMPLEMENTATION_NOTES.md`

## 🆘 Still Having Issues?

### If timer is stuck:
1. Test with denoise OFF
2. If still stuck → Problem is not denoising (likely JavaScript issue)
3. If works → Denoising causes timer to freeze

### If friends can't hear:
1. Test with denoise OFF  
2. If still can't hear → WebRTC/network problem (not denoising)
3. If works → DeepFilterNet processing issue

### Report Your Findings
When reporting issues, include:
- ✅ Mode tested (denoising on/off)
- ✅ What happened (timer behavior, audio heard or not)
- ✅ Browser console errors (if any)
- ✅ Server logs (if accessible)

---

**Remember**: This feature is for **testing and debugging**. For normal use, keep denoising enabled! 🎤✨
