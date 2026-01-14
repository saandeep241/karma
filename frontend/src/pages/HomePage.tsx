import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { FocusMode } from '../components';
import { api, type ContinuableTask } from '../api/client';

export function HomePage() {
  const navigate = useNavigate();
  const [showFocusMode, setShowFocusMode] = useState(false);

  // Fetch continuable tasks (in-progress and almost done)
  const { data: continuableData } = useQuery({
    queryKey: ['continuable-tasks'],
    queryFn: api.getContinuableTasks,
    refetchInterval: 30000,
  });

  const handleContinueTask = (taskId: string) => {
    navigate(`/browse?task=${taskId}`);
  };

  const inProgressTasks = continuableData?.in_progress || [];
  const almostDoneTasks = continuableData?.almost_done || [];
  const hasContinuableTasks = inProgressTasks.length > 0 || almostDoneTasks.length > 0;

  // Focus Mode is the main experience
  if (showFocusMode) {
    return (
      <div className="focus-bg -mx-6 -my-8 px-6 py-8 min-h-[calc(100vh-120px)]">
        <FocusMode onExit={() => setShowFocusMode(false)} />
      </div>
    );
  }

  return (
    <div className="flex gap-6 animate-fade-in">
      {/* Main Content - Always centered */}
      <div className="flex-1 space-y-8">
        {/* Hero Section */}
        <div className="text-center py-8">
          <h1 className="font-serif text-4xl md:text-5xl mb-4">
            <span className="bg-gradient-to-r from-blue-600 via-cyan-500 to-teal-400 bg-clip-text text-transparent font-bold">
              Make it count.
            </span>
          </h1>
          <p className="text-[var(--karma-text-muted)] text-lg max-w-xl mx-auto">
            Got a few minutes? Let's make them productive.
          </p>
        </div>

        {/* Main CTA Card */}
        <div className="max-w-md mx-auto">
          <div className="focus-card text-center">
            <div className="text-5xl mb-4">✨</div>
            <h2 className="font-bold text-2xl mb-3 text-gray-800">
              Ready to be productive?
            </h2>
            <p className="text-gray-500 mb-6">
              Tell me how much time you have and I'll suggest the perfect task.
            </p>
            <button
              onClick={() => setShowFocusMode(true)}
              className="w-full py-4 bg-[var(--karma-accent)] hover:bg-[var(--karma-accent-hover)] text-white font-semibold rounded-full transition-all text-lg"
            >
              Let's go →
            </button>
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
