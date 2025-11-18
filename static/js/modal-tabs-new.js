// ===== MODAL TABS JS - v1720 =====
console.log('modal-tabs.js loaded - v1720');

// ===== GLOBAL DELETE FILE VARIABLES =====
let deleteVocalFileId = null;
let deleteVocalFileName = '';
let deleteDenoiseFileId = null;
let deleteDenoiseFileName = '';
let deleteBoostFileId = null;
let deleteBoostFileName = '';

// ===== DENOISE MODEL PREFERENCE =====
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ===== GLOBAL DELETE MODAL FUNCTIONS =====
window.closeDeleteFileModal = function() {
    const modal = document.getElementById('delete-file-modal');
    if (modal) {
        modal.classList.remove('active');
    }
    // Reset all delete file IDs
    deleteVocalFileId = null;
    deleteVocalFileName = '';
    deleteDenoiseFileId = null;
    deleteDenoiseFileName = '';
    deleteBoostFileId = null;
    deleteBoostFileName = '';
};

window.confirmDeleteFile = function() {
    if (deleteVocalFileId) {
        confirmDeleteVocalFile();
    } else if (deleteDenoiseFileId) {
        confirmDeleteDenoiseFile();
    } else if (deleteBoostFileId) {
        confirmDeleteBoostFile();
    }
};

// ===== DENOISE BOOST TOGGLE =====
let isBoostEnabled = false;

window.handleBoostContainerClick = function(event) {
    const slider = document.getElementById('denoise-boost-level');
    
    // If boost is active and click is on slider, don't toggle - let slider work
    if (isBoostEnabled && event.target === slider) {
        return;
    }
    
    // Toggle boost on/off
    toggleDenoiseBoost();
};

function toggleDenoiseBoost() {
    const container = document.getElementById('volume-boost-container');
    const label = document.getElementById('boost-label-toggle');
    const slider = document.getElementById('denoise-boost-level');
    
    // Toggle state
    isBoostEnabled = !isBoostEnabled;
    
    // Update container appearance
    if (isBoostEnabled) {
        container.classList.add('active');
    } else {
        container.classList.remove('active');
    }
    
    // Update slider state
    slider.disabled = !isBoostEnabled;
}

// Update boost label when slider changes
window.updateBoostLabel = function() {
    const slider = document.getElementById('denoise-boost-level');
    const label = document.getElementById('denoise-boost-value');
    label.textContent = slider.value + 'x';
};

// Update boost tab label when slider changes
function updateBoostTabLabel() {
    const slider = document.getElementById('boost-level');
    const label = document.getElementById('boost-level-value');
    label.textContent = slider.value + 'x';
}

// ===== SPEAKER EXTRACTION BOOST TOGGLE =====
let isSpeakerBoostEnabled = false;

window.handleSpeakerBoostContainerClick = function(event) {
    const slider = document.getElementById('speaker-boost-level');
    
    // If boost is active and click is on slider, don't toggle - let slider work
    if (isSpeakerBoostEnabled && event.target === slider) {
        return;
    }
    
    // Toggle boost on/off
    toggleSpeakerBoost();
};

function toggleSpeakerBoost() {
    const container = document.getElementById('speaker-volume-boost-container');
    const slider = document.getElementById('speaker-boost-level');
    
    // Toggle state
    isSpeakerBoostEnabled = !isSpeakerBoostEnabled;
    
    // Update container appearance
    if (isSpeakerBoostEnabled) {
        container.classList.add('active');
    } else {
        container.classList.remove('active');
    }
    
    // Update slider state
    slider.disabled = !isSpeakerBoostEnabled;
}

// Update speaker boost label when slider changes
window.updateSpeakerBoostLabel = function() {
    const slider = document.getElementById('speaker-boost-level');
    const label = document.getElementById('speaker-boost-value');
    label.textContent = slider.value + 'x';
};

// ===== DENOISE FILE INPUT HANDLING =====
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
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);
        
        wrapper.classList.add('has-file');
        mainText.textContent = fileName;
        subText.textContent = `${fileSize} MB`;
        clearBtn.style.display = 'flex';
        icon.textContent = '✅';
    } else {
        wrapper.classList.remove('has-file');
        mainText.textContent = 'Choose an audio file';
        subText.textContent = 'WAV, MP3, FLAC, OGG, M4A';
        clearBtn.style.display = 'none';
        icon.textContent = '📁';
    }
}

// File input change listener
document.addEventListener('DOMContentLoaded', function() {
    const audioFileInput = document.getElementById('audio-file-input');
    if (audioFileInput) {
        audioFileInput.addEventListener('change', updateFileInputUI);
    }
});

// ===== DENOISE POLLING FOR UPDATES (defined early for use in switchModalTab) =====
let denoisePollingInterval = null;

