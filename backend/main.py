import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routes import students, attendance, analytics, settings, ai_routes, ai_websocket
from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.camera_capture import CameraCapture
from backend.app.recognition.ai_worker import AIProcessingWorker
from backend.routes.ai_websocket import ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("facenexa.main")

# Create database tables
Base.metadata.create_all(bind=engine)

# Singletons for backend camera & worker
camera = CameraCapture(device=0)
worker = AIProcessingWorker(camera=camera)
ai_routes.set_camera_and_worker(camera, worker)

# Link AI worker callback to WebSocket broadcast
worker.set_on_result(ws_manager.broadcast_results)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing AI ModelManager...")
    try:
        manager = ModelManager.get_instance()
        manager.initialize()
    except Exception as e:
        logger.error(f"AI ModelManager initialization failed: {e}")

    logger.info("Starting Camera and AI Worker...")
    try:
        camera.start()
        worker.start()
    except Exception as e:
        logger.error(f"Failed to start camera/worker: {e}")

    yield

    # Shutdown
    logger.info("Stopping AI Worker and Camera...")
    try:
        worker.stop()
        camera.stop()
        ModelManager.get_instance().release()
    except Exception as e:
        logger.error(f"Shutdown cleanup error: {e}")

app = FastAPI(title="Face Nexa API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["attendance"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(ai_routes.router, prefix="/api", tags=["ai"])
app.include_router(ai_websocket.router, tags=["ai-websocket"])

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

