import cv2
import numpy as np
import mediapipe as mp
import math

class FaceDetector:
    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        """Initializes the MediaPipe Face Mesh detector."""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Landmark indices for Left Eye EAR
        self.LEFT_EYE_INDICES = {
            'horizontal': (33, 133),
            'vertical_1': (160, 144),
            'vertical_2': (158, 153)
        }
        # Landmark indices for Right Eye EAR
        self.RIGHT_EYE_INDICES = {
            'horizontal': (362, 263),
            'vertical_1': (385, 380),
            'vertical_2': (387, 373)
        }
        
        # Cache for frame-skipping
        self.last_results = None

    def _get_distance_3d(self, p1, p2) -> float:
        """Calculates the Euclidean distance between two 3D landmarks."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def calculate_ear(self, landmarks) -> float:
        """Calculates the average Eye Aspect Ratio (EAR) for both eyes."""
        # Left Eye EAR
        left_h = self._get_distance_3d(landmarks.landmark[self.LEFT_EYE_INDICES['horizontal'][0]], 
                                        landmarks.landmark[self.LEFT_EYE_INDICES['horizontal'][1]])
        left_v1 = self._get_distance_3d(landmarks.landmark[self.LEFT_EYE_INDICES['vertical_1'][0]], 
                                         landmarks.landmark[self.LEFT_EYE_INDICES['vertical_1'][1]])
        left_v2 = self._get_distance_3d(landmarks.landmark[self.LEFT_EYE_INDICES['vertical_2'][0]], 
                                         landmarks.landmark[self.LEFT_EYE_INDICES['vertical_2'][1]])
        
        left_ear = (left_v1 + left_v2) / (2.0 * left_h) if left_h > 0 else 0.0

        # Right Eye EAR
        right_h = self._get_distance_3d(landmarks.landmark[self.RIGHT_EYE_INDICES['horizontal'][0]], 
                                         landmarks.landmark[self.RIGHT_EYE_INDICES['horizontal'][1]])
        right_v1 = self._get_distance_3d(landmarks.landmark[self.RIGHT_EYE_INDICES['vertical_1'][0]], 
                                          landmarks.landmark[self.RIGHT_EYE_INDICES['vertical_1'][1]])
        right_v2 = self._get_distance_3d(landmarks.landmark[self.RIGHT_EYE_INDICES['vertical_2'][0]], 
                                          landmarks.landmark[self.RIGHT_EYE_INDICES['vertical_2'][1]])
        
        right_ear = (right_v1 + right_v2) / (2.0 * right_h) if right_h > 0 else 0.0

        return (left_ear + right_ear) / 2.0

    def calculate_yaw_ratio(self, landmarks) -> float:
        """
        Calculates the ratio of nose-to-left-eye distance to nose-to-right-eye distance.
        This provides a lightweight estimate of horizontal head turn (yaw).
        """
        nose = landmarks.landmark[4]
        left_eye = landmarks.landmark[33]
        right_eye = landmarks.landmark[263]

        # Horizontal 2D distance projection
        dist_left = abs(nose.x - left_eye.x)
        dist_right = abs(nose.x - right_eye.x)

        if dist_right == 0:
            return 1.0  # Fallback to center-like ratio if right distance is 0

        return dist_left / dist_right

    def process_frame(self, frame: np.ndarray, frame_count: int, force_process: bool = False) -> dict | None:
        """
        Processes a frame and returns face metadata.
        Uses cached results on skipped frames to maintain visual continuity.
        """
        # If we skip the frame and have a cached result, return the cache
        if not force_process and frame_count % 5 != 0 and self.last_results is not None:
            return self.last_results

        # Process frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            self.last_results = None
            return None

        # Extract landmarks of the first detected face
        landmarks = results.multi_face_landmarks[0]
        h, w, _ = frame.shape

        # Calculate bounding box
        x_coords = [lm.x for lm in landmarks.landmark]
        y_coords = [lm.y for lm in landmarks.landmark]
        
        xmin, xmax = int(min(x_coords) * w), int(max(x_coords) * w)
        ymin, ymax = int(min(y_coords) * h), int(max(y_coords) * h)
        
        # Add padding to bounding box
        pad_x = int((xmax - xmin) * 0.1)
        pad_y = int((ymax - ymin) * 0.1)
        
        xmin = max(0, xmin - pad_x)
        ymin = max(0, ymin - pad_y)
        xmax = min(w, xmax + pad_x)
        ymax = min(h, ymax + pad_y)

        ear = self.calculate_ear(landmarks)
        yaw_ratio = self.calculate_yaw_ratio(landmarks)

        # Assemble result dictionary
        self.last_results = {
            'bbox': (xmin, ymin, xmax - xmin, ymax - ymin),  # x, y, w, h
            'ear': ear,
            'yaw_ratio': yaw_ratio,
            'landmarks': landmarks
        }
        return self.last_results

    def close(self):
        """Releases the Face Mesh resources."""
        self.face_mesh.close()
