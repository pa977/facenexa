"""
WebSocket manager and endpoint for real-time AI face detection results.

Endpoint:
    /ws/ai — Broadcasts real-time face bounding boxes, quality indicators,
             and performance metrics to connected frontend clients.
             NEVER broadcasts raw embeddings.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.recognition.recognition_models import (
    AIProcessingMetrics,
    FaceDetectionResult,
)

logger = logging.getLogger("facenexa.websocket")

router = APIRouter()


class AIWebSocketManager:
    """Manages active WebSocket connections and broadcasts AI inference updates."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Total active: %d", len(self.active_connections))

    def broadcast_results(
        self, results: List[FaceDetectionResult], metrics: AIProcessingMetrics
    ) -> None:
        """Synchronous method called from background AI worker thread."""
        if not self.active_connections:
            return

        payload = {
            "type": "face_detection_update",
            "faces": [face.model_dump() for face in results],
            "metrics": metrics.model_dump(),
        }
        message_str = json.dumps(payload)

        # Schedule thread-safe broadcast in the main asyncio event loop
        if self._loop is not None and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(message_str), self._loop
            )

    async def _async_broadcast(self, message_str: str) -> None:
        disconnected = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.disconnect(conn)


# Global WebSocket manager instance
ws_manager = AIWebSocketManager()


@router.websocket("/ws/ai")
async def ai_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live face detection overlays."""
    ws_manager.set_loop(asyncio.get_running_loop())
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and accept ping/messages from client
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
        ws_manager.disconnect(websocket)
