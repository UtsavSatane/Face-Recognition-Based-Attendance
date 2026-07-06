import os
import shutil
import pytest
import numpy as np
from src.encoder import FaceEncoder

TEST_EMB_DIR = "data/test_embeddings"

@pytest.fixture
def encoder():
    """Sets up a FaceEncoder pointing to a test embedding directory."""
    # We bypass model initialization by mocking the prepare and get functions of FaceAnalysis
    # if we want to run unit tests without loading the model.
    enc = FaceEncoder(model_name="buffalo_l", base_dir=TEST_EMB_DIR)
    
    yield enc
    
    # Teardown: remove test directory
    if os.path.exists(TEST_EMB_DIR):
        shutil.rmtree(TEST_EMB_DIR)

def test_compare_embeddings(encoder):
    """Tests the cosine similarity calculations."""
    # Perfect match (identical vectors)
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([1.0, 0.0, 0.0])
    assert pytest.approx(encoder.compare_embeddings(v1, v2), abs=1e-4) == 1.0
    
    # Orthogonal vectors (similarity = 0)
    v3 = np.array([0.0, 1.0, 0.0])
    assert pytest.approx(encoder.compare_embeddings(v1, v3), abs=1e-4) == 0.0
    
    # Opposite vectors (similarity = -1)
    v4 = np.array([-1.0, 0.0, 0.0])
    assert pytest.approx(encoder.compare_embeddings(v1, v4), abs=1e-4) == -1.0

def test_save_and_load_embeddings(encoder):
    """Tests saving numpy arrays to disk and reloading them."""
    emb = np.random.rand(512)
    name = "John Doe"
    
    # Save
    path = encoder.save_embedding(name, emb)
    assert os.path.exists(path)
    assert path.endswith("John_Doe.npy") or path.endswith("John Doe.npy")
    
    # Load
    loaded = encoder.load_embeddings()
    assert name in loaded
    assert np.allclose(loaded[name], emb)

def test_find_match(encoder):
    """Tests finding matches within enrolled profiles using similarity scores."""
    # Enroll a user
    emb_john = np.array([1.0, 0.0, 0.0, 0.0])
    encoder.save_embedding("John", emb_john)
    
    # Input vector close to John (dot product = 0.95)
    input_emb = np.array([0.95, 0.3122, 0.0, 0.0]) # Norm = 1.0
    
    # Under high threshold (e.g. 0.98), should not match
    match, score = encoder.find_match(input_emb, threshold=0.98)
    assert match is None
    assert pytest.approx(score, abs=1e-2) == 0.95
    
    # Under standard threshold (e.g. 0.5), should match John
    match, score = encoder.find_match(input_emb, threshold=0.5)
    assert match == "John"
    assert pytest.approx(score, abs=1e-2) == 0.95

def test_delete_embedding(encoder):
    """Tests deleting a user's local embedding profile."""
    emb = np.random.rand(512)
    name = "Jane Smith"
    
    encoder.save_embedding(name, emb)
    assert name in encoder.load_embeddings()
    
    deleted = encoder.delete_embedding(name)
    assert deleted is True
    assert name not in encoder.load_embeddings()
    
    # Try deleting again
    deleted_again = encoder.delete_embedding(name)
    assert deleted_again is False
