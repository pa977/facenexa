"""
AI & Camera REST API endpoints for FaceNexa — Phase 3.

Endpoints:
    GET  /api/ai/status         — AI model & system status
    GET  /api/ai/config         — Get current AI configuration
    PUT  /api/ai/config         — Update AI configuration
    GET  /api/ai/metrics        — Latest processing metrics
    POST /api/ai/process-frame  — Process a single base64 image (testing/one-off)
    GET  /api/camera/stream     — MJPEG camera stream
    POST /api/camera/start      — Start backend camera capture
    POST /api/camera/stop       — Stop backend camera capture
    GET  /api/camera/status     — Camera connection status
"""

from __future__ import annotations

import base64
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.recognition_config import get_config, set_config, RecognitionConfig
from backend.app.recognition.recognition_models import AISystemStatus, AIProcessingMetrics, FaceDetectionResult
from backend.app.recognition.frame_processor import FaceProcessingService
from backend.schemas import RecognizeRequest

router = APIRouter()

# Global camera & worker singletons managed at startup in main.py
_camera_instance = None
_worker_instance = None

def set_camera_and_worker(camera, worker):
    global _camera_instance, _worker_instance
    _camera_instance = camera
    _worker_instance = worker


# ── AI Endpoints ──────────────────────────────────────────────────────

@router.get("/ai/status", response_model=AISystemStatus)
def get_ai_status():
    """Return status of AI models, inference device, and worker state."""
    manager = ModelManager.get_instance()
    status = manager.get_status()
    if _worker_instance is not None:
        status.processing_active = _worker_instance.is_running
    return status


@router.get("/ai/config", response_model=RecognitionConfig)
def get_ai_config():
    """Get current AI configuration."""
    return get_config()


@router.put("/ai/config", response_model=RecognitionConfig)
def update_ai_config(new_config: RecognitionConfig):
    """Update AI configuration dynamically."""
    set_config(new_config)
    return get_config()


@router.get("/ai/metrics", response_model=AIProcessingMetrics)
def get_ai_metrics():
    """Get latest performance metrics from background AI worker."""
    if _worker_instance is None:
        return AIProcessingMetrics()
    return _worker_instance.latest_metrics


@router.post("/ai/process-frame")
def process_single_frame(request: RecognizeRequest):
    """Process a single base64 encoded frame (useful for manual testing)."""
    manager = ModelManager.get_instance()
    if not manager.is_ready:
        raise HTTPException(status_code=503, detail="AI models not loaded")

    # Decode base64 image
    img_data = request.image.split(',')[1] if ',' in request.image else request.image
    nparr = np.frombuffer(base64.b64decode(img_data), np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None or frame.size == 0:
        raise HTTPException(status_code=400, detail="Invalid image data")

    processor = FaceProcessingService()
    results, metrics = processor.process_frame(frame)

    return {
        "faces": results,
        "metrics": metrics
    }


# ── Camera Endpoints ──────────────────────────────────────────────────

@router.get("/camera/status")
def get_camera_status():
    """Get status of the backend camera capture."""
    if _camera_instance is None:
        return {"connected": False, "running": False, "device": "none"}
    return _camera_instance.get_status()


@router.post("/camera/start")
def start_camera(device: str | None = None):
    """Start backend camera capture."""
    if _camera_instance is None:
        raise HTTPException(status_code=500, detail="Camera service uninitialized")
    
    success = _camera_instance.start(device=device)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start camera device")

    if _worker_instance is not None and not _worker_instance.is_running:
        _worker_instance.start()

    return _camera_instance.get_status()


@router.post("/camera/stop")
def stop_camera():
    """Stop backend camera capture."""
    if _worker_instance is not None:
        _worker_instance.stop()
    if _camera_instance is not None:
        _camera_instance.stop()
    return {"status": "stopped"}


@router.get("/camera/stream")
def camera_stream():
    """MJPEG stream endpoint for frontend video tag/image overlay."""
    if _camera_instance is None or not _camera_instance.is_running:
        # Try auto-starting camera if not running
        if _camera_instance is not None:
            _camera_instance.start()
            if _worker_instance is not None and not _worker_instance.is_running:
                _worker_instance.start()
        else:
            raise HTTPException(status_code=503, detail="Camera service unavailable")

    return StreamingResponse(
        _camera_instance.generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