function startDenoisePolling() {
    if (denoisePollingInterval) return; // Already polling
    
    denoisePollingInterval = setInterval(async () => {
        try {
            const resp = await fetch('/api/denoise/files/', { credentials: 'same-origin' });
            if (resp.ok) {
                const data = await resp.json();
                const hasProcessing = data.files && data.files.some(f => f.status === 'processing' || f.status === 'pending');
                
                // Refresh the list
                if (typeof refreshDenoiseFilesList === 'function') {
                    await refreshDenoiseFilesList();
                }
                
                // Stop polling if nothing is processing
                if (!hasProcessing) {
                    stopDenoisePolling();
                }
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 3000); // Poll every 3 seconds
}

function stopDenoisePolling() {
    if (denoisePollingInterval) {
        clearInterval(denoisePollingInterval);
        denoisePollingInterval = null;
    }
}

// ===== MODAL TAB SWITCHING =====
window.switchModalTab = function(tabName) {
    // Hide all tabs
    document.querySelectorAll('.modal-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.modal-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Show selected tab
    const targetTab = document.querySelector(`.modal-tab[data-tab="${tabName}"]`);
    const targetContent = document.getElementById(`${tabName}-tab-content`);
    
    if (targetTab) targetTab.classList.add('active');
    if (targetContent) targetContent.classList.add('active');
    
    // Refresh data for the selected tab
    if (tabName === 'denoise') {
        if (typeof refreshDenoiseFilesList === 'function') {
            refreshDenoiseFilesList();
        }
        // Check if we need to start polling for processing files
        setTimeout(() => {
            fetch('/api/denoise/files/', { credentials: 'same-origin' })
                .then(resp => resp.json())
                .then(data => {
                    const hasProcessing = data.files && data.files.some(f => f.status === 'processing' || f.status === 'pending');
                    if (hasProcessing && typeof startDenoisePolling === 'function') {
                        startDenoisePolling();
                    }
                })
                .catch(e => console.error('Error checking for processing files:', e));
        }, 100);
    } else if (tabName === 'vocal') {
        if (typeof refreshVocalFilesList === 'function') {
            refreshVocalFilesList();
        }
    } else if (tabName === 'boost') {
        if (typeof refreshBoostFilesList === 'function') {
            refreshBoostFilesList();
        }
    } else if (tabName === 'speaker') {
        if (typeof refreshSpeakerFilesList === 'function') {
            refreshSpeakerFilesList();
        }
        if (typeof startSpeakerPolling === 'function') {
            startSpeakerPolling();
        }
    } else {
        // Stop speaker polling when switching away
        if (typeof stopSpeakerPolling === 'function') {
            stopSpeakerPolling();
        }
    }
};

// ===== VOCAL SEPARATION TAB FUNCTIONS =====

// Vocal file input handling
function clearVocalFileInput(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const fileInput = document.getElementById('vocal-file-input');
    fileInput.value = '';
    updateVocalFileInputUI();
}

function updateVocalFileInputUI() {
    const fileInput = document.getElementById('vocal-file-input');
    const wrapper = document.getElementById('vocal-file-input-wrapper');
    const mainText = document.getElementById('vocal-file-input-main');
    const subText = document.getElementById('vocal-file-input-sub');
    const clearBtn = document.getElementById('vocal-file-input-clear');
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

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    // Listen for vocal file selection
    const vocalFileInput = document.getElementById('vocal-file-input');
    if (vocalFileInput) {
        vocalFileInput.addEventListener('change', updateVocalFileInputUI);
    }

    // Handle vocal file upload
    const vocalUploadForm = document.getElementById('vocal-upload-form');
    if (vocalUploadForm) {
        vocalUploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('vocal-file-input');
            const statusDiv = document.getElementById('vocal-upload-status');
            
            if (!fileInput.files || !fileInput.files[0]) {
                statusDiv.textContent = 'Please select a file';
                statusDiv.style.color = '#991b1b';
                return;
            }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            statusDiv.textContent = 'Uploading...';
            statusDiv.style.color = '#6b7280';
            
            try {
                const resp = await fetch('/api/vocal/separate/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: formData,
                    credentials: 'same-origin'
                });
                
                if (!resp.ok) {
                    const error = await resp.json();
                    throw new Error(error.error || 'Upload failed');
                }
                
                const data = await resp.json();
                statusDiv.textContent = '✅ Uploaded! Vocal separation will start shortly...';
                statusDiv.style.color = '#059669';
                
                clearVocalFileInput();
                
                // Refresh list after 1 second
                setTimeout(() => {
                    refreshVocalFilesList();
                    statusDiv.textContent = '';
                }, 1000);
                
                // Poll for updates
                startVocalPolling();
                
            } catch (e) {
                statusDiv.textContent = '❌ ' + e.message;
                statusDiv.style.color = '#991b1b';
            }
        });
    }
});

