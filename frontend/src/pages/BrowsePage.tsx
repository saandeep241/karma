import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TaskCard, LoadingSpinner, EmptyState } from '../components';
import { api } from '../api/client';
import type { Task, TaskStatus, TaskCategory, TaskPriority } from '../types';

type FilterStatus = 'all' | TaskStatus;
type SortBy = 'created' | 'priority' | 'time' | 'date';
type ViewTab = 'all' | 'work' | 'personal';

// Status filter options
const STATUS_FILTERS: { value: FilterStatus; label: string; icon: string }[] = [
  { value: 'all', label: 'All', icon: '📋' },
  { value: 'pending', label: 'Pending', icon: '⏳' },
  { value: 'in_progress', label: 'In Progress', icon: '🔄' },
  { value: 'completed', label: 'Done', icon: '✅' },
];

// Category filter options
const CATEGORY_FILTERS: { value: TaskCategory | 'all'; label: string; icon: string }[] = [
  { value: 'all', label: 'All', icon: '📁' },
  { value: 'work', label: 'Work', icon: '💼' },
  { value: 'personal', label: 'Personal', icon: '🏠' },
  { value: 'health', label: 'Health', icon: '🏃' },
  { value: 'learning', label: 'Learning', icon: '📚' },
  { value: 'errands', label: 'Errands', icon: '🛒' },
  { value: 'creative', label: 'Creative', icon: '🎨' },
  { value: 'social', label: 'Social', icon: '👥' },
  { value: 'finance', label: 'Finance', icon: '💰' },
  { value: 'home', label: 'Home', icon: '🏡' },
];

// Sort options
const SORT_OPTIONS: { value: SortBy; label: string; icon: string }[] = [
  { value: 'date', label: 'Date', icon: '📅' },
  { value: 'created', label: 'Newest', icon: '🕐' },
  { value: 'priority', label: 'Priority', icon: '🎯' },
  { value: 'time', label: 'Time', icon: '⏱️' },
];

export function BrowsePage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<ViewTab>('all');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [filterCategory, setFilterCategory] = useState<TaskCategory | 'all'>('all');
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

  // Archive task mutation (mark as completed)
  const archiveTaskMutation = useMutation({
    mutationFn: (taskId: string) => api.updateTaskStatus(taskId, 'completed'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Helper to check if task is work-related
  const isWorkTask = (task: Task) => 
    task.category === 'work' || task.category === 'finance';

  // Helper to check if task is personal
  const isPersonalTask = (task: Task) => 
    !isWorkTask(task);

  // Filter and sort tasks
  const filteredTasks = tasks
    .filter((task: Task) => {
      // Tab filter (Work/Personal)
      if (activeTab === 'work' && !isWorkTask(task)) return false;
      if (activeTab === 'personal' && !isPersonalTask(task)) return false;
      
      if (filterStatus !== 'all' && task.status !== filterStatus) return false;
      if (filterCategory !== 'all' && task.category !== filterCategory) return false;
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
          <span className="badge badge-accent">
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
            <h3 className="text-xl font-semibold mb-2">⚠️ Delete All Tasks?</h3>
            <p className="text-gray-600 mb-6">
              This will permanently delete all {tasks.length} tasks. This action cannot be undone.
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

      {/* Work / Personal Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--karma-surface)] rounded-lg w-fit">
        {[
          { value: 'all' as ViewTab, label: '📋 All', count: tasks.length },
          { value: 'work' as ViewTab, label: '💼 Work', count: tasks.filter(isWorkTask).length },
          { value: 'personal' as ViewTab, label: '🏠 Personal', count: tasks.filter(isPersonalTask).length },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`px-4 py-2 rounded-md transition-all text-sm font-medium ${
              activeTab === tab.value
                ? 'bg-[var(--karma-accent)] text-white shadow'
                : 'text-[var(--karma-text-muted)] hover:text-[var(--karma-text)]'
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* Status Filter - Chips */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-[var(--karma-text-muted)] uppercase tracking-wide">Status</label>
        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((status) => (
            <button
              key={status.value}
              onClick={() => setFilterStatus(status.value)}
              className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-1.5 transition-all ${
                filterStatus === status.value
                  ? 'bg-[var(--karma-accent)] text-white shadow-sm'
                  : 'bg-[var(--karma-surface)] text-[var(--karma-text-muted)] hover:bg-[var(--karma-bg-secondary)] border border-[var(--karma-border)]'
              }`}
            >
              <span>{status.icon}</span>
              <span>{status.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Category Filter - Scrollable Chips */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-[var(--karma-text-muted)] uppercase tracking-wide">Category</label>
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
          {CATEGORY_FILTERS.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setFilterCategory(cat.value)}
              className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-1.5 whitespace-nowrap transition-all ${
                filterCategory === cat.value
                  ? 'bg-[var(--karma-accent)] text-white shadow-sm'
                  : 'bg-[var(--karma-surface)] text-[var(--karma-text-muted)] hover:bg-[var(--karma-bg-secondary)] border border-[var(--karma-border)]'
              }`}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Sort - Chips */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-[var(--karma-text-muted)] uppercase tracking-wide">Sort by</label>
        <div className="flex flex-wrap gap-2">
          {SORT_OPTIONS.map((sort) => (
            <button
              key={sort.value}
              onClick={() => setSortBy(sort.value)}
              className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-1.5 transition-all ${
                sortBy === sort.value
                  ? 'bg-[var(--karma-accent)] text-white shadow-sm'
                  : 'bg-[var(--karma-surface)] text-[var(--karma-text-muted)] hover:bg-[var(--karma-bg-secondary)] border border-[var(--karma-border)]'
              }`}
            >
              <span>{sort.icon}</span>
              <span>{sort.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Task List */}
      {filteredTasks.length === 0 ? (
        <EmptyState
          icon="📭"
          title="No tasks found"
          description={
            filterStatus === 'all' && filterCategory === 'all' && activeTab === 'all'
              ? "You haven't added any tasks yet. Start by adding some!"
              : "No tasks match your current filters."
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
                <h2 className="text-lg font-semibold text-[var(--karma-text-muted)] mb-3 flex items-center gap-2">
                  <span>📅</span>
                  {formatDate(date)}
                  <span className="text-sm font-normal">
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
                      onBreakdown={handleBreakdown}
                      onReResearch={handleReResearch}
                      onArchive={() => archiveTaskMutation.mutate(task.id)}
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
                onBreakdown={handleBreakdown}
                onReResearch={handleReResearch}
                onArchive={() => archiveTaskMutation.mutate(task.id)}
                isLoading={breakingDownTaskId === task.id}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

