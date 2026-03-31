import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, CheckCircle2, CircleDashed } from 'lucide-react';

export default function TaskVisualizer({ taskId, apiKey }) {
  const [taskData, setTaskData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Polling mechanism to fetch status every 3 seconds
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`http://localhost:8000/api/v1/tasks/${taskId}`, {
          headers: { 'X-API-Key': apiKey }
        });
        setTaskData(response.data);
      } catch (err) {
        setError("Lost connection to the execution engine.");
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [taskId, apiKey]);

  if (error) return <div className="text-red-500 text-center p-4">{error}</div>;
  if (!taskData) return <div className="text-gray-500 text-center p-4 animate-pulse">Establishing telemetry...</div>;

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 space-y-6">
      <div className="flex justify-between items-center border-b border-gray-100 pb-4">
        <h2 className="text-lg font-bold text-gray-800 flex items-center">
          <Activity size={20} className="mr-2 text-indigo-600" />
          Active Execution Graph
        </h2>
        <span className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded-full uppercase tracking-wider">
          {taskData.status} ({taskData.progress_percentage}%)
        </span>
      </div>

      {/* Node Visualization */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-500 uppercase">Current Operations</h3>
        {taskData.active_nodes?.length > 0 ? (
          taskData.active_nodes.map((node, idx) => (
            <div key={idx} className="flex items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
              <CircleDashed size={18} className="text-indigo-500 animate-spin mr-3" />
              <span className="text-gray-700 font-medium">{node}</span>
            </div>
          ))
        ) : (
          <div className="flex items-center p-3 bg-green-50 rounded-lg border border-green-100">
            <CheckCircle2 size={18} className="text-green-600 mr-3" />
            <span className="text-green-800 font-medium">All operations completed successfully.</span>
          </div>
        )}
      </div>
    </div>
  );
}