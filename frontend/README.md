# Face Nexa — frontend

React 19 + Vite single-page UI for face-based attendance.

## Commands

```powershell
npm install
npm run dev      # dev server at http://127.0.0.1:5173
npm run build    # production build -> ../backend/frontend_dist
npm run lint     # ESLint
npm run preview
```

`vite.config.js` proxies `/api` and `/ws` to the FastAPI backend on `127.0.0.1:8000`, so no CORS setup is needed in development.

## Pages

- **Dashboard** — live counts and system status
- **Live Attendance** — MJPEG camera stream, real-time face boxes and quality metrics over WebSocket
- **Students** — enroll, list and delete students
- **Analytics** — attendance charts (Recharts)
- **Settings** — recognition threshold and preferences

See the [root README](../README.md) for full setup and build instructions.
