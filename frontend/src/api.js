import axios from 'axios';

// When running inside pywebview or packaged app, API is on same host/port.
// During dev, vite proxy handles /api.
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

export default api;
