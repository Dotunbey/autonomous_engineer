import React, { useState } from 'react';
import axios from 'axios';
import { Play, Loader2, AlertCircle } from 'lucide-react';

export default function TaskSubmitter({ apiKey, onTaskStarted }) {
  const [goal, setGoal] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!goal.trim()) return;
    if (!apiKey) {
      setError("Please enter your API key in the top right corner.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Connects to the FastAPI endpoint we built earlier
      const response = await axios.post(
        'http://localhost:8000/api/v1/tasks/',
        { goal, workspace_dir: './workspace' },
        { headers: { 'X-API-Key': apiKey } }
      );
      
      onTaskStarted(response.data.task_id);
      setGoal('');
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to connect to the Autonomous Engineer API.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
      <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g., Build a Python script that scrapes HackerNews and saves the top 10 articles to a CSV..."
          className="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none h-32"
          disabled={isSubmitting}
        />
        
        {error && (
          <div className="flex items-center text-red-600 bg-red-50 p-3 rounded-md text-sm">
            <AlertCircle size={16} className="mr-2" />
            {error}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting || !goal.trim()}
            className="flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? (
              <><Loader2 size={18} className="animate-spin mr-2" /> Initializing Swarm...</>
            ) : (
              <><Play size={18} className="mr-2" /> Deploy Engineer</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}