import os
import numpy as np
import cv2
# pyrefly: ignore [missing-import]
import insightface
# pyrefly: ignore [missing-import]
from insightface.app import FaceAnalysis

class FaceEncoder:
    def __init__(self, model_name: str = "buffalo_l", base_dir: str = "data/embeddings"):
        """Initializes the InsightFace FaceAnalysis pipeline."""
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Initialize FaceAnalysis with the CPU execution provider
        self.app = FaceAnalysis(name=model_name, providers=['CPUExecutionProvider'])
        # Prepare the detector with input size 640x640
        self.app.prepare(ctx_id=0, det_size=(640, 640))

    def generate_embedding(self, frame: np.ndarray) -> np.ndarray | None:
        """
        Extracts the 512-d facial embedding from the largest face in the frame.
        InsightFace expects standard OpenCV BGR image format.
        """
        # Get face analysis predictions
        faces = self.app.get(frame)
        
        if not faces:
            return None
        
        # If multiple faces are detected, select the one with the largest bounding box area
        if len(faces) > 1:
            # bbox is [x1, y1, x2, y2]
            faces = sorted(
                faces, 
                key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), 
                reverse=True
            )
            
        largest_face = faces[0]
        
        # Try to use normed_embedding (unit length 1.0) or fall back to standard embedding
        if hasattr(largest_face, 'normed_embedding') and largest_face.normed_embedding is not None:
            return largest_face.normed_embedding
        return largest_face.embedding

    def save_embedding(self, name: str, embedding: np.ndarray) -> str:
        """Saves a user's face embedding to a local .npy file."""
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        if not safe_name:
            raise ValueError("Invalid username for embedding filename.")
            
        file_path = os.path.join(self.base_dir, f"{safe_name}.npy")
        np.save(file_path, embedding)
        return file_path

    def load_embeddings(self) -> dict:
        """Loads all face embeddings from the local disk database."""
        embeddings_dict = {}
        if not os.path.exists(self.base_dir):
            return embeddings_dict
            
        for file_name in os.listdir(self.base_dir):
            if file_name.endswith(".npy"):
                name = os.path.splitext(file_name)[0]
                file_path = os.path.join(self.base_dir, file_name)
                try:
                    embeddings_dict[name] = np.load(file_path)
                except Exception as e:
                    print(f"Error loading embedding for {name}: {e}")
                    
        return embeddings_dict

    def compare_embeddings(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Computes cosine similarity between two 512-dimensional embeddings."""
        norm_1 = np.linalg.norm(emb1)
        norm_2 = np.linalg.norm(emb2)
        if norm_1 == 0 or norm_2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm_1 * norm_2))

    def find_match(self, embedding: np.ndarray, threshold: float = 0.5) -> tuple[str, float] | tuple[None, float]:
        """
        Compares an input embedding against all registered embeddings.
        Returns (name, similarity_score) if a match exceeds the threshold.
        """
        registered = self.load_embeddings()
        if not registered:
            return None, 0.0
            
        best_match = None
        best_score = -1.0
        
        for name, reg_emb in registered.items():
            score = self.compare_embeddings(embedding, reg_emb)
            if score > best_score:
                best_score = score
                best_match = name
                
        if best_score >= threshold:
            return best_match, best_score
            
        return None, best_score

    def delete_embedding(self, name: str) -> bool:
        """Deletes a user's face embedding from local file system."""
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        file_path = os.path.join(self.base_dir, f"{safe_name}.npy")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
