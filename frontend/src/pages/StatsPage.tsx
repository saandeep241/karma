import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { LoadingSpinner, EmptyState } from '../components';
import { api } from '../api/client';
import type { TaskCategory, TaskPriority } from '../types';

const categoryLabels: Record<TaskCategory, string> = {
  work: '💼 Work',
  personal: '🏠 Personal',
  health: '🏃 Health',
  learning: '📚 Learning',
  errands: '🛒 Errands',
  creative: '🎨 Creative',
  social: '👥 Social',
  finance: '💰 Finance',
  home: '🏡 Home',
  other: '📌 Other',
};

const priorityLabels: Record<TaskPriority, string> = {
  low: '🟢 Low',
  medium: '🟡 Medium',
  high: '🟠 High',
  urgent: '🔴 Urgent',
};

export function StatsPage() {
  const queryClient = useQueryClient();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch stats
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
  });

  // Delete all tasks mutation
  const deleteAllMutation = useMutation({
    mutationFn: api.deleteAllTasks,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      setShowDeleteConfirm(false);
    },
  });

  if (isLoading) {
    return <LoadingSpinner text="Loading stats..." />;
  }

  if (error) {
    return (
      <EmptyState
        icon="⚠️"
        title="Error loading stats"
        description="Make sure the backend server is running."
        actionLabel="Retry"
        onAction={() => queryClient.invalidateQueries({ queryKey: ['stats'] })}
      />
    );
  }

  if (!stats) {
    return (
      <EmptyState
        icon="📊"
        title="No stats yet"
        description="Complete some tasks to see your productivity stats!"
        actionLabel="Browse Tasks"
        actionPath="/browse"
      />
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-serif gradient-text mb-2">
          Your Productivity Stats
        </h1>
        <p className="text-[var(--karma-text-muted)]">
          Track your progress and celebrate your wins
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <div className="text-3xl font-bold gradient-text">{stats.total_tasks}</div>
          <div className="text-sm text-[var(--karma-text-muted)]">Total Tasks</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-[var(--karma-success)]">
            {stats.completed_tasks}
          </div>
          <div className="text-sm text-[var(--karma-text-muted)]">Completed</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-[var(--karma-warning)]">
            {stats.pending_tasks}
          </div>
          <div className="text-sm text-[var(--karma-text-muted)]">Pending</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-[var(--karma-accent)]">
            {Math.round(stats.completion_rate)}%
          </div>
          <div className="text-sm text-[var(--karma-text-muted)]">Completion Rate</div>
        </div>
      </div>

      {/* Completion Progress */}
      <div className="card">
        <h3 className="font-medium mb-4">Overall Progress</h3>
        <div className="progress-bar h-4">
          <div
            className="progress-bar-fill"
            style={{ width: `${stats.completion_rate}%` }}
          />
        </div>
        <div className="flex justify-between text-sm text-[var(--karma-text-muted)] mt-2">
          <span>{stats.completed_tasks} completed</span>
          <span>{stats.pending_tasks} remaining</span>
        </div>
      </div>

      {/* Category Breakdown */}
      {stats.tasks_by_category && Object.keys(stats.tasks_by_category).length > 0 && (
        <div className="card">
          <h3 className="font-medium mb-4">Tasks by Category</h3>
          <div className="space-y-3">
            {Object.entries(stats.tasks_by_category)
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .map(([category, count]) => (
                <div key={category} className="flex items-center gap-3">
                  <span className="w-32 text-sm">
                    {categoryLabels[category as TaskCategory] || category}
                  </span>
                  <div className="flex-1 progress-bar h-2">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${((count as number) / stats.total_tasks) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm text-[var(--karma-text-muted)] w-8 text-right">
                    {count as number}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Priority Breakdown */}
      {stats.tasks_by_priority && Object.keys(stats.tasks_by_priority).length > 0 && (
        <div className="card">
          <h3 className="font-medium mb-4">Tasks by Priority</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {(['urgent', 'high', 'medium', 'low'] as TaskPriority[]).map((priority) => (
              <div key={priority} className="text-center p-3 bg-[var(--karma-surface-hover)] rounded-lg">
                <div className="text-2xl font-bold">
                  {stats.tasks_by_priority[priority] || 0}
                </div>
                <div className="text-sm text-[var(--karma-text-muted)]">
                  {priorityLabels[priority]}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Average Completion Time */}
      {stats.average_completion_time_minutes > 0 && (
        <div className="card text-center">
          <div className="text-4xl mb-2">⏱️</div>
          <div className="text-2xl font-bold">
            {Math.round(stats.average_completion_time_minutes)} min
          </div>
          <div className="text-sm text-[var(--karma-text-muted)]">
            Average task completion time
          </div>
        </div>
      )}

      {/* Danger Zone */}
      <div className="card border-red-500/30">
        <h3 className="font-medium mb-4 text-red-400">Danger Zone</h3>
        <p className="text-sm text-[var(--karma-text-muted)] mb-4">
          This action cannot be undone. All tasks will be permanently deleted.
        </p>
        
        {showDeleteConfirm ? (
          <div className="flex gap-3">
            <button
              onClick={() => deleteAllMutation.mutate()}
              disabled={deleteAllMutation.isPending}
              className="btn bg-red-500 hover:bg-red-600 text-white"
            >
              {deleteAllMutation.isPending ? (
                <LoadingSpinner size="sm" />
              ) : (
                'Yes, Delete All'
              )}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="btn btn-secondary border-red-500/30 text-red-400 hover:bg-red-500/10"
          >
            🗑️ Delete All Tasks
          </button>
        )}
      </div>
    </div>
  );
}

