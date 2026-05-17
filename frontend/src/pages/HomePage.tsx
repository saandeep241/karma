import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import { FocusMode } from '../components';
import { api } from '../api/client';
import { EmptyStatePage } from './EmptyStatePage';

export function HomePage() {
  const location = useLocation();
  const [showFocusMode, setShowFocusMode] = useState(false);

  const searchParams = new URLSearchParams(location.search);
  const shouldPreviewEmptyState =
    searchParams.get('emptyState') === '1' && !import.meta.env.PROD;

  // Reset focus mode when navigating to home (e.g., clicking logo)
  useEffect(() => {
    if (location.pathname === '/' && !location.search.includes('focus')) {
      setShowFocusMode(false);
    }
  }, [location.key, location.pathname, location.search]);

  const { data: statsData, isLoading: isStatsLoading, isError: isStatsError } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 60000,
  });

  if (isStatsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-120px)]">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    );
  }

  // Dev-only: ?emptyState=1 forces the empty state preview even if the user has tasks
  if (shouldPreviewEmptyState) {
    return <EmptyStatePage />;
  }

  // All environments: show onboarding for users who have no tasks yet
  if (!isStatsError && statsData && (statsData as any).total === 0) {
    return <EmptyStatePage />;
  }

  if (showFocusMode) {
    return (
      <div className="-mx-6 -my-8 px-6 py-8 min-h-[calc(100vh-120px)] flex items-center justify-center animate-fade-in">
        <FocusMode onExit={() => setShowFocusMode(false)} />
      </div>
    );
  }

  const completedToday = (statsData as any)?.completed_today || 0;
  const completedThisWeek = (statsData as any)?.completed_this_week || 0;
  const pendingTasks = statsData?.pending_tasks || 0;

  return (
    <div className="flex flex-col items-center animate-fade-in max-w-4xl mx-auto pt-8 sm:pt-16 md:pt-24 px-4 min-h-[calc(100vh-80px)]">
      <div className="text-center space-y-4 mb-16">
        <p className="text-gray-400 text-sm font-medium tracking-wide uppercase">Welcome back</p>
        <h1 className="font-sans font-bold text-5xl sm:text-6xl md:text-[72px] leading-tight tracking-tight text-[#001a41]">
          Make it <span className="text-[#0066cc]">count.</span>
        </h1>
        <p className="text-gray-400 text-base md:text-lg max-w-lg mx-auto leading-relaxed">
          AI-powered task suggestions for productive moments.<br />Let's make today meaningful.
        </p>
      </div>
      
      <button 
        onClick={() => setShowFocusMode(true)}
        className="bg-[#001a41] hover:bg-black text-white px-10 py-4 rounded-2xl text-[17px] font-bold shadow-[0_20px_40px_rgba(0,26,65,0.15)] transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-3 mb-24"
      >
        Tell me what to do <span className="text-xl">→</span>
      </button>

      {/* Stats Row */}
      <div className="w-full max-w-3xl grid grid-cols-3 gap-8 sm:gap-12 bg-white/50 p-8 rounded-3xl border border-gray-100/50">
        {/* Done Today */}
        <div className="flex flex-col items-center group">
          <div className="text-3xl sm:text-4xl lg:text-[48px] font-bold text-[#001a41] mb-2 leading-none">{completedToday}</div>
          <div className="text-gray-400 text-[10px] font-bold uppercase tracking-[0.2em] text-center">Done today</div>
        </div>

        {/* This Week */}
        <div className="flex flex-col items-center group border-x border-gray-100 px-8">
          <div className="text-3xl sm:text-4xl lg:text-[48px] font-bold text-[#001a41] mb-2 leading-none">{completedThisWeek}</div>
          <div className="text-gray-400 text-[10px] font-bold uppercase tracking-[0.2em] text-center">This week</div>
        </div>

        {/* To Do */}
        <div className="flex flex-col items-center group">
          <div className="text-3xl sm:text-4xl lg:text-[48px] font-bold text-[#001a41] mb-2 leading-none">{pendingTasks}</div>
          <div className="text-gray-400 text-[10px] font-bold uppercase tracking-[0.2em] text-center">To do</div>
        </div>
      </div>
    </div>
  );
}
