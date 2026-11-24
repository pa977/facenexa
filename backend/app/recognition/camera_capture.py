"""
CameraCapture — OpenCV-based backend camera service.

Runs in a background thread and provides latest-frame access.
Also generates MJPEG frames for frontend streaming.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("facenexa.camera")


class CameraCapture:
    """Manage an OpenCV VideoCapture in a background thread.

    Provides:
        • ``get_latest_frame()`` — non-blocking latest frame
        • ``generate_mjpeg()``  — MJPEG generator for HTTP streaming
        • Connection status & auto-reconnection
    """

    def __init__(self, device: int | str = 0) -> None:
        self._device = device
        self._cap: Optional[cv2.VideoCapture] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._fps: float = 0.0
        self._frame_width: int = 0
        self._frame_height: int = 0
        self._reconnect_delay: float = 2.0

    # ── Public API ────────────────────────────────────────────────────

    def start(self, device: int | str | None = None) -> bool:
        """Start capturing in a background thread."""
        if self._running:
            logger.info("Camera already running.")
            return True

        if device is not None:
            self._device = device

        if not self._open_device():
            return False

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera capture started (device=%s).", self._device)
        return True

    def stop(self) -> None:
        """Stop capturing and release the device."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._release()
        logger.info("Camera capture stopped.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def frame_size(self) -> tuple[int, int]:
        """(width, height) of the current capture."""
        return self._frame_width, self._frame_height

    @property
    def fps(self) -> float:
        return self._fps

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Return the most recent frame (or None if unavailable)."""
        with self._frame_lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
            return None

    def generate_mjpeg(self):
        """Yield MJPEG frames for HTTP streaming (multipart/x-mixed-replace).

        This is a generator — use it with a StreamingResponse.
        """
        while self._running:
            frame = self.get_latest_frame()
            if frame is None:
                time.sleep(0.03)
                continue
            ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg.tobytes()
                + b"\r\n"
            )
            time.sleep(0.033)  # ~30 FPS cap for preview

    def get_status(self) -> dict:
        return {
            "connected": self._connected,
            "running": self._running,
            "device": str(self._device),
            "resolution": f"{self._frame_width}x{self._frame_height}",
            "fps": round(self._fps, 1),
        }

    # ── Internal ──────────────────────────────────────────────────────

    def _open_device(self) -> bool:
        try:
            dev = int(self._device) if str(self._device).isdigit() else self._device
            self._cap = cv2.VideoCapture(dev, cv2.CAP_DSHOW if isinstance(dev, int) else cv2.CAP_ANY)
            if not self._cap.isOpened():
                # Retry without DirectShow
                self._cap = cv2.VideoCapture(dev)
            if self._cap.isOpened():
                self._frame_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self._frame_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
                self._connected = True
                logger.info(
                    "Camera opened: %dx%d @ %.1f FPS",
                    self._frame_width,
                    self._frame_height,
                    self._fps,
                )
                return True
            else:
                self._connected = False
                logger.error("Failed to open camera device %s.", self._device)
                return False
        except Exception as exc:
            self._connected = False
            logger.error("Camera open error: %s", exc)
            return False

    def _release(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        self._connected = False
        self._latest_frame = None

    def _capture_loop(self) -> None:
        """Continuously read frames and store the latest."""
        consecutive_failures = 0
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                self._connected = False
                logger.warning("Camera disconnected — attempting reconnect …")
                time.sleep(self._reconnect_delay)
                if not self._open_device():
                    consecutive_failures += 1
                    if consecutive_failures > 10:
                        logger.error("Camera reconnection failed too many times — stopping.")
                        self._running = False
                        break
                    continue
                consecutive_failures = 0

            ret, frame = self._cap.read()
            if not ret or frame is None:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    self._connected = False
                    logger.warning("Too many read failures.")
                time.sleep(0.01)
                continue

            consecutive_failures = 0
            self._connected = True
            with self._frame_lock:
                self._latest_frame = frame

            # Small sleep to avoid busy-spin on fast cameras
            time.sleep(0.001)

        self._release()
