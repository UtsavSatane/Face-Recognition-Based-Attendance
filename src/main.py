import os
import base64
import cv2
import numpy as np
from datetime import datetime, timedelta
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, jsonify, send_file

from database import (
    init_db, add_user, get_user_by_name, log_attendance, 
    get_attendance_today, get_all_users, delete_user, get_ist_now,
    authenticate_user, get_user_by_login_id, get_last_attendance,
    get_setting, update_setting, get_student_attendance_history,
    create_reset_request, get_reset_requests, update_reset_request_status,
    verify_and_reset_password
)
from detector import FaceDetector
from encoder import FaceEncoder

# Initialize database
init_db()

# Configure Flask app
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = "bioaccess_secure_face_attendance_key"

# Initialize AI models globally
detector = FaceDetector()
encoder = FaceEncoder()

def decode_base64_image(base64_string):
    """Converts a base64 image string into an OpenCV image (numpy array)."""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error decoding base64 image: {e}")
        return None

# ----------------- PAGE ROUTE -----------------
@app.route('/')
def index():
    """Serves the main single page web application."""
    return render_template('index.html')

# ----------------- SETTINGS API -----------------
@app.route('/api/settings', methods=['GET'])
def get_settings():
    similarity_threshold = get_setting("similarity_threshold", "0.5")
    liveness_mode = get_setting("liveness_mode", "Blink & Head Turn")
    return jsonify({
        "similarity_threshold": similarity_threshold,
        "liveness_mode": liveness_mode
    })

# ----------------- KIOSK PORTAL APIs -----------------
@app.route('/api/kiosk/frame', methods=['POST'])
def process_kiosk_frame():
    """
    Accepts video frame, processes for face detection, liveness landmarks,
    and returns liveness ratios and matching status if verified.
    """
    data = request.json
    base64_image = data.get('image')
    liveness_verified = data.get('liveness_verified', False)
    
    if not base64_image:
        return jsonify({"error": "No image data received"}), 400
        
    frame = decode_base64_image(base64_image)
    if frame is None:
        return jsonify({"error": "Failed to decode image"}), 400
        
    # Process face detection
    face_meta = detector.process_frame(frame, frame_count=0, force_process=True)
    
    if not face_meta:
        return jsonify({"face_detected": False})
        
    # Face metadata extraction
    bbox = face_meta['bbox']
    ear = face_meta['ear']
    yaw_ratio = face_meta['yaw_ratio']
    
    response_data = {
        "face_detected": True,
        "bbox": bbox,
        "ear": ear,
        "yaw_ratio": yaw_ratio,
        "matched": False
    }
    
    # If client says liveness has been verified, perform face recognition
    if liveness_verified:
        similarity_threshold = float(get_setting("similarity_threshold", "0.5"))
        liveness_mode = get_setting("liveness_mode", "Blink & Head Turn")
        
        emb = encoder.generate_embedding(frame)
        if emb is not None:
            match_id, sim = encoder.find_match(emb, similarity_threshold)
            response_data["sim_score"] = sim
            
            if match_id is not None:
                student = get_user_by_login_id(match_id)
                if student:
                    last_log = get_last_attendance(student['id'])
                    now = get_ist_now()
                    can_mark = True
                    if last_log is not None and (now - last_log) < timedelta(hours=6):
                        can_mark = False
                        
                    if not can_mark:
                        response_data["error"] = f"Already checked in: {student['name']}"
                    else:
                        log_attendance(student['id'], liveness_method=liveness_mode)
                        response_data["matched"] = True
                        response_data["name"] = student['name']
                        response_data["login_id"] = student['login_id']
            else:
                response_data["error"] = "No matching student profile found"
        else:
            response_data["error"] = "Failed to extract face embedding"
            
    return jsonify(response_data)

# ----------------- STUDENT PORTAL APIs -----------------
@app.route('/api/student/login', methods=['POST'])
def student_login():
    data = request.json
    login_id = data.get('login_id')
    password = data.get('password')
    
    if not login_id or not password:
        return jsonify({"error": "Login ID and password required"}), 400
        
    user = authenticate_user(login_id, password)
    if user and user['role'] == 'student':
        return jsonify({"user": user})
    elif user and user['role'] != 'student':
        return jsonify({"error": "Access Denied: This is not a student account"}), 403
    else:
        return jsonify({"error": "Invalid Login ID or Password"}), 401

