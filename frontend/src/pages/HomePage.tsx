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
    <div className="flex gap-6 animate-fade-in">
      {/* Main Content - Always centered */}
      <div className="flex-1 space-y-6">
        {/* Hero Section */}
        <div className="text-center py-4">
          <p className="text-gray-600 text-lg mb-2">{getGreeting()}</p>
          <h1 className="font-serif text-5xl md:text-6xl mb-4 text-[#0066cc]">
            Make it count.
          </h1>
          <p className="text-gray-600 text-lg max-w-xl mx-auto mb-8">
            Got a few minutes? Let's make them productive.
          </p>
          
          <button 
            onClick={() => setShowFocusMode(true)}
            className="bg-[#0066cc] hover:bg-[#0052a3] text-white px-10 py-4 rounded-full text-xl font-medium shadow-lg hover:shadow-xl transition-all flex items-center gap-2 mx-auto"
          >
            Tell me what to do <span className="text-2xl">→</span>
          </button>
        </div>

        {/* Stats Row */}
        <div className="max-w-2xl mx-auto mt-12">
          <div className="grid grid-cols-3 gap-8">
            {/* Done Today */}
            <div className="text-center group cursor-pointer">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-gray-200 flex items-center justify-center group-hover:border-[#0066cc] group-hover:text-[#0066cc] transition-all">
                <span className="text-2xl">✓</span>
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-1">
                {completedToday}
              </div>
              <div className="text-gray-500 text-sm">Done today</div>
            </div>

            {/* This Week */}
            <div className="text-center group cursor-pointer">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-gray-200 flex items-center justify-center group-hover:border-[#0066cc] group-hover:text-[#0066cc] transition-all">
                <span className="text-2xl">↗</span>
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-1">
                {completedThisWeek}
              </div>
              <div className="text-gray-500 text-sm">This week</div>
            </div>

            {/* To Do */}
            <div className="text-center group cursor-pointer">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-gray-200 flex items-center justify-center group-hover:border-[#0066cc] group-hover:text-[#0066cc] transition-all">
                <span className="text-2xl">📥</span>
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-1">
                {pendingTasks}
              </div>
              <div className="text-gray-500 text-sm">To do</div>
            </div>
          </div>
        </div>
      </div>

      {/* Sidebar - In Progress Tasks (only on desktop) */}
      {hasContinuableTasks && (
        <aside className="hidden lg:block w-72 shrink-0">
          <div className="sticky top-4 space-y-4">
            {/* In Progress Tasks */}
            {inProgressTasks.length > 0 && (
              <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">🔥</span>
                  <h3 className="font-semibold text-sm text-gray-700">In Progress</h3>
                </div>
                <div className="space-y-2">
                  {inProgressTasks.slice(0, 3).map((task: ContinuableTask) => (
                    <button
                      key={task.id}
                      onClick={() => handleContinueTask(task.id)}
                      className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                      <p className="text-sm font-medium line-clamp-2 mb-1 text-gray-800">{task.text}</p>
                      {task.subtask_progress && (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                            <div 
                              className="bg-amber-500 h-1.5 rounded-full"
                              style={{ width: `${task.subtask_progress.percentage}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">
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
              <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">✨</span>
                  <h3 className="font-semibold text-sm text-gray-700">Almost Done</h3>
                </div>
                <div className="space-y-2">
                  {almostDoneTasks.slice(0, 3).map((task: ContinuableTask) => (
                    <button
                      key={task.id}
                      onClick={() => handleContinueTask(task.id)}
                      className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-green-50 transition-colors"
                    >
                      <p className="text-sm font-medium line-clamp-2 mb-1 text-gray-800">{task.text}</p>
                      {task.subtask_progress && (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                            <div 
                              className="bg-green-500 h-1.5 rounded-full"
                              style={{ width: `${task.subtask_progress.percentage}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">
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
              className="block text-center text-sm text-blue-600 hover:underline"
            >
              View all tasks →
            </Link>
          </div>
        </aside>
      )}
    </div>
  );
}
