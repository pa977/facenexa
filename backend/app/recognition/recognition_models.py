"""
Pydantic data models for the recognition subsystem.

These models carry structured results through the pipeline and across
the API boundary.  Raw embeddings are intentionally excluded from
frontend-facing models.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator


# ── Bounding Box ──────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    """Axis-aligned bounding box in pixel coordinates.

    Invariants:
        x1 < x2,  y1 < y2
        All values >= 0
    """

    x1: int = Field(..., ge=0)
    y1: int = Field(..., ge=0)
    x2: int = Field(..., ge=0)
    y2: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _validate_order(self) -> "BoundingBox":
        if self.x1 >= self.x2:
            raise ValueError(f"x1 ({self.x1}) must be < x2 ({self.x2})")
        if self.y1 >= self.y2:
            raise ValueError(f"y1 ({self.y1}) must be < y2 ({self.y2})")
        return self

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def clamp(self, img_width: int, img_height: int) -> "BoundingBox":
        """Return a new BoundingBox clamped to image dimensions."""
        return BoundingBox(
            x1=max(0, min(self.x1, img_width - 1)),
            y1=max(0, min(self.y1, img_height - 1)),
            x2=max(1, min(self.x2, img_width)),
            y2=max(1, min(self.y2, img_height)),
        )


# ── Landmarks ─────────────────────────────────────────────────────────

class FaceLandmarks(BaseModel):
    """Five-point facial landmarks returned by SCRFD.

    Each value is a (x, y) coordinate pair in pixel space.
    """

    left_eye: Tuple[float, float]
    right_eye: Tuple[float, float]
    nose: Tuple[float, float]
    mouth_left: Tuple[float, float]
    mouth_right: Tuple[float, float]


# ── Quality ───────────────────────────────────────────────────────────

class FaceQualityResult(BaseModel):
    """Quality assessment for a single detected face.

    Scoring algorithm:
        overall_score = weighted sum of component scores  (range 0..1)
            face_size   → 1.0 if above min size, ramp down to 0
            blur        → 1.0 if Laplacian var >= threshold, else var/threshold
            brightness  → 1.0 if in [min, max] range, else linear falloff
            pose        → 1.0 if angles < threshold, else linear falloff
            det_conf    → raw detection confidence (already 0..1)
    """

    overall_score: float = Field(..., ge=0.0, le=1.0)
    face_size: str = Field(..., description="'good', 'small', 'too_small'")
    blur: str = Field(..., description="'good', 'poor'")
    blur_score: float = Field(..., ge=0.0, description="Laplacian variance")
    brightness: str = Field(..., description="'good', 'too_dark', 'too_bright'")
    brightness_value: float = Field(..., ge=0.0, description="Mean intensity")
    pose: str = Field(..., description="'good', 'acceptable', 'poor'")
    usable: bool = Field(..., description="True if overall_score >= quality_threshold")
    feedback: str = Field(
        default="",
        description="Human-readable suggestion (e.g. 'Move closer').",
    )


# ── Detection Result (frontend-safe) ─────────────────────────────────

class FaceDetectionResult(BaseModel):
    """Result for a single face, safe to send to the frontend.

    Raw embeddings are deliberately excluded.
    """

    face_id: int
    bbox: BoundingBox
    landmarks: Optional[FaceLandmarks] = None
    detection_confidence: float = Field(..., ge=0.0, le=1.0)
    quality: Optional[FaceQualityResult] = None
    embedding_available: bool = False
    processing_time_ms: float = 0.0


# ── Processing Metrics ────────────────────────────────────────────────

class AIProcessingMetrics(BaseModel):
    """Timing breakdown for a single frame processing cycle."""

    detection_ms: float = 0.0
    quality_ms: float = 0.0
    alignment_ms: float = 0.0
    embedding_ms: float = 0.0
    total_ms: float = 0.0
    ai_fps: float = 0.0
    faces_detected: int = 0


# ── Model Status ──────────────────────────────────────────────────────

class ModelStatus(BaseModel):
    """Status of a single AI model."""

    name: str
    loaded: bool = False
    version: str = ""
    error_message: str = ""


class AISystemStatus(BaseModel):
    """Aggregate status of the AI subsystem."""

    detection_model: ModelStatus
    recognition_model: ModelStatus
    inference_device: str = "cpu"
    status: str = "not_initialized"  # not_initialized | loading | ready | error
    processing_active: bool = False
