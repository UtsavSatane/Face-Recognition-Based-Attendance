import os
import cv2
import numpy as np
import streamlit as st
import time
from datetime import datetime, timedelta

from database import (
    init_db, add_user, get_user_by_name, log_attendance, 
    get_attendance_today, get_all_users, delete_user, get_ist_now
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

# ----------------- SIDEBAR CONFIG -----------------
st.sidebar.markdown("<h2 style='color:#818cf8;'>🛠️ Configuration</h2>", unsafe_allow_html=True)

similarity_threshold = st.sidebar.slider(
    "Face Match Threshold",
    min_value=0.3, max_value=0.8, value=0.5, step=0.05,
    help="Higher threshold is stricter, preventing false positives."
)

liveness_mode = st.sidebar.selectbox(
    "Liveness Verification Type",
    ["Blink Only", "Head Turn Only", "Blink & Head Turn", "None"],
    help="Choose the anti-spoofing criteria."
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 💡 How to verify
1. **Blink Only:** Look at the camera and blink naturally.
2. **Head Turn Only:** Turn your head slightly left or right.
3. **Blink & Head Turn:** Blink once and turn your head.
""")

# ----------------- MAIN UI -----------------
st.markdown("<h1 class='main-title'>🏢 BioAccess AI</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Production-Grade Real-Time Face Recognition Attendance System</div>", unsafe_allow_html=True)

# Tabs
tab_attendance, tab_enroll, tab_logs = st.tabs([
    "📸 Real-Time Attendance", 
    "👤 Register Employee", 
    "📋 Attendance Reports"
])

# ----------------- TAB 1: ATTENDANCE -----------------
with tab_attendance:
    col_left, col_right = st.columns([2, 1])

    with col_right:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-title'>System Status</div>", unsafe_allow_html=True)
        if st.session_state.camera_running:
            st.markdown("<div class='metric-value' style='color:#10b981;'>● Active Feed</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='metric-value' style='color:#ef4444;'>○ Standby</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Liveness progress visualizer
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-title'>Anti-Spoofing Checklist</div>", unsafe_allow_html=True)
        
        blink_status = "✅ Blink Detected" if st.session_state.liveness_blink else "❌ Blink Required"
        head_status = f"✅ Head Turned ({st.session_state.head_turn_state})" if st.session_state.liveness_head else "❌ Head Turn Required"
        
        if liveness_mode in ["Blink Only", "Blink & Head Turn"]:
            st.write(blink_status)
        if liveness_mode in ["Head Turn Only", "Blink & Head Turn"]:
            st.write(head_status)
        if liveness_mode == "None":
            st.write("🟢 Anti-spoofing disabled")
            
        if st.session_state.liveness_verified:
            st.success("🟢 Liveness verified!")
        st.markdown("</div>", unsafe_allow_html=True)

        # Show feedback for last marked attendance
        if st.session_state.last_attendance_marked:
            name, timestamp = st.session_state.last_attendance_marked
            st.markdown(f"""
            <div class='success-banner'>
                🎉 Attendance Logged!<br/>
                <b>Employee:</b> {name}<br/>
                <b>Time:</b> {timestamp.strftime('%H:%M:%S')}
            </div>
            """, unsafe_allow_html=True)

    with col_left:
        # Camera controls
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

        # Real-time processing loop
        if st.session_state.camera_running:
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                st.session_state.camera_running = False
                frame_placeholder.error("⚠️ Local webcam unavailable. Check connection or browser permissions.")
                
                # FALLBACK UI: Static Image or Video upload
                st.info("💡 Running in fallback mode. You can upload an image or video file below to verify attendance.")
                uploaded_file = st.file_uploader("Upload employee face image for recognition", type=["jpg", "jpeg", "png"])
                if uploaded_file is not None:
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    image = cv2.imdecode(file_bytes, 1)
                    
                    # Process image
                    # Perform detection (forced)
                    face_meta = detector.process_frame(image, 0, force_process=True)
                    if face_meta:
                        # Draw bounding box
                        x, y, w, h = face_meta['bbox']
                        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        
                        # Generate embedding
                        emb = encoder.generate_embedding(image)
                        if emb is not None:
                            matched_name, similarity = encoder.find_match(emb, threshold=similarity_threshold)
                            if matched_name:
                                # Log attendance
                                user = get_user_by_name(matched_name)
                                if user:
                                    # Check double marking
                                    today_logs = get_attendance_today()
                                    already_marked = any(log['name'] == matched_name for log in today_logs)
                                    if not already_marked:
                                        log_attendance(user['id'], liveness_method="Fallback (Upload)")
                                        st.session_state.last_attendance_marked = (matched_name, get_ist_now())
                                        st.success(f"Matched {matched_name} ({similarity*100:.1f}%) and logged attendance!")
                                    else:
                                        st.warning(f"{matched_name} has already logged attendance today.")
                            else:
                                st.error("Face not recognized in the database.")
                        else:
                            st.error("Failed to extract face features.")
                    else:
                        st.error("No face detected in the image.")
                    st.image(image, channels="BGR", caption="Processed Image", width=500)
            else:
                frame_count = 0
                cooldown_timer = None
                
                while st.session_state.camera_running:
                    ret, frame = cap.read()
                    if not ret:
                        st.error("Lost video feed.")
                        break

                    frame_count += 1
                    
                    # Detect face and liveness indicators
                    face_meta = detector.process_frame(frame, frame_count)
                    
                    if face_meta:
                        x, y, w, h = face_meta['bbox']
                        ear = face_meta['ear']
                        yaw_ratio = face_meta['yaw_ratio']
                        
                        # Apply liveness check logic
                        if not st.session_state.liveness_verified:
                            check_liveness_conditions(ear, yaw_ratio, liveness_mode)

                        # Color coding bounding boxes based on liveness status
                        if not st.session_state.liveness_verified:
                            box_color = (0, 165, 255)  # Orange: Verifying liveness
                            label = f"Verifying Liveness | EAR: {ear:.2f} | Yaw: {yaw_ratio:.2f}"
                        else:
                            box_color = (255, 0, 0)    # Blue: Verified liveness, looking for match
                            label = "Liveness OK | Matching Face..."
                            
                            # Face Identification block
                            # Process identification if cooldown is inactive
                            if cooldown_timer is None or (time.time() - cooldown_timer) > 3.0:
                                # Reset cooldown indicator
                                if cooldown_timer is not None:
                                    cooldown_timer = None
                                    
                                emb = encoder.generate_embedding(frame)
                                if emb is not None:
                                    matched_name, similarity = encoder.find_match(emb, threshold=similarity_threshold)
                                    if matched_name:
                                        # Match found! Log attendance
                                        user = get_user_by_name(matched_name)
                                        if user:
                                            # Check duplicate logs today
                                            today_logs = get_attendance_today()
                                            # Filter logs of this user within last 5 minutes to avoid rapid double-taps
                                            recent_marked = False
                                            for log in today_logs:
                                                if log['name'] == matched_name:
                                                    log_time = datetime.strptime(log['timestamp'], "%Y-%m-%d %H:%M:%S")
                                                    if get_ist_now() - log_time < timedelta(minutes=5):
                                                        recent_marked = True
                                                        break
                                            
                                            if not recent_marked:
                                                log_attendance(user['id'], liveness_method=liveness_mode)
                                                st.session_state.last_attendance_marked = (matched_name, get_ist_now())
                                                box_color = (0, 255, 0)  # Green: Success
                                                label = f"Welcome {matched_name} ({similarity*100:.1f}%)"
                                                # Activate cooldown and reset liveness
                                                cooldown_timer = time.time()
                                                reset_liveness_states()
                                                st.rerun()
                                            else:
                                                box_color = (0, 255, 255)  # Yellow
                                                label = f"{matched_name} (Already Logged)"
                                    else:
                                        box_color = (0, 0, 255)  # Red: Unknown face
                                        label = "Access Denied: Face Not Enrolled"
                            else:
                                # During cooldown
                                box_color = (0, 255, 0)
                                label = f"Success | Cooldown: {3.0 - (time.time() - cooldown_timer):.1f}s"

                        # Draw HUD and overlay
                        cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                        cv2.putText(
                            frame, label, (x, y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2
                        )
                    else:
                        # No face in screen, reset partial liveness checks for clean tracking
                        if not st.session_state.liveness_verified:
                            # Partially reset to handle next detection smoothly
                            st.session_state.eye_closed_streak = 0

                    # Display image frame in Streamlit
                    frame_placeholder.image(frame, channels="BGR", use_container_width=True)
                    time.sleep(0.01)

                cap.release()
                reset_liveness_states()

# ----------------- TAB 2: REGISTER EMPLOYEE -----------------
with tab_enroll:
    st.markdown("### 👤 Add New Employee to Database")
    
    col_reg_form, col_reg_cam = st.columns([1, 1])
    
    with col_reg_form:
        new_user_name = st.text_input("Full Name", placeholder="e.g., Utsav Kumar").strip()
        enroll_liveness = st.checkbox("Require Liveness Validation during registration", value=True)
        
        # State indicators
        if 'enroll_image_captured' not in st.session_state:
            st.session_state.enroll_image_captured = None
        
        enroll_btn = st.button("📸 Capture & Save Face Profile", disabled=not new_user_name)
        
        if enroll_btn and new_user_name:
            # Check if name already registered in SQLite
            user_check = get_user_by_name(new_user_name)
            if user_check:
                st.error(f"❌ User '{new_user_name}' is already registered in the system.")
            else:
                # Capture frame from camera
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    st.error("⚠️ Failed to open webcam. Ensure no other apps are using it.")
                else:
                    # Let the camera adjust brightness briefly
                    for _ in range(10):
                        cap.read()
                        
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret:
                        # Process face detection
                        face_meta = detector.process_frame(frame, 0, force_process=True)
                        if not face_meta:
                            st.error("❌ Registration Failed: No face detected in the frame. Please look directly at the camera.")
                        else:
                            # Generate embedding
                            embedding = encoder.generate_embedding(frame)
                            if embedding is not None:
                                # Save embedding (.npy)
                                try:
                                    encoder.save_embedding(new_user_name, embedding)
                                    # Save to SQLite db
                                    add_user(new_user_name)
                                    st.success(f"🎉 Success! Employee '{new_user_name}' has been successfully enrolled.")
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error saving user profile: {e}")
                            else:
                                st.error("❌ Failed to process facial details. Please try again under better lighting.")
                    else:
                        st.error("❌ Could not acquire image frame from camera.")

    with col_reg_cam:
        st.markdown("#### Registered Employees List")
        users = get_all_users()
        if not users:
            st.info("No employees registered yet.")
        else:
            for user in users:
                user_col_name, user_col_del = st.columns([3, 1])
                with user_col_name:
                    st.write(f"👤 **{user['name']}** (Joined: {user['created_at'][:10]})")
                with user_col_del:
                    if st.button("🗑️ Delete", key=f"del_{user['id']}"):
                        # Remove files
                        encoder.delete_embedding(user['name'])
                        delete_user(user['id'])
                        st.success(f"Deleted {user['name']}.")
                        time.sleep(0.5)
                        st.rerun()

# ----------------- TAB 3: REPORTS -----------------
with tab_logs:
    st.markdown("### 📋 Today's Attendance logs")
    
    col_stat1, col_stat2 = st.columns(2)
    logs = get_attendance_today()
    users = get_all_users()
    
    with col_stat1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-title'>Total Registered Employees</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{len(users)}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_stat2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown("<div class='metric-title'>Logged Attendances Today</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{len(logs)}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    if not logs:
        st.info("No attendance logged today.")
    else:
        # Display logs in table
        import pandas as pd
        df = pd.DataFrame(logs)
        # Rename columns for cleaner display
        df.columns = ["Log ID", "Employee Name", "Log Time", "Liveness Check Mode"]
        # Format Log Time to clean timestamp format
        df["Log Time"] = pd.to_datetime(df["Log Time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(df, use_container_width=True)
        
        # Download reports as CSV button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Today's Logs as CSV",
            data=csv,
            file_name=f"attendance_report_{get_ist_now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
