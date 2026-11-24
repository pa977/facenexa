import React, { useState, useEffect, useRef } from 'react';
import { UserPlus, Trash2, Camera, X } from 'lucide-react';
import api from '../api';

const Students = () => {
  const [students, setStudents] = useState([]);
  const [showForm, setShowForm] = useState(false);
  
  const [formData, setFormData] = useState({ name: '', roll_no: '', class_section: '', email: '' });
  const [images, setImages] = useState([]); // Array of base64 strings
  const [capturing, setCapturing] = useState(false);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    try {
      const res = await api.get('/students');
      setStudents(res.data);
    } catch (err) {
      console.error("Failed to fetch students");
    }
  };

  const startCapture = async () => {
    setCapturing(true);
    setImages([]);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch (err) {
      alert("Could not access camera");
      setCapturing(false);
    }
  };

  const stopCapture = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(t => t.stop());
    }
    setCapturing(false);
  };

  const captureFrame = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const video = videoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const b64 = canvas.toDataURL('image/jpeg', 0.8);
    setImages(prev => [...prev, b64]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (images.length < 5) {
      alert("Please capture at least 5 images of the student's face.");
      return;
    }
    
    try {
      await api.post('/students', { ...formData, images });
      setShowForm(false);
      setFormData({ name: '', roll_no: '', class_section: '', email: '' });
      setImages([]);
      stopCapture();
      fetchStudents();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to register student");
    }
  };

  const handleDelete = async (student_id) => {
    if (!confirm("Are you sure you want to delete this student and all their data?")) return;
    try {
      await api.delete(`/students/${student_id}`);
      fetchStudents();
    } catch (err) {
      alert("Failed to delete student");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Students</h1>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium flex items-center space-x-2"
        >
          <UserPlus size={20} />
          <span>Add Student</span>
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl flex overflow-hidden max-h-full">
            
            {/* Form Section */}
            <div className="w-1/2 p-8 overflow-y-auto">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Register Student</h2>
                <button onClick={() => {setShowForm(false); stopCapture();}} className="text-gray-400 hover:text-gray-600">
                  <X size={24} />
                </button>
              </div>
              
              <form id="studentForm" onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name</label>
                  <input required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="mt-1 w-full p-2 border rounded-md" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Roll Number</label>
                  <input required type="text" value={formData.roll_no} onChange={e => setFormData({...formData, roll_no: e.target.value})} className="mt-1 w-full p-2 border rounded-md" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Class/Section</label>
                  <input required type="text" value={formData.class_section} onChange={e => setFormData({...formData, class_section: e.target.value})} className="mt-1 w-full p-2 border rounded-md" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <input required type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="mt-1 w-full p-2 border rounded-md" />
                </div>
              </form>
            </div>

            {/* Camera Section */}
            <div className="w-1/2 bg-gray-50 p-8 border-l border-gray-200 flex flex-col">
              <h3 className="text-lg font-semibold mb-4">Face Capture</h3>
              
              {!capturing ? (
                <div className="flex-1 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg">
                  <button onClick={startCameraCapture} className="flex flex-col items-center text-blue-600 hover:text-blue-700">
                    <Camera size={48} className="mb-2" />
                    <span className="font-medium">Start Camera</span>
                  </button>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center">
                  <video ref={videoRef} className="w-full h-48 object-cover rounded-lg bg-black mb-4" muted playsInline />
                  <canvas ref={canvasRef} className="hidden" />
                  <button type="button" onClick={captureFrame} className="bg-purple-600 text-white px-6 py-2 rounded-full font-medium mb-4 hover:bg-purple-700">
                    Capture Frame ({images.length})
                  </button>
                  <p className="text-sm text-gray-500">Capture 5-10 different angles of the face.</p>
                  
                  {/* Thumbnails */}
                  <div className="flex flex-wrap gap-2 mt-4 overflow-y-auto max-h-24">
                    {images.map((img, idx) => (
                      <img key={idx} src={img} className="w-12 h-12 object-cover rounded-md border" />
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-6">
                <button type="submit" form="studentForm" className="w-full bg-green-600 text-white py-3 rounded-lg font-bold hover:bg-green-700">
                  Complete Registration
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Student List Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="p-4 font-semibold text-gray-600">Roll No</th>
              <th className="p-4 font-semibold text-gray-600">Name</th>
              <th className="p-4 font-semibold text-gray-600">Class</th>
              <th className="p-4 font-semibold text-gray-600">Enrolled</th>
              <th className="p-4 font-semibold text-gray-600 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {students.map(s => (
              <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="p-4 text-gray-900 font-medium">{s.roll_no}</td>
                <td className="p-4 text-gray-700">{s.name}</td>
                <td className="p-4 text-gray-600">{s.class_section}</td>
                <td className="p-4 text-gray-500 text-sm">{new Date(s.created_at).toLocaleDateString()}</td>
                <td className="p-4 text-right">
                  <button onClick={() => handleDelete(s.student_id)} className="text-red-500 hover:text-red-700 p-2">
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
            {students.length === 0 && (
              <tr>
                <td colSpan="5" className="p-8 text-center text-gray-400">No students registered yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  function startCameraCapture() {
    startCapture();
  }
};

export default Students;