// Refresh vocal files list (matching File Denoise tab UI exactly)
async function refreshVocalFilesList() {
    try {
        const resp = await fetch('/api/vocal/files/', { credentials: 'same-origin' });
        if (!resp.ok) {
            console.error('Failed to fetch vocal files');
            return;
        }
        const data = await resp.json();
        const list = document.getElementById('vocal-files-list');
        
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
            item.style.gap = '0.5rem';
            item.style.padding = '0.65rem';
            
            const header = document.createElement('div');
            header.style.width = '100%';
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            header.style.marginBottom = '0.35rem';
            
            const leftHeader = document.createElement('div');
            leftHeader.style.display = 'flex';
            leftHeader.style.flexDirection = 'column';
            leftHeader.style.gap = '0.15rem';
            leftHeader.style.flex = '1';
            
            const fileName = document.createElement('div');
            fileName.className = 'recording-title';
            fileName.style.fontSize = '0.9rem';
            fileName.textContent = file.original_filename;
            
            const uploadDate = document.createElement('div');
            uploadDate.className = 'muted';
            uploadDate.style.fontSize = '0.75rem';
            uploadDate.textContent = new Date(file.uploaded_at).toLocaleString();
            
            leftHeader.appendChild(fileName);
            leftHeader.appendChild(uploadDate);
            
            // Delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn-delete-file';
            deleteBtn.textContent = '❌';
            deleteBtn.onclick = () => deleteVocalFile(file.id, file.original_filename);
            
            header.appendChild(leftHeader);
            header.appendChild(deleteBtn);
            
            // Original audio row (full width)
            const originalRow = document.createElement('div');
            originalRow.style.display = 'flex';
            originalRow.style.width = '100%';
            originalRow.style.marginBottom = '0.5rem';
            
            const originalBox = document.createElement('div');
            originalBox.style.flex = '1';
            const originalLabel = document.createElement('div');
            originalLabel.className = 'muted';
            originalLabel.style.fontSize = '0.75rem';
            originalLabel.style.marginBottom = '0.2rem';
            originalLabel.textContent = '📁 Original';
            const originalAudio = document.createElement('audio');
            originalAudio.controls = true;
            originalAudio.preload = 'none';
            originalAudio.style.width = '100%';
            originalAudio.style.height = '32px';
            const originalSrc = document.createElement('source');
            originalSrc.src = file.original_file_url;
            originalSrc.type = 'audio/mpeg';
            originalAudio.appendChild(originalSrc);
            originalBox.appendChild(originalLabel);
            originalBox.appendChild(originalAudio);
            originalRow.appendChild(originalBox);
            
            // Separated audio files row (vocals + instrumental side by side)
            const separatedRow = document.createElement('div');
            separatedRow.style.display = 'flex';
            separatedRow.style.gap = '0.75rem';
            separatedRow.style.flexWrap = 'wrap';
            separatedRow.style.width = '100%';
            
            // Vocals file
            const vocalsBox = document.createElement('div');
            vocalsBox.style.flex = '1 1 250px';
            vocalsBox.style.minWidth = '250px';
            const vocalsLabel = document.createElement('div');
            vocalsLabel.className = 'muted';
            vocalsLabel.style.fontSize = '0.75rem';
            vocalsLabel.style.marginBottom = '0.2rem';
            vocalsLabel.textContent = '🎤 Vocals';
            
            if (file.status === 'completed' && file.vocals_url) {
                const vocalsAudio = document.createElement('audio');
                vocalsAudio.controls = true;
                vocalsAudio.preload = 'none';
                vocalsAudio.style.width = '100%';
                vocalsAudio.style.height = '32px';
                const vocalsSrc = document.createElement('source');
                vocalsSrc.src = file.vocals_url;
                vocalsSrc.type = 'audio/mpeg';
                vocalsAudio.appendChild(vocalsSrc);
                vocalsBox.appendChild(vocalsLabel);
                vocalsBox.appendChild(vocalsAudio);
            } else if (file.status === 'processing') {
                const processingMsg = document.createElement('div');
                processingMsg.style.padding = '0.4rem';
                processingMsg.style.background = '#fef3c7';
                processingMsg.style.color = '#92400e';
                processingMsg.style.borderRadius = '6px';
                processingMsg.style.fontSize = '0.8rem';
                processingMsg.textContent = '⏳ In Process...';
                vocalsBox.appendChild(vocalsLabel);
                vocalsBox.appendChild(processingMsg);
            } else if (file.status === 'error') {
                const errorMsg = document.createElement('div');
                errorMsg.style.padding = '0.4rem';
                errorMsg.style.background = '#fee2e2';
                errorMsg.style.color = '#991b1b';
                errorMsg.style.borderRadius = '6px';
                errorMsg.style.fontSize = '0.8rem';
                errorMsg.textContent = '❌ Failed';
                if (file.error_message) {
                    errorMsg.title = file.error_message;
                }
                vocalsBox.appendChild(vocalsLabel);
                vocalsBox.appendChild(errorMsg);
            } else {
                const pendingMsg = document.createElement('div');
                pendingMsg.style.padding = '0.4rem';
                pendingMsg.style.background = '#e0e7ff';
                pendingMsg.style.color = '#3730a3';
                pendingMsg.style.borderRadius = '6px';
                pendingMsg.style.fontSize = '0.8rem';
                pendingMsg.textContent = '⏱️ Pending...';
                vocalsBox.appendChild(vocalsLabel);
                vocalsBox.appendChild(pendingMsg);
            }
            
            // Instrumental file
            const instrumentalBox = document.createElement('div');
            instrumentalBox.style.flex = '1 1 250px';
            instrumentalBox.style.minWidth = '250px';
            const instrumentalLabel = document.createElement('div');
            instrumentalLabel.className = 'muted';
            instrumentalLabel.style.fontSize = '0.75rem';
            instrumentalLabel.style.marginBottom = '0.2rem';
            instrumentalLabel.textContent = '🎹 Instrumental';
            
            if (file.status === 'completed' && file.instrumental_url) {
                const instrumentalAudio = document.createElement('audio');
                instrumentalAudio.controls = true;
                instrumentalAudio.preload = 'none';
                instrumentalAudio.style.width = '100%';
                instrumentalAudio.style.height = '32px';
                const instrumentalSrc = document.createElement('source');
                instrumentalSrc.src = file.instrumental_url;
                instrumentalSrc.type = 'audio/mpeg';
                instrumentalAudio.appendChild(instrumentalSrc);
                instrumentalBox.appendChild(instrumentalLabel);
                instrumentalBox.appendChild(instrumentalAudio);
            } else if (file.status === 'processing') {
                const processingMsg = document.createElement('div');
                processingMsg.style.padding = '0.4rem';
                processingMsg.style.background = '#fef3c7';
                processingMsg.style.color = '#92400e';
                processingMsg.style.borderRadius = '6px';
                processingMsg.style.fontSize = '0.8rem';
                processingMsg.textContent = '⏳ In Process...';
                instrumentalBox.appendChild(instrumentalLabel);
                instrumentalBox.appendChild(processingMsg);
            } else if (file.status === 'error') {
                const errorMsg = document.createElement('div');
                errorMsg.style.padding = '0.4rem';
                errorMsg.style.background = '#fee2e2';
                errorMsg.style.color = '#991b1b';
                errorMsg.style.borderRadius = '6px';
                errorMsg.style.fontSize = '0.8rem';
                errorMsg.textContent = '❌ Failed';
                if (file.error_message) {
                    errorMsg.title = file.error_message;
                }
                instrumentalBox.appendChild(instrumentalLabel);
                instrumentalBox.appendChild(errorMsg);
            } else {
                const pendingMsg = document.createElement('div');
                pendingMsg.style.padding = '0.4rem';
                pendingMsg.style.background = '#e0e7ff';
                pendingMsg.style.color = '#3730a3';
                pendingMsg.style.borderRadius = '6px';
                pendingMsg.style.fontSize = '0.8rem';
                pendingMsg.textContent = '⏱️ Pending...';
                instrumentalBox.appendChild(instrumentalLabel);
                instrumentalBox.appendChild(pendingMsg);
            }
            
            separatedRow.appendChild(vocalsBox);
            separatedRow.appendChild(instrumentalBox);
            
            item.appendChild(header);
            item.appendChild(originalRow);
            item.appendChild(separatedRow);
            list.appendChild(item);
        });
    } catch (e) {
        console.error('Error refreshing vocal files:', e);
    }
}

// Poll for vocal processing updates
let vocalPollingInterval = null;

function startVocalPolling() {
    if (vocalPollingInterval) return;
    
    vocalPollingInterval = setInterval(async () => {
        const resp = await fetch('/api/vocal/files/', { credentials: 'same-origin' });
        if (resp.ok) {
            const data = await resp.json();
            const hasProcessing = data.files && data.files.some(f => f.status === 'processing' || f.status === 'pending');
            
            if (!hasProcessing) {
                clearInterval(vocalPollingInterval);
                vocalPollingInterval = null;
            }
            
            refreshVocalFilesList();
        }
    }, 3000);
}

// Delete vocal file
function deleteVocalFile(fileId, filename) {
    deleteVocalFileId = fileId;
    deleteVocalFileName = filename;
    document.getElementById('delete-file-name').textContent = filename;
    document.getElementById('delete-file-modal').classList.add('active');
}

