"""
Unit tests for the recognition subsystem components:
- BoundingBox validation & clamping
- FaceQualityAnalyzer (blur, brightness, size, pose)
- RecognitionConfig defaults & updates
- Error classes
"""

import pytest
import numpy as np
import cv2

from backend.app.recognition.recognition_models import BoundingBox, FaceLandmarks, FaceQualityResult
from backend.app.recognition.recognition_config import RecognitionConfig, get_config, set_config
from backend.app.recognition.face_quality import FaceQualityAnalyzer
from backend.app.recognition.errors import ModelLoadError, DetectionError, EmbeddingError, QualityError


def test_bounding_box_valid():
    bbox = BoundingBox(x1=10, y1=20, x2=100, y2=200)
    assert bbox.width == 90
    assert bbox.height == 180


def test_bounding_box_invalid_order():
    with pytest.raises(ValueError):
        BoundingBox(x1=100, y1=20, x2=10, y2=200)

    with pytest.raises(ValueError):
        BoundingBox(x1=10, y1=200, x2=100, y2=20)


def test_bounding_box_clamping():
    bbox = BoundingBox(x1=0, y1=0, x2=200, y2=300)
    clamped = bbox.clamp(img_width=150, img_height=250)
    assert clamped.x2 == 150
    assert clamped.y2 == 250


def test_config_defaults():
    config = RecognitionConfig()
    assert config.detection_confidence_threshold == 0.5
    assert config.minimum_face_width == 60
    assert config.minimum_face_height == 60
    assert config.blur_threshold == 80.0
    assert config.device == "cpu"


def test_quality_analyzer_sharp_image():
    analyzer = FaceQualityAnalyzer()

    # Generate a sharp image with high variance gradient
    sharp_img = np.zeros((100, 100, 3), dtype=np.uint8)
    sharp_img[:, :50] = 255
    sharp_img[:, 50:] = 0

    bbox = BoundingBox(x1=0, y1=0, x2=100, y2=100)
    result = analyzer.analyze(sharp_img, bbox, landmarks=None, detection_confidence=0.95)

    assert isinstance(result, FaceQualityResult)
    assert result.blur == "good"
    assert result.blur_score > 80.0
    assert result.overall_score > 0.5
    assert result.usable is True


def test_quality_analyzer_blurry_image():
    analyzer = FaceQualityAnalyzer()

    # Smooth constant grey image (0 Laplacian variance)
    blurry_img = np.full((100, 100, 3), 128, dtype=np.uint8)
    bbox = BoundingBox(x1=0, y1=0, x2=100, y2=100)
    result = analyzer.analyze(blurry_img, bbox, landmarks=None, detection_confidence=0.9)

    assert result.blur == "poor"
    assert result.blur_score < 1.0


def test_quality_analyzer_dark_image():
    analyzer = FaceQualityAnalyzer()
    dark_img = np.full((100, 100, 3), 10, dtype=np.uint8)
    bbox = BoundingBox(x1=0, y1=0, x2=100, y2=100)
    result = analyzer.analyze(dark_img, bbox, landmarks=None, detection_confidence=0.9)

    assert result.brightness == "too_dark"
    assert "Too dark" in result.feedback


def test_quality_analyzer_too_small_face():
    analyzer = FaceQualityAnalyzer()
    img = np.full((30, 30, 3), 128, dtype=np.uint8)
    bbox = BoundingBox(x1=0, y1=0, x2=30, y2=30)
    result = analyzer.analyze(img, bbox, landmarks=None, detection_confidence=0.9)

    assert result.face_size == "too_small"
    assert "Move closer" in result.feedback


def test_custom_errors():
    err = ModelLoadError(model_name="test_model", detail="file missing")
    assert "test_model" in str(err)
    assert err.detail == "file missing"

    det_err = DetectionError(detail="Corrupt frame")
    assert "Face detection failed" in str(det_err)
