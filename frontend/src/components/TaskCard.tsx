import { useState, useEffect } from 'react';
import type { Task, TaskStatus } from '../types';

interface TaskCardProps {
  task: Task;
  onStatusChange?: (taskId: string, status: TaskStatus) => void;
  onSubtaskToggle?: (taskId: string, subtaskId: string) => void; // Legacy - kept for compatibility
  onSubtaskProgressChange?: (taskId: string, subtaskId: string, progress: number) => void;
  onAddSubtask?: (taskId: string, text: string) => void;
  onBreakdown?: (taskId: string) => void;
  onReResearch?: (taskId: string) => void;
  onArchive?: () => void;
  onDelete?: (taskId: string) => void;
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
  onSubtaskToggle: _onSubtaskToggle, // Legacy - kept for compatibility
  onSubtaskProgressChange,
  onAddSubtask,
  onBreakdown,
  onReResearch,
  onArchive,
  onDelete,
  isLoading = false,
}: TaskCardProps) {
  // Suppress unused variable warning for legacy prop
  void _onSubtaskToggle;
  const [isExpanded, setIsExpanded] = useState(false);
  const [isBreakingDown, setIsBreakingDown] = useState(false);
  const [isReResearching, setIsReResearching] = useState(false);
  const [newSubtaskText, setNewSubtaskText] = useState('');
  const [showAddSubtask, setShowAddSubtask] = useState(false);

  // Use task.subtasks directly from props (synced with server)
  const subtasks = task.subtasks || [];
  const completedSubtasks = subtasks.filter(s => s.status === 'completed').length;
  const totalSubtasks = subtasks.length;
  const progress = totalSubtasks > 0 ? (completedSubtasks / totalSubtasks) * 100 : 0;

  const isCompleted = task.status === 'completed';
  const isInProgress = task.status === 'in_progress';

  // Auto-expand when breakdown is loading
  useEffect(() => {
    if (isLoading) {
      setIsBreakingDown(true);
      setIsExpanded(true);
    } else {
      setIsBreakingDown(false);
    }
  }, [isLoading]);

  const handleStatusChange = (newStatus: TaskStatus) => {
    if (!onStatusChange) return;
    onStatusChange(task.id, newStatus);
  };

  // Call the actual breakdown API
  const handleBreakdown = () => {
    setIsBreakingDown(true);
    setIsExpanded(true);
    if (onBreakdown) {
      onBreakdown(task.id);
    }
  };

  // Call the actual re-research API
  const handleReResearch = () => {
    setIsReResearching(true);
    setIsExpanded(true);
    if (onReResearch) {
      onReResearch(task.id);
    }
  };

  // Reset re-researching state when task updates
  useEffect(() => {
    setIsReResearching(false);
  }, [task.enrichment]);

  return (
    <div 
      className={`card animate-fade-in cursor-pointer ${isCompleted ? 'opacity-60 bg-[var(--karma-success)]/5' : ''} ${isInProgress ? 'border-blue-400 bg-blue-50/30' : ''}`}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span>{categoryIcons[task.category] || '📌'}</span>
            <h3 className={`font-medium ${isCompleted ? 'line-through text-[var(--karma-text-muted)]' : ''}`}>
              {task.text}
            </h3>
            {isCompleted && (
              <span className="badge badge-success">✓ Done</span>
            )}
          </div>
          
          <div className="flex items-center gap-2 flex-wrap text-sm">
            <span className={`badge ${priorityColors[task.priority] || 'badge-muted'}`}>
              {task.priority || 'medium'}
            </span>
            <span className="text-[var(--karma-text-muted)]">
              ~{task.estimated_minutes || 15} min
            </span>
            {task.tags && task.tags.length > 0 && (
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

        {/* Action Buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isCompleted ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleStatusChange('pending');
              }}
              className="btn btn-secondary text-sm py-2 px-4"
            >
              ↩️ Reopen
            </button>
          ) : isInProgress ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleStatusChange('completed');
              }}
              className="btn btn-primary text-sm py-2 px-4"
            >
              ✓ Complete
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleStatusChange('completed');
              }}
              className="btn btn-primary text-sm py-2 px-4"
            >
              ✓ Complete
            </button>
          )}
        </div>
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
              <h4 className="font-medium mb-2 text-sm">🔍 AI Research</h4>
              {task.enrichment.summary && (
                <p className="text-sm text-[var(--karma-text-muted)] mb-2">
                  {task.enrichment.summary}
                </p>
              )}
              {task.enrichment.tips && task.enrichment.tips.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-[var(--karma-text-muted)]">💡 Tips:</span>
                  <ul className="list-disc list-inside text-sm mt-1">
                    {task.enrichment.tips.slice(0, 3).map((tip: string, i: number) => (
                      <li key={i} className="text-[var(--karma-text-muted)]">{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Subtasks */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-sm">📋 Subtasks</h4>
              {!isCompleted && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAddSubtask(!showAddSubtask);
                  }}
                  className="text-xs text-[var(--karma-accent)] hover:underline"
                >
                  + Add subtask
                </button>
              )}
            </div>

            {/* Add Subtask Input */}
            {showAddSubtask && (
              <div className="flex gap-2 mb-3" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  value={newSubtaskText}
                  onChange={(e) => setNewSubtaskText(e.target.value)}
                  placeholder="Enter subtask..."
                  className="flex-1 px-3 py-2 text-sm border border-[var(--karma-border)] rounded-lg focus:outline-none focus:border-[var(--karma-accent)]"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newSubtaskText.trim()) {
                      onAddSubtask?.(task.id, newSubtaskText.trim());
                      setNewSubtaskText('');
                    }
                  }}
                />
                <button
                  onClick={() => {
                    if (newSubtaskText.trim()) {
                      onAddSubtask?.(task.id, newSubtaskText.trim());
                      setNewSubtaskText('');
                    }
                  }}
                  disabled={!newSubtaskText.trim()}
                  className="btn btn-primary text-sm px-3"
                >
                  Add
                </button>
              </div>
            )}

            {/* Subtask List */}
            {subtasks.length > 0 ? (
              <div className="space-y-3">
                {subtasks.map((subtask) => {
                  const progress = subtask.progress ?? (subtask.status === 'completed' ? 100 : 0);
                  return (
                    <div 
                      key={subtask.id} 
                      className={`p-3 rounded-lg border transition-all ${
                        progress === 100 
                          ? 'bg-green-50 border-green-200' 
                          : progress > 0
                            ? 'bg-blue-50 border-blue-200'
                            : 'bg-gray-50 border-gray-200'
                      }`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className={`text-sm font-medium ${progress === 100 ? 'line-through text-gray-400' : ''}`}>
                          {subtask.text}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400">
                            ~{subtask.estimated_minutes}m
                          </span>
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            progress === 100 
                              ? 'bg-green-100 text-green-700'
                              : progress > 0
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-gray-100 text-gray-600'
                          }`}>
                            {progress}%
                          </span>
                        </div>
                      </div>
                      
                      {/* Progress Slider */}
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="10"
                          value={progress}
                          onChange={(e) => {
                            const newProgress = parseInt(e.target.value);
                            onSubtaskProgressChange?.(task.id, subtask.id, newProgress);
                          }}
                          className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[var(--karma-accent)]"
                          style={{
                            background: `linear-gradient(to right, ${progress === 100 ? '#22c55e' : '#3b82f6'} 0%, ${progress === 100 ? '#22c55e' : '#3b82f6'} ${progress}%, #e5e7eb ${progress}%, #e5e7eb 100%)`
                          }}
                        />
                        <button
                          onClick={() => {
                            onSubtaskProgressChange?.(task.id, subtask.id, progress === 100 ? 0 : 100);
                          }}
                          className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs transition-all ${
                            progress === 100
                              ? 'bg-green-500 border-green-500 text-white'
                              : 'border-gray-300 hover:border-green-400 hover:bg-green-50'
                          }`}
                        >
                          {progress === 100 ? '✓' : ''}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">No subtasks yet. Break down this task or add manually.</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2 mt-4 flex-wrap">
            {subtasks.length === 0 && !isCompleted && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleBreakdown();
                }}
                disabled={isBreakingDown || isLoading}
                className="btn btn-secondary text-sm"
              >
                {isBreakingDown ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span> Breaking down...
                  </span>
                ) : (
                  '🔨 Break Down'
                )}
              </button>
            )}
            {!isCompleted && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleReResearch();
                }}
                disabled={isReResearching || isLoading}
                className="btn btn-ghost text-sm"
              >
                {isReResearching ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span> Researching...
                  </span>
                ) : (
                  '🔄 Re-research'
                )}
              </button>
            )}
            {onArchive && !isCompleted && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onArchive();
                }}
                className="btn btn-ghost text-sm text-[var(--karma-text-muted)]"
              >
                📦 Archive
              </button>
            )}
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm('Delete this task?')) {
                    onDelete(task.id);
                  }
                }}
                className="btn btn-ghost text-sm text-red-500 hover:text-red-700 hover:bg-red-50"
              >
                🗑️ Delete
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