async function confirmDeleteVocalFile() {
    if (!deleteVocalFileId) return;
    
    try {
        const resp = await fetch(`/api/vocal/files/${deleteVocalFileId}/delete/`, {
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
        
        closeDeleteFileModal();
        await refreshVocalFilesList();
        
    } catch (e) {
        closeDeleteFileModal();
        const statusDiv = document.getElementById('vocal-upload-status');
        statusDiv.textContent = '❌ Error deleting file: ' + e.message;
        statusDiv.style.color = '#991b1b';
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 5000);
        console.error('Delete error:', e);
    }
}

// Update confirmDeleteFile to handle both denoise and vocal files
document.addEventListener('DOMContentLoaded', function() {
    const originalConfirmDeleteFile = window.confirmDeleteFile;
    if (originalConfirmDeleteFile) {
        window.confirmDeleteFile = function() {
            if (deleteVocalFileId) {
                confirmDeleteVocalFile();
            } else {
                originalConfirmDeleteFile();
            }
        };
    }
});

// ===== DENOISE FILE UPLOAD =====
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    if (!uploadForm) return;
    
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const fileInput = document.getElementById('audio-file-input');
        const boostSlider = document.getElementById('denoise-boost-level');
        const statusDiv = document.getElementById('upload-status');
        
        if (!fileInput.files || !fileInput.files[0]) {
            statusDiv.textContent = '❌ Please select a file';
            statusDiv.style.color = '#991b1b';
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        // Add boost level if enabled
        if (isBoostEnabled) {
            formData.append('boost_level', boostSlider.value + 'x');
        } else {
            formData.append('boost_level', 'none');
        }
        
        statusDiv.textContent = '⏳ Uploading...';
        statusDiv.style.color = '#3730a3';
        
        try {
            const resp = await fetch('/api/denoise/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'same-origin'
            });
            
            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.error || 'Upload failed');
            }
            
            const data = await resp.json();
            statusDiv.textContent = '✅ Upload successful! Processing started...';
            statusDiv.style.color = '#065f46';
            
            // Clear form
            fileInput.value = '';
            if (typeof updateFileInputUI === 'function') {
                updateFileInputUI();
            }
            
            // Refresh list
            await refreshDenoiseFilesList();
            
            // Start polling for updates
            startDenoisePolling();
            
            setTimeout(() => {
                statusDiv.textContent = '';
            }, 3000);
            
        } catch (e) {
            statusDiv.textContent = '❌ Error: ' + e.message;
            statusDiv.style.color = '#991b1b';
            console.error('Upload error:', e);
        }
    });
});

// ===== DENOISE FILES LIST REFRESH =====
window.refreshDenoiseFilesList = async function refreshDenoiseFilesList() {
    const list = document.getElementById('denoise-files-list');
    if (!list) return;
    
    console.log('[DENOISE] refreshDenoiseFilesList called');
    
    try {
        const resp = await fetch('/api/denoise/files/', {
            credentials: 'same-origin'
        });
        
        if (!resp.ok) throw new Error('Failed to fetch files');
        
        const data = await resp.json();
        const files = data.files || [];
        
        console.log('[DENOISE] Files received from API:', files);
        
        if (files.length === 0) {
            list.innerHTML = '<div class="empty">No files yet</div>';
            return;
        }
        
        list.innerHTML = '';
        
        files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'recording-item';
            item.style.display = 'flex';
            item.style.flexDirection = 'column';
            item.style.gap = '0.5rem';
            item.style.padding = '0.65rem';
            item.style.marginBottom = '0.4rem';
            
            // Header with file name and delete button
            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            header.style.width = '100%';
            header.style.marginBottom = '0.35rem';
            
            const leftHeader = document.createElement('div');
            leftHeader.style.flex = '1';
            
            const fileName = document.createElement('div');
            fileName.className = 'recording-title';
            fileName.style.fontSize = '0.9rem';
            fileName.textContent = file.original_filename;
            
            const uploadDate = document.createElement('div');
            uploadDate.className = 'muted';
            uploadDate.style.fontSize = '0.75rem';
            uploadDate.textContent = new Date(file.uploaded_at).toLocaleString();
            
            leftHeader.appendChild(fileName);
            leftHeader.appendChild(uploadDate);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn-delete-file';
            deleteBtn.textContent = '❌';
            deleteBtn.onclick = () => deleteDenoiseFile(file.id, file.original_filename);
            
            header.appendChild(leftHeader);
            header.appendChild(deleteBtn);
            
            // Audio players section - full width layout
            const audiosContainer = document.createElement('div');
            audiosContainer.style.display = 'flex';
            audiosContainer.style.flexDirection = 'column';
            audiosContainer.style.gap = '0.5rem';
            audiosContainer.style.width = '100%';
            
            // Original audio - full width
            const originalBox = document.createElement('div');
            originalBox.style.width = '100%';
            
            const originalLabel = document.createElement('div');
            originalLabel.className = 'muted';
            originalLabel.style.fontSize = '0.75rem';
            originalLabel.style.marginBottom = '0.2rem';
            originalLabel.textContent = '📁 Original';
            
            const originalAudio = document.createElement('audio');
            originalAudio.controls = true;
            originalAudio.preload = 'none';
            originalAudio.style.width = '100%';
            originalAudio.style.height = '32px';
            const originalSrc = document.createElement('source');
            originalSrc.src = file.original_file_url;
            originalSrc.type = 'audio/mpeg';
            originalAudio.appendChild(originalSrc);
            
            originalBox.appendChild(originalLabel);
            originalBox.appendChild(originalAudio);
            
            // Denoised audio - full width
            const denoisedBox = document.createElement('div');
            denoisedBox.style.width = '100%';
            
            const denoisedLabel = document.createElement('div');
            denoisedLabel.className = 'muted';
            denoisedLabel.style.fontSize = '0.75rem';
            denoisedLabel.style.marginBottom = '0.2rem';
            
            // Show volume boost info if applied
            console.log(`[DENOISE] File "${file.original_filename}": boost_level="${file.boost_level}", status="${file.status}"`);
            if (file.boost_level && file.boost_level !== 'none') {
                denoisedLabel.textContent = `✨ Denoised + 🔊 ${file.boost_level} Boost`;
                console.log(`[DENOISE] Applied boost label: ${denoisedLabel.textContent}`);
            } else {
                denoisedLabel.textContent = '✨ Denoised';
                console.log(`[DENOISE] No boost applied`);
            }
            
            if (file.status === 'completed' && file.denoised_file_url) {
                const denoisedAudio = document.createElement('audio');
                denoisedAudio.controls = true;
                denoisedAudio.preload = 'none';
                denoisedAudio.style.width = '100%';
                denoisedAudio.style.height = '32px';
                const denoisedSrc = document.createElement('source');
                denoisedSrc.src = file.denoised_file_url;
                denoisedSrc.type = 'audio/mpeg';
                denoisedAudio.appendChild(denoisedSrc);
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(denoisedAudio);
            } else if (file.status === 'processing') {
                const processingMsg = document.createElement('div');
                processingMsg.style.padding = '0.4rem';
                processingMsg.style.background = '#fef3c7';
                processingMsg.style.color = '#92400e';
                processingMsg.style.borderRadius = '6px';
                processingMsg.style.fontSize = '0.8rem';
                processingMsg.textContent = '⏳ Processing...';
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(processingMsg);
            } else if (file.status === 'failed') {
                const errorMsg = document.createElement('div');
                errorMsg.style.padding = '0.4rem';
                errorMsg.style.background = '#fee2e2';
                errorMsg.style.color = '#991b1b';
                errorMsg.style.borderRadius = '6px';
                errorMsg.style.fontSize = '0.8rem';
                errorMsg.textContent = '❌ Failed';
                if (file.error_message) {
                    errorMsg.title = file.error_message;
                }
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(errorMsg);
            } else {
                const pendingMsg = document.createElement('div');
                pendingMsg.style.padding = '0.4rem';
                pendingMsg.style.background = '#e0e7ff';
                pendingMsg.style.color = '#3730a3';
                pendingMsg.style.borderRadius = '6px';
                pendingMsg.style.fontSize = '0.8rem';
                pendingMsg.textContent = '⏱️ Pending...';
                denoisedBox.appendChild(denoisedLabel);
                denoisedBox.appendChild(pendingMsg);
            }
            
            audiosContainer.appendChild(originalBox);
            audiosContainer.appendChild(denoisedBox);
            
            item.appendChild(header);
            item.appendChild(audiosContainer);
            list.appendChild(item);
        });
        
    } catch (e) {
        console.error('Error refreshing denoise files:', e);
        list.innerHTML = '<div class="empty" style="color: #991b1b;">Error loading files</div>';
    }
}

