import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { QuickWinCard, LoadingSpinner, EmptyState } from '../components';
import { api, type ContinuableTask } from '../api/client';
import type { QuickWin } from '../types';

export function HomePage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [currentQuickWin, setCurrentQuickWin] = useState<QuickWin | null>(null);
  const [showAddedMessage, setShowAddedMessage] = useState(false);
  const [showQuickWin, setShowQuickWin] = useState(false);

  // Fetch continuable tasks (in-progress and almost done)
  const { data: continuableData } = useQuery({
    queryKey: ['continuable-tasks'],
    queryFn: api.getContinuableTasks,
    refetchInterval: 30000,
  });

  // Fetch quick win - only when showQuickWin is true
  const { 
    data: quickWinData,
    isLoading: isLoadingQuickWin, 
    refetch: refetchQuickWin,
    error: quickWinError,
  } = useQuery({
    queryKey: ['quickwin'],
    queryFn: api.getQuickWin,
    enabled: showQuickWin && !currentQuickWin,
  });

  // Update current quick win when data changes
  useEffect(() => {
    if (quickWinData?.quickwin && !currentQuickWin && showQuickWin) {
      setCurrentQuickWin(quickWinData.quickwin);
    }
  }, [quickWinData, currentQuickWin, showQuickWin]);

  // Add task mutation
  const addTaskMutation = useMutation({
    mutationFn: (quickwin: QuickWin) => api.completeQuickWin(quickwin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowAddedMessage(true);
      setTimeout(() => {
        setShowAddedMessage(false);
        setCurrentQuickWin(null);
        refetchQuickWin();
      }, 1500);
    },
  });

  const handleSkip = () => {
    setCurrentQuickWin(null);
    setTimeout(() => refetchQuickWin(), 100);
  };

  const handleSuggestTask = () => {
    setShowQuickWin(true);
    setCurrentQuickWin(null);
    setTimeout(() => refetchQuickWin(), 100);
  };

  const handleBackToLanding = () => {
    setShowQuickWin(false);
    setCurrentQuickWin(null);
  };

  const handleAddTask = () => {
    if (currentQuickWin) {
      addTaskMutation.mutate(currentQuickWin);
    }
  };

  const handleContinueTask = (taskId: string) => {
    navigate(`/browse?task=${taskId}`);
  };

  const inProgressTasks = continuableData?.in_progress || [];
  const almostDoneTasks = continuableData?.almost_done || [];
  const hasContinuableTasks = inProgressTasks.length > 0 || almostDoneTasks.length > 0;

  return (
    <div className="flex gap-6 animate-fade-in">
      {/* Main Content - Always centered */}
      <div className="flex-1 space-y-8">
        {/* Hero Section */}
        <div className="text-center py-8">
          <h1 className="font-serif text-4xl md:text-5xl mb-4">
            <span className="gradient-text">Make every moment count</span>
          </h1>
          <p className="text-[var(--karma-text-muted)] text-lg max-w-xl mx-auto">
            {showQuickWin 
              ? "Here's a task suggestion for you. Add it or skip to see another!"
              : "Got a few minutes? Let me suggest something productive you can do right now."
            }
          </p>
        </div>

        {/* Main Content */}
        <div className="max-w-2xl mx-auto">
          {/* Landing Page - Always show when not in quick win flow */}
          {!showQuickWin && (
            <div className="card text-center animate-fade-in">
              <div className="text-6xl mb-6">🎯</div>
              <h2 className="font-serif text-2xl mb-4">
                Ready to be productive?
              </h2>
              <p className="text-[var(--karma-text-muted)] mb-6">
                Click below and I'll suggest a quick task based on your available time and energy.
              </p>
              <button
                onClick={handleSuggestTask}
                className="btn btn-primary text-lg px-8 py-4"
              >
                ✨ Suggest a Task
              </button>
            </div>
          )}

          {/* Quick Win Flow */}
          {showQuickWin && showAddedMessage ? (
            <div className="card text-center animate-fade-in border-[var(--karma-success)]">
              <div className="text-5xl mb-4">✅</div>
              <h2 className="font-serif text-2xl mb-2 text-[var(--karma-success)]">
                Task Added!
              </h2>
              <p className="text-[var(--karma-text-muted)] mb-4">
                Go to <Link to="/browse" className="text-[var(--karma-accent)] underline">Browse Tasks</Link> to manage and complete it.
              </p>
              <button
                onClick={handleBackToLanding}
                className="btn btn-secondary"
              >
                ← Back to Home
              </button>
            </div>
          ) : showQuickWin && isLoadingQuickWin ? (
            <LoadingSpinner text="Finding a task for you..." />
          ) : showQuickWin && quickWinError ? (
            <EmptyState
              icon="⚠️"
              title="Couldn't load suggestion"
              description="There was an error loading suggestions. Make sure the backend is running."
              actionLabel="Try Again"
              onAction={() => refetchQuickWin()}
            />
          ) : showQuickWin && currentQuickWin ? (
            <div className="space-y-4">
              <QuickWinCard
                quickwin={currentQuickWin}
                onAddTask={handleAddTask}
                onSkip={handleSkip}
                isLoading={addTaskMutation.isPending}
              />
              <button
                onClick={handleBackToLanding}
                className="w-full btn btn-ghost text-sm"
              >
                ← Back to Home
              </button>
            </div>
          ) : showQuickWin ? (
            <LoadingSpinner text="Loading..." />
          ) : null}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
          <Link
            to="/browse"
            className="card text-center no-underline hover:border-[var(--karma-accent)]"
          >
            <span className="text-3xl mb-2 block">📋</span>
            <h3 className="font-medium mb-1">Browse Tasks</h3>
            <p className="text-sm text-[var(--karma-text-muted)]">
              View and manage your task list
            </p>
          </Link>

          <Link
            to="/add"
            className="card text-center no-underline hover:border-[var(--karma-accent)]"
          >
            <span className="text-3xl mb-2 block">➕</span>
            <h3 className="font-medium mb-1">Add Tasks</h3>
            <p className="text-sm text-[var(--karma-text-muted)]">
              Import or create new tasks
            </p>
          </Link>

          <Link
            to="/stats"
            className="card text-center no-underline hover:border-[var(--karma-accent)]"
          >
            <span className="text-3xl mb-2 block">📊</span>
            <h3 className="font-medium mb-1">View Stats</h3>
            <p className="text-sm text-[var(--karma-text-muted)]">
              Track your productivity
            </p>
          </Link>
        </div>
      </div>

      {/* Sidebar - In Progress Tasks (only on desktop) */}
      {hasContinuableTasks && (
        <aside className="hidden lg:block w-72 shrink-0">
          <div className="sticky top-4 space-y-4">
            {/* In Progress Tasks */}
            {inProgressTasks.length > 0 && (
              <div className="bg-[var(--karma-surface)] rounded-xl p-4 border border-[var(--karma-border)]">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">🔥</span>
                  <h3 className="font-medium text-sm">In Progress</h3>
                </div>
                <div className="space-y-2">
                  {inProgressTasks.slice(0, 3).map((task: ContinuableTask) => (
                    <button
                      key={task.id}
                      onClick={() => handleContinueTask(task.id)}
                      className="w-full text-left p-3 bg-[var(--karma-bg)] rounded-lg hover:bg-[var(--karma-bg-secondary)] transition-colors"
                    >
                      <p className="text-sm font-medium line-clamp-2 mb-1">{task.text}</p>
                      {task.subtask_progress && (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-[var(--karma-border)] rounded-full h-1.5">
                            <div 
                              className="bg-[var(--karma-warning)] h-1.5 rounded-full"
                              style={{ width: `${task.subtask_progress.percentage}%` }}
                            />
                          </div>
                          <span className="text-xs text-[var(--karma-text-muted)]">
                            {task.subtask_progress.percentage}%
                          </span>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Almost Done Tasks */}
            {almostDoneTasks.length > 0 && (
              <div className="bg-[var(--karma-surface)] rounded-xl p-4 border border-[var(--karma-border)]">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">✨</span>
                  <h3 className="font-medium text-sm">Almost Done</h3>
                </div>
                <div className="space-y-2">
                  {almostDoneTasks.slice(0, 3).map((task: ContinuableTask) => (
                    <button
                      key={task.id}
                      onClick={() => handleContinueTask(task.id)}
                      className="w-full text-left p-3 bg-[var(--karma-bg)] rounded-lg hover:bg-[var(--karma-bg-secondary)] transition-colors"
                    >
                      <p className="text-sm font-medium line-clamp-2 mb-1">{task.text}</p>
                      {task.subtask_progress && (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-[var(--karma-border)] rounded-full h-1.5">
                            <div 
                              className="bg-[var(--karma-success)] h-1.5 rounded-full"
                              style={{ width: `${task.subtask_progress.percentage}%` }}
                            />
                          </div>
                          <span className="text-xs text-[var(--karma-text-muted)]">
                            {task.subtask_progress.percentage}%
                          </span>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Link to browse all */}
            <Link
              to="/browse?status=in_progress"
              className="block text-center text-sm text-[var(--karma-accent)] hover:underline"
            >
              View all tasks →
            </Link>
          </div>
        </aside>
      )}
    </div>
  );
}
