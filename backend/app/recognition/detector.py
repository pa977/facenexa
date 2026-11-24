"""
FaceDetector — wraps InsightFace's SCRFD detection model.

Produces structured ``FaceDetectionResult`` objects with validated
bounding boxes, confidence, and landmarks from actual model inference.
"""

from __future__ import annotations

import logging
import time
from typing import List

import numpy as np

from backend.app.recognition.errors import DetectionError
from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.recognition_config import RecognitionConfig, get_config
from backend.app.recognition.recognition_models import (
    BoundingBox,
    FaceDetectionResult,
    FaceLandmarks,
)

logger = logging.getLogger("facenexa.detector")


class FaceDetector:
    """Detect faces in a frame using the loaded InsightFace model.

    All results come from actual inference — nothing is fabricated.
    """

    def __init__(self, config: RecognitionConfig | None = None) -> None:
        self._config = config or get_config()

    def detect(self, frame: np.ndarray) -> tuple[List[FaceDetectionResult], float]:
        """Run face detection on *frame*.

        Returns:
            (detections, elapsed_ms)
        """
        manager = ModelManager.get_instance()
        if not manager.is_ready or manager.app is None:
            raise DetectionError(detail="Model not loaded.")

        if frame is None or frame.size == 0:
            raise DetectionError(detail="Empty or invalid frame.")

        img_h, img_w = frame.shape[:2]

        t0 = time.perf_counter()
        try:
            faces = manager.app.get(frame)
        except Exception as exc:
            raise DetectionError(detail=str(exc)) from exc
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        results: List[FaceDetectionResult] = []
        for idx, face in enumerate(faces):
            # ── Confidence ────────────────────────────────────────────
            det_score = float(getattr(face, "det_score", 0.0))
            if det_score < self._config.detection_confidence_threshold:
                continue

            # ── Bounding box ──────────────────────────────────────────
            raw_bbox = face.bbox.astype(int)
            try:
                bbox = BoundingBox(
                    x1=int(raw_bbox[0]),
                    y1=int(raw_bbox[1]),
                    x2=int(raw_bbox[2]),
                    y2=int(raw_bbox[3]),
                )
                bbox = bbox.clamp(img_w, img_h)
            except (ValueError, IndexError):
                logger.warning("Invalid bounding box for face %d — skipping.", idx)
                continue

            # Filter by minimum face size
            if bbox.width < self._config.minimum_face_width or bbox.height < self._config.minimum_face_height:
                continue

            # ── Landmarks ─────────────────────────────────────────────
            landmarks = None
            kps = getattr(face, "kps", None)
            if kps is None:
                kps = getattr(face, "landmark_2d_106", None)
                # Fall back to 5-point landmarks from 106-point if available
                if kps is not None and len(kps) >= 106:
                    kps = np.array([kps[38], kps[88], kps[86], kps[52], kps[61]])

            if kps is not None and len(kps) >= 5:
                try:
                    landmarks = FaceLandmarks(
                        left_eye=(float(kps[0][0]), float(kps[0][1])),
                        right_eye=(float(kps[1][0]), float(kps[1][1])),
                        nose=(float(kps[2][0]), float(kps[2][1])),
                        mouth_left=(float(kps[3][0]), float(kps[3][1])),
                        mouth_right=(float(kps[4][0]), float(kps[4][1])),
                    )
                except (IndexError, TypeError):
                    pass

            results.append(
                FaceDetectionResult(
                    face_id=idx,
                    bbox=bbox,
                    landmarks=landmarks,
                    detection_confidence=round(det_score, 4),
                )
            )

        return results, elapsed_ms
