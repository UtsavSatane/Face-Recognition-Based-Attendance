// Application State
let state = {
    currentPortal: 'home', // 'home', 'kiosk', 'student', 'admin'
    cameraStream: null,
    cameraInterval: null,
    isScanning: false,
    
    // Kiosk specific states
    livenessMode: 'Blink & Head Turn',
    similarityThreshold: 0.5,
    liveness: {
        blink: false,
        headTurn: false,
        headTurnState: 'center', // 'center', 'left', 'right'
        eyeClosedStreak: 0,
        verified: false
    },
    
    // Auth states
    studentUser: null,
    adminUser: null,
    
    // Admin tabs
    activeAdminTab: 'enroll',
    
    // Directory Filters
    directoryFilters: {
        department: null,
        section: null
    }
};

// DOM Elements
const elements = {
    navHome: document.getElementById('nav-home'),
    navKiosk: document.getElementById('nav-kiosk'),
    navStudent: document.getElementById('nav-student'),
    navAdmin: document.getElementById('nav-admin'),
    
    portalHome: document.getElementById('portal-home'),
    portalKiosk: document.getElementById('portal-kiosk'),
    portalStudent: document.getElementById('portal-student'),
    portalAdmin: document.getElementById('portal-admin'),
    
    // Home Portal cards
    cardKiosk: document.getElementById('card-kiosk'),
    cardStudent: document.getElementById('card-student'),
    cardAdmin: document.getElementById('card-admin'),
    
    // Kiosk elements
    btnStartKiosk: document.getElementById('btn-start-kiosk'),
    btnStopKiosk: document.getElementById('btn-stop-kiosk'),
    btnResetLiveness: document.getElementById('btn-reset-liveness'),
    webcam: document.getElementById('webcam'),
    overlayCanvas: document.getElementById('overlay-canvas'),
    kioskStatus: document.getElementById('kiosk-status'),
    chkBlink: document.getElementById('chk-blink'),
    chkHead: document.getElementById('chk-head'),
    livenessAlert: document.getElementById('liveness-alert'),
    successOverlay: document.getElementById('success-overlay'),
    successStudentName: document.getElementById('success-student-name'),
    
    // Student elements
    studentLoginForm: document.getElementById('student-login-form'),
    studentDashboard: document.getElementById('student-dashboard'),
    studentLoginView: document.getElementById('student-login-view'),
    studentName: document.getElementById('student-name'),
    studentLoginId: document.getElementById('student-login-id'),
    studentDept: document.getElementById('student-dept'),
    studentSec: document.getElementById('student-sec'),
    studentLogout: document.getElementById('student-logout'),
    studentTodayStatus: document.getElementById('student-today-status'),
    studentTodayTime: document.getElementById('student-today-time'),
    studentHistoryBody: document.getElementById('student-history-body'),
    studentForgotPassLink: document.getElementById('student-forgot-pass-link'),
    studentForgotView: document.getElementById('student-forgot-view'),
    studentForgotForm: document.getElementById('student-forgot-form'),
    forgotBackToLogin: document.getElementById('forgot-back-to-login'),
    forgotGoToOtp: document.getElementById('forgot-go-to-otp'),
    studentResetView: document.getElementById('student-reset-view'),
    studentResetForm: document.getElementById('student-reset-form'),
    resetBackToLogin: document.getElementById('reset-back-to-login'),
    
    // Admin elements
    adminLoginForm: document.getElementById('admin-login-form'),
    adminDashboard: document.getElementById('admin-dashboard'),
    adminLoginView: document.getElementById('admin-login-view'),
    adminName: document.getElementById('admin-name'),
    adminLoginId: document.getElementById('admin-login-id'),
    adminLogout: document.getElementById('admin-logout'),
    adminTabBtns: document.querySelectorAll('.tab-btn'),
    adminTabContents: document.querySelectorAll('.tab-content'),
    
    // Admin Tab: Register
    enrollForm: document.getElementById('enroll-form'),
    enrollCamWrapper: document.getElementById('enroll-cam-wrapper'),
    enrollWebcam: document.getElementById('enroll-webcam'),
    btnStartEnrollCam: document.getElementById('btn-start-enroll-cam'),
    btnCaptureEnroll: document.getElementById('btn-capture-enroll'),
    enrollName: document.getElementById('enroll-name'),
    enrollLogin: document.getElementById('enroll-login'),
    enrollPassword: document.getElementById('enroll-password'),
    enrollDept: document.getElementById('enroll-dept'),
    enrollSec: document.getElementById('enroll-sec'),
    
    // Admin Tab: Settings
    adminSettingsForm: document.getElementById('admin-settings-form'),
    simThresholdInput: document.getElementById('sim-threshold'),
    simThresholdVal: document.getElementById('sim-threshold-val'),
    livenessModeSelect: document.getElementById('liveness-mode-select'),
    
    // Admin Tab: Directory
    studentDirectoryList: document.getElementById('student-directory-list'),
    directoryDeptSelect: document.getElementById('directory-dept'),
    directorySecSelect: document.getElementById('directory-sec'),
    btnDirectoryFilter: document.getElementById('btn-directory-filter'),
    btnDirectoryShowAll: document.getElementById('btn-directory-show-all'),
    
    // Admin Tab: Classrooms
    classroomSelect: document.getElementById('classroom-select'),
    classroomFileSelect: document.getElementById('classroom-file-select'),
    classroomTableContainer: document.getElementById('classroom-table-container'),
    classroomFileDownloadBtn: document.getElementById('classroom-file-download'),
    
    // Admin Tab: Reports
    totalStudentsVal: document.getElementById('total-students-val'),
    todayAttendanceVal: document.getElementById('today-attendance-val'),
    reportsTableBody: document.getElementById('reports-table-body'),
    downloadReportsBtn: document.getElementById('download-reports-btn'),
    resetsTableBody: document.getElementById('resets-table-body'),
    
    // Custom Alert Elements
    customAlertOverlay: document.getElementById('custom-alert-overlay'),
    customAlertCard: document.getElementById('custom-alert-card'),
    customAlertIcon: document.getElementById('custom-alert-icon'),
    customAlertTitle: document.getElementById('custom-alert-title'),
    customAlertMessage: document.getElementById('custom-alert-message'),
    customAlertBtn: document.getElementById('custom-alert-btn')
};

