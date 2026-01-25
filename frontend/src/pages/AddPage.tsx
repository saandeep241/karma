import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { LoadingSpinner } from '../components';
import { api } from '../api/client';
import type { TaskCategory } from '../types';

const CATEGORIES: { value: TaskCategory; label: string; icon: string }[] = [
  { value: 'work', label: 'Work', icon: '💼' },
  { value: 'personal', label: 'Personal', icon: '🏠' },
  { value: 'health', label: 'Health', icon: '🏃' },
  { value: 'learning', label: 'Learning', icon: '📚' },
  { value: 'errands', label: 'Errands', icon: '🛒' },
  { value: 'creative', label: 'Creative', icon: '🎨' },
  { value: 'social', label: 'Social', icon: '👥' },
  { value: 'finance', label: 'Finance', icon: '💰' },
  { value: 'home', label: 'Home', icon: '🏡' },
  { value: 'other', label: 'Other', icon: '📌' },
];

export function AddPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [mode, setMode] = useState<'single' | 'bulk'>('single');
  const [taskText, setTaskText] = useState('');
  const [bulkTasks, setBulkTasks] = useState('');
  const [category, setCategory] = useState<TaskCategory>('other');
  const [estimatedMinutes, setEstimatedMinutes] = useState(15);
  const [dueDate, setDueDate] = useState<string>(new Date().toISOString().split('T')[0]);

  const addTaskMutation = useMutation({
    mutationFn: () => api.addTask({
      text: taskText,
      priority: 'medium',
      category,
      estimated_minutes: estimatedMinutes,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      navigate('/browse');
    },
  });

  const importTasksMutation = useMutation({
    mutationFn: (texts: string[]) => api.importTasks(texts),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      navigate('/browse');
    },
  });

  const handleSubmitSingle = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskText.trim()) return;
    addTaskMutation.mutate();
  };

  const handleSubmitBulk = (e: React.FormEvent) => {
    e.preventDefault();
    const tasks = bulkTasks.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    if (tasks.length === 0) return;
    importTasksMutation.mutate(tasks);
  };

  const isLoading = addTaskMutation.isPending || importTasksMutation.isPending;

  return (
    <div className="max-w-xl mx-auto space-y-10 animate-fade-in py-8">
      <div className="text-center">
        <h1 className="text-4xl font-serif text-gray-900 mb-2">New Task</h1>
        <p className="text-gray-500">What's on your mind?</p>
      </div>

      <div className="flex justify-center gap-1 p-1 bg-gray-50 rounded-xl border border-gray-100 max-w-xs mx-auto">
        <button
          onClick={() => setMode('single')}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
            mode === 'single' ? 'bg-white text-blue-600 shadow-sm border border-gray-100' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Single
        </button>
        <button
          onClick={() => setMode('bulk')}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
            mode === 'bulk' ? 'bg-white text-blue-600 shadow-sm border border-gray-100' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Bulk Import
        </button>
      </div>

      {mode === 'single' ? (
        <form onSubmit={handleSubmitSingle} className="space-y-8 bg-white p-8 rounded-3xl border border-gray-100 shadow-xl shadow-gray-100/50">
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">The task</label>
            <textarea
              value={taskText}
              onChange={(e) => setTaskText(e.target.value)}
              placeholder="What needs to be done?"
              className="w-full p-4 rounded-2xl border border-gray-100 bg-gray-50 focus:bg-white focus:border-blue-200 focus:outline-none focus:ring-4 focus:ring-blue-50 transition-all resize-none text-lg"
              rows={2}
              disabled={isLoading}
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">When</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full p-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-50 transition-all text-sm"
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Time (mins)</label>
              <div className="flex gap-2">
                {[15, 30, 60].map(mins => (
                  <button
                    key={mins}
                    type="button"
                    onClick={() => setEstimatedMinutes(mins)}
                    className={`flex-1 py-2.5 rounded-xl text-sm font-medium border transition-all ${
                      estimatedMinutes === mins ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-50 text-gray-500 border-gray-100 hover:border-blue-200'
                    }`}
                  >
                    {mins}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Category</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.slice(0, 5).map(cat => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setCategory(cat.value)}
                  className={`px-4 py-2 rounded-full border text-sm transition-all flex items-center gap-2 ${
                    category === cat.value ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-50 text-gray-500 border-gray-100 hover:border-gray-200'
                  }`}
                >
                  <span>{cat.icon}</span>
                  <span>{cat.label}</span>
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={!taskText.trim() || isLoading}
            className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-lg shadow-blue-200 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? <LoadingSpinner size="sm" /> : 'Create task'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleSubmitBulk} className="space-y-6 bg-white p-8 rounded-3xl border border-gray-100 shadow-xl shadow-gray-100/50">
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-widest ml-1">Bulk entry</label>
            <textarea
              value={bulkTasks}
              onChange={(e) => setBulkTasks(e.target.value)}
              placeholder="Task one&#10;Task two&#10;Task three..."
              rows={8}
              className="w-full p-4 rounded-2xl border border-gray-100 bg-gray-50 focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-50 transition-all resize-none font-mono text-sm"
              disabled={isLoading}
              autoFocus
            />
            <p className="text-[10px] text-gray-400 italic ml-1">AI will automatically categorize and prioritize these for you.</p>
          </div>

          <button
            type="submit"
            disabled={!bulkTasks.trim() || isLoading}
            className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-lg shadow-blue-200 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? <LoadingSpinner size="sm" /> : `Import ${bulkTasks.split('\n').filter(l => l.trim()).length} tasks`}
          </button>
        </form>
      )}
    </div>
  );
}
