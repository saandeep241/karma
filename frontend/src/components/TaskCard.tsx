import { useState } from 'react';
import type { Task, TaskStatus } from '../types';

interface TaskCardProps {
  task: Task;
  onStatusChange?: (taskId: string, status: TaskStatus) => void;
  onSubtaskToggle?: (taskId: string, subtaskId: string) => void;
  onBreakdown?: (taskId: string) => void;
  onReResearch?: (taskId: string) => void;
  onArchive?: () => void;
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

const statusConfig: Record<string, { label: string; color: string; icon: string }> = {
  pending: { label: 'Pending', color: 'bg-gray-100 text-gray-600', icon: '⏳' },
  in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-600', icon: '🔄' },
  completed: { label: 'Done', color: 'bg-green-100 text-green-600', icon: '✓' },
};

export function TaskCard({
  task,
  onStatusChange,
  onSubtaskToggle,
  onBreakdown,
  onReResearch,
  onArchive,
  isLoading = false,
}: TaskCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isBreakingDown, setIsBreakingDown] = useState(false);
  const [isReResearching, setIsReResearching] = useState(false);
  const [localSubtasks, setLocalSubtasks] = useState(task.subtasks || []);
  const [localEnrichment, setLocalEnrichment] = useState(task.enrichment);

  const completedSubtasks = localSubtasks?.filter(s => s.status === 'completed').length || 0;
  const totalSubtasks = localSubtasks?.length || 0;
  const progress = totalSubtasks > 0 ? (completedSubtasks / totalSubtasks) * 100 : 0;

  const isCompleted = task.status === 'completed';
  const isInProgress = task.status === 'in_progress';

  const handleStatusChange = (newStatus: TaskStatus) => {
    if (!onStatusChange) return;
    onStatusChange(task.id, newStatus);
  };

  // Dummy breakdown function
  const handleBreakdown = async () => {
    setIsBreakingDown(true);
    setIsExpanded(true);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Generate dummy subtasks
    const dummySubtasks = [
      { id: `${task.id}-sub-1`, text: `Step 1: Plan and prepare for "${task.text}"`, status: 'pending' as const, estimated_minutes: 5, order: 1 },
      { id: `${task.id}-sub-2`, text: `Step 2: Execute the main part`, status: 'pending' as const, estimated_minutes: Math.floor((task.estimated_minutes || 15) * 0.6), order: 2 },
      { id: `${task.id}-sub-3`, text: `Step 3: Review and finalize`, status: 'pending' as const, estimated_minutes: 5, order: 3 },
    ];
    
    setLocalSubtasks(dummySubtasks);
    setIsBreakingDown(false);
    
    // Also call the actual onBreakdown if provided
    if (onBreakdown) {
      onBreakdown(task.id);
    }
  };

  // Dummy re-research function
  const handleReResearch = async () => {
    setIsReResearching(true);
    setIsExpanded(true);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Generate dummy enrichment
    const dummyEnrichment = {
      summary: `Here's what you need to know about "${task.text}"`,
      tips: [
        'Break this task into smaller chunks for better focus',
        'Set a timer to stay on track',
        'Take short breaks between work sessions',
      ],
      steps: [
        'Gather all necessary materials',
        'Set up your workspace',
        'Complete the task systematically',
      ],
    };
    
    setLocalEnrichment(dummyEnrichment);
    setIsReResearching(false);
    
    // Also call the actual onReResearch if provided
    if (onReResearch) {
      onReResearch(task.id);
    }
  };

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
          {localEnrichment && (
            <div className="mb-4 p-3 bg-[var(--karma-surface-hover)] rounded-lg">
              <h4 className="font-medium mb-2 text-sm">🔍 AI Research</h4>
              {localEnrichment.summary && (
                <p className="text-sm text-[var(--karma-text-muted)] mb-2">
                  {localEnrichment.summary}
                </p>
              )}
              {localEnrichment.tips && localEnrichment.tips.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-[var(--karma-text-muted)]">💡 Tips:</span>
                  <ul className="list-disc list-inside text-sm mt-1">
                    {localEnrichment.tips.slice(0, 3).map((tip, i) => (
                      <li key={i} className="text-[var(--karma-text-muted)]">{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Subtasks */}
          {localSubtasks && localSubtasks.length > 0 && (
            <div className="mb-4">
              <h4 className="font-medium mb-2 text-sm">📋 Subtasks</h4>
              <div className="space-y-2">
                {localSubtasks.map((subtask) => (
                  <div 
                    key={subtask.id} 
                    className={`flex items-center gap-3 p-2 rounded-lg border ${
                      subtask.status === 'completed' 
                        ? 'bg-green-50 border-green-200' 
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <button
                      onClick={() => {
                        const newStatus = subtask.status === 'completed' ? 'pending' : 'completed';
                        setLocalSubtasks(prev => 
                          prev.map(s => s.id === subtask.id ? { ...s, status: newStatus } : s)
                        );
                        if (onSubtaskToggle) {
                          onSubtaskToggle(task.id, subtask.id);
                        }
                      }}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        subtask.status === 'completed'
                          ? 'bg-green-500 border-green-500 text-white'
                          : 'border-gray-300 hover:border-blue-400'
                      }`}
                    >
                      {subtask.status === 'completed' && '✓'}
                    </button>
                    <span className={`flex-1 text-sm ${subtask.status === 'completed' ? 'line-through text-gray-400' : ''}`}>
                      {subtask.text}
                    </span>
                    <span className="text-xs text-gray-400">
                      ~{subtask.estimated_minutes}m
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 mt-4 flex-wrap">
            {localSubtasks.length === 0 && !isCompleted && (
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

