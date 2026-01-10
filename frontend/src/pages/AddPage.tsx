import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { LoadingSpinner } from '../components';
import { api } from '../api/client';
import type { TaskCategory, TaskPriority } from '../types';

type EnergyLevel = 'very_low' | 'low' | 'medium' | 'high' | 'very_high';

export function AddPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [mode, setMode] = useState<'single' | 'bulk'>('single');
  const [taskText, setTaskText] = useState('');
  const [bulkTasks, setBulkTasks] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [category, setCategory] = useState<TaskCategory>('other');
  const [estimatedMinutes, setEstimatedMinutes] = useState(15);
  const [energyLevel, setEnergyLevel] = useState<EnergyLevel>('medium');

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

          {/* Time Available */}
          <div>
            <label className="block text-sm font-medium mb-3">
              ⏱️ How much time do you have?
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

          {/* Energy Level */}
          <div>
            <label className="block text-sm font-medium mb-3">
              ⚡ How's your energy level?
            </label>
            <div className="grid grid-cols-5 gap-2">
              {[
                { value: 'very_low' as EnergyLevel, label: '😵', desc: 'Exhausted' },
                { value: 'low' as EnergyLevel, label: '😴', desc: 'Tired' },
                { value: 'medium' as EnergyLevel, label: '😊', desc: 'Normal' },
                { value: 'high' as EnergyLevel, label: '😄', desc: 'Good' },
                { value: 'very_high' as EnergyLevel, label: '🔥', desc: 'Energized' },
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setEnergyLevel(option.value)}
                  className={`py-3 px-2 rounded-lg border transition-all text-center ${
                    energyLevel === option.value
                      ? 'bg-[var(--karma-accent)] text-white border-[var(--karma-accent)]'
                      : 'border-[var(--karma-border)] hover:border-[var(--karma-accent)]'
                  }`}
                >
                  <div className="text-xl">{option.label}</div>
                  <div className="text-xs mt-1 opacity-80">{option.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Category & Priority Row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">📁 Category</label>
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
              <label className="block text-sm font-medium mb-2">🎯 Priority</label>
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
          </div>

          <button
            type="submit"
            disabled={!taskText.trim() || isLoading}
            className="btn btn-primary w-full"
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

