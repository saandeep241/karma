import { useState, useEffect, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { QuickWin, Task } from '../types';

// Types
type Mood = 'enthusiastic' | 'neutral' | 'tired' | 'overwhelmed' | 'low_energy';
type TimeAvailable = 5 | 10 | 15;
type FlowStep = 'landing' | 'suggestion' | 'proceed_choice' | 'timer' | 'breakdown_timer' | 'completed';

// Confetti colors
const CONFETTI_COLORS = ['#0066cc', '#00ccff', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

// Confetti component
function Confetti() {
  const pieces = Array.from({ length: 50 }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    delay: Math.random() * 2,
    color: CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)],
    size: 8 + Math.random() * 8,
  }));

  return (
    <div className="confetti">
      {pieces.map((piece) => (
        <div
          key={piece.id}
          className="confetti-piece"
          style={{
            left: `${piece.left}%`,
            animationDelay: `${piece.delay}s`,
            backgroundColor: piece.color,
            width: piece.size,
            height: piece.size,
          }}
        />
      ))}
    </div>
  );
}

// Get time-based greeting
function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

interface FocusModeProps {
  onExit: () => void;
}

const MOODS: { value: Mood; label: string; emoji: string }[] = [
  { value: 'enthusiastic', label: 'Enthusiastic', emoji: '🤩' },
  { value: 'neutral', label: 'Neutral', emoji: '😐' },
  { value: 'tired', label: 'Tired', emoji: '😴' },
  { value: 'overwhelmed', label: 'Overwhelmed', emoji: '🤯' },
  { value: 'low_energy', label: 'Low Energy', emoji: '🔋' },
];