// Custom Alert Modal Function
function showAlert(message, type = 'info') {
    const overlay = elements.customAlertOverlay;
    const card = elements.customAlertCard;
    const iconContainer = elements.customAlertIcon;
    const titleEl = elements.customAlertTitle;
    const msgEl = elements.customAlertMessage;
    const btn = elements.customAlertBtn;

    if (!overlay || !card) return Promise.resolve();

    // Reset classes
    card.className = 'custom-alert-modal';
    iconContainer.className = 'custom-alert-icon';

    // Map types to icons and titles
    let iconHTML = '';
    let titleText = '';

    // Apply color theme and icons
    switch (type.toLowerCase()) {
        case 'success':
            card.classList.add('success');
            iconContainer.classList.add('success');
            iconHTML = '<i class="fas fa-check-circle"></i>';
            titleText = 'Success';
            break;
        case 'error':
        case 'danger':
            card.classList.add('error');
            iconContainer.classList.add('error');
            iconHTML = '<i class="fas fa-times-circle"></i>';
            titleText = 'Error';
            break;
        case 'warning':
            card.classList.add('warning');
            iconContainer.classList.add('warning');
            iconHTML = '<i class="fas fa-exclamation-triangle"></i>';
            titleText = 'Warning';
            break;
        case 'info':
default:
            card.classList.add('info');
            iconContainer.classList.add('info');
            iconHTML = '<i class="fas fa-info-circle"></i>';
            titleText = 'Notification';
            break;
    }

    iconContainer.innerHTML = iconHTML;
    titleEl.textContent = titleText;
    msgEl.innerHTML = String(message).replace(/\n/g, '<br>');

    // Show overlay
    overlay.classList.add('active');

    // Return a promise that resolves when the alert is closed
    return new Promise((resolve) => {
        const closeAlert = () => {
            overlay.classList.remove('active');
            btn.removeEventListener('click', closeAlert);
            overlay.removeEventListener('click', overlayClick);
            resolve();
        };

        const overlayClick = (e) => {
            if (e.target === overlay) {
                closeAlert();
            }
        };

        btn.addEventListener('click', closeAlert);
        overlay.addEventListener('click', overlayClick);
        btn.focus();
    });
}

// Intercept window.alert
window.alert = function(message) {
    let type = 'info';
    const msg = String(message).toLowerCase();
    if (msg.includes('success') || msg.includes('enrolled') || msg.includes('approved') || msg.includes('successfully') || msg.includes('reset')) {
        type = 'success';
    } else if (msg.includes('fail') || msg.includes('error') || msg.includes('denied') || msg.includes('invalid') || msg.includes('incorrect') || msg.includes('not found') || msg.includes('unable to')) {
        type = 'error';
    } else if (msg.includes('warn') || msg.includes('must be') || msg.includes('please capture') || msg.includes('attention')) {
        type = 'warning';
    }
    showAlert(message, type);
};

// Hidden canvas for frame capturing
const captureCanvas = document.createElement('canvas');
const captureCtx = captureCanvas.getContext('2d');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    setupThemeToggle();
    setupNavigation();
    setupKioskControls();
    setupStudentAuth();
    setupAdminAuth();
    setupAdminDashboard();
    fetchSystemSettings();
});

// Fetch system settings on load
async function fetchSystemSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();
        state.livenessMode = data.liveness_mode;
        state.similarityThreshold = parseFloat(data.similarity_threshold);
        
        // Populate inputs
        elements.simThresholdInput.value = state.similarityThreshold;
        elements.simThresholdVal.textContent = state.similarityThreshold;
        elements.livenessModeSelect.value = state.livenessMode;
    } catch (e) {
        console.error('Error fetching settings:', e);
    }
}

// Navigation Handling
function setupNavigation() {
    const switchPortal = (portalName) => {
        // Stop current cameras
        stopKioskCamera();
        stopEnrollCamera();
        
        state.currentPortal = portalName;
        
        // Update Nav bar highlights
        elements.navHome.classList.remove('active');
        elements.navKiosk.classList.remove('active');
        elements.navStudent.classList.remove('active');
        elements.navAdmin.classList.remove('active');
        
        if (portalName === 'home') elements.navHome.classList.add('active');
        if (portalName === 'kiosk') elements.navKiosk.classList.add('active');
        if (portalName === 'student') elements.navStudent.classList.add('active');
        if (portalName === 'admin') elements.navAdmin.classList.add('active');
        
        // Toggle views
        elements.portalHome.style.display = portalName === 'home' ? 'block' : 'none';
        elements.portalKiosk.style.display = portalName === 'kiosk' ? 'block' : 'none';
        elements.portalStudent.style.display = portalName === 'student' ? 'block' : 'none';
        elements.portalAdmin.style.display = portalName === 'admin' ? 'block' : 'none';
        
        // Show correct sub-views based on auth
        if (portalName === 'student') {
            if (state.studentUser) {
                showStudentDashboard();
            } else {
                elements.studentLoginView.style.display = 'block';
                elements.studentDashboard.style.display = 'none';
                elements.studentForgotView.style.display = 'none';
                elements.studentResetView.style.display = 'none';
            }
        }
        if (portalName === 'admin') {
            if (state.adminUser) {
                showAdminDashboard();
            } else {
                elements.adminLoginView.style.display = 'block';
                elements.adminDashboard.style.display = 'none';
            }
        }
    };
    
    elements.navHome.addEventListener('click', () => switchPortal('home'));
    elements.navKiosk.addEventListener('click', () => switchPortal('kiosk'));
    elements.navStudent.addEventListener('click', () => switchPortal('student'));
    elements.navAdmin.addEventListener('click', () => switchPortal('admin'));
    
    elements.cardKiosk.addEventListener('click', () => switchPortal('kiosk'));
    elements.cardStudent.addEventListener('click', () => switchPortal('student'));
    elements.cardAdmin.addEventListener('click', () => switchPortal('admin'));
}