function deleteDenoiseFile(fileId, filename) {
    deleteDenoiseFileId = fileId;
    deleteDenoiseFileName = filename;
    document.getElementById('delete-file-name').textContent = filename;
    document.getElementById('delete-file-modal').classList.add('active');
}

async function confirmDeleteDenoiseFile() {
    if (!deleteDenoiseFileId) return;
    
    try {
        const resp = await fetch(`/api/denoise/files/${deleteDenoiseFileId}/delete/`, {
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
        
        closeDeleteFileModal();
        await refreshDenoiseFilesList();
        
    } catch (e) {
        closeDeleteFileModal();
        const statusDiv = document.getElementById('upload-status');
        statusDiv.textContent = '❌ Error deleting file: ' + e.message;
        statusDiv.style.color = '#991b1b';
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 5000);
        console.error('Delete error:', e);
    }
}

// Update the confirm delete function to handle all file types
if (typeof window.confirmDeleteFile === 'undefined') {
    window.confirmDeleteFile = function() {
        if (deleteVocalFileId) {
            confirmDeleteVocalFile();
        } else if (deleteDenoiseFileId) {
            confirmDeleteDenoiseFile();
        } else if (deleteBoostFileId) {
            confirmDeleteBoostFile();
        }
    };
}

// ===== AUDIO BOOST TAB FUNCTIONS =====

// Boost file input handling
function clearBoostFileInput(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const fileInput = document.getElementById('boost-file-input');
    fileInput.value = '';
    updateBoostFileInputUI();
}

function updateBoostFileInputUI() {
    const fileInput = document.getElementById('boost-file-input');
    const wrapper = document.getElementById('boost-file-input-wrapper');
    const mainText = document.getElementById('boost-file-input-main');
    const subText = document.getElementById('boost-file-input-sub');
    const clearBtn = document.getElementById('boost-file-input-clear');
    const icon = wrapper.querySelector('.file-input-icon');
    
    if (fileInput.files && fileInput.files[0]) {
        const file = fileInput.files[0];
        const fileName = file.name;
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);
        
        wrapper.classList.add('has-file');
        mainText.textContent = fileName;
        subText.textContent = `${fileSize} MB`;
        clearBtn.style.display = 'flex';
        icon.textContent = '✅';
    } else {
        wrapper.classList.remove('has-file');
        mainText.textContent = 'Choose an audio file';
        subText.textContent = 'WAV, MP3, FLAC, OGG, M4A';
        clearBtn.style.display = 'none';
        icon.textContent = '📁';
    }
}

// File input change listener
document.addEventListener('DOMContentLoaded', function() {
    const boostFileInput = document.getElementById('boost-file-input');
    if (boostFileInput) {
        boostFileInput.addEventListener('change', updateBoostFileInputUI);
    }
});

// Upload form submission
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('boost-upload-form');
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const fileInput = document.getElementById('boost-file-input');
        const boostSlider = document.getElementById('boost-level');
        const statusDiv = document.getElementById('boost-upload-status');
        
        if (!fileInput.files || !fileInput.files[0]) {
            statusDiv.textContent = '❌ Please select a file';
            statusDiv.style.color = '#991b1b';
            return;
        }
        
        // Map slider values (2-5) to boost levels
        const boostLevelMap = {
            '2': 'gentle',
            '3': 'medium',
            '4': 'strong',
            '5': 'max'
        };
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('boost_level', boostLevelMap[boostSlider.value]);
        
        statusDiv.textContent = '⏳ Uploading...';
        statusDiv.style.color = '#3730a3';
        
        try {
            const resp = await fetch('/api/boost/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'same-origin'
            });
            
            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.error || 'Upload failed');
            }
            
            const data = await resp.json();
            statusDiv.textContent = '✅ Upload successful! Processing started...';
            statusDiv.style.color = '#065f46';
            
            // Clear form
            fileInput.value = '';
            updateBoostFileInputUI();
            
            // Refresh list and start polling
            await refreshBoostFilesList();
            startBoostPolling();
            
            setTimeout(() => {
                statusDiv.textContent = '';
            }, 3000);
            
        } catch (e) {
            statusDiv.textContent = '❌ Error: ' + e.message;
            statusDiv.style.color = '#991b1b';
            console.error('Upload error:', e);
        }
    });
});

