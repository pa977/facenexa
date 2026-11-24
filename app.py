import os
import sys
import threading
import time
import webview
import uvicorn
from backend.main import app as fastapi_app

def start_server():
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error")

def get_base_path():
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return base_path

if __name__ == '__main__':
    # Start FastAPI server in a daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Load URL. If bundled, we could serve static files from FastAPI.
    # We will let Vite's preview or built static files run, but for now we'll just point pywebview to localhost:8000
    # Wait, the build script will copy React build to backend/frontend_dist
    
    # If we are running in PyInstaller, we need to serve the frontend via FastAPI
    # Let's add static files mounting to the fastapi_app if the folder exists.
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    frontend_dist = os.path.join(get_base_path(), "backend", "frontend_dist")
    if os.path.exists(frontend_dist):
        fastapi_app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
        
        @fastapi_app.get("/{full_path:path}")
        async def catch_all(full_path: str):
            # Try to return the requested file
            file_path = os.path.join(frontend_dist, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            # Default to index.html for React Router
            return FileResponse(os.path.join(frontend_dist, "index.html"))

    # Create pywebview window
    webview.create_window('Face Nexa', 'http://127.0.0.1:8000', width=1200, height=800, min_size=(800, 600))
    webview.start()