// Theme Toggle handling
function setupThemeToggle() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (!themeToggleBtn) return;
    
    // Check saved theme or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
    
    const setLightMode = (isLight) => {
        if (isLight) {
            document.documentElement.classList.add('light-theme');
            themeToggleBtn.innerHTML = '<i class="fas fa-moon"></i>';
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.classList.remove('light-theme');
            themeToggleBtn.innerHTML = '<i class="fas fa-sun"></i>';
            localStorage.setItem('theme', 'dark');
        }
    };
    
    // Initialize
    if (savedTheme === 'light' || (!savedTheme && systemPrefersLight)) {
        setLightMode(true);
    } else {
        setLightMode(false);
    }
    
    // Toggle click handler
    themeToggleBtn.addEventListener('click', () => {
        const isCurrentLight = document.documentElement.classList.contains('light-theme');
        setLightMode(!isCurrentLight);
    });
}

// ----------------- KIOSK CONTROLS & CAMERA -----------------
function setupKioskControls() {
    elements.btnStartKiosk.addEventListener('click', startKioskCamera);
    elements.btnStopKiosk.addEventListener('click', stopKioskCamera);
    elements.btnResetLiveness.addEventListener('click', resetLivenessState);
}

async function startKioskCamera() {
    resetLivenessState();
    elements.btnStartKiosk.style.display = 'none';
    elements.btnStopKiosk.style.display = 'inline-flex';
    elements.btnResetLiveness.style.display = 'inline-flex';
    document.querySelector('.camera-wrapper').classList.add('active');
    
    try {
        state.cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 }
        });
        elements.webcam.srcObject = state.cameraStream;
        state.isScanning = true;
        
        // Wait until video has metadata
        elements.webcam.onloadedmetadata = () => {
            elements.overlayCanvas.width = elements.webcam.videoWidth;
            elements.overlayCanvas.height = elements.webcam.videoHeight;
            captureCanvas.width = elements.webcam.videoWidth;
            captureCanvas.height = elements.webcam.videoHeight;
            
            // Start periodic processing
            state.cameraInterval = setInterval(processKioskFrame, 200); // 5 FPS
        };
    } catch (e) {
        console.error('Error starting camera:', e);
        elements.kioskStatus.innerHTML = '<span style="color:var(--danger)">● Camera Access Denied</span>';
        stopKioskCamera();
    }
}

function stopKioskCamera() {
    state.isScanning = false;
    isProcessingKioskFrame = false;
    if (state.cameraInterval) {
        clearInterval(state.cameraInterval);
        state.cameraInterval = null;
    }
    if (state.cameraStream) {
        state.cameraStream.getTracks().forEach(track => track.stop());
        state.cameraStream = null;
    }
    elements.webcam.srcObject = null;
    elements.btnStartKiosk.style.display = 'inline-flex';
    elements.btnStopKiosk.style.display = 'none';
    elements.btnResetLiveness.style.display = 'none';
    document.querySelector('.camera-wrapper').classList.remove('active');
    elements.kioskStatus.innerHTML = '<span style="color:var(--text-secondary)">○ Ready</span>';
    
    // Clear canvas
    const ctx = elements.overlayCanvas.getContext('2d');
    ctx.clearRect(0, 0, elements.overlayCanvas.width, elements.overlayCanvas.height);
}

function resetLivenessState() {
    state.liveness = {
        blink: false,
        headTurn: false,
        headTurnState: 'center',
        eyeClosedStreak: 0,
        verified: false
    };
    updateLivenessChecklist();
    elements.livenessAlert.style.display = 'none';
}

function updateLivenessChecklist() {
    // Blink checklist status
    if (state.livenessMode === 'None' || state.livenessMode === 'Head Turn Only') {
        elements.chkBlink.style.display = 'none';
    } else {
        elements.chkBlink.style.display = 'flex';
        if (state.liveness.blink) {
            elements.chkBlink.className = 'checklist-item verified';
            elements.chkBlink.querySelector('.check-icon').innerHTML = '<i class="fas fa-check-circle"></i>';
        } else {
            elements.chkBlink.className = 'checklist-item';
            elements.chkBlink.querySelector('.check-icon').innerHTML = '<i class="far fa-circle"></i>';
        }
    }
    
    // Head Turn checklist status
    if (state.livenessMode === 'None' || state.livenessMode === 'Blink Only') {
        elements.chkHead.style.display = 'none';
    } else {
        elements.chkHead.style.display = 'flex';
        if (state.liveness.headTurn) {
            elements.chkHead.className = 'checklist-item verified';
            elements.chkHead.querySelector('.check-icon').innerHTML = '<i class="fas fa-check-circle"></i>';
            elements.chkHead.querySelector('.checklist-text').textContent = `Head Turn Detected (${state.liveness.headTurnState.toUpperCase()})`;
        } else {
            elements.chkHead.className = 'checklist-item';
            elements.chkHead.querySelector('.check-icon').innerHTML = '<i class="far fa-circle"></i>';
            elements.chkHead.querySelector('.checklist-text').textContent = 'Head Turn (Left or Right)';
        }
    }
    
    if (state.liveness.verified) {
        elements.livenessAlert.style.display = 'block';
        elements.livenessAlert.className = 'status-banner success';
        elements.livenessAlert.innerHTML = '<i class="fas fa-check-circle"></i> Liveness Verified! Scanning face...';
    } else {
        elements.livenessAlert.style.display = 'none';
    }
}

