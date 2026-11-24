"""
FaceProcessingService — orchestrates the full AI pipeline for a single frame.

    Frame → Detection → Quality → Alignment → Embedding → Results

Measures timing for every stage and produces structured results.
Raw embeddings are stored internally but never exposed to the frontend.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.app.recognition.alignment import FaceAligner
from backend.app.recognition.detector import FaceDetector
from backend.app.recognition.embedding import EmbeddingGenerator
from backend.app.recognition.errors import (
    AlignmentError,
    DetectionError,
    EmbeddingError,
    QualityError,
)
from backend.app.recognition.face_quality import FaceQualityAnalyzer
from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.recognition_config import RecognitionConfig, get_config
from backend.app.recognition.recognition_models import (
    AIProcessingMetrics,
    FaceDetectionResult,
)

logger = logging.getLogger("facenexa.frame_processor")


class FaceProcessingService:
    """Process a single camera frame through the full pipeline.

    Results include per-face detections (frontend-safe) and processing
    metrics.  Embeddings are kept in ``_latest_embeddings`` for Phase 4
    but never sent to the frontend.
    """

    def __init__(self, config: RecognitionConfig | None = None) -> None:
        self._config = config or get_config()
        self._detector = FaceDetector(self._config)
        self._quality = FaceQualityAnalyzer(self._config)
        self._aligner = FaceAligner()
        self._embedding_gen = EmbeddingGenerator()

        # Last embeddings produced (face_id → np.ndarray).
        # Available for Phase 4 identity matching.
        self._latest_embeddings: Dict[int, np.ndarray] = {}

    @property
    def latest_embeddings(self) -> Dict[int, np.ndarray]:
        """Embeddings from the most recent ``process_frame`` call.

        Keyed by ``face_id``.  This is backend-only — never serialize to frontend.
        """
        return self._latest_embeddings

    def process_frame(
        self, frame: np.ndarray
    ) -> Tuple[List[FaceDetectionResult], AIProcessingMetrics]:
        """Run the full pipeline.

        Returns:
            (face_results, metrics)
        """
        t_total_start = time.perf_counter()
        self._latest_embeddings = {}

        img_h, img_w = frame.shape[:2]

        # ── 1. Detection ──────────────────────────────────────────────
        try:
            detections, det_ms = self._detector.detect(frame)
        except DetectionError as exc:
            logger.warning("Detection failed: %s", exc.detail)
            return [], AIProcessingMetrics(
                total_ms=(time.perf_counter() - t_total_start) * 1000.0
            )

        # ── 2. Quality + 3. Alignment + 4. Embedding ─────────────────
        quality_ms_total = 0.0
        align_ms_total = 0.0
        embed_ms_total = 0.0

        for det in detections:
            face_start = time.perf_counter()

            # Crop face region for quality analysis
            bbox = det.bbox.clamp(img_w, img_h)
            face_crop = frame[bbox.y1 : bbox.y2, bbox.x1 : bbox.x2]

            if face_crop.size == 0:
                continue

            # ── Quality ───────────────────────────────────────────────
            t_q = time.perf_counter()
            try:
                quality = self._quality.analyze(
                    face_crop, bbox, det.landmarks, det.detection_confidence
                )
                det.quality = quality
            except Exception as exc:
                logger.warning("Quality analysis failed for face %d: %s", det.face_id, exc)
            quality_ms_total += (time.perf_counter() - t_q) * 1000.0

            # Skip alignment + embedding if quality is too low
            if det.quality is not None and not det.quality.usable:
                continue

            # ── Alignment ─────────────────────────────────────────────
            t_a = time.perf_counter()
            try:
                aligned, _ = self._aligner.align(frame, bbox, det.landmarks)
            except Exception as exc:
                logger.warning("Alignment failed for face %d: %s", det.face_id, exc)
                continue
            align_ms_total += (time.perf_counter() - t_a) * 1000.0

            # ── Embedding ─────────────────────────────────────────────
            t_e = time.perf_counter()
            try:
                embedding, _ = self._embedding_gen.generate(aligned)
                det.embedding_available = True
                self._latest_embeddings[det.face_id] = embedding
            except EmbeddingError as exc:
                logger.warning("Embedding failed for face %d: %s", det.face_id, exc.detail)
            embed_ms_total += (time.perf_counter() - t_e) * 1000.0

            det.processing_time_ms = round((time.perf_counter() - face_start) * 1000.0, 2)

        total_ms = (time.perf_counter() - t_total_start) * 1000.0
        ai_fps = 1000.0 / total_ms if total_ms > 0 else 0.0

        metrics = AIProcessingMetrics(
            detection_ms=round(det_ms, 2),
            quality_ms=round(quality_ms_total, 2),
            alignment_ms=round(align_ms_total, 2),
            embedding_ms=round(embed_ms_total, 2),
            total_ms=round(total_ms, 2),
            ai_fps=round(ai_fps, 2),
            faces_detected=len(detections),
        )

        return detections, metrics
