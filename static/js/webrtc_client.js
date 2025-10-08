/**
 * WebRTC Client for audio streaming
 */

class WebRTCClient {
    constructor() {
        this.pc = null;
        this.localStream = null;
        this.remoteAudio = null;
        this.sessionId = null;
    }

    async startBroadcast() {
        try {
            // Get microphone access
            this.localStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: false, // We do this on server
                    autoGainControl: true
                },
                video: false
            });

            // Create peer connection
            this.pc = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            });

            // Add local stream to peer connection
            this.localStream.getTracks().forEach(track => {
                this.pc.addTrack(track, this.localStream);
            });

            // Create offer
            const offer = await this.pc.createOffer();
            await this.pc.setLocalDescription(offer);

            // Wait for ICE gathering to complete
            await this.waitForIceGathering();

            // Send offer to server
            const response = await fetch('/api/webrtc/offer/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    sdp: this.pc.localDescription.sdp,
                    type: 'offer'
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Set remote description (server's answer)
                await this.pc.setRemoteDescription({
                    type: 'answer',
                    sdp: data.sdp
                });

                this.sessionId = data.session_id;
                return true;
            } else {
                throw new Error(data.error || 'Failed to start broadcast');
            }

        } catch (error) {
            console.error('Error starting broadcast:', error);
            this.stopBroadcast();
            throw error;
        }
    }

    async startListening(username, audioElement) {
        try {
            this.remoteAudio = audioElement;

            // Create peer connection
            this.pc = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            });

            // Handle incoming audio track
            this.pc.ontrack = (event) => {
                console.log('Received remote track');
                if (event.streams && event.streams[0]) {
                    this.remoteAudio.srcObject = event.streams[0];
                }
            };

            // Create offer
            const offer = await this.pc.createOffer({
                offerToReceiveAudio: true
            });
            await this.pc.setLocalDescription(offer);

            // Wait for ICE gathering
            await this.waitForIceGathering();

            // Send offer to server
            const response = await fetch(`/api/webrtc/listen/${username}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    sdp: this.pc.localDescription.sdp,
                    type: 'offer'
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Set remote description (server's answer)
                await this.pc.setRemoteDescription({
                    type: 'answer',
                    sdp: data.sdp
                });

                return true;
            } else {
                throw new Error(data.error || 'Failed to start listening');
            }

        } catch (error) {
            console.error('Error starting listening:', error);
            this.stopListening();
            throw error;
        }
    }

    stopBroadcast() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }

        this.sessionId = null;
    }

    stopListening() {
        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }

        if (this.remoteAudio) {
            this.remoteAudio.srcObject = null;
            this.remoteAudio = null;
        }
    }

    waitForIceGathering() {
        return new Promise((resolve) => {
            if (this.pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                const checkState = () => {
                    if (this.pc.iceGatheringState === 'complete') {
                        this.pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                this.pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }
}
