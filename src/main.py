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
    get_setting, update_setting, get_student_attendance_history
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
if 'portal' not in st.session_state:
    st.session_state.portal = "Home"
if 'kiosk_marked_name' not in st.session_state:
    st.session_state.kiosk_marked_name = None

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
    marked_name = st.session_state.kiosk_marked_name if st.session_state.kiosk_marked_name else "Attendance"
    st.markdown(f"""
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
        <h2 style="color: white; margin-top: 0;">🎉 Success!</h2>
        <p style="font-size: 1.25rem; font-weight: 500; margin-bottom: 0;">Checked In: <b>{marked_name}</b></p>
    </div>
    <style>
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translate(-50%, -45%); }}
            to {{ opacity: 1; transform: translate(-50%, -50%); }}
        }}
    </style>
    """, unsafe_allow_html=True)
    time.sleep(3.0)
    st.session_state.attendance_success = False
    st.session_state.kiosk_marked_name = None
    st.rerun()

# ----------------- LOGIN / SECURITY ROUTING -----------------
similarity_threshold = float(get_setting("similarity_threshold", "0.5"))
liveness_mode = get_setting("liveness_mode", "Blink & Head Turn")

# Side Navigation Header
if st.session_state.portal != "Home":
    st.sidebar.markdown("<h2 style='color:#818cf8; text-align: center;'>🌐 Navigation</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🏠 Switch Portal", use_container_width=True):
        st.session_state.portal = "Home"
        st.session_state.camera_running = False
        st.session_state.user = None
        reset_liveness_states()
        st.rerun()