let isProcessingKioskFrame = false;

async function processKioskFrame() {
    if (!state.isScanning || isProcessingKioskFrame) return;
    
    isProcessingKioskFrame = true;
    
    // Capture current webcam frame
    captureCtx.drawImage(elements.webcam, 0, 0, captureCanvas.width, captureCanvas.height);
    const base64Frame = captureCanvas.toDataURL('image/jpeg');
    
    try {
        const response = await fetch('/api/kiosk/frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: base64Frame,
                liveness_verified: state.liveness.verified
            })
        });
        
        const result = await response.json();
        
        // Draw overlay (bbox & markers)
        drawOverlay(result);
        
        if (result.face_detected) {
            elements.kioskStatus.innerHTML = '<span style="color:var(--accent-primary)">● Active Scan</span>';
            
            // Check Liveness local state machine
            if (!state.liveness.verified) {
                const ear = result.ear;
                const yaw = result.yaw_ratio;
                
                // 1. Blink check
                if (ear < 0.20) {
                    state.liveness.eyeClosedStreak++;
                } else {
                    if (state.liveness.eyeClosedStreak >= 1) {
                        state.liveness.blink = true;
                    }
                    state.liveness.eyeClosedStreak = 0;
                }
                
                // 2. Head turn check
                if (yaw < 0.55) {
                    state.liveness.headTurnState = 'left';
                    state.liveness.headTurn = true;
                } else if (yaw > 1.82) {
                    state.liveness.headTurnState = 'right';
                    state.liveness.headTurn = true;
                }
                
                // 3. Overall liveness check
                if (state.livenessMode === 'Blink Only') {
                    if (state.liveness.blink) state.liveness.verified = true;
                } else if (state.livenessMode === 'Head Turn Only') {
                    if (state.liveness.headTurn) state.liveness.verified = true;
                } else if (state.livenessMode === 'Blink & Head Turn') {
                    if (state.liveness.blink && state.liveness.headTurn) state.liveness.verified = true;
                } else {
                    state.liveness.verified = true;
                }
                
                updateLivenessChecklist();
            } else {
                // If verified, backend runs matching. Check if backend found a match
                if (result.matched) {
                    // Stop camera, show success overlay
                    stopKioskCamera();
                    showSuccessOverlay(result.name);
                } else if (result.error === "Attendance is marked") {
                    // Stop camera, show popup
                    stopKioskCamera();
                    showAlert("Attendance is marked", "info");
                } else if (result.sim_score > 0) {
                    elements.kioskStatus.innerHTML = `<span style="color:var(--warning)">Scanning... Sim: ${result.sim_score.toFixed(2)}</span>`;
                }
            }
        } else {
            elements.kioskStatus.innerHTML = '<span style="color:var(--text-secondary)">○ No Face Detected</span>';
            state.liveness.eyeClosedStreak = 0;
        }
    } catch (e) {
        console.error('Error processing frame:', e);
    } finally {
        isProcessingKioskFrame = false;
    }
}

function drawOverlay(result) {
    const ctx = elements.overlayCanvas.getContext('2d');
    ctx.clearRect(0, 0, elements.overlayCanvas.width, elements.overlayCanvas.height);
    
    if (result.face_detected && result.bbox) {
        const [x, y, w, h] = result.bbox;
        
        // Choose box color based on liveness status
        let boxColor = '#f59e0b'; // warning (orange) during verify
        if (state.liveness.verified) {
            boxColor = result.matched ? '#10b981' : '#ef4444'; // success green or error red
        }
        
        ctx.strokeStyle = boxColor;
        ctx.lineWidth = 3;
        ctx.shadowColor = boxColor;
        ctx.shadowBlur = 10;
        
        // Draw rounded rectangle bounding box
        drawRoundedRect(ctx, x, y, w, h, 12);
        
        // Draw status text on top of box
        ctx.shadowBlur = 0;
        ctx.fillStyle = boxColor;
        ctx.font = 'bold 14px Inter, sans-serif';
        let label = 'VERIFYING LIVENESS';
        if (state.liveness.verified) {
            label = result.matched ? `MATCH: ${result.name.toUpperCase()}` : 'UNKNOWN USER';
        }
        ctx.fillText(label, x, y - 10);
    }
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height - radius);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.stroke();
}

function showSuccessOverlay(studentName) {
    elements.successStudentName.textContent = studentName;
    elements.successOverlay.classList.add('active');
    
    // Play sound if possible or visual effect
    setTimeout(() => {
        elements.successOverlay.classList.remove('active');
        // Redirect to homepage
        elements.navHome.click();
    }, 3000);
}