// Refresh boost files list
async function refreshBoostFilesList() {
    const list = document.getElementById('boost-files-list');
    if (!list) return;
    
    try {
        const resp = await fetch('/api/boost/files/', {
            credentials: 'same-origin'
        });
        
        if (!resp.ok) throw new Error('Failed to fetch files');
        
        const data = await resp.json();
        const files = data.files || [];
        
        if (files.length === 0) {
            list.innerHTML = '<div class="empty">No files yet</div>';
            return;
        }
        
        list.innerHTML = '';
        
        files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'recording-item';
            item.style.flexDirection = 'column';
            item.style.alignItems = 'stretch';
            item.style.gap = '0.5rem';
            item.style.padding = '0.65rem';
            
            const header = document.createElement('div');
            header.style.width = '100%';
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            header.style.marginBottom = '0.35rem';
            
            const leftHeader = document.createElement('div');
            leftHeader.style.display = 'flex';
            leftHeader.style.flexDirection = 'column';
            leftHeader.style.gap = '0.15rem';
            leftHeader.style.flex = '1';
            
            const fileName = document.createElement('div');
            fileName.className = 'recording-title';
            fileName.style.fontSize = '0.9rem';
            fileName.textContent = file.original_filename;
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'muted';
            fileInfo.style.fontSize = '0.75rem';
            
            // Map boost levels to display labels
            const boostLevelMap = {
                'gentle': '2x',
                'medium': '3x',
                'strong': '4x',
                'max': '5x'
            };
            
            const boostLabel = boostLevelMap[file.boost_level] || '3x';
            fileInfo.textContent = `🔊 ${boostLabel} Volume • ${new Date(file.uploaded_at).toLocaleString()}`;
            
            leftHeader.appendChild(fileName);
            leftHeader.appendChild(fileInfo);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn-delete-file';
            deleteBtn.textContent = '❌';
            deleteBtn.onclick = () => deleteBoostFile(file.id, file.original_filename);
            
            header.appendChild(leftHeader);
            header.appendChild(deleteBtn);
            
            // Original audio row (full width)
            const originalRow = document.createElement('div');
            originalRow.style.display = 'flex';
            originalRow.style.width = '100%';
            originalRow.style.marginBottom = '0.5rem';
            
            const originalBox = document.createElement('div');
            originalBox.style.flex = '1';
            const originalLabel = document.createElement('div');
            originalLabel.className = 'muted';
            originalLabel.style.fontSize = '0.75rem';
            originalLabel.style.marginBottom = '0.2rem';
            originalLabel.textContent = '📁 Original';
            const originalAudio = document.createElement('audio');
            originalAudio.controls = true;
            originalAudio.preload = 'none';
            originalAudio.style.width = '100%';
            originalAudio.style.height = '32px';
            const originalSrc = document.createElement('source');
            originalSrc.src = file.original_file_url;
            originalSrc.type = 'audio/mpeg';
            originalAudio.appendChild(originalSrc);
            originalBox.appendChild(originalLabel);
            originalBox.appendChild(originalAudio);
            originalRow.appendChild(originalBox);
            
            // Boosted audio row (full width)
            const boostedRow = document.createElement('div');
            boostedRow.style.display = 'flex';
            boostedRow.style.width = '100%';
            
            const boostedBox = document.createElement('div');
            boostedBox.style.flex = '1';
            const boostedLabel = document.createElement('div');
            boostedLabel.className = 'muted';
            boostedLabel.style.fontSize = '0.75rem';
            boostedLabel.style.marginBottom = '0.2rem';
            boostedLabel.textContent = '🔊 Boosted';
            
            if (file.status === 'completed' && file.boosted_file_url) {
                const boostedAudio = document.createElement('audio');
                boostedAudio.controls = true;
                boostedAudio.preload = 'none';
                boostedAudio.style.width = '100%';
                boostedAudio.style.height = '32px';
                const boostedSrc = document.createElement('source');
                boostedSrc.src = file.boosted_file_url;
                boostedSrc.type = 'audio/mpeg';
                boostedAudio.appendChild(boostedSrc);
                boostedBox.appendChild(boostedLabel);
                boostedBox.appendChild(boostedAudio);
            } else if (file.status === 'processing') {
                const processingMsg = document.createElement('div');
                processingMsg.style.padding = '0.4rem';
                processingMsg.style.background = '#fef3c7';
                processingMsg.style.color = '#92400e';
                processingMsg.style.borderRadius = '6px';
                processingMsg.style.fontSize = '0.8rem';
                processingMsg.textContent = '⏳ Processing...';
                boostedBox.appendChild(boostedLabel);
                boostedBox.appendChild(processingMsg);
            } else if (file.status === 'error') {
                const errorMsg = document.createElement('div');
                errorMsg.style.padding = '0.4rem';
                errorMsg.style.background = '#fee2e2';
                errorMsg.style.color = '#991b1b';
                errorMsg.style.borderRadius = '6px';
                errorMsg.style.fontSize = '0.8rem';
                errorMsg.textContent = '❌ Failed';
                if (file.error_message) {
                    errorMsg.title = file.error_message;
                }
                boostedBox.appendChild(boostedLabel);
                boostedBox.appendChild(errorMsg);
            } else {
                const pendingMsg = document.createElement('div');
                pendingMsg.style.padding = '0.4rem';
                pendingMsg.style.background = '#e0e7ff';
                pendingMsg.style.color = '#3730a3';
                pendingMsg.style.borderRadius = '6px';
                pendingMsg.style.fontSize = '0.8rem';
                pendingMsg.textContent = '⏱️ Pending...';
                boostedBox.appendChild(boostedLabel);
                boostedBox.appendChild(pendingMsg);
            }
            
            boostedRow.appendChild(boostedBox);
            
            item.appendChild(header);
            item.appendChild(originalRow);
            item.appendChild(boostedRow);
            list.appendChild(item);
        });
        
    } catch (e) {
        console.error('Error refreshing boost files:', e);
        list.innerHTML = '<div class="empty" style="color: #991b1b;">Error loading files</div>';
    }
}

function deleteBoostFile(fileId, filename) {
    deleteBoostFileId = fileId;
    deleteBoostFileName = filename;
    document.getElementById('delete-file-name').textContent = filename;
    document.getElementById('delete-file-modal').classList.add('active');
}

