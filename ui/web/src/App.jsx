import React, { useState } from 'react';
import { Settings, Code2 } from 'lucide-react';
import TaskSubmitter from './components/TaskSubmitter';
import TaskVisualizer from './components/TaskVisualizer';

export default function App() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('agent_api_key') || '');
  const [activeTaskId, setActiveTaskId] = useState(null);

  const handleSaveKey = (e) => {
    const key = e.target.value;
    setApiKey(key);
    localStorage.setItem('agent_api_key', key);
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center sticky top-0 z-10">
        <div className="flex items-center space-x-2 text-indigo-600">
          <Code2 size={24} />
          <span className="text-xl font-bold">Autonomous Engineer</span>
        </div>
        <div className="flex items-center space-x-3">
          <Settings size={18} className="text-gray-400" />
          <input
            type="password"
            placeholder="Enter API Key..."
            value={apiKey}
            onChange={handleSaveKey}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-64"
          />
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto py-10 px-6 space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900">
            What are we building today?
          </h1>
          <p className="text-lg text-gray-500">
            Submit an engineering goal, and the AI swarm will plan, code, and test it automatically.
          </p>
        </div>

        {/* Task Input Section */}
        <TaskSubmitter 
          apiKey={apiKey} 
          onTaskStarted={(taskId) => setActiveTaskId(taskId)} 
        />

        {/* Visualization Section */}
        {activeTaskId && (
          <TaskVisualizer 
            taskId={activeTaskId} 
            apiKey={apiKey} 
          />
        )}
      </main>
    </div>
  );
}