// ----------------- STUDENT PORTAL -----------------
function setupStudentAuth() {
    elements.studentLoginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const loginId = document.getElementById('student-id-input').value.trim();
        const password = document.getElementById('student-pass-input').value.trim();
        
        try {
            const response = await fetch('/api/student/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ login_id: loginId, password })
            });
            const data = await response.json();
            
            if (response.ok && data.user) {
                state.studentUser = data.user;
                showStudentDashboard();
            } else {
                showAlert(data.error || 'Authentication Failed', 'error');
            }
        } catch (err) {
            console.error('Error logging in student:', err);
        }
    });
    
    elements.studentLogout.addEventListener('click', () => {
        state.studentUser = null;
        elements.studentLoginForm.reset();
        elements.studentLoginView.style.display = 'block';
        elements.studentDashboard.style.display = 'none';
    });

    // Toggle Forgot Password View
    elements.studentForgotPassLink.addEventListener('click', (e) => {
        e.preventDefault();
        elements.studentLoginView.style.display = 'none';
        elements.studentForgotView.style.display = 'block';
    });

    elements.forgotBackToLogin.addEventListener('click', (e) => {
        e.preventDefault();
        elements.studentForgotView.style.display = 'none';
        elements.studentLoginView.style.display = 'block';
    });

    elements.forgotGoToOtp.addEventListener('click', (e) => {
        e.preventDefault();
        elements.studentForgotView.style.display = 'none';
        elements.studentResetView.style.display = 'block';
    });

    elements.resetBackToLogin.addEventListener('click', (e) => {
        e.preventDefault();
        elements.studentResetView.style.display = 'none';
        elements.studentLoginView.style.display = 'block';
    });

    // Handle Forgot Password Form Submission
    elements.studentForgotForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const loginId = document.getElementById('forgot-student-id').value.trim();
        try {
            const response = await fetch('/api/student/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ login_id: loginId })
            });
            const data = await response.json();
            if (response.ok) {
                showAlert(data.message || 'Request sent to admin for approval.', 'success');
                elements.studentForgotForm.reset();
                elements.studentForgotView.style.display = 'none';
                elements.studentResetView.style.display = 'block';
                document.getElementById('reset-student-id').value = loginId;
            } else {
                showAlert(data.error || 'Failed to send request', 'error');
            }
        } catch (err) {
            console.error('Error requesting password reset:', err);
            showAlert('An error occurred. Please try again.', 'error');
        }
    });

    // Handle OTP Password Reset Form Submission
    elements.studentResetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const loginId = document.getElementById('reset-student-id').value.trim();
        const otp = document.getElementById('reset-otp-input').value.trim();
        const newPassword = document.getElementById('reset-new-password').value.trim();

        try {
            const response = await fetch('/api/student/reset-with-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ login_id: loginId, otp, new_password: newPassword })
            });
            const data = await response.json();
            if (response.ok) {
                showAlert(data.message || 'Password reset successfully!', 'success');
                elements.studentResetForm.reset();
                elements.studentResetView.style.display = 'none';
                elements.studentLoginView.style.display = 'block';
            } else {
                showAlert(data.error || 'Failed to reset password', 'error');
            }
        } catch (err) {
            console.error('Error resetting password with OTP:', err);
            showAlert('An error occurred. Please try again.', 'error');
        }
    });
}