async function confirmDeleteBoostFile() {
    if (!deleteBoostFileId) return;
    
    try {
        const resp = await fetch(`/api/boost/files/${deleteBoostFileId}/delete/`, {
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
        
        closeDeleteFileModal();
        await refreshBoostFilesList();
        
    } catch (e) {
        closeDeleteFileModal();
        const statusDiv = document.getElementById('boost-upload-status');
        statusDiv.textContent = '❌ Error deleting file: ' + e.message;
        statusDiv.style.color = '#991b1b';
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 5000);
        console.error('Delete error:', e);
    }
}

// Polling for processing files
let boostPollingInterval = null;

function startBoostPolling() {
    if (boostPollingInterval) return;
    
    boostPollingInterval = setInterval(async () => {
        const list = document.getElementById('boost-files-list');
        if (!list || !document.getElementById('boost-tab-content').classList.contains('active')) {
            stopBoostPolling();
            return;
        }
        
        await refreshBoostFilesList();
    }, 3000);
}

function stopBoostPolling() {
    if (boostPollingInterval) {
        clearInterval(boostPollingInterval);
        boostPollingInterval = null;
    }
}

// ===== SPEAKER EXTRACTION TAB =====
let deleteSpeakerFileId = null;
let deleteSpeakerFileName = '';

window.handleSpeakerBoostContainerClick = function(event) {
    const slider = document.getElementById('speaker-boost-level');
    
    // If boost is active and click is on slider, don't toggle - let slider work
    if (isSpeakerBoostEnabled && event.target === slider) {
        return;
    }
    
    // Toggle boost on/off
    toggleSpeakerBoost();
};

function toggleSpeakerBoost() {
    const container = document.getElementById('speaker-volume-boost-container');
    const slider = document.getElementById('speaker-boost-level');
    
    // Toggle state
    isSpeakerBoostEnabled = !isSpeakerBoostEnabled;
    
    // Update container appearance
    if (isSpeakerBoostEnabled) {
        container.classList.add('active');
    } else {
        container.classList.remove('active');
    }
    
    // Update slider state
    slider.disabled = !isSpeakerBoostEnabled;
}

window.updateSpeakerBoostLabel = function() {
    const slider = document.getElementById('speaker-boost-level');
    const label = document.getElementById('speaker-boost-value');
    label.textContent = slider.value + 'x';
};

window.clearSpeakerConversationInput = function(event) {
    event.preventDefault();
    event.stopPropagation();
    const input = document.getElementById('speaker-conversation-input');
    input.value = '';
    document.getElementById('speaker-conversation-main').textContent = 'Conversation audio';
    document.getElementById('speaker-conversation-sub').textContent = 'The multi-speaker recording';
    document.getElementById('speaker-conversation-clear').style.display = 'none';
};

window.clearSpeakerTargetInput = function(event) {
    event.preventDefault();
    event.stopPropagation();
    const input = document.getElementById('speaker-target-input');
    input.value = '';
    document.getElementById('speaker-target-main').textContent = 'Target speaker sample';
    document.getElementById('speaker-target-sub').textContent = 'Voice sample of person to extract';
    document.getElementById('speaker-target-clear').style.display = 'none';
};

// Initialize speaker extraction form handlers
(function initSpeakerExtractionHandlers() {
    const conversationInput = document.getElementById('speaker-conversation-input');
    const targetInput = document.getElementById('speaker-target-input');
    
    if (conversationInput) {
        conversationInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('speaker-conversation-main').textContent = file.name;
                document.getElementById('speaker-conversation-sub').textContent = formatFileSize(file.size);
                document.getElementById('speaker-conversation-clear').style.display = 'block';
            }
        });
    }
    
    if (targetInput) {
        targetInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('speaker-target-main').textContent = file.name;
                document.getElementById('speaker-target-sub').textContent = formatFileSize(file.size);
                document.getElementById('speaker-target-clear').style.display = 'block';
            }
        });
    }
    
    // Speaker extraction form submit
    const speakerForm = document.getElementById('speaker-upload-form');
    if (speakerForm) {
        speakerForm.addEventListener('submit', handleSpeakerUpload);
    }
})();

async function handleSpeakerUpload(e) {
    e.preventDefault();
    
    const conversationInput = document.getElementById('speaker-conversation-input');
    const targetInput = document.getElementById('speaker-target-input');
    const statusDiv = document.getElementById('speaker-upload-status');
    const boostSlider = document.getElementById('speaker-boost-level');
    
    const conversationFile = conversationInput.files[0];
    const targetFile = targetInput.files[0];
    
    if (!conversationFile || !targetFile) {
        statusDiv.textContent = 'Please select both conversation and target speaker files';
        statusDiv.style.color = '#ef4444';
        return;
    }
    
    const formData = new FormData();
    formData.append('conversation_file', conversationFile);
    formData.append('target_file', targetFile);
    
    // Add boost level if enabled
    if (isSpeakerBoostEnabled) {
        formData.append('boost_level', boostSlider.value + 'x');
    } else {
        formData.append('boost_level', 'none');
    }
    
    statusDiv.textContent = 'Uploading...';
    statusDiv.style.color = '#6b7280';
    
    try {
        const response = await fetch('/api/speaker/extract/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.textContent = 'Upload successful! Processing...';
            statusDiv.style.color = '#10b981';
            
            // Clear form
            clearSpeakerConversationInput(new Event('click'));
            clearSpeakerTargetInput(new Event('click'));
            
            // Refresh list
            await refreshSpeakerFilesList();
            startSpeakerPolling();
            
            setTimeout(() => {
                statusDiv.textContent = '';
            }, 3000);
        } else {
            statusDiv.textContent = data.error || 'Upload failed';
            statusDiv.style.color = '#ef4444';
        }
    } catch (error) {
        statusDiv.textContent = 'Error uploading files';
        statusDiv.style.color = '#ef4444';
        console.error('Upload error:', error);
    }
}

