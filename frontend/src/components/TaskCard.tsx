import { useState } from 'react';
import type { Task, TaskStatus } from '../types';
import { SubtaskList } from './SubtaskList';

interface TaskCardProps {
  task: Task;
  onStatusChange?: (taskId: string, status: TaskStatus) => void;
  onSubtaskToggle?: (taskId: string, subtaskId: string) => void;
  onBreakdown?: (taskId: string) => void;
  onReResearch?: (taskId: string) => void;
  isLoading?: boolean;
}

const priorityColors: Record<string, string> = {
  low: 'badge-muted',
  medium: 'badge-accent',
  high: 'badge-warning',
  urgent: 'bg-red-500/20 text-red-400',
};

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

export function TaskCard({
  task,
  onStatusChange,
  onSubtaskToggle,
  onBreakdown,
  onReResearch,
  isLoading = false,
}: TaskCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const completedSubtasks = task.subtasks.filter(s => s.status === 'completed').length;
  const totalSubtasks = task.subtasks.length;
  const progress = totalSubtasks > 0 ? (completedSubtasks / totalSubtasks) * 100 : 0;

  const handleToggleComplete = () => {
    if (!onStatusChange) return;
    const newStatus: TaskStatus = task.status === 'completed' ? 'pending' : 'completed';
    onStatusChange(task.id, newStatus);
  };

  return (
    <div 
      className={`card animate-fade-in ${task.status === 'completed' ? 'opacity-60' : ''}`}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleToggleComplete();
          }}
          className={`checkbox mt-1 flex-shrink-0 ${task.status === 'completed' ? 'checked' : ''}`}
          aria-label={task.status === 'completed' ? 'Mark incomplete' : 'Mark complete'}
        />
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span>{categoryIcons[task.category] || '📌'}</span>
            <h3 className={`font-medium ${task.status === 'completed' ? 'line-through text-[var(--karma-text-muted)]' : ''}`}>
              {task.text}
            </h3>
            {task.is_dummy && (
              <span className="badge badge-warning text-xs">Demo</span>
            )}
          </div>
          
          <div className="flex items-center gap-2 flex-wrap text-sm">
            <span className={`badge ${priorityColors[task.priority]}`}>
              {task.priority}
            </span>
            <span className="text-[var(--karma-text-muted)]">
              ~{task.estimated_minutes} min
            </span>
            {task.tags.length > 0 && (
              <div className="flex gap-1">
                {task.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="badge badge-muted">
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Progress bar for subtasks */}
          {totalSubtasks > 0 && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-[var(--karma-text-muted)] mb-1">
                <span>Subtasks</span>
                <span>{completedSubtasks}/{totalSubtasks}</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-bar-fill" 
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className="btn-ghost p-2 rounded-lg"
        >
          <span className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-[var(--karma-border)] animate-slide-up">
          {/* Notes */}
          {task.notes && (
            <p className="text-[var(--karma-text-muted)] text-sm mb-4">
              {task.notes}
            </p>
          )}

          {/* Enrichment */}
          {task.enrichment && (
            <div className="mb-4 p-3 bg-[var(--karma-surface-hover)] rounded-lg">
              <h4 className="font-medium mb-2 text-sm">AI Research</h4>
              {task.enrichment.summary && (
                <p className="text-sm text-[var(--karma-text-muted)] mb-2">
                  {task.enrichment.summary}
                </p>
              )}
              {task.enrichment.tips && task.enrichment.tips.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-[var(--karma-text-muted)]">Tips:</span>
                  <ul className="list-disc list-inside text-sm mt-1">
                    {task.enrichment.tips.slice(0, 3).map((tip, i) => (
                      <li key={i} className="text-[var(--karma-text-muted)]">{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Subtasks */}
          {task.subtasks.length > 0 && onSubtaskToggle && (
            <SubtaskList
              subtasks={task.subtasks}
              taskId={task.id}
              onToggle={(subtaskId) => onSubtaskToggle(task.id, subtaskId)}
            />
          )}

          {/* Actions */}
          <div className="flex gap-2 mt-4">
            {!task.subtasks_generated && onBreakdown && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onBreakdown(task.id);
                }}
                disabled={isLoading}
                className="btn btn-secondary text-sm"
              >
                {isLoading ? (
                  <span className="spinner" />
                ) : (
                  '🔨 Break Down'
                )}
              </button>
            )}
            {onReResearch && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onReResearch(task.id);
                }}
                disabled={isLoading}
                className="btn btn-ghost text-sm"
              >
                🔄 Re-research
              </button>
            )}
          </div>

          {/* Agent Reasoning */}
          {task.agent_reasoning && (
            <div className="mt-4 p-3 bg-[var(--karma-bg)] rounded-lg border border-[var(--karma-border)]">
              <span className="text-xs text-[var(--karma-text-muted)]">🤖 AI Reasoning:</span>
              <p className="text-sm mt-1 text-[var(--karma-text-muted)] italic">
                {task.agent_reasoning}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

