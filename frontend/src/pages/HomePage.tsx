import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useLocation } from 'react-router-dom';
import { FocusMode } from '../components';
import { api } from '../api/client';

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

  const { data: statsData } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 60000,
  });

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
    <div className="flex flex-col items-center animate-fade-in max-w-4xl mx-auto pt-24">
      <div className="text-center space-y-4 mb-12">
        <p className="text-gray-500 text-[18px]">{getGreeting()}</p>
        <h1 className="font-sans font-bold text-[64px] leading-none tracking-tight text-[#1a1a1a]">
          Make it <span className="text-[#0066cc]">count.</span>
        </h1>
        <p className="text-gray-400 text-[18px]">
          Got a few minutes? Let's make them productive.
        </p>
      </div>
      
      <button 
        onClick={() => setShowFocusMode(true)}
        className="bg-[#0066cc] hover:bg-[#0052a3] text-white px-10 py-4 rounded-full text-[17px] font-bold shadow-2xl shadow-blue-200/50 transition-all flex items-center gap-2 mb-28"
      >
        Tell me what to do <span className="text-xl">→</span>
      </button>

      {/* Stats Row */}
      <div className="w-full max-w-2xl grid grid-cols-3 gap-16">
        {/* Done Today */}
        <div className="flex flex-col items-center group">
          <div className="w-12 h-12 mb-6 rounded-full border border-gray-100 flex items-center justify-center text-[#9ca3af]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 16V12"></path>
              <path d="M12 8H12.01"></path>
            </svg>
          </div>
          <div className="text-[44px] font-bold text-[#1a1a1a] mb-1 leading-none">{completedToday}</div>
          <div className="text-gray-400 text-[11px] font-bold uppercase tracking-[0.15em]">Done today</div>
        </div>

        {/* This Week */}
        <div className="flex flex-col items-center group">
          <div className="w-12 h-12 mb-6 rounded-full border border-gray-100 flex items-center justify-center text-[#9ca3af]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
              <polyline points="17 6 23 6 23 12"></polyline>
            </svg>
          </div>
          <div className="text-[44px] font-bold text-[#1a1a1a] mb-1 leading-none">{completedThisWeek}</div>
          <div className="text-gray-400 text-[11px] font-bold uppercase tracking-[0.15em]">This week</div>
        </div>

        {/* To Do */}
        <div className="flex flex-col items-center group">
          <div className="w-12 h-12 mb-6 rounded-full border border-gray-100 flex items-center justify-center text-[#9ca3af]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
          </div>
          <div className="text-[44px] font-bold text-[#1a1a1a] mb-1 leading-none">{pendingTasks}</div>
          <div className="text-gray-400 text-[11px] font-bold uppercase tracking-[0.15em]">To do</div>
        </div>
      </div>
    </div>
  );
}