async function showStudentDashboard() {
    elements.studentLoginView.style.display = 'none';
    elements.studentDashboard.style.display = 'block';
    
    // Populate profile details
    elements.studentName.textContent = state.studentUser.name;
    elements.studentLoginId.textContent = state.studentUser.login_id;
    elements.studentDept.textContent = state.studentUser.department || 'N/A';
    elements.studentSec.textContent = state.studentUser.section || 'N/A';
    
    // Fetch and populate dashboard logs
    try {
        const response = await fetch(`/api/student/dashboard?user_id=${state.studentUser.id}`);
        const data = await response.json();
        
        // Today status
        if (data.marked_today) {
            elements.studentTodayStatus.innerHTML = '<span class="badge badge-success">● Checked In</span>';
            elements.studentTodayTime.textContent = `Logged today at: ${data.last_log_time}`;
        } else {
            elements.studentTodayStatus.innerHTML = '<span class="badge badge-danger">○ Absent / Pending</span>';
            elements.studentTodayTime.textContent = 'Your attendance has not been recorded yet.';
        }
        
        // History table
        elements.studentHistoryBody.innerHTML = '';
        if (data.history && data.history.length > 0) {
            data.history.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.id}</td>
                    <td>${row.timestamp}</td>
                    <td><span class="badge badge-info">${row.liveness_method}</span></td>
                `;
                elements.studentHistoryBody.appendChild(tr);
            });
        } else {
            elements.studentHistoryBody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-secondary)">No attendance records found.</td></tr>';
        }
    } catch (e) {
        console.error('Error fetching student dashboard:', e);
    }
}

// ----------------- ADMIN PORTAL -----------------
function setupAdminAuth() {
    elements.adminLoginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const loginId = document.getElementById('admin-id-input').value.trim();
        const password = document.getElementById('admin-pass-input').value.trim();
        
        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ login_id: loginId, password })
            });
            const data = await response.json();
            
            if (response.ok && data.user) {
                state.adminUser = data.user;
                showAdminDashboard();
            } else {
                showAlert(data.error || 'Authentication Failed', 'error');
            }
        } catch (err) {
            console.error('Error logging in admin:', err);
        }
    });
    
    elements.adminLogout.addEventListener('click', () => {
        state.adminUser = null;
        elements.adminLoginForm.reset();
        elements.adminLoginView.style.display = 'block';
        elements.adminDashboard.style.display = 'none';
        stopEnrollCamera();
    });
}

function showAdminDashboard() {
    elements.adminLoginView.style.display = 'none';
    elements.adminDashboard.style.display = 'block';
    
    elements.adminName.textContent = state.adminUser.name;
    elements.adminLoginId.textContent = state.adminUser.login_id;
    
    // Default active tab
    switchAdminTab(state.activeAdminTab);
}

function setupAdminDashboard() {
    // Tab switching
    elements.adminTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            switchAdminTab(tabName);
        });
    });
    
    // Camera toggle for Register Tab
    elements.btnStartEnrollCam.addEventListener('click', startEnrollCamera);
    elements.btnCaptureEnroll.addEventListener('click', captureEnrollFrame);
    
    // Enrollment Form submission
    elements.enrollForm.addEventListener('submit', handleEnrollment);
    
    // Live threshold value update
    elements.simThresholdInput.addEventListener('input', (e) => {
        elements.simThresholdVal.textContent = e.target.value;
    });
    
    // Save Settings
    elements.adminSettingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const threshold = elements.simThresholdInput.value;
        const livenessMode = elements.livenessModeSelect.value;
        
        try {
            const response = await fetch('/api/admin/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ threshold, liveness_mode: livenessMode })
            });
            
            if (response.ok) {
                state.livenessMode = livenessMode;
                state.similarityThreshold = parseFloat(threshold);
                showAlert('System settings updated successfully!', 'success');
            } else {
                showAlert('Failed to update settings', 'error');
            }
        } catch (err) {
            console.error(err);
        }
    });
    
    // Classroom inspection
    elements.classroomSelect.addEventListener('change', handleClassroomSelect);
    elements.classroomFileSelect.addEventListener('change', handleClassroomFileSelect);
    
    // Directory filters
    elements.btnDirectoryFilter.addEventListener('click', () => {
        const department = elements.directoryDeptSelect.value;
        const section = elements.directorySecSelect.value;
        if (!department || !section) {
            showAlert('Please select both a department and a section.', 'warning');
            return;
        }
        state.directoryFilters = { department, section };
        fetchStudentDirectory(department, section);
    });
    
    elements.btnDirectoryShowAll.addEventListener('click', () => {
        elements.directoryDeptSelect.value = '';
        elements.directorySecSelect.value = '';
        state.directoryFilters = { department: null, section: null };
        fetchStudentDirectory();
    });
}

function switchAdminTab(tabName) {
    state.activeAdminTab = tabName;
    stopEnrollCamera();
    
    elements.adminTabBtns.forEach(btn => {
        if (btn.dataset.tab === tabName) btn.classList.add('active');
        else btn.classList.remove('active');
    });
    
    elements.adminTabContents.forEach(content => {
        if (content.id === `tab-${tabName}`) content.classList.add('active');
        else content.classList.remove('active');
    });
    
    // Tab specific load actions
    if (tabName === 'directory') {
        elements.directoryDeptSelect.value = '';
        elements.directorySecSelect.value = '';
        state.directoryFilters = { department: null, section: null };
        elements.studentDirectoryList.innerHTML = `
            <div style="text-align:center;color:var(--text-secondary);padding: 2.5rem 1.5rem;background:rgba(255,255,255,0.02);border-radius:12px;border:1px dashed var(--border-color)">
                <i class="fas fa-filter" style="font-size: 2.5rem; margin-bottom: 1rem; display: block; color: var(--accent-primary); opacity: 0.7;"></i>
                <p style="font-size:1.1rem;font-weight:500;margin-bottom:0.5rem;color:var(--text-primary)">Filter Student Directory</p>
                <p style="font-size:0.9rem;max-width:400px;margin:0 auto;line-height:1.5">Please select a department and section above, then click <b>View Students</b>, or click <b>Display All</b> to see everyone.</p>
            </div>
        `;
    }
    if (tabName === 'classrooms') fetchClassroomDirectories();
    if (tabName === 'reports') fetchAttendanceReports();
    if (tabName === 'resets') fetchResetRequests();
}

// Admin Tab: Register Student Camera
let enrollStream = null;

async function startEnrollCamera() {
    try {
        enrollStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 }
        });
        elements.enrollWebcam.srcObject = enrollStream;
        elements.enrollCamWrapper.style.display = 'block';
        elements.btnStartEnrollCam.style.display = 'none';
        elements.btnCaptureEnroll.style.display = 'inline-flex';
    } catch (e) {
        console.error(e);
        showAlert('Camera access denied', 'error');
    }
}

function stopEnrollCamera() {
    if (enrollStream) {
        enrollStream.getTracks().forEach(track => track.stop());
        enrollStream = null;
    }
    elements.enrollWebcam.srcObject = null;
    elements.enrollCamWrapper.style.display = 'none';
    elements.btnStartEnrollCam.style.display = 'inline-flex';
    elements.btnCaptureEnroll.style.display = 'none';
}

let capturedFrameBase64 = null;

function captureEnrollFrame() {
    // Capture to a temporary canvas and freeze/show preview or save image
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = elements.enrollWebcam.videoWidth;
    tempCanvas.height = elements.enrollWebcam.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.drawImage(elements.enrollWebcam, 0, 0, tempCanvas.width, tempCanvas.height);
    
    capturedFrameBase64 = tempCanvas.toDataURL('image/jpeg');
    
    // Stop camera and show text
    stopEnrollCamera();
    
    // Update button visual
    elements.btnStartEnrollCam.innerHTML = '<i class="fas fa-camera"></i> Retake Face Capture';
    elements.btnStartEnrollCam.classList.remove('btn-primary');
    elements.btnStartEnrollCam.style.background = 'rgba(255,255,255,0.05)';
    elements.btnStartEnrollCam.style.border = '1px solid var(--border-color)';
    
    // Check form disabled status
    checkEnrollSubmitStatus();
}

function checkEnrollSubmitStatus() {
    const name = elements.enrollName.value.trim();
    const login = elements.enrollLogin.value.trim();
    const password = elements.enrollPassword.value.trim();
    const dept = elements.enrollDept.value.trim();
    const sec = elements.enrollSec.value.trim();
    
    const submitBtn = document.getElementById('btn-submit-enroll');
    if (name && login && password && dept && sec && capturedFrameBase64) {
        submitBtn.disabled = false;
    } else {
        submitBtn.disabled = true;
    }
}

// Add event listeners for form validation
['enroll-name', 'enroll-login', 'enroll-password', 'enroll-dept', 'enroll-sec'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener('input', checkEnrollSubmitStatus);
        el.addEventListener('change', checkEnrollSubmitStatus);
    }
});

async function handleEnrollment(e) {
    e.preventDefault();
    if (!capturedFrameBase64) {
        showAlert('Please capture student face first.', 'warning');
        return;
    }
    
    const name = elements.enrollName.value.trim();
    const loginId = elements.enrollLogin.value.trim();
    const password = elements.enrollPassword.value.trim();
    const department = elements.enrollDept.value.trim();
    const section = elements.enrollSec.value.trim();
    
    try {
        const response = await fetch('/api/admin/enroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                login_id: loginId,
                password,
                department,
                section,
                image: capturedFrameBase64
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert('Student registered and face enrolled successfully!', 'success');
            elements.enrollForm.reset();
            capturedFrameBase64 = null;
            elements.btnStartEnrollCam.innerHTML = '<i class="fas fa-camera"></i> Start Camera & Scan Face';
            elements.btnStartEnrollCam.style.background = '';
            checkEnrollSubmitStatus();
        } else {
            showAlert(result.error || 'Failed to enrol student', 'error');
        }
    } catch (err) {
        console.error(err);
        showAlert('Enrolment error', 'error');
    }
}

// Admin Tab: Student Directory
async function fetchStudentDirectory(department = null, section = null) {
    try {
        let url = '/api/admin/students';
        const params = new URLSearchParams();
        if (department) params.append('department', department);
        if (section) params.append('section', section);
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        const response = await fetch(url);
        const students = await response.json();
        
        elements.studentDirectoryList.innerHTML = '';
        if (students && students.length > 0) {
            students.forEach(s => {
                const item = document.createElement('div');
                item.className = 'student-directory-item';
                
                const deptSec = `Dept: ${s.department || 'N/A'} | Sec: ${s.section || 'N/A'}`;
                
                item.innerHTML = `
                    <div class="student-info">
                        <h4>${s.name}</h4>
                        <p>Login ID: <code>${s.login_id}</code> | ${deptSec}</p>
                    </div>
                    <button class="btn-danger btn-delete-student" data-id="${s.id}" data-login="${s.login_id}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                `;
                elements.studentDirectoryList.appendChild(item);
            });
            
            // Delete Handlers
            document.querySelectorAll('.btn-delete-student').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const studentId = btn.dataset.id;
                    const loginId = btn.dataset.login;
                    if (confirm(`Are you sure you want to delete student ${loginId}?`)) {
                        try {
                            const res = await fetch('/api/admin/delete_student', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ id: studentId, login_id: loginId })
                            });
                            if (res.ok) {
                                fetchStudentDirectory(state.directoryFilters.department, state.directoryFilters.section);
                            } else {
                                showAlert('Error deleting student', 'error');
                            }
                        } catch (err) {
                            console.error(err);
                        }
                    }
                });
            });
        } else {
            const filterInfo = (department || section) ? 'matching the selected filters' : 'found';
            elements.studentDirectoryList.innerHTML = `<div style="text-align:center;color:var(--text-secondary)">No enrolled students ${filterInfo}.</div>`;
        }
    } catch (e) {
        console.error(e);
    }
}

