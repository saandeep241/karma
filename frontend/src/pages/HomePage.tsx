import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { QuickWinCard, LoadingSpinner, EmptyState } from '../components';
import { api } from '../api/client';
import type { QuickWin } from '../types';

export function HomePage() {
  const queryClient = useQueryClient();
  const [currentQuickWin, setCurrentQuickWin] = useState<QuickWin | null>(null);

  // Fetch health status
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.checkHealth,
  });

  // Fetch quick win
  const { 
    data: quickWinData,
    isLoading: isLoadingQuickWin, 
    refetch: refetchQuickWin,
    error: quickWinError,
  } = useQuery({
    queryKey: ['quickwin'],
    queryFn: api.getQuickWin,
    enabled: !currentQuickWin,
  });

  // Update current quick win when data changes
  useEffect(() => {
    if (quickWinData?.quickwin && !currentQuickWin) {
      setCurrentQuickWin(quickWinData.quickwin);
    }
  }, [quickWinData, currentQuickWin]);

  // Complete quick win mutation
  const completeQuickWinMutation = useMutation({
    mutationFn: (quickwin: QuickWin) => api.completeQuickWin(quickwin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setCurrentQuickWin(null);
      refetchQuickWin();
    },
  });

  const handleSkip = () => {
    setCurrentQuickWin(null);
    refetchQuickWin();
  };

  const handleComplete = () => {
    if (currentQuickWin) {
      completeQuickWinMutation.mutate(currentQuickWin);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero Section */}
      <div className="text-center py-8">
        <h1 className="font-serif text-4xl md:text-5xl italic mb-4">
          <span className="gradient-text">Make every moment count</span>
        </h1>
        <p className="text-[var(--karma-text-muted)] text-lg max-w-xl mx-auto">
          Got a few minutes? Let AI suggest something productive you can accomplish right now.
        </p>
        
        {/* AI Status Badge */}
        {health && (
          <div className="mt-4 inline-flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${health.ai_enabled ? 'bg-[var(--karma-success)]' : 'bg-[var(--karma-warning)]'}`} />
            <span className="text-sm text-[var(--karma-text-muted)]">
              {health.ai_enabled ? 'AI Mode Active' : 'Demo Mode'}
            </span>
          </div>
        )}
      </div>

      {/* Quick Win Section */}
      <div className="max-w-lg mx-auto">
        {isLoadingQuickWin ? (
          <LoadingSpinner text="Finding a quick win for you..." />
        ) : quickWinError ? (
          <EmptyState
            icon="⚠️"
            title="Couldn't load quick win"
            description="There was an error loading suggestions. Make sure the backend is running."
            actionLabel="Try Again"
            onAction={() => refetchQuickWin()}
          />
        ) : currentQuickWin ? (
          <QuickWinCard
            quickwin={currentQuickWin}
            onComplete={handleComplete}
            onSkip={handleSkip}
            isLoading={completeQuickWinMutation.isPending}
          />
        ) : (
          <LoadingSpinner text="Loading..." />
        )}
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

