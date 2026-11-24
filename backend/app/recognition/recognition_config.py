"""
AI configuration for the FaceNexa recognition subsystem.

All thresholds are configurable.  Values here are sensible defaults
tuned for a classroom attendance scenario on commodity hardware.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def _default_model_dir() -> str:
    """Return a project-relative model directory (FaceNexa/models/insightface)."""
    # Walk up from this file to find the project root
    # backend/app/recognition/recognition_config.py  →  project root is 3 levels up
    project_root = Path(__file__).resolve().parents[3]
    return str(project_root / "models" / "insightface")


class RecognitionConfig(BaseModel):
    """Central configuration for the AI pipeline.

    Attributes are grouped by subsystem and documented with their units
    so that callers know what they are adjusting.
    """

    # ── Model paths ───────────────────────────────────────────────────
    model_name: str = Field(
        default="buffalo_l",
        description="InsightFace model pack name (e.g. buffalo_l, buffalo_sc).",
    )
    model_dir: str = Field(
        default_factory=_default_model_dir,
        description="Directory where InsightFace model packs are stored.",
    )

    # ── Detection ─────────────────────────────────────────────────────
    detection_confidence_threshold: float = Field(
        default=0.5,
        ge=0.1,
        le=1.0,
        description="Minimum detection confidence to consider a face valid.",
    )
    minimum_face_width: int = Field(
        default=60,
        ge=10,
        description="Minimum face bounding-box width (pixels).",
    )
    minimum_face_height: int = Field(
        default=60,
        ge=10,
        description="Minimum face bounding-box height (pixels).",
    )

    # ── Quality – Blur ────────────────────────────────────────────────
    blur_threshold: float = Field(
        default=80.0,
        ge=0.0,
        description="Laplacian-variance below this value is considered blurry.",
    )

    # ── Quality – Brightness ──────────────────────────────────────────
    brightness_min: float = Field(
        default=40.0,
        ge=0.0,
        le=255.0,
        description="Mean pixel intensity below this is 'too dark'.",
    )
    brightness_max: float = Field(
        default=220.0,
        ge=0.0,
        le=255.0,
        description="Mean pixel intensity above this is 'too bright'.",
    )

    # ── Quality – Pose ────────────────────────────────────────────────
    pose_yaw_threshold: float = Field(
        default=45.0,
        ge=0.0,
        le=90.0,
        description="Maximum yaw angle (degrees) before a face is flagged.",
    )
    pose_pitch_threshold: float = Field(
        default=45.0,
        ge=0.0,
        le=90.0,
        description="Maximum pitch angle (degrees) before a face is flagged.",
    )

    # ── Processing ────────────────────────────────────────────────────
    ai_processing_fps: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="Target AI processing frames per second.",
    )

    # ── Quality weights (for overall score) ───────────────────────────
    weight_face_size: float = Field(default=0.20)
    weight_blur: float = Field(default=0.25)
    weight_brightness: float = Field(default=0.20)
    weight_pose: float = Field(default=0.20)
    weight_detection_conf: float = Field(default=0.15)

    # ── Inference device ──────────────────────────────────────────────
    device: str = Field(
        default="cpu",
        description="Inference device: 'cpu' or 'cuda'. Auto-detected at startup.",
    )

    # ── Quality gate ──────────────────────────────────────────────────
    quality_threshold: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description=(
            "Overall quality score below which embedding generation is skipped. "
            "Kept intentionally low so borderline faces still get embeddings."
        ),
    )

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=())


# ── Singleton helper ──────────────────────────────────────────────────

_global_config: RecognitionConfig | None = None


def get_config() -> RecognitionConfig:
    """Return the global recognition config, creating it on first call."""
    global _global_config
    if _global_config is None:
        _global_config = RecognitionConfig()
    return _global_config


def set_config(config: RecognitionConfig) -> None:
    """Replace the global recognition config (useful for tests / API updates)."""
    global _global_config
    _global_config = config
