# BioAccess | AI Face Recognition Attendance System

BioAccess is a modern, modular, production-ready real-time Face Recognition Attendance System built with **Python 3.11+**, **Streamlit**, **MediaPipe**, and **InsightFace**. It features a browser-based interactive dashboard, anti-spoofing liveness checks, and high-performance processing.

## 🚀 Key Features

*   **Real-Time Face Recognition:** Recognizes employees using a 512-dimensional facial embedding generated via InsightFace's `buffalo_l` model.
*   **Anti-Spoofing Liveness Checks:**
    *   **Blink Detection (Eye Aspect Ratio - EAR):** Prevents photo/video attacks by requiring the user to blink.
    *   **Head Turn (Yaw Ratio):** Evaluates 2D perspective shifts of landmarks to confirm voluntary motion.
*   **Frame-Skipping Optimization:** Processes every 5th frame for feature recognition to keep CPU usage low and maintain high FPS.
*   **SQLite Database Logging:** Manages registered employees and logs attendance records.
*   **Webcam Fallback Mode:** Allows uploading static images or videos if a camera is unavailable.

---

## 📂 Project Structure

```text
├── data/                       # Local database & embedding storage
│   ├── embeddings/             # Enrolled user .npy embedding vectors
│   └── attendance.db           # SQLite attendance logs
├── src/
│   ├── database.py             # SQLite CRUD operations
│   ├── detector.py             # MediaPipe FaceMesh face & liveness detection
│   ├── encoder.py              # InsightFace 512-d embedding extraction
│   └── main.py                 # Streamlit UI & Orchestration loop
├── tests/
│   ├── test_database.py        # SQLite unit tests
│   └── test_detector.py        # EAR & Yaw ratio mathematical unit tests
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
└── README.md                   # Setup and execution guide
```

---

## 🛠️ Installation & Setup

### Prerequisites

1.  **Python 3.11+**
2.  **Windows C++ Build Tools:**
    *   *Why?* The `insightface` and `onnxruntime` libraries contain C extensions. On Windows, if pre-compiled wheels are missing, pip compiles them from source, requiring a compiler.
    *   *Solution:* Download and install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and select **Desktop development with C++**.

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

### 1. Launch the Streamlit Dashboard
```bash
streamlit run src/main.py
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

## 🧪 Running Automated Tests

A unit test suite validates database and mathematical logic. You do not need a camera to run these tests.

```bash
pytest tests/
```

---

## 🐳 Docker Deployment

### Build the Image
```bash
docker build -t face-attendance .
```

### Run the Container
Streamlit applications inside a container require port mapping.
```bash
docker run -p 8501:8501 face-attendance
```

> [!IMPORTANT]
> **Webcam inside Docker:** Container environments do not have automatic access to host hardware.
> *   **Linux:** Pass the device node:
>     ```bash
>     docker run -p 8501:8501 --device=/dev/video0 face-attendance
>     ```
> *   **Windows / macOS:** Docker Desktop does not natively support USB camera passthrough. If run inside a container on these platforms, use the **Fallback File Upload** in the dashboard to process images/videos.
