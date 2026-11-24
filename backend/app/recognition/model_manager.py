"""
ModelManager — singleton responsible for loading and managing InsightFace models.

Loads models once at startup and exposes them for reuse.  If loading fails the
backend stays alive and reports the error through ``get_status()``.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

from backend.app.recognition.errors import ModelLoadError
from backend.app.recognition.recognition_config import RecognitionConfig, get_config
from backend.app.recognition.recognition_models import (
    AISystemStatus,
    ModelStatus,
)

logger = logging.getLogger("facenexa.model_manager")


class ModelManager:
    """Loads, holds, and releases InsightFace models.

    Thread-safe — concurrent callers will see a consistent state.
    The manager uses a lock to prevent duplicate loading.
    """

    _instance: Optional["ModelManager"] = None
    _lock = threading.Lock()

    # ── Singleton accessor ────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "ModelManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Release the current singleton (for tests)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.release()
            cls._instance = None

    # ── Init ──────────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._app = None  # insightface.app.FaceAnalysis instance
        self._det_model_status = ModelStatus(name="SCRFD Face Detector")
        self._rec_model_status = ModelStatus(name="ArcFace Recognition")
        self._inference_device: str = "cpu"
        self._status: str = "not_initialized"
        self._init_lock = threading.Lock()
        self._embedding_dim: int = 0
        self._config: RecognitionConfig = get_config()

    # ── Public API ────────────────────────────────────────────────────

    def initialize(self, config: RecognitionConfig | None = None) -> None:
        """Load models.  Safe to call multiple times — will no-op if already loaded."""
        with self._init_lock:
            if self._status == "ready":
                logger.info("Models already loaded — skipping re-init.")
                return
            if config is not None:
                self._config = config
            self._status = "loading"
            self._load_models()

    @property
    def app(self):
        """Return the InsightFace FaceAnalysis instance (or None)."""
        return self._app

    @property
    def inference_device(self) -> str:
        return self._inference_device

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    @property
    def is_ready(self) -> bool:
        return self._status == "ready"

    def get_status(self) -> AISystemStatus:
        return AISystemStatus(
            detection_model=self._det_model_status.model_copy(),
            recognition_model=self._rec_model_status.model_copy(),
            inference_device=self._inference_device,
            status=self._status,
            processing_active=False,  # set by AIWorker
        )

    def release(self) -> None:
        """Release model resources."""
        with self._init_lock:
            self._app = None
            self._status = "not_initialized"
            self._det_model_status.loaded = False
            self._rec_model_status.loaded = False
            logger.info("Models released.")

    # ── Internal ──────────────────────────────────────────────────────

    def _detect_device(self) -> tuple[list[str], str]:
        """Detect available ONNX execution providers and pick the best."""
        try:
            import onnxruntime as ort

            available = ort.get_available_providers()
            if "CUDAExecutionProvider" in available:
                logger.info("GPU (CUDA) available — using GPU for inference.")
                return (["CUDAExecutionProvider", "CPUExecutionProvider"], "cuda")
            logger.info("Using CPU for inference.")
            return (["CPUExecutionProvider"], "cpu")
        except Exception:
            return (["CPUExecutionProvider"], "cpu")

    def _load_models(self) -> None:
        """Actually load InsightFace models."""
        try:
            import insightface
            from insightface.app import FaceAnalysis

            providers, device = self._detect_device()
            self._inference_device = device
            self._config.device = device

            model_dir = self._config.model_dir
            Path(model_dir).mkdir(parents=True, exist_ok=True)

            logger.info(
                "Loading InsightFace model pack '%s' from '%s' …",
                self._config.model_name,
                model_dir,
            )

            t0 = time.perf_counter()
            self._app = FaceAnalysis(
                name=self._config.model_name,
                root=model_dir,
                providers=providers,
            )
            self._app.prepare(ctx_id=0 if device == "cuda" else -1, det_size=(640, 640))
            load_time = time.perf_counter() - t0

            # ── Verify detection model ────────────────────────────────
            det_loaded = False
            for model in self._app.models:
                task = getattr(model, "taskname", "")
                if task == "detection":
                    det_loaded = True
                    det_name = getattr(model, "name", "SCRFD")
                    self._det_model_status = ModelStatus(
                        name=det_name, loaded=True, version=str(getattr(model, "name", ""))
                    )

            if not det_loaded:
                self._det_model_status = ModelStatus(
                    name="SCRFD Face Detector",
                    loaded=False,
                    error_message="Detection model not found in pack.",
                )

            # ── Verify recognition model ──────────────────────────────
            rec_loaded = False
            for model in self._app.models:
                task = getattr(model, "taskname", "")
                if task == "recognition":
                    rec_loaded = True
                    rec_name = getattr(model, "name", "ArcFace")
                    # Discover actual embedding dimensionality
                    output_shape = getattr(model, "output_shape", None)
                    if output_shape is not None:
                        self._embedding_dim = output_shape[-1]
                    else:
                        # Fallback: run a dummy forward pass
                        try:
                            dummy = np.zeros((1, 3, 112, 112), dtype=np.float32)
                            out = model.session.run(None, {model.session.get_inputs()[0].name: dummy})
                            self._embedding_dim = out[0].shape[-1]
                        except Exception:
                            self._embedding_dim = 512  # common default

                    self._rec_model_status = ModelStatus(
                        name=rec_name,
                        loaded=True,
                        version=f"dim={self._embedding_dim}",
                    )

            if not rec_loaded:
                self._rec_model_status = ModelStatus(
                    name="ArcFace Recognition",
                    loaded=False,
                    error_message="Recognition model not found in pack.",
                )

            # ── Final status ──────────────────────────────────────────
            if det_loaded and rec_loaded:
                self._status = "ready"
                logger.info(
                    "Models loaded in %.2f s — detection: %s, recognition: %s (dim=%d), device: %s",
                    load_time,
                    self._det_model_status.name,
                    self._rec_model_status.name,
                    self._embedding_dim,
                    self._inference_device,
                )
            else:
                self._status = "error"
                logger.warning("One or more models failed to load.")

            # ── Quick sanity inference ────────────────────────────────
            if self._status == "ready":
                self._verify_inference()

        except ImportError as exc:
            self._status = "error"
            err = f"InsightFace or ONNX Runtime is not installed: {exc}"
            self._det_model_status.error_message = err
            self._rec_model_status.error_message = err
            logger.error(err)

        except Exception as exc:
            self._status = "error"
            err = f"Model loading failed: {exc}"
            self._det_model_status.error_message = err
            self._rec_model_status.error_message = err
            logger.exception(err)

    def _verify_inference(self) -> None:
        """Run a quick synthetic frame through the pipeline to confirm inference works."""
        try:
            dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # We just call get — no faces expected, but it should not crash.
            _ = self._app.get(dummy_frame)
            logger.info("Inference verification passed.")
        except Exception as exc:
            self._status = "error"
            logger.error("Inference verification failed: %s", exc)
