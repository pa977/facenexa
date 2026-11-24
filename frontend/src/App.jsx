import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { LayoutDashboard, Users, Camera, PieChart, Settings as SettingsIcon } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import LiveAttendance from './pages/LiveAttendance';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

function App() {
  return (
    <Router>
      <div className="flex h-screen bg-gray-100 font-sans">
        {/* Sidebar */}
        <aside className="w-64 bg-slate-900 text-white flex flex-col">
          <div className="h-16 flex items-center justify-center border-b border-slate-700">
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-teal-400">
              Face Nexa
            </h1>
          </div>
          <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
            <Link to="/" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-slate-800 transition-colors">
              <LayoutDashboard size={20} className="text-blue-400" />
              <span>Dashboard</span>
            </Link>
            <Link to="/attendance" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-slate-800 transition-colors">
              <Camera size={20} className="text-teal-400" />
              <span>Live Attendance</span>
            </Link>
            <Link to="/students" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-slate-800 transition-colors">
              <Users size={20} className="text-purple-400" />
              <span>Students</span>
            </Link>
            <Link to="/analytics" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-slate-800 transition-colors">
              <PieChart size={20} className="text-pink-400" />
              <span>Analytics</span>
            </Link>
          </nav>
          <div className="p-4 border-t border-slate-700">
            <Link to="/settings" className="flex items-center space-x-3 p-3 rounded-lg hover:bg-slate-800 transition-colors">
              <SettingsIcon size={20} className="text-gray-400" />
              <span>Settings</span>
            </Link>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-gray-50">
          <div className="p-8 h-full">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/attendance" element={<LiveAttendance />} />
              <Route path="/students" element={<Students />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
}

export default App;
