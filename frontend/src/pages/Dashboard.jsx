import React, { useState, useEffect } from 'react';
import { Users, CheckCircle, TrendingUp, Activity, Cpu, ShieldCheck, AlertCircle, Camera } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../api';

const StatCard = ({ title, value, icon: Icon, colorClass }) => (
  <div className="bg-white rounded-xl shadow-sm p-6 flex items-center space-x-4 border border-gray-100">
    <div className={`p-3 rounded-full ${colorClass} bg-opacity-10`}>
      <Icon className={colorClass.replace('bg-', 'text-')} size={24} />
    </div>
    <div>
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <h3 className="text-2xl font-bold text-gray-900">{value}</h3>
    </div>
  </div>
);

const Dashboard = () => {
  const [counts, setCounts] = useState({ total_students: 0, today_attendance: 0, today_percentage: 0, seven_day_average: 0 });
  const [dailyData, setDailyData] = useState([]);
  const [aiStatus, setAiStatus] = useState(null);
  const [cameraStatus, setCameraStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [countsRes, dailyRes, aiRes, cameraRes] = await Promise.allSettled([
          api.get('/analytics/counts'),
          api.get('/analytics/daily-counts'),
          api.get('/ai/status'),
          api.get('/camera/status')
        ]);

        if (countsRes.status === 'fulfilled') setCounts(countsRes.value.data);
        if (dailyRes.status === 'fulfilled') setDailyData(dailyRes.value.data);
        if (aiRes.status === 'fulfilled') setAiStatus(aiRes.value.data);
        if (cameraRes.status === 'fulfilled') setCameraStatus(cameraRes.value.data);

      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="flex justify-center items-center h-full"><p className="text-lg text-gray-500 animate-pulse">Loading dashboard...</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500">FaceNexa Control & Analytics Overview</p>
        </div>
        <div className="text-sm text-gray-500">{new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
      </div>

      {/* AI System Status Panel */}
      <div className="bg-slate-900 text-white rounded-xl shadow-sm p-6 border border-slate-800">
        <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-3">
          <h2 className="text-lg font-bold flex items-center gap-2 text-slate-100">
            <Cpu className="text-teal-400" size={20} />
            AI SYSTEM STATUS
          </h2>
          <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
            aiStatus?.status === 'ready' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
          }`}>
            <span className={`w-2 h-2 rounded-full ${aiStatus?.status === 'ready' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            {aiStatus?.status?.toUpperCase() || 'INITIALIZING'}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 text-sm">
          <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400 block mb-1">Camera Stream</span>
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${cameraStatus?.running ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              <span className="font-semibold text-slate-200">{cameraStatus?.running ? 'Connected' : 'Offline'}</span>
            </div>
          </div>

          <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400 block mb-1">Face Detection</span>
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${aiStatus?.detection_model?.loaded ? 'bg-emerald-400' : 'bg-red-400'}`} />
              <span className="font-semibold text-slate-200">{aiStatus?.detection_model?.loaded ? 'Loaded' : 'Failed'}</span>
            </div>
          </div>

          <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400 block mb-1">Face Recognition</span>
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${aiStatus?.recognition_model?.loaded ? 'bg-emerald-400' : 'bg-red-400'}`} />
              <span className="font-semibold text-slate-200">{aiStatus?.recognition_model?.loaded ? 'Loaded' : 'Failed'}</span>
            </div>
          </div>

          <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400 block mb-1">Inference Engine</span>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-teal-300 uppercase">{aiStatus?.inference_device || 'CPU'}</span>
            </div>
          </div>

          <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400 block mb-1">AI Pipeline</span>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-200">{aiStatus?.processing_active ? 'Active Loop' : 'Standby'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Total Students" value={counts.total_students} icon={Users} colorClass="bg-blue-500 text-blue-500" />
        <StatCard title="Today's Attendance" value={counts.today_attendance} icon={CheckCircle} colorClass="bg-green-500 text-green-500" />
        <StatCard title="Today's Percentage" value={`${counts.today_percentage}%`} icon={Activity} colorClass="bg-purple-500 text-purple-500" />
        <StatCard title="7-Day Average" value={`${counts.seven_day_average}%`} icon={TrendingUp} colorClass="bg-pink-500 text-pink-500" />
      </div>

      {/* Charts */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <h2 className="text-xl font-semibold mb-6">30-Day Attendance Trend</h2>
        <div className="h-80 w-full">
          {dailyData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                <XAxis dataKey="date" stroke="#9CA3AF" tick={{fill: '#6B7280'}} tickLine={false} axisLine={false} />
                <YAxis stroke="#9CA3AF" tick={{fill: '#6B7280'}} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                  cursor={{ stroke: '#E5E7EB', strokeWidth: 2 }}
                />
                <Line type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={3} dot={{r: 4, strokeWidth: 2}} activeDot={{r: 6}} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-gray-400">No attendance data available yet.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
