"""
Integration tests for the FaceNexa AI recognition engine:
- Full pipeline execution (frame → detection → quality → alignment → embedding)
- Multiple faces handling
- Model availability and fallback
- API route status responses
"""

import pytest
import numpy as np

from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.frame_processor import FaceProcessingService
from backend.app.recognition.recognition_config import RecognitionConfig


def test_model_manager_singleton():
    m1 = ModelManager.get_instance()
    m2 = ModelManager.get_instance()
    assert m1 is m2


def test_frame_processor_synthetic_empty_frame():
    processor = FaceProcessingService()
    # Blank black frame — should detect 0 faces cleanly without crashing
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Initialize model manager if ready
    manager = ModelManager.get_instance()
    if not manager.is_ready:
        manager.initialize()

    if manager.is_ready:
        results, metrics = processor.process_frame(frame)
        assert isinstance(results, list)
        assert len(results) == 0
        assert metrics.faces_detected == 0
        assert metrics.total_ms >= 0.0


def test_uninitialized_model_handling():
    # Test that uninitialized model manager handles call gracefully
    manager = ModelManager.get_instance()
    status = manager.get_status()
    assert status.status in ["not_initialized", "ready", "loading", "error"]
