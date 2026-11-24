import os
import subprocess
import shutil
import sys

def main():
    print("Starting build process...")
    
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    frontend_dist = os.path.join(backend_dir, 'frontend_dist')

    # 1. Build React Frontend
    print("Building React frontend...")
    # Using shell=True for npm on Windows
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm_cmd, "run", "build"], cwd=frontend_dir, check=True)

    print("Frontend build complete.")

    # 2. Run PyInstaller
    print("Running PyInstaller...")
    
    # We need to include the frontend_dist folder in the single executable.
    # On Windows: --add-data "backend/frontend_dist;backend/frontend_dist"
    
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "FaceNexa",
        "--onefile",
        "--noconsole",
        "--add-data", f"backend/frontend_dist{os.pathsep}backend/frontend_dist",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "sqlalchemy.sql.default_comparator",
        "--hidden-import", "face_recognition",
        "--hidden-import", "cv2",
        "app.py"
    ]
    
    subprocess.run(pyinstaller_cmd, check=True)
    
    print("Build complete! Executable is in the 'dist' folder.")

if __name__ == "__main__":
    main()
