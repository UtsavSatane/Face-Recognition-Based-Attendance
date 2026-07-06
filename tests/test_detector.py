import pytest
from src.detector import FaceDetector

class MockLandmark:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

class MockLandmarksList:
    def __init__(self, landmarks_dict: dict):
        self.landmark = [MockLandmark(0.0, 0.0, 0.0)] * 478
        for idx, coords in landmarks_dict.items():
            self.landmark[idx] = MockLandmark(*coords)

@pytest.fixture
def detector():
    # Pass dummy values as we won't call the underlying MediaPipe process in these unit tests
    return FaceDetector()

def test_calculate_ear_open_eyes(detector):
    """Tests EAR calculation when eyes are wide open."""
    landmarks_data = {
        # Left Eye (Horizontal: 33, 133; Vertical 1: 160, 144; Vertical 2: 158, 153)
        33: (1.0, 2.0, 0.0),
        133: (3.0, 2.0, 0.0), # Horizontal width = 2.0
        160: (2.0, 2.3, 0.0),
        144: (2.0, 1.7, 0.0), # Vertical 1 = 0.6
        158: (2.0, 2.3, 0.0),
        153: (2.0, 1.7, 0.0), # Vertical 2 = 0.6
        
        # Right Eye (Horizontal: 362, 263; Vertical 1: 385, 380; Vertical 2: 387, 373)
        362: (10.0, 2.0, 0.0),
        263: (12.0, 2.0, 0.0), # Horizontal width = 2.0
        385: (11.0, 2.3, 0.0),
        380: (11.0, 1.7, 0.0), # Vertical 1 = 0.6
        387: (11.0, 2.3, 0.0),
        373: (11.0, 1.7, 0.0), # Vertical 2 = 0.6
    }
    
    mock_landmarks = MockLandmarksList(landmarks_data)
    ear = detector.calculate_ear(mock_landmarks)
    
    # Left eye: (0.6 + 0.6) / (2 * 2) = 1.2 / 4 = 0.3
    # Right eye: (0.6 + 0.6) / (2 * 2) = 1.2 / 4 = 0.3
    # Average: 0.3
    assert pytest.approx(ear, abs=1e-4) == 0.30

def test_calculate_ear_closed_eyes(detector):
    """Tests EAR calculation when eyelids are closed."""
    landmarks_data = {
        # Left Eye (Eyelids closed -> very small vertical distance)
        33: (1.0, 2.0, 0.0),
        133: (3.0, 2.0, 0.0),
        160: (2.0, 2.05, 0.0),
        144: (2.0, 1.95, 0.0), # Vertical 1 = 0.1
        158: (2.0, 2.05, 0.0),
        153: (2.0, 1.95, 0.0), # Vertical 2 = 0.1
        
        # Right Eye
        362: (10.0, 2.0, 0.0),
        263: (12.0, 2.0, 0.0),
        385: (11.0, 2.05, 0.0),
        380: (11.0, 1.95, 0.0), # Vertical 1 = 0.1
        387: (11.0, 2.05, 0.0),
        373: (11.0, 1.95, 0.0), # Vertical 2 = 0.1
    }
    
    mock_landmarks = MockLandmarksList(landmarks_data)
    ear = detector.calculate_ear(mock_landmarks)
    
    # Left eye: (0.1 + 0.1) / (2 * 2) = 0.2 / 4 = 0.05
    # Right eye: 0.05
    # Average: 0.05
    assert pytest.approx(ear, abs=1e-4) == 0.05

def test_calculate_yaw_ratio_center(detector):
    """Tests head turn ratio when face is looking straight at the camera."""
    landmarks_data = {
        4: (2.0, 2.0, 0.0),    # Nose tip at x=2.0
        33: (1.0, 2.0, 0.0),   # Left outer eye corner at x=1.0 (distance = 1.0)
        263: (3.0, 2.0, 0.0),  # Right outer eye corner at x=3.0 (distance = 1.0)
    }
    
    mock_landmarks = MockLandmarksList(landmarks_data)
    ratio = detector.calculate_yaw_ratio(mock_landmarks)
    
    # Ratio = 1.0 / 1.0 = 1.0
    assert pytest.approx(ratio, abs=1e-4) == 1.0

def test_calculate_yaw_ratio_turned_right(detector):
    """Tests head turn ratio when turned right (nose tip closer to right corner)."""
    landmarks_data = {
        4: (2.8, 2.0, 0.0),    # Nose tip shifted right to x=2.8
        33: (1.0, 2.0, 0.0),   # Left outer corner (distance = 1.8)
        263: (3.0, 2.0, 0.0),  # Right outer corner (distance = 0.2)
    }
    
    mock_landmarks = MockLandmarksList(landmarks_data)
    ratio = detector.calculate_yaw_ratio(mock_landmarks)
    
    # Ratio = 1.8 / 0.2 = 9.0
    assert pytest.approx(ratio, abs=1e-4) == 9.0

def test_calculate_yaw_ratio_turned_left(detector):
    """Tests head turn ratio when turned left (nose tip closer to left corner)."""
    landmarks_data = {
        4: (1.2, 2.0, 0.0),    # Nose tip shifted left to x=1.2
        33: (1.0, 2.0, 0.0),   # Left outer corner (distance = 0.2)
        263: (3.0, 2.0, 0.0),  # Right outer corner (distance = 1.8)
    }
    
    mock_landmarks = MockLandmarksList(landmarks_data)
    ratio = detector.calculate_yaw_ratio(mock_landmarks)
    
    # Ratio = 0.2 / 1.8 = 0.1111
    assert pytest.approx(ratio, abs=1e-4) == 0.1111
