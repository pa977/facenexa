"""
FaceNexa Recognition Subsystem — Phase 3

AI face-processing pipeline:
  Camera Frame → Detection → Quality → Alignment → Embedding

Uses InsightFace (SCRFD + ArcFace) with ONNX Runtime.
Runs entirely on CPU; optional GPU acceleration when available.
"""

from backend.app.recognition.recognition_config import RecognitionConfig
from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.detector import FaceDetector
from backend.app.recognition.face_quality import FaceQualityAnalyzer
from backend.app.recognition.alignment import FaceAligner
from backend.app.recognition.embedding import EmbeddingGenerator
from backend.app.recognition.frame_processor import FaceProcessingService
from backend.app.recognition.recognition_models import (
    BoundingBox,
    FaceLandmarks,
    FaceQualityResult,
    FaceDetectionResult,
    AIProcessingMetrics,
    ModelStatus,
    AISystemStatus,
)

__all__ = [
    "RecognitionConfig",
    "ModelManager",
    "FaceDetector",
    "FaceQualityAnalyzer",
    "FaceAligner",
    "EmbeddingGenerator",
    "FaceProcessingService",
    "BoundingBox",
    "FaceLandmarks",
    "FaceQualityResult",
    "FaceDetectionResult",
    "AIProcessingMetrics",
    "ModelStatus",
    "AISystemStatus",
]
