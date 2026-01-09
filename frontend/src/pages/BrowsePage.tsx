import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TaskCard, LoadingSpinner, EmptyState } from '../components';
import { api } from '../api/client';
import type { Task, TaskStatus, TaskCategory, TaskPriority } from '../types';

type FilterStatus = 'all' | TaskStatus;
type SortBy = 'created' | 'priority' | 'time';

export function BrowsePage() {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [filterCategory, setFilterCategory] = useState<TaskCategory | 'all'>('all');
  const [sortBy, setSortBy] = useState<SortBy>('created');
  const [breakingDownTaskId, setBreakingDownTaskId] = useState<string | null>(null);

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

  // Filter and sort tasks
  const filteredTasks = tasks
    .filter((task: Task) => {
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
        case 'created':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

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
        <h1 className="text-2xl font-serif italic gradient-text">Your Tasks</h1>
        <span className="badge badge-accent">
          {filteredTasks.length} task{filteredTasks.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        {/* Status Filter */}
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
          className="input w-auto"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>

        {/* Category Filter */}
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value as TaskCategory | 'all')}
          className="input w-auto"
        >
          <option value="all">All Categories</option>
          <option value="work">💼 Work</option>
          <option value="personal">🏠 Personal</option>
          <option value="health">🏃 Health</option>
          <option value="learning">📚 Learning</option>
          <option value="errands">🛒 Errands</option>
          <option value="creative">🎨 Creative</option>
          <option value="social">👥 Social</option>
          <option value="finance">💰 Finance</option>
          <option value="home">🏡 Home</option>
        </select>

        {/* Sort */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortBy)}
          className="input w-auto"
        >
          <option value="created">Newest First</option>
          <option value="priority">By Priority</option>
          <option value="time">By Time</option>
        </select>
      </div>

      {/* Task List */}
      {filteredTasks.length === 0 ? (
        <EmptyState
          icon="📭"
          title="No tasks found"
          description={
            filterStatus === 'all' && filterCategory === 'all'
              ? "You haven't added any tasks yet. Start by adding some!"
              : "No tasks match your current filters."
          }
          actionLabel="Add Tasks"
          actionPath="/add"
        />
      ) : (
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
                isLoading={breakingDownTaskId === task.id}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

