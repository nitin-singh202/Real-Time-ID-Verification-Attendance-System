/**
 * Live Scanner Controller & HUD Polling Engine
 */

let lastScanTimestamp = 0;
let audioContext = null;

// Initialize Web Audio API for responsive gate chimes
function initAudio() {
    if (!audioContext) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
            audioContext = new AudioCtx();
        }
    }
}

function playBeep(type = 'success') {
    try {
        initAudio();
        if (!audioContext) return;
        if (audioContext.state === 'suspended') {
            audioContext.resume();
        }

        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.connect(gain);
        gain.connect(audioContext.destination);

        const now = audioContext.currentTime;

        if (type === 'success') {
            // Dual tone high pleasant chime
            osc.frequency.setValueAtTime(587.33, now); // D5
            osc.frequency.setValueAtTime(880.00, now + 0.08); // A5
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
            osc.start(now);
            osc.stop(now + 0.3);
        } else if (type === 'warning') {
            // Mid tone double blip
            osc.frequency.setValueAtTime(440, now);
            gain.gain.setValueAtTime(0.12, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
            osc.start(now);
            osc.stop(now + 0.25);
        } else {
            // Low buzz tone
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(180, now);
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
            osc.start(now);
            osc.stop(now + 0.35);
        }
    } catch (e) {
        console.debug("Audio play error", e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Enable audio on first user click anywhere
    document.body.addEventListener('click', initAudio, { once: true });

    // Start live polling of scanner status
    startPolling();

    // Event & Mode handlers
    const eventSelect = document.getElementById('targetEventSelect');
    if (eventSelect) {
        eventSelect.addEventListener('change', () => {
            updateScannerSettings({ event_name: eventSelect.value });
        });
    }

    const exitToggle = document.getElementById('exitModeToggle');
    if (exitToggle) {
        exitToggle.addEventListener('change', () => {
            updateScannerSettings({ is_exit_mode: exitToggle.checked });
        });
    }

    const cameraIndexSelect = document.getElementById('cameraIndexSelect');
    if (cameraIndexSelect) {
        cameraIndexSelect.addEventListener('change', () => {
            updateScannerSettings({ camera_index: cameraIndexSelect.value });
        });
    }

    // Manual Scan Input Form
    const manualForm = document.getElementById('manualScanForm');
    if (manualForm) {
        manualForm.addEventListener('submit', handleManualScan);
    }

    // Image Upload Scan Form
    const uploadForm = document.getElementById('uploadScanForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleUploadScan);
    }
});

function updateScannerSettings(settings) {
    fetch('/api/scanner/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    })
    .then(r => r.json())
    .then(data => {
        console.log("Scanner settings updated:", data);
    })
    .catch(err => console.error("Error updating settings:", err));
}

function startPolling() {
    setInterval(() => {
        fetch('/api/scan_status')
            .then(res => res.json())
            .then(data => {
                if (data && data.timestamp && data.timestamp > lastScanTimestamp) {
                    lastScanTimestamp = data.timestamp;
                    if (data.status !== "IDLE") {
                        renderScanHUD(data);
                    }
                }
            })
            .catch(err => console.debug("Poll error:", err));
    }, 450);
}

function renderScanHUD(data) {
    const card = document.getElementById('hudStatusCard');
    const badge = document.getElementById('hudBadge');
    const messageEl = document.getElementById('hudMessage');
    const profileContainer = document.getElementById('hudParticipantProfile');
    const logsBody = document.getElementById('liveScanLogsBody');

    if (!card) return;

    // Reset classes
    card.classList.remove('verified', 'already_scanned', 'danger');

    if (data.status === 'VERIFIED_NEW') {
        card.classList.add('verified');
        badge.className = 'badge badge-success hud-badge';
        badge.textContent = '✓ VERIFIED PRESENT';
        playBeep('success');
    } else if (data.status === 'ALREADY_VERIFIED') {
        card.classList.add('already_scanned');
        badge.className = 'badge badge-warning hud-badge';
        badge.textContent = '✓ ALREADY SCANNED';
        playBeep('warning');
    } else if (data.status === 'EXIT_RECORDED') {
        card.classList.add('verified');
        badge.className = 'badge badge-info hud-badge';
        badge.textContent = '✓ EXIT RECORDED';
        playBeep('success');
    } else {
        card.classList.add('danger');
        badge.className = 'badge badge-danger hud-badge';
        badge.textContent = '✗ NOT VERIFIED';
        playBeep('danger');
    }

    messageEl.textContent = data.message || '';

    if (data.participant) {
        const p = data.participant;
        profileContainer.innerHTML = `
            <div class="participant-profile-card">
                <div class="profile-row">
                    <span class="profile-label">Full Name</span>
                    <span class="profile-val">${p.name}</span>
                </div>
                <div class="profile-row">
                    <span class="profile-label">Registration No</span>
                    <span class="profile-val" style="font-family: monospace; color: #60a5fa;">${p.registration_number}</span>
                </div>
                <div class="profile-row">
                    <span class="profile-label">Event</span>
                    <span class="profile-val">${data.event_name || p.event_name}</span>
                </div>
                <div class="profile-row">
                    <span class="profile-label">Entry Time</span>
                    <span class="profile-val" style="color: #34d399;">${data.entry_time || 'Just Now'}</span>
                </div>
                ${data.exit_time ? `
                <div class="profile-row">
                    <span class="profile-label">Exit Time</span>
                    <span class="profile-val" style="color: #60a5fa;">${data.exit_time}</span>
                </div>` : ''}
                <div class="profile-row">
                    <span class="profile-label">Category</span>
                    <span class="profile-val">${p.category || 'Participant'}</span>
                </div>
            </div>
        `;

        // Add to live session logs table
        if (logsBody) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${p.name}</strong></td>
                <td><code style="color: #60a5fa;">${p.registration_number}</code></td>
                <td><span class="badge badge-${data.badge_status}">${data.status.replace('_', ' ')}</span></td>
                <td>${data.entry_time || new Date().toLocaleTimeString()}</td>
            `;
            logsBody.insertBefore(tr, logsBody.firstChild);
            // Keep maximum 8 items in live log
            if (logsBody.children.length > 8) {
                logsBody.removeChild(logsBody.lastChild);
            }
        }
    } else {
        profileContainer.innerHTML = `
            <div class="participant-profile-card" style="border-color: rgba(239,68,68,0.3); text-align: center; padding: 20px;">
                <p style="color: #f87171; font-weight: 600;">Access Denied</p>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Unrecognized badge or unregistered registration ID.</p>
            </div>
        `;
    }
}

function handleManualScan(e) {
    e.preventDefault();
    const input = document.getElementById('manualRegInput');
    const code = input.value.trim();
    if (!code) return;

    const eventSelect = document.getElementById('targetEventSelect');
    const exitToggle = document.getElementById('exitModeToggle');

    fetch('/api/scan_manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            code: code,
            event_name: eventSelect ? eventSelect.value : '',
            is_exit: exitToggle ? exitToggle.checked : false
        })
    })
    .then(r => r.json())
    .then(res => {
        renderScanHUD(res);
        input.value = '';
    })
    .catch(err => alert("Error verifying code: " + err));
}

function handleUploadScan(e) {
    e.preventDefault();
    const fileInput = document.getElementById('qrFileInput');
    if (!fileInput.files || !fileInput.files[0]) {
        alert("Please choose a QR image file.");
        return;
    }

    const eventSelect = document.getElementById('targetEventSelect');
    const formData = new FormData();
    formData.append('qr_image', fileInput.files[0]);
    if (eventSelect) formData.append('event_name', eventSelect.value);

    fetch('/api/scan_upload', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(res => {
        renderScanHUD(res);
        closeModal('uploadModal');
        fileInput.value = '';
    })
    .catch(err => alert("Error scanning uploaded image: " + err));
}
