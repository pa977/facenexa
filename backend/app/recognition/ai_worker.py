"""
AIProcessingWorker — background thread running the face-processing pipeline.

Consumes the latest frame from ``CameraCapture`` at a configurable FPS,
runs the full pipeline (Detection → Quality → Alignment → Embedding),
and broadcasts structured results via a callback.

Does not block the API, camera, or WebSocket threads.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from backend.app.recognition.camera_capture import CameraCapture
from backend.app.recognition.frame_processor import FaceProcessingService
from backend.app.recognition.recognition_config import RecognitionConfig, get_config
from backend.app.recognition.recognition_models import (
    AIProcessingMetrics,
    FaceDetectionResult,
)

logger = logging.getLogger("facenexa.ai_worker")

# Type alias for the result callback
ResultCallback = Callable[
    [List[FaceDetectionResult], AIProcessingMetrics], None
]


class AIProcessingWorker:
    """Background worker that processes camera frames through the AI pipeline.

    Results are delivered via ``on_result`` callback (set by the WebSocket
    broadcaster).
    """

    def __init__(
        self,
        camera: CameraCapture,
        config: RecognitionConfig | None = None,
    ) -> None:
        self._camera = camera
        self._config = config or get_config()
        self._processor = FaceProcessingService(self._config)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_result: Optional[ResultCallback] = None

        # Latest results (thread-safe read)
        self._latest_results: List[FaceDetectionResult] = []
        self._latest_metrics = AIProcessingMetrics()
        self._results_lock = threading.Lock()

        # Rolling FPS tracker
        self._frame_times: list[float] = []

    # ── Public API ────────────────────────────────────────────────────

    def set_on_result(self, callback: ResultCallback) -> None:
        """Register a callback invoked after every frame is processed."""
        self._on_result = callback

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("AI worker started (target FPS=%.1f).", self._config.ai_processing_fps)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("AI worker stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def latest_results(self) -> List[FaceDetectionResult]:
        with self._results_lock:
            return list(self._latest_results)

    @property
    def latest_metrics(self) -> AIProcessingMetrics:
        with self._results_lock:
            return self._latest_metrics.model_copy()

    @property
    def latest_embeddings(self) -> Dict[int, np.ndarray]:
        """Expose embeddings from the frame processor (backend-only)."""
        return self._processor.latest_embeddings

    # ── Internal loop ─────────────────────────────────────────────────

    def _run_loop(self) -> None:
        target_interval = 1.0 / max(1.0, self._config.ai_processing_fps)

        while self._running:
            loop_start = time.perf_counter()

            # Grab the newest frame (latest-frame architecture)
            frame = self._camera.get_latest_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            try:
                results, metrics = self._processor.process_frame(frame)

                # Update rolling FPS
                self._frame_times.append(time.perf_counter())
                # Keep last 30 timestamps
                if len(self._frame_times) > 30:
                    self._frame_times = self._frame_times[-30:]
                if len(self._frame_times) >= 2:
                    span = self._frame_times[-1] - self._frame_times[0]
                    metrics.ai_fps = round(
                        (len(self._frame_times) - 1) / span if span > 0 else 0.0, 2
                    )

                with self._results_lock:
                    self._latest_results = results
                    self._latest_metrics = metrics

                # Notify listener
                if self._on_result is not None:
                    try:
                        self._on_result(results, metrics)
                    except Exception as exc:
                        logger.warning("Result callback error: %s", exc)

            except Exception as exc:
                logger.exception("AI worker frame processing error: %s", exc)

            # Throttle to target FPS
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
