# Face Nexa

**Offline, on-device face recognition attendance for classrooms and organizations.**

Face Nexa is a self-contained desktop application that marks student attendance from a webcam. Every face is detected, encoded and matched **locally** — there are no cloud APIs, no uploads and no telemetry. Records live in a SQLite database under `~/.face-nexa`, so the app keeps working with no network connection.

---

## Features

- **Student enrollment** — register students with one or more sample photos; face embeddings are computed on-device and stored alongside the raw samples.
- **Face recognition attendance** — webcam frames are matched against enrolled embeddings (`face_recognition` / dlib) and a daily record is created with a confidence score and a saved snapshot.
- **Duplicate protection** — a student can only be marked present once per day; repeat appearances report "Already marked present today".
- **Live AI pipeline** — an optional InsightFace / ONNX Runtime worker streams real-time face boxes, quality checks (blur, lighting, pose) and per-stage latency over a WebSocket to the Live Attendance screen.
- **Backend-owned camera** — OpenCV captures frames in the browser-free backend and serves an MJPEG stream; start/stop and status are available over REST.
- **Dashboard & analytics** — student/present/absent counts, today's percentage and 7-day average, plus 30-day attendance charts rendered with Recharts.
- **Settings** — adjust the recognition confidence threshold (default `0.6`) at runtime.
- **Desktop packaging** — runs as a native window via PyWebview and ships as a single-file Windows `.exe` (PyInstaller) with an optional Inno Setup installer.
- **API docs** — interactive Swagger UI at `/docs` for every REST endpoint.

> **Development status:** daily attendance, enrollment, live detection, analytics and packaging are implemented. The real-time AI worker currently reports recognition as "pending"; its embeddings are ready to be wired into the attendance decision path.

---

## Tech stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, Vite 8, React Router 7, Tailwind CSS 4, Recharts, Axios, Lucide icons |
| Backend | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2, SQLite |
| Face AI | OpenCV, `face_recognition` (dlib), optional InsightFace + ONNX Runtime |
| Desktop | PyWebview, PyInstaller, Inno Setup |

---

## Project structure

```
.
├── app.py                     # Desktop entry point: FastAPI server + PyWebview window
├── build.py                   # Builds React, then freezes app.py into dist/FaceNexa.exe
├── download_models.py         # Downloads + verifies the InsightFace ONNX pack
├── installer.iss              # Inno Setup script for FaceNexaSetup.exe
├── test_face.jpg              # Sample image for manual recognition tests
├── backend/
│   ├── main.py                # FastAPI app, lifespan, routers, camera + AI worker
│   ├── database.py            # SQLite engine and local data directories
│   ├── models.py              # Student, Attendance, EmotionLog, Setting tables
│   ├── schemas.py             # Pydantic request/response models
│   ├── requirements.txt       # Python dependencies
│   ├── routes/                # students, attendance, analytics, settings, AI, WebSocket
│   ├── services/face_service.py  # Enrollment embeddings and face matching
│   ├── app/recognition/       # Model manager, detector, alignment, quality, worker
│   └── tests/                 # pytest suite
├── frontend/
│   ├── src/pages/             # Dashboard, LiveAttendance, Students, Analytics, Settings
│   ├── src/App.jsx            # Sidebar navigation and routes
│   └── vite.config.js         # Dev proxy (/api, /ws) and build output
└── models/insightface/        # Optional ONNX model files (not committed)
```

---

## Prerequisites

- **Python 3.10–3.11** (3.11 recommended)
- **Node.js 20+** and npm
- A webcam for live features
- Windows for building the `.exe` installer (development itself is cross-platform)

`face_recognition` depends on dlib. If a wheel is not available for your Python version, install [CMake](https://cmake.org/download/) and the Visual Studio C++ Build Tools before `pip install`.

---

## Development setup

```powershell
# 1. Clone and create a virtual environment
git clone https://github.com/pa977/facenexa.git
cd facenexa
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Download the AI models (~290 MB, needed for live face detection)
python download_models.py
```

`download_models.py` is idempotent and verifies checksums; it only needs internet once. Skip it if you only plan to use enrollment and daily check-in via `face_recognition`.

Run the backend and frontend in two terminals:

```powershell
# Terminal 1 — API (http://127.0.0.1:8000, docs at /docs)
uvicorn backend.main:app --reload
```

```powershell
# Terminal 2 — UI (http://127.0.0.1:5173)
cd frontend
npm run dev
```

Vite proxies `/api` and `/ws` to the backend, so both parts behave as one application.

### Desktop mode

Build the frontend first so the API can serve it, then start the native window:

```powershell
cd frontend; npm run build; cd ..
python app.py
```

`app.py` mounts `backend/frontend_dist` as static files and opens `http://127.0.0.1:8000` in a PyWebview window.

---

## Building the Windows executable

```powershell
python build.py
```

This runs `npm run build` and then PyInstaller, producing **`dist/FaceNexa.exe`**. Compile `installer.iss` with [Inno Setup](https://jrsoftware.org/isinfo.php) to generate `FaceNexaSetup.exe` with Start Menu and optional desktop shortcuts.

Large model files are intentionally not tracked by Git. Run `python download_models.py` before packaging to place the InsightFace `buffalo_l` ONNX files under `models/insightface/models/buffalo_l/`. The EXE is built without the models, so install them on each machine where the app will run (or point the model manager at your own models).

---

## API overview

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health check |
| `POST /api/students/` | Enroll a student (name, roll no, class, email, base64 images) |
| `GET /api/students/` | List students |
| `DELETE /api/students/{id}` | Delete a student and their face data |
| `POST /api/attendance/recognize` | Identify a face from an image and mark attendance |
| `GET /api/attendance/today` | Today's attendance records |
| `GET /api/analytics/counts` | Summary counts and percentages |
| `GET /api/analytics/daily-counts` | Attendance for the last 30 days |
| `GET /api/settings/` · `POST /api/settings/` | Read/update settings |
| `GET /api/ai/status` · `/ai/config` · `/ai/metrics` | AI worker status and configuration |
| `POST /api/camera/start` · `/stop` · `GET /api/camera/stream` | Backend camera control and MJPEG stream |
| `WS /ws/ai` | Real-time face detection events |

Full reference: `http://127.0.0.1:8000/docs`.

---

## Data & privacy

- Database: `~/.face-nexa/facenexa.db`
- Enrollment images and embeddings: `~/.face-nexa/students/<student_id>/`
- Attendance snapshots: `~/.face-nexa/attendance/`

All paths are local to the machine. Face embeddings are never returned by the API and no data leaves the device.

---

## Tests and checks

```powershell
python -m pytest backend/tests -v
cd frontend; npm run lint; npm run build
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `face_recognition` install fails | Install CMake + VS C++ Build Tools, or use a matching dlib wheel / Python 3.11 |
| Frontend shows "Backend offline" | Start the API (`uvicorn backend.main:app --reload`) |
| `npm run dev` blocked by PowerShell policy | Use `npm.cmd run dev` |
| Camera will not start | Confirm no other app is using the webcam, then call `POST /api/camera/start` |
| "AI LOADING" badge persists | Models are not installed yet — run `python download_models.py` and restart |
| Database issues | Remove `~/.face-nexa/facenexa.db`; tables are recreated on next start |

---

## Roadmap

- [x] Student enrollment and daily attendance
- [x] Live camera preview, detection and quality assessment
- [x] Analytics dashboard and reports
- [x] Windows packaging and installer
- [ ] Connect AI embeddings to automatic recognition
- [ ] Session-based attendance (PRESENT / LATE / ABSENT / EXCUSED)
- [ ] Backup / restore and audit history
