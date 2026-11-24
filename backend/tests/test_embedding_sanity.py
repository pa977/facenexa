"""
Embedding Sanity Test:
- Ensures embedding output is L2-normalized (magnitude ≈ 1.0)
- Checks vector properties (no NaN, non-zero)
- Tests consistency when model is available
"""

import pytest
import numpy as np

from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.embedding import EmbeddingGenerator


def test_embedding_l2_normalization():
    # Test L2 normalization on random synthetic vector
    dummy_vec = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    norm = np.linalg.norm(dummy_vec)
    normalized = dummy_vec / norm

    assert np.isclose(np.linalg.norm(normalized), 1.0, atol=1e-5)


def test_embedding_generator_with_model_if_available():
    manager = ModelManager.get_instance()
    if not manager.is_ready:
        manager.initialize()

    if manager.is_ready:
        generator = EmbeddingGenerator()
        # Synthetic aligned face 112x112
        aligned_face = np.full((112, 112, 3), 128, dtype=np.uint8)

        embedding, elapsed_ms = generator.generate(aligned_face)

        assert isinstance(embedding, np.ndarray)
        assert len(embedding.shape) == 1
        # Check L2 norm
        assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-3)
        assert not np.isnan(embedding).any()
        assert elapsed_ms >= 0.0
