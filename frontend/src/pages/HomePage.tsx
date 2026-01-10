import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { QuickWinCard, LoadingSpinner, EmptyState } from '../components';
import { api } from '../api/client';
import type { QuickWin } from '../types';

type EnergyLevel = 'very_low' | 'low' | 'medium' | 'high' | 'very_high';

interface UserContext {
  available_minutes: number;
  energy_level: EnergyLevel;
}

export function HomePage() {
  const queryClient = useQueryClient();
  const [currentQuickWin, setCurrentQuickWin] = useState<QuickWin | null>(null);
  const [showAddedMessage, setShowAddedMessage] = useState(false);
  const [showContextForm, setShowContextForm] = useState(false);
  const [showQuickWin, setShowQuickWin] = useState(false); // Start with landing page
  const [editableTaskText, setEditableTaskText] = useState('');
  const [userContext, setUserContext] = useState<UserContext>({
    available_minutes: 15,
    energy_level: 'medium',
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

  // Add task mutation (was complete, now just adds to task list)
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
    // Small delay then refetch
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
    setShowContextForm(false);
  };

  const handleAddTask = () => {
    // Show context form first and populate editable text
    if (currentQuickWin) {
      setEditableTaskText(currentQuickWin.text);
    }
    setShowContextForm(true);
  };

  const handleConfirmAdd = () => {
    if (currentQuickWin) {
      // Add context and edited text to the quickwin before saving
      const quickWinWithContext = {
        ...currentQuickWin,
        text: editableTaskText.trim() || currentQuickWin.text,
        estimated_minutes: userContext.available_minutes,
        energy_required: userContext.energy_level,
      };
      addTaskMutation.mutate(quickWinWithContext);
      setShowContextForm(false);
    }
  };

  const handleCancelContext = () => {
    setShowContextForm(false);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero Section */}
      <div className="text-center py-8">
        <h1 className="font-serif text-4xl md:text-5xl italic mb-4">
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
      <div className="max-w-lg mx-auto">
        {/* Landing Page - Suggest a Task Button */}
        {!showQuickWin && !showContextForm && (
          <div className="card text-center animate-fade-in">
            <div className="text-6xl mb-6">🎯</div>
            <h2 className="font-serif text-2xl italic mb-4">
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
        {showQuickWin && showContextForm && currentQuickWin ? (
          <div className="card animate-fade-in">
            <h2 className="font-serif text-2xl italic mb-4 text-center">
              📝 Quick Context
            </h2>
            <p className="text-[var(--karma-text-muted)] text-center mb-6">
              Tell us a bit about your current state to better track this task.
            </p>
            
            {/* Editable Task Text */}
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">
                ✏️ Task Description
              </label>
              <textarea
                value={editableTaskText}
                onChange={(e) => setEditableTaskText(e.target.value)}
                className="w-full p-3 rounded-lg border border-[var(--karma-border)] bg-white focus:border-[var(--karma-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--karma-accent)]/20 resize-none"
                rows={2}
                placeholder="What do you want to do?"
              />
              <p className="text-xs text-[var(--karma-text-muted)] mt-1">
                {currentQuickWin.category} • Suggested: ~{currentQuickWin.estimated_minutes} min
              </p>
            </div>

            {/* Time Available */}
            <div className="mb-6">
              <label className="block text-sm font-medium mb-3">
                ⏱️ How much time do you have?
              </label>
              <div className="grid grid-cols-4 gap-2">
                {[5, 15, 30, 60].map((mins) => (
                  <button
                    key={mins}
                    onClick={() => setUserContext(prev => ({ ...prev, available_minutes: mins }))}
                    className={`py-2 px-3 rounded-lg border transition-all ${
                      userContext.available_minutes === mins
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
            <div className="mb-6">
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
                    onClick={() => setUserContext(prev => ({ ...prev, energy_level: option.value }))}
                    className={`py-3 px-2 rounded-lg border transition-all text-center ${
                      userContext.energy_level === option.value
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

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleCancelContext}
                className="flex-1 btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAdd}
                disabled={addTaskMutation.isPending}
                className="flex-1 btn-primary"
              >
                {addTaskMutation.isPending ? 'Adding...' : '✓ Add Task'}
              </button>
            </div>
          </div>
        ) : showQuickWin && showAddedMessage ? (
          <div className="card text-center animate-fade-in border-[var(--karma-success)]">
            <div className="text-5xl mb-4">✅</div>
            <h2 className="font-serif text-2xl italic mb-2 text-[var(--karma-success)]">
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
  );
}
