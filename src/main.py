import os
import cv2
import numpy as np
import streamlit as st
import time
from datetime import datetime, timedelta

from database import (
    init_db, add_user, get_user_by_name, log_attendance, 
    get_attendance_today, get_all_users, delete_user, get_ist_now,
    authenticate_user, get_user_by_login_id, get_last_attendance,
    get_setting, update_setting
)
from detector import FaceDetector
from encoder import FaceEncoder

# Initialize database on startup
init_db()

# Page configuration
st.set_page_config(
    page_title="BioAccess | AI Face Attendance",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    /* Gradient Background & General Style */
    .reportview-container {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        color: #f8fafc;
    }
    
    /* Title Stylings */
    .main-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.2rem;
        text-align: left;
    }
    .subtitle {
        font-family: 'Inter', sans-serif;
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(12px);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
    }

    /* Success / Warning Banners */
    .success-banner {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }
    
    /* Styled buttons */
    .stButton>button {
        background: linear-gradient(135deg, #4f46e5, #6366f1);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: opacity 0.2s;
    }
    .stButton>button:hover {
        opacity: 0.95;
    }
    
    /* Premium Portal Cards */
    div[data-testid="stForm"] {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25) !important;
        backdrop-filter: blur(16px);
        transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
    }
    div[data-testid="stForm"]:hover {
        transform: translateY(-4px);
        border-color: rgba(99, 102, 241, 0.4) !important;
        box-shadow: 0 15px 40px rgba(99, 102, 241, 0.15) !important;
    }
    .portal-header {
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .portal-desc {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- CACHED RESOURCES -----------------
@st.cache_resource
def get_detector():
    """Caches FaceDetector instance."""
    return FaceDetector()

@st.cache_resource
def get_encoder():
    """Caches FaceEncoder instance."""
    return FaceEncoder()

# Load models safely
with st.spinner("Loading AI Models (MediaPipe & InsightFace)..."):
    try:
        detector = get_detector()
        encoder = get_encoder()
    except Exception as e:
        st.error(f"Error initializing face recognition models: {e}")
        st.info("Ensure C++ Build Tools and ONNX Runtime are installed properly on Windows.")

# ----------------- STATE INITIALIZATION -----------------
if 'liveness_blink' not in st.session_state:
    st.session_state.liveness_blink = False
if 'liveness_head' not in st.session_state:
    st.session_state.liveness_head = False
if 'eye_closed_streak' not in st.session_state:
    st.session_state.eye_closed_streak = 0
if 'head_turn_state' not in st.session_state:
    st.session_state.head_turn_state = 'center' # 'center', 'left', 'right'
if 'liveness_verified' not in st.session_state:
    st.session_state.liveness_verified = False
if 'last_attendance_marked' not in st.session_state:
    st.session_state.last_attendance_marked = None  # (user_name, time)
if 'camera_running' not in st.session_state:
    st.session_state.camera_running = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'attendance_success' not in st.session_state:
    st.session_state.attendance_success = False

# ----------------- HELPER FUNCTIONS -----------------
def reset_liveness_states():
    """Resets tracking variables for liveness verification."""
    st.session_state.liveness_blink = False
    st.session_state.liveness_head = False
    st.session_state.eye_closed_streak = 0
    st.session_state.head_turn_state = 'center'
    st.session_state.liveness_verified = False

def check_liveness_conditions(ear: float, yaw_ratio: float, mode: str):
    """
    State machine for blink and head turn detection.
    Updates session state liveness flags.
    """
    # 1. Blink Detection (Hysteresis based on frame status)
    if ear < 0.20:
        # User closed their eyes
        st.session_state.eye_closed_streak += 1
    else:
        # Eye is open, check if it was closed previously
        if st.session_state.eye_closed_streak >= 1:
            st.session_state.liveness_blink = True
        st.session_state.eye_closed_streak = 0

    # 2. Head Turn Detection (horizontal yaw ratio)
    if yaw_ratio < 0.55:
        st.session_state.head_turn_state = 'left'
        st.session_state.liveness_head = True
    elif yaw_ratio > 1.82:
        st.session_state.head_turn_state = 'right'
        st.session_state.liveness_head = True

    # 3. Overall Liveness Assessment
    if mode == "Blink Only":
        if st.session_state.liveness_blink:
            st.session_state.liveness_verified = True
    elif mode == "Head Turn Only":
        if st.session_state.liveness_head:
            st.session_state.liveness_verified = True
    elif mode == "Blink & Head Turn":
        if st.session_state.liveness_blink and st.session_state.liveness_head:
            st.session_state.liveness_verified = True
    else:  # "None"
        st.session_state.liveness_verified = True

# ----------------- SUCCESS POPUP OVERLAY -----------------
if st.session_state.attendance_success:
    st.markdown("""
    <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: rgba(16, 185, 129, 0.95);
        color: white;
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        z-index: 99999;
        text-align: center;
        backdrop-filter: blur(12px);
        border: 2px solid rgba(255, 255, 255, 0.2);
        animation: fadeIn 0.4s ease;
    ">
        <h2 style="color: white; margin-top: 0;">🎉 Checked In!</h2>
        <p style="font-size: 1.25rem; font-weight: 500; margin-bottom: 0;">Attendance Marked Successfully!</p>
    </div>
    <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translate(-50%, -45%); }
            to { opacity: 1; transform: translate(-50%, -50%); }
        }
    </style>
    """, unsafe_allow_html=True)
    time.sleep(3.0)
    st.session_state.attendance_success = False
    st.rerun()

# ----------------- LOGIN / SECURITY ROUTING -----------------
if st.session_state.user is None:
    st.markdown("<div style='text-align: center; margin-top: 3rem;'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title' style='text-align: center;'>🔑 BioAccess Portal Login</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle' style='text-align: center;'>Select your portal and enter your credentials</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    col_l, col1, col2, col_r = st.columns([1, 4, 4, 1])
    
    with col1:
        with st.form("student_login_form"):
            st.markdown("<div class='portal-header'>🎓 Student Portal</div>", unsafe_allow_html=True)
            st.markdown("<div class='portal-desc'>Access your student dashboard and log attendance</div>", unsafe_allow_html=True)
            student_id = st.text_input("Student Login ID", placeholder="e.g. roll_number").strip()
            student_pwd = st.text_input("Student Password", type="password", placeholder="Password").strip()
            student_btn = st.form_submit_button("Log In to Student Portal", use_container_width=True)
            
            if student_btn:
                if not student_id or not student_pwd:
                    st.error("Please fill in both Student Login ID and Password.")
                else:
                    user = authenticate_user(student_id, student_pwd)
                    if user and user['role'] == 'student':
                        st.session_state.user = user
                        st.success(f"Welcome back, {user['name']}!")
                        time.sleep(1.0)
                        st.rerun()
                    elif user and user['role'] != 'student':
                        st.error("Access Denied: This account is not a student account.")
                    else:
                        st.error("Invalid Login ID or Password.")
                        
    with col2:
        with st.form("admin_login_form"):
            st.markdown("<div class='portal-header'>🏢 Admin Portal</div>", unsafe_allow_html=True)
            st.markdown("<div class='portal-desc'>Configure settings, register students, and view logs</div>", unsafe_allow_html=True)
            admin_id = st.text_input("Admin Login ID", placeholder="Admin ID").strip()
            admin_pwd = st.text_input("Admin Password", type="password", placeholder="Password").strip()
            admin_btn = st.form_submit_button("Log In to Admin Portal", use_container_width=True)
            
            if admin_btn:
                if not admin_id or not admin_pwd:
                    st.error("Please fill in both Admin Login ID and Password.")
                else:
                    user = authenticate_user(admin_id, admin_pwd)
                    if user and user['role'] == 'admin':
                        st.session_state.user = user
                        st.success("Admin authenticated successfully!")
                        time.sleep(1.0)
                        st.rerun()
                    elif user and user['role'] != 'admin':
                        st.error("Access Denied: This account is not an admin account.")
                    else:
                        st.error("Invalid Login ID or Password.")
    st.stop()

# Load Global Settings from database
similarity_threshold = float(get_setting("similarity_threshold", "0.5"))
liveness_mode = get_setting("liveness_mode", "Blink & Head Turn")

# Sidebar profile and Logout
st.sidebar.markdown("<h2 style='color:#818cf8;'>👤 Profile Details</h2>", unsafe_allow_html=True)
st.sidebar.write(f"**Name:** {st.session_state.user['name']}")
st.sidebar.write(f"**Login ID:** {st.session_state.user['login_id']}")

role_label = st.session_state.user['role'].upper()
role_color = "#38bdf8" if st.session_state.user['role'] == "admin" else "#818cf8"
st.sidebar.markdown(
    f"<span style='background-color:{role_color}22; color:{role_color}; padding:0.25rem 0.6rem; border-radius:4px; font-weight:bold; font-size:0.85rem;'>{role_label} PORTAL</span>",
    unsafe_allow_html=True
)

st.sidebar.markdown("---")
if st.sidebar.button("🔓 Logout", use_container_width=True):
    st.session_state.user = None
    st.session_state.camera_running = False
    reset_liveness_states()
    st.rerun()

# ----------------- ADMIN PORTAL -----------------
if st.session_state.user['role'] == "admin":
    st.markdown("<h1 class='main-title'>🏢 Admin Control Panel</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Manage student directory, set face threshold criteria, and inspect reports</div>", unsafe_allow_html=True)
    
    tab_enroll, tab_settings, tab_students, tab_logs = st.tabs([
        "👤 Register Student",
        "⚙️ Threshold Settings",
        "📋 Student Directory",
        "📊 Attendance Reports"
    ])
    
    # 1. REGISTER STUDENT
    with tab_enroll:
        st.markdown("### Add New Student Profile")
        col_reg_form, col_reg_cam = st.columns([1, 1])
        
        with col_reg_form:
            reg_name = st.text_input("Full Name", placeholder="e.g. Utsav Kumar").strip()
            reg_login = st.text_input("Login ID / Roll Number", placeholder="e.g. utsav2026").strip()
            reg_password = st.text_input("Password", type="password", placeholder="e.g. studpwd123").strip()
            
            enroll_btn = st.button("📸 Capture & Enrol Student Face", disabled=not (reg_name and reg_login and reg_password))
            
            if enroll_btn:
                # Check login_id duplicate
                if get_user_by_login_id(reg_login) is not None:
                    st.error(f"❌ Login ID '{reg_login}' is already registered in the system.")
                else:
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        st.error("❌ Webcam is not accessible.")
                    else:
                        for _ in range(10):
                            cap.read()
                        ret, frame = cap.read()
                        cap.release()
                        
                        if ret:
                            face_meta = detector.process_frame(frame, 0, force_process=True)
                            if not face_meta:
                                st.error("❌ No face detected. Make sure to look straight at the camera under clean lighting.")
                            else:
                                emb = encoder.generate_embedding(frame)
                                if emb is not None:
                                    try:
                                        encoder.save_embedding(reg_login, emb)
                                        add_user(reg_name, reg_login, reg_password, role='student')
                                        st.success(f"🎉 Success! Student '{reg_name}' enrolled successfully.")
                                        time.sleep(1.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error registering student: {e}")
                                else:
                                    st.error("❌ Failed to process facial features. Try again.")
                        else:
                            st.error("❌ Camera failed to capture a frame.")
                            
        with col_reg_cam:
            st.info("💡 Enrolment Guidelines:\n- Ensure the student's face is centered in the camera feed.\n- Avoid strong background glare or dark shadows.")

    # 2. THRESHOLD SETTINGS
    with tab_settings:
        st.markdown("### Configure Face Match & Anti-Spoofing Parameters")
        
        sim_val = st.slider(
            "Face Match Threshold",
            min_value=0.3, max_value=0.8, value=similarity_threshold, step=0.05,
            help="Higher values are stricter (fewer false positives, but harder to match)."
        )
        
        live_val = st.selectbox(
            "Liveness Verification Type",
            ["Blink Only", "Head Turn Only", "Blink & Head Turn", "None"],
            index=["Blink Only", "Head Turn Only", "Blink & Head Turn", "None"].index(liveness_mode),
            help="Select the liveness rules required for valid authentication."
        )
        
        if st.button("💾 Save Configuration", use_container_width=True):
            update_setting("similarity_threshold", str(sim_val))
            update_setting("liveness_mode", live_val)
            st.success("System configurations updated successfully!")
            time.sleep(1.0)
            st.rerun()

    # 3. STUDENT DIRECTORY
    with tab_students:
        st.markdown("### Registered Students Directory")
        students = get_all_users()
        if not students:
            st.info("No students enrolled yet.")
        else:
            for s in students:
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.write(f"👤 **{s['name']}** (Login ID: `{s['login_id']}`)")
                with c2:
                    st.write(f"📅 Enrolled: {s['created_at'][:16]}")
                with c3:
                    if st.button("🗑️ Delete", key=f"del_{s['id']}", use_container_width=True):
                        encoder.delete_embedding(s['login_id'])
                        delete_user(s['id'])
                        st.success(f"Removed {s['name']}.")
                        time.sleep(0.5)
                        st.rerun()

    # 4. ATTENDANCE REPORTS
    with tab_logs:
        st.markdown("### Attendance Logs (Today)")
        logs = get_attendance_today()
        
        col_stat1, col_stat2 = st.columns(2)
        students = get_all_users()
        
        with col_stat1:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-title'>Total Enrolled Students</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{len(students)}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_stat2:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-title'>Attendances Logged Today</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{len(logs)}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        if not logs:
            st.info("No attendance logged today.")
        else:
            import pandas as pd
            df = pd.DataFrame(logs)
            df.columns = ["Log ID", "Student Name", "Log Time", "Liveness Mode"]
            df["Log Time"] = pd.to_datetime(df["Log Time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Today's Reports as CSV",
                data=csv,
                file_name=f"attendance_report_{get_ist_now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

# ----------------- STUDENT PORTAL -----------------
else:
    st.markdown("<h1 class='main-title'>🎓 Student Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>Hello, {st.session_state.user['name']}! Authenticate your attendance securely below.</div>", unsafe_allow_html=True)
    
    # 6-Hour Cooldown Verification
    last_log = get_last_attendance(st.session_state.user['id'])
    now = get_ist_now()
    
    can_mark = True
    cooldown_rem = None
    
    if last_log is not None:
        diff = now - last_log
        if diff < timedelta(hours=6):
            can_mark = False
            cooldown_rem = timedelta(hours=6) - diff
            
    if not can_mark:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-title' style='color:#ef4444;'>🚫 Cooldown Active</div>", unsafe_allow_html=True)
        
        tot_secs = int(cooldown_rem.total_seconds())
        h, rem = divmod(tot_secs, 3600)
        m, s = divmod(rem, 60)
        
        st.markdown(f"<div class='metric-value'>{h:02d}h {m:02d}m {s:02d}s</div>", unsafe_allow_html=True)
        st.write("You have already logged your attendance. Repeated attendance is disabled for 6 hours.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.info(f"Last logged at: **{last_log.strftime('%Y-%m-%d %H:%M:%S')} (IST)**")
        
    else:
        col_left, col_right = st.columns([2, 1])
        
        with col_right:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-title'>System Status</div>", unsafe_allow_html=True)
            if st.session_state.camera_running:
                st.markdown("<div class='metric-value' style='color:#10b981;'>● Active Feed</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='metric-value' style='color:#38bdf8;'>○ Eligible</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-title'>Anti-Spoofing Checklist</div>", unsafe_allow_html=True)
            
            b_chk = "✅ Blink Detected" if st.session_state.liveness_blink else "❌ Blink Required"
            h_chk = f"✅ Head Turned ({st.session_state.head_turn_state})" if st.session_state.liveness_head else "❌ Head Turn Required"
            
            if liveness_mode in ["Blink Only", "Blink & Head Turn"]:
                st.write(b_chk)
            if liveness_mode in ["Head Turn Only", "Blink & Head Turn"]:
                st.write(h_chk)
            if liveness_mode == "None":
                st.write("🟢 Anti-spoofing disabled")
                
            if st.session_state.liveness_verified:
                st.success("🟢 Liveness verified!")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_left:
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if not st.session_state.camera_running:
                    if st.button("▶️ Start Attendance Camera", use_container_width=True):
                        st.session_state.camera_running = True
                        reset_liveness_states()
                        st.rerun()
                else:
                    if st.button("⏹️ Stop Camera", use_container_width=True):
                        st.session_state.camera_running = False
                        st.rerun()
            with btn_col2:
                if st.button("🔄 Reset Liveness Check", use_container_width=True):
                    reset_liveness_states()
                    
            frame_placeholder = st.empty()
            
            if st.session_state.camera_running:
                cap = cv2.VideoCapture(0)
                student_emb_path = os.path.join("data/embeddings", f"{st.session_state.user['login_id']}.npy")
                
                if not os.path.exists(student_emb_path):
                    st.session_state.camera_running = False
                    frame_placeholder.error("⚠️ Face profile not registered. Please contact the administrator to enrol your face profile.")
                elif not cap.isOpened():
                    st.session_state.camera_running = False
                    frame_placeholder.error("⚠️ Webcam unavailable. Verify your camera settings.")
                    
                    # Fallback
                    st.info("💡 Fallback Mode: Upload your photo to verify.")
                    uploaded_file = st.file_uploader("Upload Image Profile", type=["jpg", "jpeg", "png"])
                    if uploaded_file is not None:
                        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                        image = cv2.imdecode(file_bytes, 1)
                        face_meta = detector.process_frame(image, 0, force_process=True)
                        if face_meta:
                            emb = encoder.generate_embedding(image)
                            if emb is not None:
                                reg_emb = np.load(student_emb_path)
                                sim = encoder.compare_embeddings(emb, reg_emb)
                                if sim >= similarity_threshold:
                                    log_attendance(st.session_state.user['id'], liveness_method="Fallback (Upload)")
                                    st.session_state.attendance_success = True
                                    st.session_state.camera_running = False
                                    st.session_state.last_attendance_marked = (st.session_state.user['name'], get_ist_now())
                                    st.rerun()
                                else:
                                    st.error("Face does not match your registered profile.")
                            else:
                                st.error("Failed to extract face features.")
                        else:
                            st.error("No face detected in upload.")
                else:
                    frame_count = 0
                    reg_emb = np.load(student_emb_path)
                    
                    while st.session_state.camera_running:
                        ret, frame = cap.read()
                        if not ret:
                            st.error("Lost webcam stream feed.")
                            break
                            
                        frame_count += 1
                        face_meta = detector.process_frame(frame, frame_count)
                        
                        if face_meta:
                            x, y, w, h = face_meta['bbox']
                            ear = face_meta['ear']
                            yaw_ratio = face_meta['yaw_ratio']
                            
                            if not st.session_state.liveness_verified:
                                check_liveness_conditions(ear, yaw_ratio, liveness_mode)
                                
                            if not st.session_state.liveness_verified:
                                box_color = (0, 165, 255)
                                label = f"Verifying Liveness | EAR: {ear:.2f} | Yaw: {yaw_ratio:.2f}"
                            else:
                                box_color = (255, 0, 0)
                                label = "Liveness OK | Matching Face..."
                                
                                emb = encoder.generate_embedding(frame)
                                if emb is not None:
                                    sim = encoder.compare_embeddings(emb, reg_emb)
                                    if sim >= similarity_threshold:
                                        log_attendance(st.session_state.user['id'], liveness_method=liveness_mode)
                                        st.session_state.attendance_success = True
                                        st.session_state.camera_running = False
                                        st.session_state.last_attendance_marked = (st.session_state.user['name'], get_ist_now())
                                        cap.release()
                                        reset_liveness_states()
                                        st.rerun()
                                    else:
                                        box_color = (0, 0, 255)
                                        label = f"Match Failed: Not {st.session_state.user['name']}"
                                else:
                                    box_color = (0, 0, 255)
                                    label = "Failed to extract face features."
                                    
                            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
                        else:
                            if not st.session_state.liveness_verified:
                                st.session_state.eye_closed_streak = 0
                                
                        frame_placeholder.image(frame, channels="BGR", use_container_width=True)
                        time.sleep(0.01)
                        
                    cap.release()
                    reset_liveness_states()