@app.route('/api/student/dashboard', methods=['GET'])
def student_dashboard():
    user_id_str = request.args.get('user_id')
    if not user_id_str:
        return jsonify({"error": "Missing user_id parameter"}), 400
        
    user_id = int(user_id_str)
    
    # Check if marked today
    last_log = get_last_attendance(user_id)
    now = get_ist_now()
    marked_today = False
    last_log_time = ""
    
    if last_log is not None and last_log.date() == now.date():
        marked_today = True
        last_log_time = last_log.strftime("%I:%M %p")
        
    # Get attendance history
    history = get_student_attendance_history(user_id)
    formatted_history = []
    for h in history:
        formatted_history.append({
            "id": h["id"],
            "timestamp": datetime.strptime(h["timestamp"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %I:%M %p"),
            "liveness_method": h["liveness_method"]
        })
        
    return jsonify({
        "marked_today": marked_today,
        "last_log_time": last_log_time,
        "history": formatted_history
    })

# ----------------- ADMIN PORTAL APIs -----------------
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    login_id = data.get('login_id')
    password = data.get('password')
    
    if not login_id or not password:
        return jsonify({"error": "Login ID and password required"}), 400
        
    user = authenticate_user(login_id, password)
    if user and user['role'] == 'admin':
        return jsonify({"user": user})
    elif user and user['role'] != 'admin':
        return jsonify({"error": "Access Denied: This is not an administrator account"}), 403
    else:
        return jsonify({"error": "Invalid Login ID or Password"}), 401

@app.route('/api/admin/students', methods=['GET'])
def admin_students_directory():
    students = get_all_users()
    return jsonify(students)

@app.route('/api/admin/delete_student', methods=['POST'])
def admin_delete_student():
    data = request.json
    student_id = data.get('id')
    login_id = data.get('login_id')
    
    if not student_id or not login_id:
        return jsonify({"error": "Missing student ID or login ID"}), 400
        
    try:
        # Delete embedding file
        encoder.delete_embedding(login_id)
        # Delete from db
        delete_user(int(student_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/enroll', methods=['POST'])
def admin_enroll_student():
    data = request.json
    name = data.get('name')
    login_id = data.get('login_id')
    password = data.get('password')
    department = data.get('department')
    section = data.get('section')
    base64_image = data.get('image')
    
    if not all([name, login_id, password, department, section, base64_image]):
        return jsonify({"error": "All fields are required"}), 400
        
    if get_user_by_login_id(login_id) is not None:
        return jsonify({"error": f"Login ID '{login_id}' is already registered."}), 400
        
    frame = decode_base64_image(base64_image)
    if frame is None:
        return jsonify({"error": "Failed to decode camera capture image"}), 400
        
    # Check if face exists in capture
    face_meta = detector.process_frame(frame, 0, force_process=True)
    if not face_meta:
        return jsonify({"error": "No face detected. Please ensure your face is fully centered and try again."}), 400
        
    # Generate face embedding
    emb = encoder.generate_embedding(frame)
    if emb is None:
        return jsonify({"error": "Failed to extract face features. Please try again under clean lighting."}), 400
        
    try:
        encoder.save_embedding(login_id, emb)
        add_user(name, login_id, password, role='student', department=department, section=section)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Error saving profile: {e}"}), 500

@app.route('/api/admin/settings', methods=['POST'])
def admin_update_settings():
    data = request.json
    threshold = data.get('threshold')
    liveness_mode = data.get('liveness_mode')
    
    if not threshold or not liveness_mode:
        return jsonify({"error": "Threshold and liveness mode parameters required"}), 400
        
    try:
        update_setting("similarity_threshold", str(threshold))
        update_setting("liveness_mode", liveness_mode)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/classrooms', methods=['GET'])
def admin_list_classrooms():
    classrooms_dir = "classrooms"
    if not os.path.exists(classrooms_dir):
        return jsonify({"classrooms": []})
        
    dirs = [d for d in os.listdir(classrooms_dir) if os.path.isdir(os.path.join(classrooms_dir, d))]
    return jsonify({"classrooms": sorted(dirs)})

@app.route('/api/admin/classrooms/<classroom>', methods=['GET'])
def admin_list_classroom_files(classroom):
    classroom_path = os.path.join("classrooms", classroom)
    if not os.path.exists(classroom_path):
        return jsonify({"files": []})
        
    files = [f for f in os.listdir(classroom_path) if f.endswith(".csv")]
    return jsonify({"files": sorted(files)})

@app.route('/api/admin/classrooms/<classroom>/<file_name>', methods=['GET'])
def admin_view_classroom_file(classroom, file_name):
    file_path = os.path.join("classrooms", classroom, file_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
        
    import csv
    try:
        headers = []
        rows = []
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            for r in reader:
                rows.append(r)
        return jsonify({
            "headers": headers,
            "rows": rows
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/download_classroom', methods=['GET'])
def admin_download_classroom_file():
    classroom = request.args.get('classroom')
    file_name = request.args.get('file')
    
    if not classroom or not file_name:
        return "Missing parameters", 400
        
    file_path = os.path.join("classrooms", classroom, file_name)
    if not os.path.exists(file_path):
        return "File not found", 404
        
    return send_file(os.path.abspath(file_path), as_attachment=True, download_name=file_name)

@app.route('/api/admin/reports', methods=['GET'])
def admin_get_reports():
    logs = get_attendance_today()
    students = get_all_users()
    
    formatted_logs = []
    for l in logs:
        formatted_logs.append({
            "id": l["id"],
            "name": l["name"],
            "timestamp": datetime.strptime(l["timestamp"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %I:%M:%S %p"),
            "liveness_method": l["liveness_method"]
        })
        
    return jsonify({
        "total_students": len(students),
        "today_attendance_count": len(logs),
        "logs": formatted_logs
    })

@app.route('/api/admin/download_report', methods=['GET'])
def admin_download_report():
    import csv
    import io
    
    logs = get_attendance_today()
    
    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log ID", "Student Name", "Timestamp", "Liveness Mode"])
    
    for l in logs:
        timestamp_formatted = datetime.strptime(l["timestamp"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %I:%M:%S %p")
        writer.writerow([l["id"], l["name"], timestamp_formatted, l["liveness_method"]])
        
    output.seek(0)
    
    # Convert String to Bytes
    bytes_io = io.BytesIO()
    bytes_io.write(output.getvalue().encode('utf-8'))
    bytes_io.seek(0)
    
    date_str = get_ist_now().strftime("%Y-%m-%d")
    return send_file(
        bytes_io,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"attendance_report_{date_str}.csv"
    )

# ----------------- PASSWORD RESET SYSTEM APIs -----------------
@app.route('/api/student/forgot-password', methods=['POST'])
def student_forgot_password():
    data = request.json
    login_id = data.get('login_id')
    if not login_id:
        return jsonify({"error": "Student Login ID is required"}), 400
        
    try:
        create_reset_request(login_id)
        return jsonify({"success": True, "message": "Request sent to admin for approval."})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/student/reset-with-otp', methods=['POST'])
def student_reset_with_otp():
    data = request.json
    login_id = data.get('login_id')
    otp = data.get('otp')
    new_password = data.get('new_password')
    
    if not login_id or not otp or not new_password:
        return jsonify({"error": "All fields (Student ID, OTP, and New Password) are required."}), 400
        
    try:
        success, message = verify_and_reset_password(login_id, otp, new_password)
        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"error": message}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/admin/reset-requests', methods=['GET'])
def admin_get_reset_requests():
    try:
        requests_list = get_reset_requests()
        return jsonify(requests_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/reset-requests/<int:request_id>/action', methods=['POST'])
def admin_reset_request_action(request_id):
    data = request.json
    action = data.get('action')
    admin_id = data.get('admin_id')
    
    if not action or action not in ['approve', 'reject']:
        return jsonify({"error": "Invalid action. Must be 'approve' or 'reject'."}), 400
    if not admin_id:
        return jsonify({"error": "Admin ID is required for audit logs."}), 400
        
    try:
        if action == 'approve':
            import random
            otp = f"{random.randint(100000, 999999)}"
            update_reset_request_status(request_id, 'APPROVED', int(admin_id), otp)
            return jsonify({"success": True, "message": "Request approved.", "otp": otp})
        else:
            update_reset_request_status(request_id, 'REJECTED', int(admin_id))
            return jsonify({"success": True, "message": "Request rejected."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- MAIN SERVER RUN -----------------
def open_browser():
    webbrowser.open_new("http://localhost:6030/")

if __name__ == '__main__':
    # Prevent opening browser twice when Flask reloader is active
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, open_browser).start()

    # Running locally, binding to localhost
    app.run(host='127.0.0.1', port=6030, debug=True)