# 1. HOME PORTAL SELECTOR
if st.session_state.portal == "Home":
    st.markdown("<div style='text-align: center; margin-top: 2rem;'>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title' style='text-align: center;'>🔑 BioAccess Portal</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle' style='text-align: center;'>Select a portal to access the system</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.form("home_kiosk_card"):
            st.markdown("<div class='portal-header'>📸 Mark Attendance</div>", unsafe_allow_html=True)
            st.markdown("<div class='portal-desc'>Kiosk-style interface. Real-time facial scan for students. No login required.</div>", unsafe_allow_html=True)
            kiosk_btn = st.form_submit_button("Launch Kiosk Mode", use_container_width=True)
            if kiosk_btn:
                st.session_state.portal = "Kiosk"
                st.session_state.camera_running = False
                st.session_state.user = None
                reset_liveness_states()
                st.rerun()
                
    with col2:
        with st.form("home_student_card"):
            st.markdown("<div class='portal-header'>🎓 Student Portal</div>", unsafe_allow_html=True)
            st.markdown("<div class='portal-desc'>Dashboard to view your attendance history and check-in verification status. Login required.</div>", unsafe_allow_html=True)
            student_btn = st.form_submit_button("Enter Student Portal", use_container_width=True)
            if student_btn:
                st.session_state.portal = "Student"
                st.session_state.user = None
                st.rerun()
                
    with col3:
        with st.form("home_admin_card"):
            st.markdown("<div class='portal-header'>🏢 Admin Portal</div>", unsafe_allow_html=True)
            st.markdown("<div class='portal-desc'>Register students, configure matching thresholds, and export logs. Login required.</div>", unsafe_allow_html=True)
            admin_btn = st.form_submit_button("Enter Admin Portal", use_container_width=True)
            if admin_btn:
                st.session_state.portal = "Admin"
                st.session_state.user = None
                st.rerun()
    st.stop()

# 2. KIOSK PORTAL
elif st.session_state.portal == "Kiosk":
    st.markdown("<h1 class='main-title'>📸 Attendance Kiosk</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Place your face in the camera view to check in automatically.</div>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([2, 1])
    
    with col_right:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-title'>System Status</div>", unsafe_allow_html=True)
        if st.session_state.camera_running:
            st.markdown("<div class='metric-value' style='color:#10b981;'>● Active Scan</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='metric-value' style='color:#38bdf8;'>○ Ready</div>", unsafe_allow_html=True)
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
                if st.button("▶️ Start Kiosk Camera", use_container_width=True):
                    st.session_state.camera_running = True
                    reset_liveness_states()
                    st.rerun()
            else:
                if st.button("⏹️ Stop Kiosk Camera", use_container_width=True):
                    st.session_state.camera_running = False
                    st.rerun()
        with btn_col2:
            if st.button("🔄 Reset Liveness", use_container_width=True):
                reset_liveness_states()
                st.rerun()
                
        frame_placeholder = st.empty()
        
        if st.session_state.camera_running:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.session_state.camera_running = False
                frame_placeholder.error("⚠️ Webcam unavailable. Verify your camera settings.")
            else:
                frame_count = 0
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
                            label = "Liveness OK | Identifying Face..."
                            
                            emb = encoder.generate_embedding(frame)
                            if emb is not None:
                                match_id, sim = encoder.find_match(emb, similarity_threshold)
                                if match_id is not None:
                                    student = get_user_by_login_id(match_id)
                                    if student:
                                        last_log = get_last_attendance(student['id'])
                                        now = get_ist_now()
                                        can_mark = True
                                        if last_log is not None and (now - last_log) < timedelta(hours=6):
                                            can_mark = False
                                            
                                        if not can_mark:
                                            box_color = (0, 165, 255)
                                            label = f"Already Checked In: {student['name']}"
                                        else:
                                            log_attendance(student['id'], liveness_method=liveness_mode)
                                            st.session_state.attendance_success = True
                                            st.session_state.kiosk_marked_name = student['name']
                                            st.session_state.camera_running = False
                                            cap.release()
                                            reset_liveness_states()
                                            st.rerun()
                                else:
                                    box_color = (0, 0, 255)
                                    label = f"Scanning... (Best Sim: {sim:.2f})"
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
    st.stop()

# 3. STUDENT PORTAL
elif st.session_state.portal == "Student":
    if st.session_state.user is None or st.session_state.user['role'] != 'student':
        st.markdown("<div style='text-align: center; margin-top: 3rem;'>", unsafe_allow_html=True)
        st.markdown("<h1 class='main-title' style='text-align: center;'>🔑 Student Portal Login</h1>", unsafe_allow_html=True)
        st.markdown("<div class='subtitle' style='text-align: center;'>Please authenticate to view your dashboard</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        col_l, col_mid, col_r = st.columns([1, 2, 1])
        with col_mid:
            with st.form("student_login_form"):
                st.markdown("<div class='portal-header'>🎓 Student Login</div>", unsafe_allow_html=True)
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
        st.stop()
        
    # Render Student Profile Details in Sidebar
    st.sidebar.markdown("<h2 style='color:#818cf8;'>👤 Profile Details</h2>", unsafe_allow_html=True)
    st.sidebar.write(f"**Name:** {st.session_state.user['name']}")
    st.sidebar.write(f"**Login ID:** {st.session_state.user['login_id']}")
    st.sidebar.write(f"**Department:** {st.session_state.user.get('department') or 'N/A'}")
    st.sidebar.write(f"**Section:** {st.session_state.user.get('section') or 'N/A'}")
    st.sidebar.markdown(
        f"<span style='background-color:#818cf822; color:#818cf8; padding:0.25rem 0.6rem; border-radius:4px; font-weight:bold; font-size:0.85rem;'>STUDENT PORTAL</span>",
        unsafe_allow_html=True
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.camera_running = False
        reset_liveness_states()
        st.rerun()

    # Dashboard contents
    st.markdown(f"<h1 class='main-title'>🎓 Student Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>Hello, {st.session_state.user['name']}! Review your attendance history and verification status.</div>", unsafe_allow_html=True)
    
    col_status, col_history = st.columns([1, 2])
    
    with col_status:
        st.markdown("### Today's Status")
        last_log = get_last_attendance(st.session_state.user['id'])
        now = get_ist_now()
        marked_today = False
        if last_log is not None and last_log.date() == now.date():
            marked_today = True
            
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-title'>Verification Status</div>", unsafe_allow_html=True)
        if marked_today:
            st.markdown("<div class='metric-value' style='color:#10b981;'>● Checked In</div>", unsafe_allow_html=True)
            st.write(f"Logged today at: **{last_log.strftime('%I:%M %p')}**")
        else:
            st.markdown("<div class='metric-value' style='color:#ef4444;'>○ Absent / Pending</div>", unsafe_allow_html=True)
            st.write("Your attendance for today has not been marked yet.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_history:
        st.markdown("### Personal Attendance History")
        history = get_student_attendance_history(st.session_state.user['id'])
        if not history:
            st.info("No attendance records found.")
        else:
            import pandas as pd
            df = pd.DataFrame(history)
            df.columns = ["Record ID", "Date & Time", "Verification Method"]
            df["Date & Time"] = pd.to_datetime(df["Date & Time"]).dt.strftime("%Y-%m-%d %I:%M %p")
            st.dataframe(df, use_container_width=True)
    st.stop()

# 4. ADMIN PORTAL
elif st.session_state.portal == "Admin":
    if st.session_state.user is None or st.session_state.user['role'] != 'admin':
        st.markdown("<div style='text-align: center; margin-top: 3rem;'>", unsafe_allow_html=True)
        st.markdown("<h1 class='main-title' style='text-align: center;'>🔑 Admin Portal Login</h1>", unsafe_allow_html=True)
        st.markdown("<div class='subtitle' style='text-align: center;'>Please authenticate to view the administrative panel</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        col_l, col_mid, col_r = st.columns([1, 2, 1])
        with col_mid:
            with st.form("admin_login_form"):
                st.markdown("<div class='portal-header'>🏢 Admin Login</div>", unsafe_allow_html=True)
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

    # Render Profile Details in Sidebar
    st.sidebar.markdown("<h2 style='color:#818cf8;'>👤 Profile Details</h2>", unsafe_allow_html=True)
    st.sidebar.write(f"**Name:** {st.session_state.user['name']}")
    st.sidebar.write(f"**Login ID:** {st.session_state.user['login_id']}")
    st.sidebar.markdown(
        f"<span style='background-color:#38bdf822; color:#38bdf8; padding:0.25rem 0.6rem; border-radius:4px; font-weight:bold; font-size:0.85rem;'>ADMIN PORTAL</span>",
        unsafe_allow_html=True
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.camera_running = False
        reset_liveness_states()
        st.rerun()

    st.markdown("<h1 class='main-title'>🏢 Admin Control Panel</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Manage student directory, set face threshold criteria, and inspect reports</div>", unsafe_allow_html=True)
    
    tab_enroll, tab_settings, tab_students, tab_classrooms, tab_logs = st.tabs([
        "👤 Register Student",
        "⚙️ Threshold Settings",
        "📋 Student Directory",
        "🏫 Classroom Files",
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
            reg_department = st.text_input("Department", placeholder="e.g. Computer Science").strip()
            reg_section = st.text_input("Section", placeholder="e.g. A").strip()
            
            enroll_btn = st.button("📸 Capture & Enrol Student Face", disabled=not (reg_name and reg_login and reg_password and reg_department and reg_section))
            
            if enroll_btn:
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
                                        add_user(reg_name, reg_login, reg_password, role='student', department=reg_department, section=reg_section)
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
                dept_sec = f" | Dept: **{s.get('department') or 'N/A'}** | Sec: **{s.get('section') or 'N/A'}**"
                with c1:
                    st.write(f"👤 **{s['name']}** (Login ID: `{s['login_id']}`){dept_sec}")
                with c2:
                    st.write(f"📅 Enrolled: {s['created_at'][:16]}")
                with c3:
                    if st.button("🗑️ Delete", key=f"del_{s['id']}", use_container_width=True):
                        encoder.delete_embedding(s['login_id'])
                        delete_user(s['id'])
                        st.success(f"Removed {s['name']}.")
                        time.sleep(0.5)
                        st.rerun()

    # 3.5. CLASSROOM FILES
    with tab_classrooms:
        st.markdown("### 🏫 Classroom Attendance Folders")
        
        classrooms_dir = "classrooms"
        if not os.path.exists(classrooms_dir) or not os.listdir(classrooms_dir):
            st.info("No classroom folders have been created yet. Classroom folders are automatically created when attendance is successfully logged for a student with an assigned department and section.")
        else:
            # List all classroom directories
            dirs = [d for d in os.listdir(classrooms_dir) if os.path.isdir(os.path.join(classrooms_dir, d))]
            if not dirs:
                st.info("No classroom folders have been created yet.")
            else:
                selected_classroom = st.selectbox("Select Classroom Folder to Inspect", sorted(dirs))
                
                if selected_classroom:
                    classroom_path = os.path.join(classrooms_dir, selected_classroom)
                    files = [f for f in os.listdir(classroom_path) if f.endswith(".csv")]
                    
                    if not files:
                        st.warning("No attendance files found in this classroom folder.")
                    else:
                        selected_file = st.selectbox("Select Attendance File", sorted(files))
                        
                        if selected_file:
                            file_path = os.path.join(classroom_path, selected_file)
                            import pandas as pd
                            try:
                                df_class = pd.read_csv(file_path)
                                st.markdown(f"#### Preview: `{selected_file}`")
                                st.dataframe(df_class, use_container_width=True)
                                
                                # Download button
                                with open(file_path, "rb") as f:
                                    st.download_button(
                                        label="📥 Download CSV File",
                                        data=f,
                                        file_name=selected_file,
                                        mime="text/csv",
                                        use_container_width=True
                                    )
                            except Exception as e:
                                st.error(f"Error reading file: {e}")

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
