import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TaskCard, LoadingSpinner, EmptyState } from '../components';
import { api } from '../api/client';
import type { Task, TaskStatus, TaskPriority } from '../types';

type FilterStatus = 'all' | TaskStatus;
type SortBy = 'created' | 'priority' | 'time' | 'date';

export function BrowsePage() {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [sortBy, setSortBy] = useState<SortBy>('date');
  const [breakingDownTaskId, setBreakingDownTaskId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch all tasks
  const { data: tasks = [], isLoading, error } = useQuery({
    queryKey: ['tasks'],
    queryFn: api.getAllTasks,
  });

  // Update task status mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: TaskStatus }) =>
      api.updateTaskStatus(taskId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] }); // Also invalidate stats
    },
  });

  // Breakdown task mutation
  const breakdownMutation = useMutation({
    mutationFn: (taskId: string) => api.breakdownTask(taskId),
    onMutate: (taskId) => {
      setBreakingDownTaskId(taskId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onSettled: () => {
      setBreakingDownTaskId(null);
    },
  });

  // Update subtask status mutation
  const updateSubtaskMutation = useMutation({
    mutationFn: ({ taskId, subtaskId }: { taskId: string; subtaskId: string }) => {
      const task = tasks.find(t => t.id === taskId);
      const subtask = task?.subtasks.find(s => s.id === subtaskId);
      const newStatus = subtask?.status === 'completed' ? 'pending' : 'completed';
      return api.updateSubtaskStatus(taskId, subtaskId, newStatus);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Update subtask progress mutation
  const updateSubtaskProgressMutation = useMutation({
    mutationFn: ({ taskId, subtaskId, progress }: { taskId: string; subtaskId: string; progress: number }) => {
      return api.updateSubtaskProgress(taskId, subtaskId, progress);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Add subtask mutation
  const addSubtaskMutation = useMutation({
    mutationFn: ({ taskId, text }: { taskId: string; text: string }) => {
      return api.addSubtask(taskId, text);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Re-research mutation
  const reResearchMutation = useMutation({
    mutationFn: (taskId: string) => api.reResearchTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Delete all tasks mutation
  const deleteAllMutation = useMutation({
    mutationFn: () => api.deleteAllTasks(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowDeleteConfirm(false);
    },
  });

  // Delete single task mutation
  const deleteTaskMutation = useMutation({
    mutationFn: (taskId: string) => api.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Archive task mutation (mark as completed)
  const archiveTaskMutation = useMutation({
    mutationFn: (taskId: string) => api.updateTaskStatus(taskId, 'completed'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const filteredTasks = tasks
    .filter((task: Task) => {
      if (filterStatus !== 'all' && task.status !== filterStatus) return false;
      return true;
    })
    .sort((a: Task, b: Task) => {
      switch (sortBy) {
        case 'priority': {
          const priorityOrder: Record<TaskPriority, number> = { urgent: 0, high: 1, medium: 2, low: 3 };
          return priorityOrder[a.priority] - priorityOrder[b.priority];
        }
        case 'time':
          return a.estimated_minutes - b.estimated_minutes;
        case 'date':
          const dateA = a.created_at?.split('T')[0] || '';
          const dateB = b.created_at?.split('T')[0] || '';
          if (dateA !== dateB) return dateB.localeCompare(dateA);
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

  const tasksByDate = filteredTasks.reduce((acc: Record<string, Task[]>, task: Task) => {
    const date = task.created_at?.split('T')[0] || 'Unknown';
    if (!acc[date]) acc[date] = [];
    acc[date].push(task);
    return acc;
  }, {});

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (dateStr === today.toISOString().split('T')[0]) return 'Today';
    if (dateStr === yesterday.toISOString().split('T')[0]) return 'Yesterday';
    
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  if (isLoading) return <LoadingSpinner text="Loading tasks..." />;

  if (error) {
    return (
      <EmptyState
        icon="⚠️"
        title="Error loading tasks"
        description="Make sure the backend server is running on port 8000."
        actionLabel="Retry"
        onAction={() => queryClient.invalidateQueries({ queryKey: ['tasks'] })}
      />
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8 animate-fade-in max-w-4xl mx-auto px-4 sm:px-6">
      {/* Header */}
      <div className="flex items-end justify-between border-b border-gray-100 pb-3 sm:pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-serif text-gray-900">Your tasks</h1>
          <p className="text-gray-500 text-xs sm:text-sm mt-1">
            {filteredTasks.length} item{filteredTasks.length !== 1 ? 's' : ''} total
          </p>
        </div>
        {tasks.length > 0 && (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="text-xs sm:text-sm text-gray-400 hover:text-red-500 transition-colors flex items-center gap-1"
          >
            <span>🗑️</span>
            <span className="hidden sm:inline">Clear all</span>
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between gap-2 sm:gap-4 flex-wrap">
        <div className="flex gap-1 p-1 bg-gray-50 rounded-xl border border-gray-100 overflow-x-auto">
          {[
            { value: 'all' as FilterStatus, label: 'All' },
            { value: 'pending' as FilterStatus, label: 'To Do' },
            { value: 'in_progress' as FilterStatus, label: 'Doing' },
            { value: 'completed' as FilterStatus, label: 'Done' },
          ].map((status) => (
            <button
              key={status.value}
              onClick={() => setFilterStatus(status.value)}
              className={`px-3 sm:px-4 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap ${
                filterStatus === status.value
                  ? 'bg-white text-blue-600 shadow-sm border border-gray-100'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {status.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-xs sm:text-sm text-gray-500">
          <span className="hidden sm:inline">Sort by</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="bg-transparent border-none text-gray-900 font-medium cursor-pointer focus:outline-none hover:text-blue-600 text-xs sm:text-sm"
          >
            <option value="date">Date</option>
            <option value="priority">Priority</option>
            <option value="time">Time</option>
            <option value="created">Newest</option>
          </select>
        </div>
      </div>

      {/* Task List */}
      {filteredTasks.length === 0 ? (
        <EmptyState
          icon="📭"
          title="No tasks here"
          description={
            filterStatus === 'all'
              ? "Your list is empty. Add something to get started!"
              : "No tasks match this filter."
          }
          actionLabel="Add a task"
          actionPath="/add"
        />
      ) : sortBy === 'date' ? (
        <div className="space-y-10">
          {Object.entries(tasksByDate)
            .sort(([a], [b]) => b.localeCompare(a))
            .map(([date, dateTasks]) => (
              <div key={date} className="space-y-4">
                <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2 px-1">
                  {formatDate(date)}
                  <span className="h-px flex-1 bg-gray-100"></span>
                </h2>
                <div className="space-y-3">
                  {dateTasks.map((task: Task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onStatusChange={(taskId, status) => updateStatusMutation.mutate({ taskId, status })}
                      onSubtaskToggle={(taskId, subtaskId) => updateSubtaskMutation.mutate({ taskId, subtaskId })}
                      onSubtaskProgressChange={(taskId, subtaskId, progress) => 
                        updateSubtaskProgressMutation.mutate({ taskId, subtaskId, progress })
                      }
                      onAddSubtask={(taskId, text) => 
                        addSubtaskMutation.mutate({ taskId, text })
                      }
                      onBreakdown={(taskId) => breakdownMutation.mutate(taskId)}
                      onReResearch={(taskId) => reResearchMutation.mutate(taskId)}
                      onArchive={() => archiveTaskMutation.mutate(task.id)}
                      onDelete={(taskId) => deleteTaskMutation.mutate(taskId)}
                      isLoading={breakingDownTaskId === task.id}
                    />
                  ))}
                </div>
              </div>
            ))}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task: Task) => (
            <TaskCard
              key={task.id}
              task={task}
              onStatusChange={(taskId, status) => updateStatusMutation.mutate({ taskId, status })}
              onSubtaskToggle={(taskId, subtaskId) => updateSubtaskMutation.mutate({ taskId, subtaskId })}
              onSubtaskProgressChange={(taskId, subtaskId, progress) => 
                updateSubtaskProgressMutation.mutate({ taskId, subtaskId, progress })
              }
              onAddSubtask={(taskId, text) => 
                addSubtaskMutation.mutate({ taskId, text })
              }
              onBreakdown={(taskId) => breakdownMutation.mutate(taskId)}
              onReResearch={(taskId) => reResearchMutation.mutate(taskId)}
              onArchive={() => archiveTaskMutation.mutate(task.id)}
              onDelete={(taskId) => deleteTaskMutation.mutate(taskId)}
              isLoading={breakingDownTaskId === task.id}
            />
          ))}
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-gray-900/20 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 sm:p-8 max-w-sm w-full shadow-2xl border border-gray-100">
            <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-2">Clear all tasks?</h3>
            <p className="text-sm sm:text-base text-gray-500 mb-6 sm:mb-8 leading-relaxed">
              This will permanently delete all your tasks. This action cannot be undone.
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-4 py-2.5 rounded-xl font-medium text-gray-600 hover:bg-gray-50 transition-colors text-sm sm:text-base"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteAllMutation.mutate()}
                disabled={deleteAllMutation.isPending}
                className="flex-1 px-4 py-2.5 rounded-xl font-medium bg-red-500 text-white hover:bg-red-600 transition-colors shadow-lg shadow-red-200 text-sm sm:text-base"
              >
                {deleteAllMutation.isPending ? 'Clearing...' : 'Yes, clear all'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
