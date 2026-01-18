import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { FocusMode } from '../components';
import { api, type ContinuableTask } from '../api/client';

// Get time-based greeting
function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [showFocusMode, setShowFocusMode] = useState(false);

  // Reset focus mode when navigating to home (e.g., clicking logo)
  useEffect(() => {
    if (location.pathname === '/' && !location.search.includes('focus')) {
      setShowFocusMode(false);
    }
  }, [location.key]);

  const { data: continuableData } = useQuery({
    queryKey: ['continuable-tasks'],
    queryFn: api.getContinuableTasks,
    refetchInterval: 30000,
  });

  const { data: statsData } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 60000,
  });

  const handleContinueTask = (taskId: string) => {
    navigate(`/browse?task=${taskId}`);
  };

  const inProgressTasks = continuableData?.in_progress || [];
  const almostDoneTasks = continuableData?.almost_done || [];
  const hasContinuableTasks = inProgressTasks.length > 0 || almostDoneTasks.length > 0;

  if (showFocusMode) {
    return (
      <div className="focus-bg -mx-6 -my-8 px-6 py-8 min-h-[calc(100vh-120px)]">
        <FocusMode onExit={() => setShowFocusMode(false)} />
      </div>
    );
  }

  const completedToday = (statsData as any)?.completed_today || 0;
  const completedThisWeek = (statsData as any)?.completed_this_week || 0;
  const pendingTasks = statsData?.pending_tasks || 0;

  return (
    <div className="flex flex-col items-center animate-fade-in max-w-4xl mx-auto pt-12">
      <div className="text-center space-y-2 mb-12">
        <p className="text-gray-500 text-lg">{getGreeting()}</p>
        <h1 className="font-sans font-bold text-[56px] leading-tight tracking-tight text-[#1a1a1a]">
          Make it <span className="text-[#0066cc]">count.</span>
        </h1>
        <p className="text-gray-400 text-lg">
          Got a few minutes? Let's make them productive.
        </p>
      </div>
      
      <button 
        onClick={() => setShowFocusMode(true)}
        className="bg-[#0066cc] hover:bg-[#0052a3] text-white px-10 py-4 rounded-full text-lg font-bold shadow-xl shadow-blue-100 transition-all flex items-center gap-2 mb-20"
      >
        Tell me what to do <span className="text-xl">→</span>
      </button>

      {/* Stats Row */}
      <div className="w-full max-w-2xl grid grid-cols-3 gap-12">
        {/* Done Today */}
        <div className="flex flex-col items-center group">
          <div className="w-12 h-12 mb-6 rounded-full border border-gray-100 flex items-center justify-center text-gray-400">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="16 12 12 8 8 12"></polyline>
              <line x1="12" y1="16" x2="12" y2="8"></line>
            </svg>
          </div>
          <div className="text-4xl font-bold text-[#1a1a1a] mb-1">{completedToday}</div>
          <div className="text-gray-400 text-xs font-medium uppercase tracking-widest">Done today</div>
        </div>

        {/* This Week */}
        <div className="flex flex-col items-center group">
          <div className="w-12 h-12 mb-6 rounded-full border border-gray-100 flex items-center justify-center text-gray-400">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
              <polyline points="17 6 23 6 23 12"></polyline>
            </svg>
          </div>
          <div className="text-4xl font-bold text-[#1a1a1a] mb-1">{completedThisWeek}</div>
          <div className="text-gray-400 text-xs font-medium uppercase tracking-widest">This week</div>
        </div>

        {/* To Do */}
        <div className="flex flex-col items-center group">
          <div className="w-12 h-12 mb-6 rounded-full border border-gray-100 flex items-center justify-center text-gray-400">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 8V21H3V8"></path>
              <path d="M1 3H23V8H1V3Z"></path>
              <path d="M10 12H14"></path>
            </svg>
          </div>
          <div className="text-4xl font-bold text-[#1a1a1a] mb-1">{pendingTasks}</div>
          <div className="text-gray-400 text-xs font-medium uppercase tracking-widest">To do</div>
        </div>
      </div>

      {/* Continuable Tasks Sidebar (Hidden on center layout) */}
      {hasContinuableTasks && (
        <div className="hidden">
          {/* Maintained for logic but hidden to match mockup layout */}
        </div>
      )}
    </div>
  );
}
