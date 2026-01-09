import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { LoadingSpinner } from '../components';
import { api } from '../api/client';
import type { TaskCategory, TaskPriority } from '../types';

export function AddPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [mode, setMode] = useState<'single' | 'bulk'>('single');
  const [taskText, setTaskText] = useState('');
  const [bulkTasks, setBulkTasks] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [category, setCategory] = useState<TaskCategory>('other');
  const [estimatedMinutes, setEstimatedMinutes] = useState(30);

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
        <h1 className="text-2xl font-serif italic gradient-text mb-2">Add Tasks</h1>
        <p className="text-[var(--karma-text-muted)]">
          Add tasks individually or import multiple at once
        </p>
      </div>

      {/* Mode Toggle */}
      <div className="flex justify-center gap-2">
        <button
          onClick={() => setMode('single')}
          className={`btn ${mode === 'single' ? 'btn-primary' : 'btn-secondary'}`}
        >
          Single Task
        </button>
        <button
          onClick={() => setMode('bulk')}
          className={`btn ${mode === 'bulk' ? 'btn-primary' : 'btn-secondary'}`}
        >
          Bulk Import
        </button>
      </div>

      {/* Single Task Form */}
      {mode === 'single' && (
        <form onSubmit={handleSubmitSingle} className="card space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">
              What do you need to do?
            </label>
            <input
              type="text"
              value={taskText}
              onChange={(e) => setTaskText(e.target.value)}
              placeholder="e.g., Review quarterly report"
              className="input"
              disabled={isLoading}
              autoFocus
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="input"
                disabled={isLoading}
              >
                <option value="low">🟢 Low</option>
                <option value="medium">🟡 Medium</option>
                <option value="high">🟠 High</option>
                <option value="urgent">🔴 Urgent</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as TaskCategory)}
                className="input"
                disabled={isLoading}
              >
                <option value="work">💼 Work</option>
                <option value="personal">🏠 Personal</option>
                <option value="health">🏃 Health</option>
                <option value="learning">📚 Learning</option>
                <option value="errands">🛒 Errands</option>
                <option value="creative">🎨 Creative</option>
                <option value="social">👥 Social</option>
                <option value="finance">💰 Finance</option>
                <option value="home">🏡 Home</option>
                <option value="other">📌 Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Estimated Time (min)
              </label>
              <input
                type="number"
                value={estimatedMinutes}
                onChange={(e) => setEstimatedMinutes(parseInt(e.target.value) || 30)}
                min={1}
                max={480}
                className="input"
                disabled={isLoading}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={!taskText.trim() || isLoading}
            className="btn btn-primary w-full"
          >
            {isLoading ? <LoadingSpinner size="sm" /> : 'Add Task'}
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
            className="btn btn-primary w-full"
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

