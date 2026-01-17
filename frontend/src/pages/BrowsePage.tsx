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
      // Find the current subtask status and toggle it
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

  // Filter and sort tasks
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
          // Sort by date (newest first), then by created_at within same date
          const dateA = a.created_at?.split('T')[0] || '';
          const dateB = b.created_at?.split('T')[0] || '';
          if (dateA !== dateB) return dateB.localeCompare(dateA);
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'created':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

  // Group tasks by date for display
  const tasksByDate = filteredTasks.reduce((acc: Record<string, Task[]>, task: Task) => {
    const date = task.created_at?.split('T')[0] || 'Unknown';
    if (!acc[date]) acc[date] = [];
    acc[date].push(task);
    return acc;
  }, {});

  // Format date for display
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

  const handleStatusChange = (taskId: string, status: TaskStatus) => {
    updateStatusMutation.mutate({ taskId, status });
  };

  const handleSubtaskToggle = (taskId: string, subtaskId: string) => {
    updateSubtaskMutation.mutate({ taskId, subtaskId });
  };

  const handleBreakdown = (taskId: string) => {
    breakdownMutation.mutate(taskId);
  };

  const handleReResearch = (taskId: string) => {
    reResearchMutation.mutate(taskId);
  };

  if (isLoading) {
    return <LoadingSpinner text="Loading tasks..." />;
  }

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
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-serif gradient-text">Your Tasks</h1>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-sm font-medium">
            {filteredTasks.length} task{filteredTasks.length !== 1 ? 's' : ''}
          </span>
          {tasks.length > 0 && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="text-sm text-red-500 hover:text-red-700 hover:underline"
            >
              🗑️ Delete All
            </button>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md mx-4 shadow-2xl">
            <h3 className="text-xl font-semibold mb-2">Delete All Tasks?</h3>
            <p className="text-gray-600 mb-6">
              This will permanently delete all {tasks.length} tasks.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteAllMutation.mutate()}
                disabled={deleteAllMutation.isPending}
                className="flex-1 btn bg-red-500 text-white hover:bg-red-600"
              >
                {deleteAllMutation.isPending ? 'Deleting...' : 'Delete All'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Simple Filter Bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Status Tabs */}
        <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
          {[
            { value: 'all' as FilterStatus, label: 'All' },
            { value: 'pending' as FilterStatus, label: 'To Do' },
            { value: 'in_progress' as FilterStatus, label: 'Doing' },
            { value: 'completed' as FilterStatus, label: 'Done' },
          ].map((status) => (
            <button
              key={status.value}
              onClick={() => setFilterStatus(status.value)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                filterStatus === status.value
                  ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-200'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              {status.label}
            </button>
          ))}
        </div>

        {/* Sort Toggle */}
        <div className="flex items-center gap-2 ml-auto text-sm text-gray-500">
          <span>Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="bg-transparent border-none text-blue-600 font-medium cursor-pointer focus:outline-none hover:text-blue-700"
          >
            <option value="date">Date</option>
            <option value="priority">Priority</option>
            <option value="time">Duration</option>
            <option value="created">Newest</option>
          </select>
        </div>
      </div>

      {/* Task List */}
      {filteredTasks.length === 0 ? (
        <EmptyState
          icon="📭"
          title="No tasks found"
          description={
            filterStatus === 'all'
              ? "You haven't added any tasks yet. Start by adding some!"
              : "No tasks match your current filter."
          }
          actionLabel="Add Tasks"
          actionPath="/add"
        />
      ) : sortBy === 'date' ? (
        // Grouped by date view
        <div className="space-y-6">
          {Object.entries(tasksByDate)
            .sort(([a], [b]) => b.localeCompare(a))
            .map(([date, dateTasks]) => (
              <div key={date}>
                <h2 className="text-lg font-semibold text-blue-600 mb-3 flex items-center gap-2">
                  <span>📅</span>
                  {formatDate(date)}
                  <span className="text-sm font-normal text-gray-500">
                    ({dateTasks.length} task{dateTasks.length !== 1 ? 's' : ''})
                  </span>
                </h2>
                <div className="space-y-3">
                  {dateTasks.map((task: Task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onStatusChange={handleStatusChange}
                      onSubtaskToggle={handleSubtaskToggle}
                      onSubtaskProgressChange={(taskId, subtaskId, progress) => 
                        updateSubtaskProgressMutation.mutate({ taskId, subtaskId, progress })
                      }
                      onAddSubtask={(taskId, text) => 
                        addSubtaskMutation.mutate({ taskId, text })
                      }
                      onBreakdown={handleBreakdown}
                      onReResearch={handleReResearch}
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
        // Flat list view
        <div className="space-y-4">
          {filteredTasks.map((task: Task, index: number) => (
            <div
              key={task.id}
              className={`animate-fade-in stagger-${Math.min(index + 1, 5)}`}
              style={{ opacity: 0 }}
            >
              <TaskCard
                task={task}
                onStatusChange={handleStatusChange}
                onSubtaskToggle={handleSubtaskToggle}
                onSubtaskProgressChange={(taskId, subtaskId, progress) => 
                  updateSubtaskProgressMutation.mutate({ taskId, subtaskId, progress })
                }
                onAddSubtask={(taskId, text) => 
                  addSubtaskMutation.mutate({ taskId, text })
                }
                onBreakdown={handleBreakdown}
                onReResearch={handleReResearch}
                onArchive={() => archiveTaskMutation.mutate(task.id)}
                onDelete={(taskId) => deleteTaskMutation.mutate(taskId)}
                isLoading={breakingDownTaskId === task.id}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

