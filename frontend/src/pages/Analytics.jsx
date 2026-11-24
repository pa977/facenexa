import React, { useState, useEffect } from 'react';
import { Calendar, User, Check, X } from 'lucide-react';
import api from '../api';

const Analytics = () => {
  const [todayAttendance, setTodayAttendance] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTodayAttendance();
  }, []);

  const fetchTodayAttendance = async () => {
    try {
      const res = await api.get('/attendance/today');
      setTodayAttendance(res.data);
    } catch (err) {
      console.error("Failed to fetch today's attendance", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8">Loading analytics...</div>;

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Analytics & Reports</h1>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Calendar size={20} className="text-blue-500" />
            Today's Attendance Log
          </h2>
          <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-medium">
            {todayAttendance.length} Present
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-0">
          <table className="w-full text-left">
            <thead className="bg-gray-50 border-b border-gray-100 sticky top-0">
              <tr>
                <th className="p-4 font-semibold text-gray-600">Student ID</th>
                <th className="p-4 font-semibold text-gray-600">Time</th>
                <th className="p-4 font-semibold text-gray-600">Status</th>
                <th className="p-4 font-semibold text-gray-600">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {todayAttendance.map(record => (
                <tr key={record.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="p-4 text-gray-900 font-medium">
                    <div className="flex items-center gap-2">
                      <User size={16} className="text-gray-400" />
                      {record.student_id.substring(0, 8)}...
                    </div>
                  </td>
                  <td className="p-4 text-gray-700">
                    {new Date(record.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="p-4">
                    <span className="flex items-center gap-1 text-green-600 bg-green-50 px-2 py-1 rounded-md w-max text-sm font-medium">
                      <Check size={14} /> {record.status}
                    </span>
                  </td>
                  <td className="p-4 text-gray-600">
                    {(record.confidence * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
              {todayAttendance.length === 0 && (
                <tr>
                  <td colSpan="4" className="p-12 text-center text-gray-400">
                    No attendance recorded today.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
