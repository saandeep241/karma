import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { LoadingSpinner } from '../components';
import { api } from '../api/client';
import type { TaskCategory, TaskPriority } from '../types';

// Category options with icons
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

// Priority options with colors
const PRIORITIES: { value: TaskPriority; label: string; color: string }[] = [
  { value: 'low', label: 'Low', color: 'bg-green-500' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-500' },
  { value: 'high', label: 'High', color: 'bg-orange-500' },
  { value: 'urgent', label: 'Urgent', color: 'bg-red-500' },
];

export function AddPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [mode, setMode] = useState<'single' | 'bulk'>('single');
  const [taskText, setTaskText] = useState('');
  const [bulkTasks, setBulkTasks] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [category, setCategory] = useState<TaskCategory>('other');
  const [estimatedMinutes, setEstimatedMinutes] = useState(15);
  const [dueDate, setDueDate] = useState<string>(new Date().toISOString().split('T')[0]);

  // Add single task mutation
  const addTaskMutation = useMutation({
    mutationFn: () => api.addTask({
      text: taskText,
      priority,
      category,
      estimated_minutes: estimatedMinutes,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setTaskText('');
      navigate('/browse');
    },
  });

  // Import bulk tasks mutation
  const importTasksMutation = useMutation({
    mutationFn: (texts: string[]) => api.importTasks(texts),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setBulkTasks('');
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
    const tasks = bulkTasks
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);
    
    if (tasks.length === 0) return;
    importTasksMutation.mutate(tasks);
  };

  const isLoading = addTaskMutation.isPending || importTasksMutation.isPending;

  return (
    <div className="max-w-2xl mx-auto space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-serif gradient-text mb-2">Add Tasks</h1>
        <p className="text-gray-500">
          Add tasks individually or import multiple at once
        </p>
      </div>

      {/* Mode Toggle */}
      <div className="flex justify-center gap-2">
        <button
          onClick={() => setMode('single')}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            mode === 'single'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Single Task
        </button>
        <button
          onClick={() => setMode('bulk')}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            mode === 'bulk'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Bulk Import
        </button>
      </div>

      {/* Single Task Form */}
      {mode === 'single' && (
        <form onSubmit={handleSubmitSingle} className="card space-y-6">
          {/* Task Description */}
          <div>
            <label className="block text-sm font-medium mb-2">
              ✏️ What do you need to do?
            </label>
            <textarea
              value={taskText}
              onChange={(e) => setTaskText(e.target.value)}
              placeholder="e.g., Review quarterly report"
              className="w-full p-3 rounded-lg border border-[var(--karma-border)] bg-white focus:border-[var(--karma-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--karma-accent)]/20 resize-none"
              rows={2}
              disabled={isLoading}
              autoFocus
            />
          </div>

          {/* Due Date - Date Picker */}
          <div>
            <label className="block text-sm font-medium mb-2">
              📅 When do you want to do this?
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full p-3 rounded-lg border border-[var(--karma-border)] bg-white focus:border-[var(--karma-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--karma-accent)]/20"
              disabled={isLoading}
            />
            <div className="flex gap-2 mt-2">
              <button
                type="button"
                onClick={() => setDueDate(new Date().toISOString().split('T')[0])}
                className={`text-xs px-3 py-1 rounded-full border transition-all ${
                  dueDate === new Date().toISOString().split('T')[0]
                    ? 'bg-[var(--karma-accent)] text-white border-[var(--karma-accent)]'
                    : 'border-[var(--karma-border)] hover:border-[var(--karma-accent)]'
                }`}
              >
                Today
              </button>
              <button
                type="button"
                onClick={() => {
                  const tomorrow = new Date();
                  tomorrow.setDate(tomorrow.getDate() + 1);
                  setDueDate(tomorrow.toISOString().split('T')[0]);
                }}
                className={`text-xs px-3 py-1 rounded-full border transition-all ${
                  dueDate === (() => { const d = new Date(); d.setDate(d.getDate() + 1); return d.toISOString().split('T')[0]; })()
                    ? 'bg-[var(--karma-accent)] text-white border-[var(--karma-accent)]'
                    : 'border-[var(--karma-border)] hover:border-[var(--karma-accent)]'
                }`}
              >
                Tomorrow
              </button>
              <button
                type="button"
                onClick={() => {
                  const nextWeek = new Date();
                  nextWeek.setDate(nextWeek.getDate() + 7);
                  setDueDate(nextWeek.toISOString().split('T')[0]);
                }}
                className="text-xs px-3 py-1 rounded-full border border-[var(--karma-border)] hover:border-[var(--karma-accent)] transition-all"
              >
                Next Week
              </button>
            </div>
          </div>

          {/* Time Estimate */}
          <div>
            <label className="block text-sm font-medium mb-3">
              ⏱️ Estimated time
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[5, 15, 30, 60].map((mins) => (
                <button
                  key={mins}
                  type="button"
                  onClick={() => setEstimatedMinutes(mins)}
                  className={`py-2 px-3 rounded-lg border transition-all ${
                    estimatedMinutes === mins
                      ? 'bg-[var(--karma-accent)] text-white border-[var(--karma-accent)]'
                      : 'border-[var(--karma-border)] hover:border-[var(--karma-accent)]'
                  }`}
                >
                  {mins} min
                </button>
              ))}
            </div>
          </div>

          {/* Category - Chips/Tags */}
          <div>
            <label className="block text-sm font-medium mb-3">
              📁 Category
            </label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setCategory(cat.value)}
                  disabled={isLoading}
                  className={`px-3 py-2 rounded-full border transition-all text-sm flex items-center gap-1 ${
                    category === cat.value
                      ? 'bg-[var(--karma-accent)] text-white border-[var(--karma-accent)]'
                      : 'border-[var(--karma-border)] hover:border-[var(--karma-accent)] hover:bg-[var(--karma-bg-secondary)]'
                  }`}
                >
                  <span>{cat.icon}</span>
                  <span>{cat.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Priority - Visual Buttons */}
          <div>
            <label className="block text-sm font-medium mb-3">
              🎯 Priority
            </label>
            <div className="grid grid-cols-4 gap-2">
              {PRIORITIES.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setPriority(p.value)}
                  disabled={isLoading}
                  className={`py-3 px-4 rounded-lg border transition-all text-center ${
                    priority === p.value
                      ? 'border-[var(--karma-accent)] ring-2 ring-[var(--karma-accent)]/30'
                      : 'border-[var(--karma-border)] hover:border-[var(--karma-accent)]'
                  }`}
                >
                  <div className={`w-3 h-3 rounded-full ${p.color} mx-auto mb-1`} />
                  <div className="text-sm font-medium">{p.label}</div>
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={!taskText.trim() || isLoading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? <LoadingSpinner size="sm" /> : '✓ Add Task'}
          </button>
        </form>
      )}

      {/* Bulk Import Form */}
      {mode === 'bulk' && (
        <form onSubmit={handleSubmitBulk} className="card space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">
              Enter tasks (one per line)
            </label>
            <textarea
              value={bulkTasks}
              onChange={(e) => setBulkTasks(e.target.value)}
              placeholder={`Review quarterly report
Schedule team meeting
Update project documentation
Send invoice to client`}
              rows={8}
              className="input resize-none"
              disabled={isLoading}
              autoFocus
            />
            <p className="text-xs text-[var(--karma-text-muted)] mt-2">
              AI will analyze each task and suggest priority, category, and time estimates
            </p>
          </div>

          <button
            type="submit"
            disabled={!bulkTasks.trim() || isLoading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <LoadingSpinner size="sm" text="Analyzing tasks..." />
            ) : (
              `Import ${bulkTasks.split('\n').filter(l => l.trim()).length || 0} Tasks`
            )}
          </button>
        </form>
      )}

      {/* Error Display */}
      {(addTaskMutation.error || importTasksMutation.error) && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {(addTaskMutation.error || importTasksMutation.error)?.message || 'An error occurred'}
        </div>
      )}
    </div>
  );
}

