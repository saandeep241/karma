import type { Subtask } from '../types';

interface SubtaskListProps {
  subtasks: Subtask[];
  taskId: string;
  onToggle: (subtaskId: string) => void;
}

export function SubtaskList({ subtasks, onToggle }: SubtaskListProps) {
  const sortedSubtasks = [...subtasks].sort((a, b) => a.order - b.order);

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-[var(--karma-text-muted)]">
        Steps to Complete
      </h4>
      <ul className="space-y-2">
        {sortedSubtasks.map((subtask, index) => (
          <li
            key={subtask.id}
            className={`flex items-start gap-3 p-3 rounded-lg transition-all ${
              subtask.status === 'completed'
                ? 'bg-[var(--karma-success)]/10'
                : 'bg-[var(--karma-surface-hover)]'
            }`}
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggle(subtask.id);
              }}
              className={`checkbox flex-shrink-0 mt-0.5 ${
                subtask.status === 'completed' ? 'checked' : ''
              }`}
              aria-label={
                subtask.status === 'completed'
                  ? 'Mark subtask incomplete'
                  : 'Mark subtask complete'
              }
            />
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[var(--karma-text-muted)] text-sm font-mono">
                  {index + 1}.
                </span>
                <span
                  className={`text-sm ${
                    subtask.status === 'completed'
                      ? 'line-through text-[var(--karma-text-muted)]'
                      : ''
                  }`}
                >
                  {subtask.text}
                </span>
              </div>
              
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-[var(--karma-text-muted)]">
                  ⏱️ ~{subtask.estimated_minutes} min
                </span>
                {subtask.status === 'in_progress' && (
                  <span className="badge badge-accent text-xs">In Progress</span>
                )}
                {subtask.status === 'skipped' && (
                  <span className="badge badge-muted text-xs">Skipped</span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
      
      {/* Total time estimate */}
      <div className="flex justify-end text-sm text-[var(--karma-text-muted)] pt-2">
        Total: ~{subtasks.reduce((sum, s) => sum + s.estimated_minutes, 0)} min
      </div>
    </div>
  );
}

