# BioAccess | AI Face Recognition Attendance System

BioAccess is a modern, modular, production-grade real-time Face Recognition Attendance System built with **Python 3.11+**, **Streamlit**, **MediaPipe**, and **InsightFace**. It features a browser-based interactive dashboard, anti-spoofing liveness checks, and high-performance processing.

The application has been fully optimized to operate on **Indian Standard Time (IST)**, ensuring precise, region-specific logging, duplicate prevention, and report generation.

---

## 🚀 Key Features

*   **Real-Time Face Recognition:** Recognizes employees using a 512-dimensional facial embedding generated via InsightFace's `buffalo_l` model.
*   **Anti-Spoofing Liveness Checks:**
    *   **Blink Detection (Eye Aspect Ratio - EAR):** Prevents static photo/video presentation attacks by requiring the user to blink.
    *   **Head Turn (Yaw Ratio):** Evaluates 2D perspective shifts of facial landmarks to confirm voluntary motion.
*   **Frame-Skipping Optimization:** Processes every 5th frame for feature recognition to keep CPU usage low and maintain high FPS.
*   **SQLite Database Logging:** Manages registered employees and logs attendance records.
*   **Webcam Fallback Mode:** Allows uploading static images or videos if a camera is unavailable.
*   **IST Timezone Alignment:** Timestamps are recorded in Indian Standard Time (`UTC+05:30`), fixing duplicate log checks and aligning reports with the local work day.

---

## 📂 Project Structure

```text
├── data/                       # Local database & embedding storage
│   ├── embeddings/             # Enrolled user .npy embedding vectors
│   └── attendance.db           # SQLite attendance logs (stored in IST)
├── src/
│   ├── database.py             # SQLite database connections, CRUD operations, & IST helpers
│   ├── detector.py             # MediaPipe FaceMesh face & liveness detection
│   ├── encoder.py              # InsightFace 512-d embedding extraction
│   └── main.py                 # Streamlit UI, camera loops, & orchestration
├── tests/
│   ├── test_database.py        # SQLite database unit tests
│   ├── test_detector.py        # EAR & Yaw ratio mathematical unit tests
│   └── test_encoder.py         # Embedding generation & matching unit tests
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation and setup guide
```

---

## 🛠️ Installation & Setup

### Prerequisites

1.  **Python 3.11+**
2.  **Windows C++ Build Tools:**
    *   *Why?* The `insightface` and `onnxruntime` libraries contain C extensions. On Windows, if precompiled wheels are missing, pip compiles them from source, which requires a compiler.
    *   *Solution:* Download and install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and select the **Desktop development with C++** workload.

### Local Setup (Virtual Environment)

1.  **Clone or navigate to the project directory:**
    ```bash
    cd c:/Users/UTSAV/Desktop/Face
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    
    # Windows
    .venv\Scripts\activate
    
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

---

## 🏁 How to Run

### 1. Launch the Flask UI Dashboard
```bash
.venv\Scripts\python src/main.py
```
This opens the browser dashboard at `http://localhost:8501`.

### 2. User Enrollment Workflow
1.  Navigate to the **Register Employee** tab.
2.  Type the employee's full name.
3.  Look directly at the webcam and click **Capture & Save Face Profile**.
4.  The system will extract the face signature and save it to `data/embeddings/`.

### 3. Attendance Recording
1.  Navigate to the **Real-Time Attendance** tab.
2.  Configure your desired anti-spoofing mode in the sidebar (e.g., *Blink Only*, *Head Turn Only*, *Blink & Head Turn*).
3.  Click **Start Attendance Camera**.
4.  Follow the HUD instructions (e.g., blink or turn your head). Once liveness is verified, the system identifies you, logs attendance in SQLite, and displays a success banner.
5.  View today's records under the **Attendance Reports** tab.

---

## 🇮🇳 Timezone Configuration & Migration (IST)

The system is configured to use **Indian Standard Time (IST - UTC+05:30)** natively. 

### Implementation Details
- **Explicit IST Generation:** The database interface uses `get_ist_now()` in python:
  ```python
  def get_ist_now() -> datetime:
      ist = timezone(timedelta(hours=5, minutes=30))
      return datetime.now(ist).replace(tzinfo=None)
  ```
  This creates a naive datetime object set to the correct local time offset, avoiding discrepancies between different SQLite system clocks and local python environments.
- **Double Tap Protection:** Rapid duplicate checks (preventing marking attendance twice within 5 minutes) comparison checks now correctly compare database log timestamps and local current time in the same timezone (IST).
- **Date-based Queries:** Queries for today's logs filter precisely by today's date in IST instead of relying on SQLite's UTC date functions.

### Database Migration
If you had existing logs stored in UTC format, they can be migrated to IST using the migration script:
```bash
python .system_generated/tasks/migrate_to_ist.py
```
This updates existing entries in `users` and `attendance` tables by shifting the UTC timestamps forward by `+5 hours 30 minutes`.

---

## 🧪 Running Automated Tests

A unit test suite validates database, math, and encoder logic. You do not need a camera to run these tests.

```bash
# Activate virtual environment and run tests
.venv\Scripts\pytest
```
