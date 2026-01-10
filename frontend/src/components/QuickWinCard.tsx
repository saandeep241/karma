import type { QuickWin } from '../types';

interface QuickWinCardProps {
  quickwin: QuickWin;
  onAddTask: () => void;
  onSkip: () => void;
  isLoading?: boolean;
}

const categoryIcons: Record<string, string> = {
  work: '💼',
  personal: '🏠',
  health: '🏃',
  learning: '📚',
  errands: '🛒',
  creative: '🎨',
  social: '👥',
  finance: '💰',
  home: '🏡',
  other: '📌',
};

export function QuickWinCard({
  quickwin,
  onAddTask,
  onSkip,
  isLoading = false,
}: QuickWinCardProps) {
  return (
    <div className="card animate-pulse-glow border-[var(--karma-accent)]/50">
      <div className="text-center">
        {/* Icon */}
        <div className="text-5xl mb-4">
          {categoryIcons[quickwin.category] || '✨'}
        </div>

        {/* Title */}
        <h2 className="font-serif text-2xl italic mb-2 gradient-text">
          Quick Win
        </h2>

        {/* Task Text */}
        <p className="text-lg mb-4">
          {quickwin.text}
        </p>

        {/* Time Estimate */}
        <div className="flex items-center justify-center gap-2 text-[var(--karma-text-muted)] mb-6">
          <span>⏱️</span>
          <span>~{quickwin.estimated_minutes} min</span>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-center">
          <button
            onClick={onSkip}
            disabled={isLoading}
            className="btn btn-secondary"
          >
            Show Another
          </button>
          <button
            onClick={onAddTask}
            disabled={isLoading}
            className="btn btn-primary"
          >
            {isLoading ? (
              <span className="spinner" />
            ) : (
              <>
                <span>➕</span>
                Add Task
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
