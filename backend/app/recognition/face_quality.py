"""
FaceQualityAnalyzer — evaluates whether a detected face is suitable for recognition.

Checks:
    • Face size (bounding-box dimensions)
    • Blur (Laplacian variance)
    • Brightness (mean pixel intensity of face region)
    • Pose (approximate yaw/pitch from eye-nose geometry)
    • Detection confidence (passed through)

All thresholds are configurable via ``RecognitionConfig``.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import cv2
import numpy as np

from backend.app.recognition.recognition_config import RecognitionConfig, get_config
from backend.app.recognition.recognition_models import (
    BoundingBox,
    FaceLandmarks,
    FaceQualityResult,
)

logger = logging.getLogger("facenexa.quality")


class FaceQualityAnalyzer:
    """Produce a ``FaceQualityResult`` for a detected face region."""

    def __init__(self, config: RecognitionConfig | None = None) -> None:
        self._config = config or get_config()

    # ── Public API ────────────────────────────────────────────────────

    def analyze(
        self,
        face_crop: np.ndarray,
        bbox: BoundingBox,
        landmarks: Optional[FaceLandmarks],
        detection_confidence: float,
    ) -> FaceQualityResult:
        """Run all quality checks and return a structured result."""
        cfg = self._config

        # Component scores (0..1)
        size_score, size_label = self._check_size(bbox)
        blur_score_raw, blur_score_norm, blur_label = self._check_blur(face_crop)
        brightness_val, brightness_score, brightness_label = self._check_brightness(face_crop)
        pose_score, pose_label = self._check_pose(landmarks)
        conf_score = min(1.0, max(0.0, detection_confidence))

        # Weighted overall score
        overall = (
            cfg.weight_face_size * size_score
            + cfg.weight_blur * blur_score_norm
            + cfg.weight_brightness * brightness_score
            + cfg.weight_pose * pose_score
            + cfg.weight_detection_conf * conf_score
        )
        overall = round(min(1.0, max(0.0, overall)), 4)

        usable = overall >= cfg.quality_threshold

        # Build human-readable feedback
        feedback = self._build_feedback(size_label, blur_label, brightness_label, pose_label)

        return FaceQualityResult(
            overall_score=overall,
            face_size=size_label,
            blur=blur_label,
            blur_score=round(blur_score_raw, 2),
            brightness=brightness_label,
            brightness_value=round(brightness_val, 2),
            pose=pose_label,
            usable=usable,
            feedback=feedback,
        )

    # ── Component checks ──────────────────────────────────────────────

    def _check_size(self, bbox: BoundingBox) -> tuple[float, str]:
        """Return (score, label) for face size."""
        cfg = self._config
        w, h = bbox.width, bbox.height
        if w >= cfg.minimum_face_width and h >= cfg.minimum_face_height:
            return 1.0, "good"
        # Ramp between 50% of minimum and minimum
        ratio_w = w / cfg.minimum_face_width if cfg.minimum_face_width > 0 else 1.0
        ratio_h = h / cfg.minimum_face_height if cfg.minimum_face_height > 0 else 1.0
        ratio = min(ratio_w, ratio_h)
        if ratio <= 0.5:
            return 0.0, "too_small"
        return round(ratio, 4), "small"

    def _check_blur(self, crop: np.ndarray) -> tuple[float, float, str]:
        """Return (raw_laplacian_var, normalised_score, label)."""
        if crop is None or crop.size == 0:
            return 0.0, 0.0, "poor"
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        threshold = self._config.blur_threshold
        if lap_var >= threshold:
            return lap_var, 1.0, "good"
        score = lap_var / threshold if threshold > 0 else 0.0
        return lap_var, round(score, 4), "poor"

    def _check_brightness(self, crop: np.ndarray) -> tuple[float, float, str]:
        """Return (mean_intensity, normalised_score, label)."""
        if crop is None or crop.size == 0:
            return 0.0, 0.0, "too_dark"
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        mean_val = float(np.mean(gray))
        b_min = self._config.brightness_min
        b_max = self._config.brightness_max

        if b_min <= mean_val <= b_max:
            return mean_val, 1.0, "good"
        if mean_val < b_min:
            score = mean_val / b_min if b_min > 0 else 0.0
            return mean_val, round(max(0.0, score), 4), "too_dark"
        # mean_val > b_max
        overshoot = mean_val - b_max
        headroom = 255.0 - b_max
        score = 1.0 - (overshoot / headroom) if headroom > 0 else 0.0
        return mean_val, round(max(0.0, score), 4), "too_bright"

    def _check_pose(self, landmarks: Optional[FaceLandmarks]) -> tuple[float, str]:
        """Approximate yaw/pitch from 5-point landmarks.

        This is a rough heuristic, not a calibrated head-pose estimator.
        It is intentionally lenient so that slightly turned faces still pass.
        """
        if landmarks is None:
            # No landmarks → we cannot check → assume acceptable
            return 0.7, "acceptable"

        le = np.array(landmarks.left_eye)
        re = np.array(landmarks.right_eye)
        nose = np.array(landmarks.nose)

        # ── Yaw estimate ──────────────────────────────────────────────
        eye_center = (le + re) / 2.0
        eye_dist = float(np.linalg.norm(re - le))
        if eye_dist < 1.0:
            return 0.5, "acceptable"

        nose_offset_x = nose[0] - eye_center[0]
        # ratio: 0 = centred, ±0.5 = far left/right
        yaw_ratio = abs(nose_offset_x) / eye_dist

        # ── Pitch estimate ────────────────────────────────────────────
        nose_offset_y = nose[1] - eye_center[1]
        pitch_ratio = abs(nose_offset_y) / eye_dist

        # Convert to approximate degrees (rough calibration)
        yaw_deg = yaw_ratio * 90.0
        pitch_deg = pitch_ratio * 90.0

        yaw_ok = yaw_deg < self._config.pose_yaw_threshold
        pitch_ok = pitch_deg < self._config.pose_pitch_threshold

        if yaw_ok and pitch_ok:
            # score inversely proportional to angle
            score = 1.0 - 0.5 * max(yaw_deg, pitch_deg) / max(
                self._config.pose_yaw_threshold, self._config.pose_pitch_threshold
            )
            return round(max(0.0, score), 4), "good"

        if yaw_deg < self._config.pose_yaw_threshold * 1.3 and pitch_deg < self._config.pose_pitch_threshold * 1.3:
            return 0.5, "acceptable"

        return 0.1, "poor"

    # ── Feedback ──────────────────────────────────────────────────────

    @staticmethod
    def _build_feedback(size: str, blur: str, brightness: str, pose: str) -> str:
        """Build a single concise feedback string from component labels."""
        parts: list[str] = []
        if size == "too_small":
            parts.append("Move closer")
        elif size == "small":
            parts.append("Face too small")
        if blur == "poor":
            parts.append("Face too blurry")
        if brightness == "too_dark":
            parts.append("Too dark")
        elif brightness == "too_bright":
            parts.append("Too bright")
        if pose == "poor":
            parts.append("Turn toward camera")
        if not parts:
            return ""
        return " · ".join(parts)
