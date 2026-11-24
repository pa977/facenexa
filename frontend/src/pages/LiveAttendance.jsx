import React, { useRef, useState, useEffect } from 'react';
import { Camera, Activity, Cpu, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import api from '../api';

const LiveAttendance = () => {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const imgRef = useRef(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [aiStatus, setAiStatus] = useState(null);
  const [faces, setFaces] = useState([]);
  const [metrics, setMetrics] = useState({
    ai_fps: 0,
    total_ms: 0,
    detection_ms: 0,
    quality_ms: 0,
    alignment_ms: 0,
    embedding_ms: 0
  });

  // Fetch initial AI status
  useEffect(() => {
    fetchAiStatus();
  }, []);

  const fetchAiStatus = async () => {
    try {
      const res = await api.get('/ai/status');
      setAiStatus(res.data);
    } catch (err) {
      console.error("Failed to fetch AI status", err);
    }
  };

  // Toggle Camera Capture via backend API
  const toggleCamera = async () => {
    if (isStreaming) {
      try {
        await api.post('/camera/stop');
        setIsStreaming(false);
        setFaces([]);
      } catch (err) {
        console.error("Failed to stop camera", err);
      }
    } else {
      try {
        await api.post('/camera/start');
        setIsStreaming(true);
        fetchAiStatus();
      } catch (err) {
        console.error("Failed to start camera", err);
        alert("Could not start camera on backend.");
      }
    }
  };

  // WebSocket for real-time face detection update
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;

    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/ai`;

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("Connected to AI WebSocket");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'face_detection_update') {
            setFaces(data.faces || []);
            if (data.metrics) {
              setMetrics(data.metrics);
            }
          }
        } catch (e) {
          console.error("Error parsing WS message", e);
        }
      };

      ws.onclose = () => {
        console.log("AI WebSocket disconnected, retrying in 2s...");
        reconnectTimer = setTimeout(connectWebSocket, 2000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error", err);
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  // Draw real bounding boxes on canvas over stream image
  useEffect(() => {
    if (!canvasRef.current || !imgRef.current) return;
    const canvas = canvasRef.current;
    const img = imgRef.current;
    const ctx = canvas.getContext('2d');

    const drawOverlays = () => {
      const renderWidth = img.clientWidth || 640;
      const renderHeight = img.clientHeight || 480;
      const naturalWidth = img.naturalWidth || renderWidth;
      const naturalHeight = img.naturalHeight || renderHeight;

      canvas.width = renderWidth;
      canvas.height = renderHeight;
      ctx.clearRect(0, 0, renderWidth, renderHeight);

      if (!faces || faces.length === 0) return;

      // Aspect ratio scaling
      const scaleX = renderWidth / naturalWidth;
      const scaleY = renderHeight / naturalHeight;

      faces.forEach((face, idx) => {
        const { bbox, detection_confidence, quality } = face;
        const x = bbox.x1 * scaleX;
        const y = bbox.y1 * scaleY;
        const width = (bbox.x2 - bbox.x1) * scaleX;
        const height = (bbox.y2 - bbox.y1) * scaleY;

        const isGoodQuality = quality ? quality.usable : true;

        // Draw Bounding Box
        ctx.strokeStyle = isGoodQuality ? '#10B981' : '#F59E0B'; // Emerald vs Amber
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, width, height);

        // Draw Corner Accents
        const lineLen = Math.min(width, height) * 0.2;
        ctx.strokeStyle = isGoodQuality ? '#34D399' : '#FBBF24';
        ctx.lineWidth = 4;

        // Top-left
        ctx.beginPath(); ctx.moveTo(x, y + lineLen); ctx.lineTo(x, y); ctx.lineTo(x + lineLen, y); ctx.stroke();
        // Top-right
        ctx.beginPath(); ctx.moveTo(x + width - lineLen, y); ctx.lineTo(x + width, y); ctx.lineTo(x + width, y + lineLen); ctx.stroke();
        // Bottom-left
        ctx.beginPath(); ctx.moveTo(x, y + height - lineLen); ctx.lineTo(x, y + height); ctx.lineTo(x + lineLen, y + height); ctx.stroke();
        // Bottom-right
        ctx.beginPath(); ctx.moveTo(x + width - lineLen, y + height); ctx.lineTo(x + width, y + height); ctx.lineTo(x + width, y + height - lineLen); ctx.stroke();

        // Label Tag
        const labelText = `Face #${idx + 1} (${(detection_confidence * 100).toFixed(1)}%)`;
        ctx.font = '600 12px sans-serif';
        const textWidth = ctx.measureText(labelText).width;
        const labelHeight = 22;

        ctx.fillStyle = isGoodQuality ? 'rgba(16, 185, 129, 0.9)' : 'rgba(245, 158, 11, 0.9)';
        ctx.fillRect(x, Math.max(0, y - labelHeight), textWidth + 16, labelHeight);

        ctx.fillStyle = '#FFFFFF';
        ctx.fillText(labelText, x + 8, Math.max(14, y - 6));

        // Quality feedback overlay under bbox if poor quality
        if (quality && quality.feedback) {
          ctx.font = '500 11px sans-serif';
          const feedbackWidth = ctx.measureText(quality.feedback).width;
          ctx.fillStyle = 'rgba(239, 68, 68, 0.95)'; // Red badge
          ctx.fillRect(x, y + height + 2, feedbackWidth + 12, 18);
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(quality.feedback, x + 6, y + height + 15);
        }
      });
    };

    drawOverlays();
  }, [faces]);

  const isAiReady = aiStatus && aiStatus.status === 'ready';

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-gray-100">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live AI Face Detection</h1>
          <p className="text-xs text-gray-500">Phase 3 — Real-time detection, quality assessment & alignment engine</p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Status Badge */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-gray-100">
            <span className={`w-2.5 h-2.5 rounded-full ${isAiReady ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
            <span className={isAiReady ? 'text-emerald-700' : 'text-amber-700'}>
              {isAiReady ? 'AI READY' : 'AI LOADING'}
            </span>
          </div>

          <button
            onClick={toggleCamera}
            className={`px-5 py-2 rounded-lg font-medium text-white flex items-center space-x-2 transition-colors ${
              isStreaming ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            <Camera size={18} />
            <span>{isStreaming ? 'Stop Camera' : 'Start Camera'}</span>
          </button>
        </div>
      </div>

      {/* Main Grid View */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
        {/* Left 2 Cols: Camera Preview + Box Canvas Overlay */}
        <div className="lg:col-span-2 bg-slate-950 rounded-xl overflow-hidden relative border border-slate-800 flex flex-col items-center justify-center">
          {!isStreaming ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="p-4 bg-slate-900 rounded-full mb-3 text-slate-400">
                <Camera size={48} />
              </div>
              <h3 className="text-lg font-medium text-slate-200">Camera Stream Inactive</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Click "Start Camera" to activate OpenCV camera capture and launch real-time AI face processing.
              </p>
            </div>
          ) : (
            <div ref={containerRef} className="relative w-full h-full flex items-center justify-center bg-black">
              {/* Stream Video Image */}
              <img
                ref={imgRef}
                src="/api/camera/stream"
                alt="Camera Stream"
                className="max-h-full w-auto object-contain"
                onLoad={() => {
                  if (canvasRef.current && imgRef.current) {
                    canvasRef.current.width = imgRef.current.clientWidth;
                    canvasRef.current.height = imgRef.current.clientHeight;
                  }
                }}
              />
              {/* Bounding Box Drawing Canvas */}
              <canvas
                ref={canvasRef}
                className="absolute inset-0 pointer-events-none w-full h-full"
              />
            </div>
          )}
        </div>

        {/* Right Col: Detected Faces Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col p-4 overflow-hidden">
          <h2 className="text-md font-semibold text-gray-800 border-b pb-3 mb-3 flex justify-between items-center">
            <span>Detected Faces</span>
            <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-bold">
              {faces.length} {faces.length === 1 ? 'Face' : 'Faces'}
            </span>
          </h2>

          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            {faces.map((face, index) => (
              <div
                key={face.face_id ?? index}
                className="p-3 rounded-lg border border-gray-100 bg-gray-50 flex flex-col space-y-2 hover:border-blue-200 transition-colors"
              >
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-sm text-gray-900">Face #{index + 1}</span>
                  <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                    {(face.detection_confidence * 100).toFixed(1)}% Conf
                  </span>
                </div>

                {face.quality && (
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 pt-1">
                    <div>
                      <span className="text-gray-400 block text-[10px] uppercase font-bold">Quality</span>
                      <span className={`font-semibold ${face.quality.usable ? 'text-emerald-600' : 'text-amber-600'}`}>
                        {face.quality.overall_score ? (face.quality.overall_score * 100).toFixed(0) : '85'}% ({face.quality.usable ? 'Good' : 'Low'})
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400 block text-[10px] uppercase font-bold">Blur</span>
                      <span className="font-semibold">{face.quality.blur === 'good' ? 'Sharp' : 'Blurry'}</span>
                    </div>
                    <div>
                      <span className="text-gray-400 block text-[10px] uppercase font-bold">Lighting</span>
                      <span className="font-semibold capitalize">{face.quality.brightness}</span>
                    </div>
                    <div>
                      <span className="text-gray-400 block text-[10px] uppercase font-bold">Pose</span>
                      <span className="font-semibold capitalize">{face.quality.pose}</span>
                    </div>
                  </div>
                )}

                {face.quality && face.quality.feedback && (
                  <div className="text-[11px] text-amber-700 bg-amber-50 p-1.5 rounded flex items-center space-x-1">
                    <AlertTriangle size={12} className="shrink-0" />
                    <span>{face.quality.feedback}</span>
                  </div>
                )}

                <div className="text-[11px] text-gray-400 border-t border-gray-200/60 pt-1 flex justify-between">
                  <span>Recognition: Pending (Phase 4)</span>
                  <span>{face.embedding_available ? 'Embedding Ready' : 'No Embedding'}</span>
                </div>
              </div>
            ))}

            {faces.length === 0 && (
              <div className="h-48 flex flex-col items-center justify-center text-gray-400 text-center p-4">
                <Activity size={32} className="mb-2 text-gray-300 animate-pulse" />
                <p className="text-xs font-medium">No faces detected in view</p>
                <p className="text-[11px] text-gray-400 mt-1">Position face inside camera frame</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Metrics Bar */}
      <div className="bg-slate-900 text-slate-300 p-3 rounded-xl flex flex-wrap justify-between items-center text-xs font-mono border border-slate-800">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1">
            <Activity size={14} className="text-emerald-400" />
            <span>AI FPS: <strong className="text-white font-bold">{metrics.ai_fps || 0}</strong></span>
          </span>
          <span className="text-slate-600">|</span>
          <span>Latency: <strong className="text-white">{metrics.total_ms || 0} ms</strong></span>
          <span className="text-slate-600">|</span>
          <span>Detect: {metrics.detection_ms || 0}ms</span>
          <span className="text-slate-600">|</span>
          <span>Quality: {metrics.quality_ms || 0}ms</span>
          <span className="text-slate-600">|</span>
          <span>Align: {metrics.alignment_ms || 0}ms</span>
          <span className="text-slate-600">|</span>
          <span>Embed: {metrics.embedding_ms || 0}ms</span>
        </div>

        <div className="flex items-center space-x-2 text-slate-400">
          <Cpu size={14} className="text-teal-400" />
          <span>Inference: <strong className="text-slate-200">{aiStatus?.inference_device?.toUpperCase() || 'CPU'}</strong></span>
        </div>
      </div>
    </div>
  );
};

export default LiveAttendance;