// Admin Tab: Classroom Attendance Folders
async function fetchClassroomDirectories() {
    try {
        const response = await fetch('/api/admin/classrooms');
        const data = await response.json();
        
        elements.classroomSelect.innerHTML = '<option value="">-- Choose Classroom --</option>';
        elements.classroomFileSelect.innerHTML = '<option value="">-- Choose File --</option>';
        elements.classroomFileSelect.disabled = true;
        elements.classroomTableContainer.innerHTML = '';
        elements.classroomFileDownloadBtn.style.display = 'none';
        
        if (data.classrooms && data.classrooms.length > 0) {
            data.classrooms.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = d;
                elements.classroomSelect.appendChild(opt);
            });
        }
    } catch (e) {
        console.error(e);
    }
}

async function handleClassroomSelect() {
    const classroom = elements.classroomSelect.value;
    elements.classroomFileSelect.innerHTML = '<option value="">-- Choose File --</option>';
    elements.classroomTableContainer.innerHTML = '';
    elements.classroomFileDownloadBtn.style.display = 'none';
    
    if (!classroom) {
        elements.classroomFileSelect.disabled = true;
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/classrooms/${classroom}`);
        const data = await response.json();
        
        if (data.files && data.files.length > 0) {
            elements.classroomFileSelect.disabled = false;
            data.files.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f;
                opt.textContent = f;
                elements.classroomFileSelect.appendChild(opt);
            });
        } else {
            elements.classroomFileSelect.disabled = true;
        }
    } catch (e) {
        console.error(e);
    }
}

async function handleClassroomFileSelect() {
    const classroom = elements.classroomSelect.value;
    const file = elements.classroomFileSelect.value;
    elements.classroomTableContainer.innerHTML = '';
    elements.classroomFileDownloadBtn.style.display = 'none';
    
    if (!classroom || !file) return;
    
    try {
        const response = await fetch(`/api/admin/classrooms/${classroom}/${file}`);
        const data = await response.json();
        
        if (data.headers && data.rows) {
            let tableHtml = `
                <table class="classroom-data-table">
                    <thead>
                        <tr>
                            ${data.headers.map(h => `<th>${h}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.rows.map(row => `
                            <tr>
                                ${row.map(val => `<td>${val}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            elements.classroomTableContainer.innerHTML = tableHtml;
            
            // Show download link
            elements.classroomFileDownloadBtn.style.display = 'inline-flex';
            elements.classroomFileDownloadBtn.href = `/api/admin/download_classroom?classroom=${classroom}&file=${file}`;
        }
    } catch (e) {
        console.error(e);
    }
}

// Admin Tab: Attendance Reports
async function fetchAttendanceReports() {
    try {
        const response = await fetch('/api/admin/reports');
        const data = await response.json();
        
        elements.totalStudentsVal.textContent = data.total_students;
        elements.todayAttendanceVal.textContent = data.today_attendance_count;
        
        elements.reportsTableBody.innerHTML = '';
        if (data.logs && data.logs.length > 0) {
            data.logs.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.id}</td>
                    <td>${row.name}</td>
                    <td>${row.timestamp}</td>
                    <td><span class="badge badge-info">${row.liveness_method}</span></td>
                `;
                elements.reportsTableBody.appendChild(tr);
            });
            elements.downloadReportsBtn.style.display = 'inline-flex';
        } else {
            elements.reportsTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-secondary)">No attendance logs recorded today.</td></tr>';
            elements.downloadReportsBtn.style.display = 'none';
        }
    } catch (e) {
        console.error(e);
    }
}