async function refreshSpeakerFilesList() {
    const list = document.getElementById('speaker-files-list');
    if (!list) return;
    
    try {
        const resp = await fetch('/api/speaker/files/', {
            credentials: 'same-origin'
        });
        
        if (!resp.ok) throw new Error('Failed to fetch files');
        
        const data = await resp.json();
        const files = data.files || [];
        
        if (files.length === 0) {
            list.innerHTML = '<div class="empty">No files yet</div>';
            return;
        }
        
        list.innerHTML = '';
        
        files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'recording-item';
            item.style.display = 'flex';
            item.style.flexDirection = 'column';
            item.style.gap = '0.5rem';
            item.style.padding = '0.65rem';
            item.style.marginBottom = '0.4rem';
            
            // Header with file name and delete button
            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            header.style.width = '100%';
            header.style.marginBottom = '0.35rem';
            
            const leftHeader = document.createElement('div');
            leftHeader.style.flex = '1';
            
            const fileName = document.createElement('div');
            fileName.className = 'recording-title';
            fileName.style.fontSize = '0.9rem';
            fileName.textContent = file.conversation_filename;
            
            const uploadDate = document.createElement('div');
            uploadDate.className = 'muted';
            uploadDate.style.fontSize = '0.75rem';
            uploadDate.textContent = `Target: ${file.target_filename} • ${new Date(file.uploaded_at).toLocaleString()}`;
            
            leftHeader.appendChild(fileName);
            leftHeader.appendChild(uploadDate);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn-delete-file';
            deleteBtn.textContent = '❌';
            deleteBtn.onclick = () => deleteSpeakerFile(file.id, file.conversation_filename);
            
            header.appendChild(leftHeader);
            header.appendChild(deleteBtn);
            
            // Audio players section
            const audiosContainer = document.createElement('div');
            audiosContainer.style.display = 'flex';
            audiosContainer.style.flexDirection = 'column';
            audiosContainer.style.gap = '0.5rem';
            audiosContainer.style.width = '100%';
            
            // Conversation audio (original)
            const convBox = document.createElement('div');
            convBox.style.width = '100%';
            
            const convLabel = document.createElement('div');
            convLabel.className = 'muted';
            convLabel.style.fontSize = '0.75rem';
            convLabel.style.marginBottom = '0.2rem';
            convLabel.textContent = '🎙️ Conversation';
            
            const convAudio = document.createElement('audio');
            convAudio.controls = true;
            convAudio.preload = 'none';
            convAudio.style.width = '100%';
            convAudio.style.height = '32px';
            const convSrc = document.createElement('source');
            convSrc.src = file.conversation_url;
            convSrc.type = 'audio/mpeg';
            convAudio.appendChild(convSrc);
            
            convBox.appendChild(convLabel);
            convBox.appendChild(convAudio);
            
            // Target speaker sample
            const targetBox = document.createElement('div');
            targetBox.style.width = '100%';
            
            const targetLabel = document.createElement('div');
            targetLabel.className = 'muted';
            targetLabel.style.fontSize = '0.75rem';
            targetLabel.style.marginBottom = '0.2rem';
            targetLabel.textContent = '🎯 Target Sample';
            
            const targetAudio = document.createElement('audio');
            targetAudio.controls = true;
            targetAudio.preload = 'none';
            targetAudio.style.width = '100%';
            targetAudio.style.height = '32px';
            const targetSrc = document.createElement('source');
            targetSrc.src = file.target_url;
            targetSrc.type = 'audio/mpeg';
            targetAudio.appendChild(targetSrc);
            
            targetBox.appendChild(targetLabel);
            targetBox.appendChild(targetAudio);
            
            // Extracted audio
            if (file.status === 'completed' && file.extracted_url) {
                const extractedBox = document.createElement('div');
                extractedBox.style.width = '100%';
                
                const extractedLabel = document.createElement('div');
                extractedLabel.className = 'muted';
                extractedLabel.style.fontSize = '0.75rem';
                extractedLabel.style.marginBottom = '0.2rem';
                
                const similarityPercent = file.similarity_score ? (file.similarity_score * 100).toFixed(1) : 'N/A';
                if (file.boost_level && file.boost_level !== 'none') {
                    extractedLabel.textContent = `✨ Extracted (${similarityPercent}% match) + 🔊 ${file.boost_level} Boost`;
                } else {
                    extractedLabel.textContent = `✨ Extracted (${similarityPercent}% match)`;
                }
                
                const extractedAudio = document.createElement('audio');
                extractedAudio.controls = true;
                extractedAudio.preload = 'none';
                extractedAudio.style.width = '100%';
                extractedAudio.style.height = '32px';
                const extractedSrc = document.createElement('source');
                extractedSrc.src = file.extracted_url;
                extractedSrc.type = 'audio/mpeg';
                extractedAudio.appendChild(extractedSrc);
                
                extractedBox.appendChild(extractedLabel);
                extractedBox.appendChild(extractedAudio);
                audiosContainer.appendChild(extractedBox);
            } else if (file.status === 'processing') {
                const statusDiv = document.createElement('div');
                statusDiv.className = 'muted';
                statusDiv.style.fontSize = '0.8rem';
                statusDiv.style.textAlign = 'center';
                statusDiv.style.padding = '0.5rem';
                statusDiv.innerHTML = '⏳ Processing...';
                audiosContainer.appendChild(statusDiv);
            } else if (file.status === 'pending') {
                const statusDiv = document.createElement('div');
                statusDiv.className = 'muted';
                statusDiv.style.fontSize = '0.8rem';
                statusDiv.style.textAlign = 'center';
                statusDiv.style.padding = '0.5rem';
                statusDiv.innerHTML = '⏸️ Pending...';
                audiosContainer.appendChild(statusDiv);
            } else if (file.status === 'error') {
                const statusDiv = document.createElement('div');
                statusDiv.style.fontSize = '0.8rem';
                statusDiv.style.textAlign = 'center';
                statusDiv.style.padding = '0.5rem';
                statusDiv.style.color = '#ef4444';
                statusDiv.innerHTML = `❌ Error: ${file.error_message || 'Unknown error'}`;
                audiosContainer.appendChild(statusDiv);
            }
            
            audiosContainer.insertBefore(convBox, audiosContainer.firstChild);
            audiosContainer.insertBefore(targetBox, audiosContainer.children[1]);
            
            item.appendChild(header);
            item.appendChild(audiosContainer);
            list.appendChild(item);
        });
        
    } catch (error) {
        console.error('Error refreshing speaker files list:', error);
    }
}

window.deleteSpeakerFile = function(fileId, filename) {
    deleteSpeakerFileId = fileId;
    deleteSpeakerFileName = filename;
    
    const modal = document.getElementById('delete-file-modal');
    const fileNameSpan = document.getElementById('delete-file-name');
    
    if (modal && fileNameSpan) {
        fileNameSpan.textContent = filename;
        modal.classList.add('active');
    }
};

async function confirmDeleteSpeakerFile() {
    if (!deleteSpeakerFileId) return;
    
    try {
        const response = await fetch(`/api/speaker/files/${deleteSpeakerFileId}/delete/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            await refreshSpeakerFilesList();
        } else {
            console.error('Failed to delete file');
        }
    } catch (error) {
        console.error('Error deleting file:', error);
    }
    
    deleteSpeakerFileId = null;
    deleteSpeakerFileName = '';
    closeDeleteFileModal();
}

// Update confirmDeleteFile to handle speaker files
const originalConfirmDeleteFile = window.confirmDeleteFile;
window.confirmDeleteFile = function() {
    if (deleteSpeakerFileId) {
        confirmDeleteSpeakerFile();
    } else {
        originalConfirmDeleteFile();
    }
};

// Polling for speaker extraction status updates
let speakerPollingInterval = null;

function startSpeakerPolling() {
    if (speakerPollingInterval) return;
    
    speakerPollingInterval = setInterval(async () => {
        const list = document.getElementById('speaker-files-list');
        if (!list || !document.getElementById('speaker-tab-content').classList.contains('active')) {
            stopSpeakerPolling();
            return;
        }
        
        await refreshSpeakerFilesList();
    }, 3000);
}

function stopSpeakerPolling() {
    if (speakerPollingInterval) {
        clearInterval(speakerPollingInterval);
        speakerPollingInterval = null;
    }
}