export function FocusMode({ onExit }: FocusModeProps) {
  const queryClient = useQueryClient();
  
  // Flow state
  const [step, setStep] = useState<FlowStep>('landing');
  const [timeAvailable, setTimeAvailable] = useState<TimeAvailable>(5);
  const [mood, setMood] = useState<Mood>('neutral');
  
  // Task state
  const [currentTask, setCurrentTask] = useState<QuickWin | null>(null);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [isLoadingTask, setIsLoadingTask] = useState(false);
  
  // Timer state
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  
  // Subtask state for breakdown view
  const [subtasks, setSubtasks] = useState<{ id: string; text: string; completed: boolean }[]>([]);

  // Fetch a task suggestion
  const fetchSuggestion = useCallback(async () => {
    setIsLoadingTask(true);
    try {
      const data = await api.getQuickWin();
      if (data?.quickwin) {
        setCurrentTask(data.quickwin);
        setStep('suggestion');
      }
    } catch (error) {
      console.error('Failed to fetch suggestion:', error);
    } finally {
      setIsLoadingTask(false);
    }
  }, []);

  // Add task mutation
  const addTaskMutation = useMutation({
    mutationFn: (quickwin: QuickWin) => api.completeQuickWin(quickwin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Breakdown task mutation
  const breakdownMutation = useMutation({
    mutationFn: (taskId: string) => api.breakdownTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Complete task mutation
  const completeTaskMutation = useMutation({
    mutationFn: (taskId: string) => api.updateTaskStatus(taskId, 'completed'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setStep('completed');
    },
  });

  // Timer effect
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isTimerRunning && timeRemaining > 0) {
      interval = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            setIsTimerRunning(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isTimerRunning, timeRemaining]);

  // Format time for display
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Handle "Let's go" from suggestion
  const handleLetsGo = async () => {
    if (!currentTask) return;
    
    try {
      // Add the task - API returns { success, task_id, message }
      const result = await addTaskMutation.mutateAsync(currentTask);
      if (result?.success && result?.task_id) {
        // Create a minimal task object for the flow
        setActiveTask({
          id: result.task_id,
          text: currentTask.text,
          status: 'pending',
          priority: 'medium',
          category: currentTask.category?.toLowerCase() || 'other',
          estimated_minutes: currentTask.estimated_minutes || timeAvailable,
          subtasks: [],
          created_at: new Date().toISOString(),
          tags: ['quick-win'],
          subtasks_generated: false,
          is_dummy: currentTask.is_dummy,
        } as Task);
        setStep('proceed_choice');
      }
    } catch (error) {
      console.error('Failed to add task:', error);
    }
  };

  // Handle skip - get another suggestion
  const handleSkip = () => {
    setCurrentTask(null);
    fetchSuggestion();
  };

  // Handle "Let's go (Direct)" - start timer immediately
  const handleDirectStart = () => {
    setTimeRemaining(timeAvailable * 60);
    setIsTimerRunning(true);
    setStep('timer');
  };

  // Handle "Make it easy" - break down then start timer
  const handleBreakdown = async () => {
    if (!activeTask || breakdownMutation.isPending) return;
    
    try {
      const data = await breakdownMutation.mutateAsync(activeTask.id);
      // Set subtasks from the response - generate IDs if not present
      if (data?.subtasks && data.subtasks.length > 0) {
        setSubtasks(data.subtasks.map((s: any, index: number) => ({
          id: s.id || `subtask-${index}`,
          text: s.text || s.instruction,
          completed: s.status === 'completed',
        })));
      }
      setTimeRemaining(timeAvailable * 60);
      setIsTimerRunning(true);
      setStep('breakdown_timer');
    } catch (error) {
      console.error('Failed to break down task:', error);
    }
  };

  // Handle task completion
  const handleComplete = () => {
    if (activeTask) {
      completeTaskMutation.mutate(activeTask.id);
    } else {
      setStep('completed');
    }
  };

  // Handle subtask toggle - auto-complete when all done
  const toggleSubtask = (id: string) => {
    setSubtasks((prev) => {
      const updated = prev.map((s) => (s.id === id ? { ...s, completed: !s.completed } : s));
      // Check if all subtasks are now completed
      const allCompleted = updated.length > 0 && updated.every((s) => s.completed);
      if (allCompleted && activeTask) {
        // Auto-complete the task after a brief delay for visual feedback
        setTimeout(() => {
          completeTaskMutation.mutate(activeTask.id);
        }, 500);
      }
      return updated;
    });
  };

  // Get another quick win
  const handleGetAnother = () => {
    setCurrentTask(null);
    setActiveTask(null);
    setSubtasks([]);
    setStep('landing');
  };

  // Render based on current step
  const renderStep = () => {
    switch (step) {
      // ============ LANDING - Time & Mood Selection ============
      case 'landing':
        return (
          <div className="focus-card animate-card-entrance">
            <p className="text-center text-gray-500 mb-1">{getGreeting()} 👋</p>
            <h1 className="text-3xl md:text-4xl font-bold text-center mb-2">
              <span className="shimmer-text">
                Make it count.
              </span>
            </h1>
            <p className="text-gray-500 text-center mb-8">What's your vibe right now?</p>

            {/* Time Available */}
            <div className="mb-6">
              <p className="text-xs font-semibold text-blue-500 uppercase tracking-wider text-center mb-3">
                Time Available
              </p>
              <div className="flex justify-center gap-3">
                {([5, 10, 15] as TimeAvailable[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTimeAvailable(t)}
                    className={`px-6 py-3 rounded-xl text-lg font-semibold transition-all ${
                      timeAvailable === t
                        ? 'bg-blue-50 border-2 border-blue-400 text-blue-700'
                        : 'bg-gray-50 border-2 border-transparent text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {t}m
                  </button>
                ))}
              </div>
            </div>

            {/* Current Mood */}
            <div className="mb-8">
              <p className="text-xs font-semibold text-blue-500 uppercase tracking-wider text-center mb-3">
                Current Mood
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {MOODS.map((m) => (
                  <button
                    key={m.value}
                    onClick={() => setMood(m.value)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                      mood === m.value
                        ? 'bg-amber-50 border-2 border-amber-400 text-amber-700'
                        : 'bg-gray-50 border-2 border-transparent text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {m.label} {m.emoji}
                  </button>
                ))}
              </div>
            </div>

            {/* Start Button */}
            <button
              onClick={fetchSuggestion}
              disabled={isLoadingTask}
              className="w-full py-4 bg-[var(--karma-accent)] hover:bg-[var(--karma-accent-hover)] text-white font-semibold rounded-full btn-lift disabled:opacity-50"
            >
              {isLoadingTask ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="spinner" style={{ width: '1rem', height: '1rem', borderWidth: '2px' }} />
                  Finding a task...
                </span>
              ) : "Let's go →"}
            </button>
          </div>
        );

      // ============ SUGGESTION - Task Card ============
      case 'suggestion':
        if (!currentTask) return null;
        return (
          <div className="focus-card animate-card-entrance">
            {/* Sparkle icon */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-full flex items-center justify-center shadow-lg">
                <span className="text-3xl">✨</span>
              </div>
            </div>

            <h2 className="text-xl md:text-2xl font-bold text-center text-gray-800 mb-3">
              Why don't you take {timeAvailable} minutes to...
            </h2>
            
            <p className="text-2xl md:text-3xl text-[var(--karma-accent)] font-bold text-center mb-4 leading-tight">
              {currentTask.text}?
            </p>
            
            <div className="flex items-center justify-center gap-3 mb-8">
              <span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-sm font-medium">
                ⏱ ~{currentTask.estimated_minutes} min
              </span>
              <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm font-medium">
                {currentTask.category}
              </span>
            </div>

            {/* Let's go button */}
            <button
              onClick={handleLetsGo}
              disabled={addTaskMutation.isPending}
              className="w-full py-4 bg-[var(--karma-accent)] hover:bg-[var(--karma-accent-hover)] text-white font-semibold rounded-full btn-lift mb-3 disabled:opacity-50"
            >
              {addTaskMutation.isPending ? 'Adding...' : "Let's go →"}
            </button>

            {/* Skip button */}
            <button
              onClick={handleSkip}
              className="w-full py-3 text-gray-500 hover:text-gray-700 font-medium transition-all flex items-center justify-center gap-2 hover:bg-gray-50 rounded-full"
            >
              <span>↻</span> Skip, show me another
            </button>
          </div>
        );

      // ============ PROCEED CHOICE - Direct vs Breakdown ============
      case 'proceed_choice':
        return (
          <div className="focus-card animate-fade-in">
            <h2 className="text-2xl md:text-3xl font-bold text-center text-gray-800 mb-2">
              How would you like to proceed?
            </h2>
            <p className="text-gray-500 text-center mb-8">Choose the path that feels right.</p>

            {/* Option 1: Direct */}
            <button
              onClick={handleDirectStart}
              className="w-full p-5 mb-3 bg-blue-50 hover:bg-blue-100 rounded-2xl text-left transition-all border-2 border-transparent hover:border-blue-200"
            >
              <p className="text-blue-700 font-bold text-lg">Let's go (Direct)</p>
              <p className="text-gray-500 text-sm">Start the timer and dive right in.</p>
            </button>

            {/* Option 2: Break down */}
            <button
              onClick={handleBreakdown}
              disabled={breakdownMutation.isPending}
              className="w-full p-5 bg-orange-50 hover:bg-orange-100 rounded-2xl text-left transition-all border-2 border-transparent hover:border-orange-200 disabled:opacity-50"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-800 font-bold text-lg">Make it easy</p>
                  <p className="text-gray-500 text-sm">
                    {breakdownMutation.isPending ? 'Breaking down...' : 'Break it down into small, manageable steps.'}
                  </p>
                </div>
                <span className="text-xl">☰</span>
              </div>
            </button>
          </div>
        );

      // ============ TIMER - Simple countdown ============
      case 'timer':
        return (
          <div className="focus-card animate-card-entrance">
            <div className="flex justify-center mb-4">
              <span className="text-4xl">🎯</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-center text-gray-800 mb-6">
              {activeTask?.text || currentTask?.text}
            </h2>
            
            {/* Big timer display with glow */}
            <div className="text-6xl md:text-7xl font-light text-[var(--karma-accent)] text-center mb-8 font-mono timer-glow">
              {formatTime(timeRemaining)}
            </div>

            {/* Done button */}
            <button
              onClick={handleComplete}
              disabled={completeTaskMutation.isPending}
              className="w-full py-4 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-full btn-lift disabled:opacity-50"
            >
              {completeTaskMutation.isPending ? 'Completing...' : '✓ Done!'}
            </button>
          </div>
        );

      // ============ BREAKDOWN TIMER - With subtasks ============
      case 'breakdown_timer':
        const completedCount = subtasks.filter((s) => s.completed).length;
        return (
          <div className="focus-card animate-fade-in">
            <h2 className="text-xl md:text-2xl font-bold text-center text-gray-800 mb-2">
              {activeTask?.text || currentTask?.text}
            </h2>
            
            {/* Timer display */}
            <div className="text-5xl md:text-6xl font-light text-[var(--karma-accent)] text-center mb-4 font-mono">
              {formatTime(timeRemaining)}
            </div>

            {/* Progress */}
            <div className="flex items-center justify-between text-sm text-gray-500 mb-2">
              <span>Progress</span>
              <span>{completedCount} of {subtasks.length}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mb-6">
              <div
                className="bg-[var(--karma-accent)] h-2 rounded-full transition-all"
                style={{ width: `${subtasks.length > 0 ? (completedCount / subtasks.length) * 100 : 0}%` }}
              />
            </div>

            {/* Subtask list */}
            <div className="space-y-2 mb-6 max-h-48 overflow-y-auto">
              {subtasks.map((subtask) => (
                <button
                  key={subtask.id}
                  onClick={() => toggleSubtask(subtask.id)}
                  className={`w-full p-3 rounded-xl text-left flex items-center gap-3 transition-all ${
                    subtask.completed
                      ? 'bg-green-50 text-green-700'
                      : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                      subtask.completed
                        ? 'bg-green-500 border-green-500 text-white'
                        : 'border-gray-300'
                    }`}
                  >
                    {subtask.completed && <span className="text-sm">✓</span>}
                  </div>
                  <span className={subtask.completed ? 'line-through' : ''}>{subtask.text}</span>
                </button>
              ))}
            </div>

            {/* Mark as done anyway */}
            <button
              onClick={handleComplete}
              className="w-full py-3 text-gray-500 hover:text-gray-700 font-medium transition-all"
            >
              Mark as done anyway
            </button>
          </div>
        );

      // ============ COMPLETED - Celebration ============
      case 'completed':
        return (
          <>
            <Confetti />
            <div className="focus-card animate-celebration">
              {/* Success icon */}
              <div className="flex justify-center mb-4">
                <div className="w-24 h-24 bg-gradient-to-br from-green-100 to-emerald-200 rounded-full flex items-center justify-center shadow-lg animate-check-pop">
                  <span className="text-5xl">🏆</span>
                </div>
              </div>

              <h2 className="text-3xl font-bold text-center text-gray-800 mb-2">
                Nice work! 🎉
              </h2>
              <p className="text-gray-500 text-center mb-8">
                You made progress. Every small step counts.
              </p>

              {/* Get another quick win */}
              <button
                onClick={handleGetAnother}
                className="w-full py-4 bg-[var(--karma-accent)] hover:bg-[var(--karma-accent-hover)] text-white font-semibold rounded-full btn-lift mb-3"
              >
                ↻ Get another quick win
              </button>

              {/* Exit */}
              <button
                onClick={onExit}
                className="w-full py-3 text-gray-500 hover:text-gray-700 font-medium transition-all flex items-center justify-center gap-2 hover:bg-gray-50 rounded-full"
              >
                ✕ I'm done for now
              </button>
            </div>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center p-4">
      {/* Back button - always visible at top */}
      {step !== 'landing' && (
        <button
          onClick={() => {
            if (step === 'completed') {
              onExit();
            } else if (step === 'suggestion') {
              setStep('landing');
              setCurrentTask(null);
            } else if (step === 'proceed_choice') {
              setStep('suggestion');
            } else if (step === 'timer' || step === 'breakdown_timer') {
              setStep('proceed_choice');
              setIsTimerRunning(false);
            } else {
              onExit();
            }
          }}
          className="self-start mb-4 text-gray-500 hover:text-gray-700 flex items-center gap-2 transition-all"
        >
          ← Back
        </button>
      )}
      <div className="w-full max-w-md">
        {renderStep()}
      </div>
    </div>
  );
}