// Admin Tab: Password Reset Requests
async function fetchResetRequests() {
    try {
        const response = await fetch('/api/admin/reset-requests');
        const data = await response.json();
        
        elements.resetsTableBody.innerHTML = '';
        if (data && data.length > 0) {
            data.forEach(req => {
                const tr = document.createElement('tr');
                
                // Format Status Badge
                let statusBadge = '';
                if (req.status === 'PENDING') statusBadge = '<span class="badge badge-warning">PENDING</span>';
                else if (req.status === 'APPROVED') statusBadge = '<span class="badge badge-success">APPROVED</span>';
                else if (req.status === 'REJECTED') statusBadge = '<span class="badge badge-danger">REJECTED</span>';
                else if (req.status === 'EXPIRED') statusBadge = '<span class="badge badge-danger" style="background:var(--danger);opacity:0.6;">EXPIRED</span>';
                else if (req.status === 'COMPLETED') statusBadge = '<span class="badge badge-success" style="background:#10b981;opacity:0.7;">COMPLETED</span>';
                
                // Action column rendering
                let actionHtml = '';
                if (req.status === 'PENDING') {
                    actionHtml = `
                        <button class="btn-primary btn-approve-reset" data-id="${req.id}" style="padding:0.25rem 0.6rem; font-size:0.8rem; background:#10b981; border:none; margin-right:0.5rem;"><i class="fas fa-check"></i> Approve</button>
                        <button class="btn-danger btn-reject-reset" data-id="${req.id}" style="padding:0.25rem 0.6rem; font-size:0.8rem; border:none;"><i class="fas fa-times"></i> Reject</button>
                    `;
                } else if (req.status === 'APPROVED') {
                    actionHtml = `OTP: <strong style="color:var(--warning); font-size:1.1rem; letter-spacing:1px;">${req.otp || 'N/A'}</strong>`;
                } else {
                    actionHtml = '-';
                }
                
                // Audit logs string
                let auditHtml = '';
                if (req.admin_name) {
                    const actionWord = req.status === 'APPROVED' || req.status === 'COMPLETED' ? 'Approved' : 'Rejected';
                    auditHtml = `<div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.2rem;">${actionWord} by ${req.admin_name} (${req.admin_login_id})</div>`;
                }
                
                tr.innerHTML = `
                    <td>${req.id}</td>
                    <td>${req.student_name}</td>
                    <td><code>${req.student_login_id}</code></td>
                    <td>${req.created_at}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <div>${actionHtml}</div>
                        ${auditHtml}
                    </td>
                `;
                elements.resetsTableBody.appendChild(tr);
            });
            
            // Add action listeners
            document.querySelectorAll('.btn-approve-reset').forEach(btn => {
                btn.addEventListener('click', () => handleResetAction(btn.dataset.id, 'approve'));
            });
            document.querySelectorAll('.btn-reject-reset').forEach(btn => {
                btn.addEventListener('click', () => handleResetAction(btn.dataset.id, 'reject'));
            });
            
        } else {
            elements.resetsTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary)">No password reset requests found.</td></tr>';
        }
    } catch (e) {
        console.error('Error fetching reset requests:', e);
    }
}

async function handleResetAction(requestId, action) {
    if (!state.adminUser) {
        showAlert("You must be logged in as admin to perform this action.", "warning");
        return;
    }
    
    if (confirm(`Are you sure you want to ${action} this password reset request?`)) {
        try {
            const response = await fetch(`/api/admin/reset-requests/${requestId}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action, admin_id: state.adminUser.id })
            });
            const data = await response.json();
            
            if (response.ok) {
                if (action === 'approve') {
                    showAlert(`Request approved! Temporary OTP is: ${data.otp}`, 'success');
                } else {
                    showAlert('Request rejected successfully.', 'success');
                }
                fetchResetRequests();
            } else {
                showAlert(data.error || `Failed to ${action} request`, 'error');
            }
        } catch (err) {
            console.error(err);
            showAlert('An error occurred. Please try again.', 'error');
        }
    }
}
