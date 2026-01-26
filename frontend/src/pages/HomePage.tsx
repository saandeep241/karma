import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
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
  const location = useLocation();
  const [showFocusMode, setShowFocusMode] = useState(false);

  // Reset focus mode when navigating to home (e.g., clicking logo)
  useEffect(() => {
    if (location.pathname === '/' && !location.search.includes('focus')) {
      setShowFocusMode(false);
    }
  }, [location.key, location.pathname, location.search]);

  const { data: statsData } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 60000,
  });

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
    <div className="flex flex-col items-center animate-fade-in max-w-4xl mx-auto pt-8 sm:pt-16 md:pt-24 px-4">
      <div className="text-center space-y-3 sm:space-y-4 mb-8 sm:mb-12">
        <p className="text-gray-500 text-sm sm:text-base md:text-[18px]">{getGreeting()}</p>
        <h1 className="font-sans font-bold text-4xl sm:text-5xl md:text-6xl lg:text-[64px] leading-none tracking-tight text-[#1a1a1a]">
          Make it <span className="text-[#0066cc]">count.</span>
        </h1>
        <p className="text-gray-400 text-sm sm:text-base md:text-[18px] px-4">
          Got a few minutes? Let's make them productive.
        </p>
      </div>
      
      <button 
        onClick={() => setShowFocusMode(true)}
        className="bg-[#0066cc] hover:bg-[#0052a3] text-white px-6 sm:px-8 md:px-10 py-3 sm:py-3.5 md:py-4 rounded-full text-sm sm:text-base md:text-[17px] font-bold shadow-2xl shadow-blue-200/50 transition-all flex items-center gap-2 mb-12 sm:mb-20 md:mb-28"
      >
        Tell me what to do <span className="text-lg sm:text-xl">→</span>
      </button>

      {/* Stats Row */}
      <div className="w-full max-w-2xl grid grid-cols-3 gap-4 sm:gap-8 md:gap-12 lg:gap-16">
        {/* Done Today */}
        <div className="flex flex-col items-center group">
          <div className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 mb-3 sm:mb-4 md:mb-6 rounded-full border border-gray-100 flex items-center justify-center text-[#9ca3af]">
            <svg width="18" height="18" className="sm:w-20 sm:h-20 md:w-22 md:h-22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 16V12"></path>
              <path d="M12 8H12.01"></path>
            </svg>
          </div>
          <div className="text-2xl sm:text-3xl md:text-4xl lg:text-[44px] font-bold text-[#1a1a1a] mb-1 leading-none">{completedToday}</div>
          <div className="text-gray-400 text-[9px] sm:text-[10px] md:text-[11px] font-bold uppercase tracking-[0.15em] text-center">Done today</div>
        </div>

        {/* This Week */}
        <div className="flex flex-col items-center group">
          <div className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 mb-3 sm:mb-4 md:mb-6 rounded-full border border-gray-100 flex items-center justify-center text-[#9ca3af]">
            <svg width="18" height="18" className="sm:w-20 sm:h-20 md:w-22 md:h-22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
              <polyline points="17 6 23 6 23 12"></polyline>
            </svg>
          </div>
          <div className="text-2xl sm:text-3xl md:text-4xl lg:text-[44px] font-bold text-[#1a1a1a] mb-1 leading-none">{completedThisWeek}</div>
          <div className="text-gray-400 text-[9px] sm:text-[10px] md:text-[11px] font-bold uppercase tracking-[0.15em] text-center">This week</div>
        </div>

        {/* To Do */}
        <div className="flex flex-col items-center group">
          <div className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 mb-3 sm:mb-4 md:mb-6 rounded-full border border-gray-100 flex items-center justify-center text-[#9ca3af]">
            <svg width="18" height="18" className="sm:w-20 sm:h-20 md:w-22 md:h-22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 7H2V11H22V7Z" />
              <path d="M2 11V21H22V11" />
              <path d="M10 15H14" />
            </svg>
          </div>
          <div className="text-2xl sm:text-3xl md:text-4xl lg:text-[44px] font-bold text-[#1a1a1a] mb-1 leading-none">{pendingTasks}</div>
          <div className="text-gray-400 text-[9px] sm:text-[10px] md:text-[11px] font-bold uppercase tracking-[0.15em] text-center">To do</div>
        </div>
      </div>
    </div>
  );
}
