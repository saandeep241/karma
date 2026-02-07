import { useState, useEffect, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { QuickWin, Task } from '../types';

// Types
type Mood = 'enthusiastic' | 'neutral' | 'tired' | 'overwhelmed' | 'low_energy';
type TimeAvailable = number;
type FlowStep = 'landing' | 'suggestion' | 'proceed_choice' | 'timer' | 'breakdown_timer' | 'completed';

// Confetti component removed as themed celebration icon is preferred

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

/**
 * Maps UI mood values to backend EmotionalState enum values.
 * Backend expects: motivated, happy, calm, focused, creative, tired, sleepy, stressed, anxious, bored, neutral
 */
function mapMoodToBackendEmotionalState(mood: Mood): string {
  const moodMap: Record<Mood, string> = {
    'enthusiastic': 'motivated',  // Enthusiastic -> motivated (energized, ready to go)
    'neutral': 'neutral',          // Neutral -> neutral (exact match)
    'tired': 'tired',              // Tired -> tired (exact match)
    'overwhelmed': 'stressed',    // Overwhelmed -> stressed (feeling pressured)
    'low_energy': 'tired',         // Low Energy -> tired (similar state)
  };
  return moodMap[mood];
}

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
  
  // Track suggested and completed task IDs to avoid suggesting them again
  const [excludedTaskIds, setExcludedTaskIds] = useState<string[]>([]);

  // Fetch a task suggestion
  const fetchSuggestion = useCallback(async () => {
    setIsLoadingTask(true);
    try {
      // Use the new suggestion endpoint that considers all tasks
      const energyLevel = mood === 'enthusiastic' ? 'high' : mood === 'tired' || mood === 'low_energy' ? 'low' : 'medium';
      const backendEmotionalState = mapMoodToBackendEmotionalState(mood);
      const data = await api.getStoredSuggestion({
        time_available: timeAvailable,
        energy_level: energyLevel,
        emotional_state: backendEmotionalState,
        excluded_task_ids: excludedTaskIds,
      });
      if (data?.suggestion?.task) {
        // Convert suggestion to QuickWin format for compatibility
        const task = data.suggestion.task;
        const isQuickWin = data.suggestion.is_generic_quickwin === true;
        // When backend returns a QuickWin (nothing fit time/energy), task has a one-off id; treat as new so "Let's go" creates via completeQuickWin
        const taskId = isQuickWin ? '' : (task.id || '');

        // Only add to excluded list if it's a real task from the list (not a QuickWin)
        if (taskId && !excludedTaskIds.includes(taskId)) {
          setExcludedTaskIds(prev => [...prev, taskId]);
        }

        setCurrentTask({
          id: taskId,
          text: task.text,
          estimated_minutes: task.estimated_minutes || timeAvailable,
          category: task.category || 'other',
          is_dummy: task.is_dummy || false,
        });
        setStep('suggestion');
      } else {
        // Fallback to quickwin if no suggestion
        const backendEmotionalState = mapMoodToBackendEmotionalState(mood);
        const quickwinData = await api.getQuickWin(timeAvailable, backendEmotionalState);
        if (quickwinData?.quickwin) {
          setCurrentTask(quickwinData.quickwin);
          setStep('suggestion');
        }
      }
    } catch (error) {
      console.error('Failed to fetch suggestion:', error);
      // Fallback to quickwin on error
      try {
        const backendEmotionalState = mapMoodToBackendEmotionalState(mood);
        const quickwinData = await api.getQuickWin(timeAvailable, backendEmotionalState);
        if (quickwinData?.quickwin) {
          setCurrentTask(quickwinData.quickwin);
          setStep('suggestion');
        }
      } catch (fallbackError) {
        console.error('Failed to fetch quickwin fallback:', fallbackError);
      }
    } finally {
      setIsLoadingTask(false);
    }
  }, [timeAvailable, mood, excludedTaskIds]);

  // Add task mutation
  const addTaskMutation = useMutation({
    mutationFn: (quickwin: QuickWin) => api.completeQuickWin(quickwin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] }); // Also invalidate stats
    },
  });

  // Breakdown task mutation
  const breakdownMutation = useMutation({
    mutationFn: (taskId: string) => api.breakdownTask(taskId, { saveSubtasks: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] }); // Also invalidate stats
    },
  });

  // Complete task mutation
  const completeTaskMutation = useMutation({
    mutationFn: (taskId: string) => api.updateTaskStatus(taskId, 'completed'),
    onSuccess: (_, taskId) => {
      // Add completed task to excluded list so it won't be suggested again
      if (taskId && !excludedTaskIds.includes(taskId)) {
        setExcludedTaskIds(prev => [...prev, taskId]);
      }
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] }); // Also invalidate stats
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
      // If task already exists (has an ID from storage), update its status instead of creating a new one
      if (currentTask.id && currentTask.id.trim() !== '') {
        // Task exists in database - update its status to in_progress
        await api.updateTaskStatus(currentTask.id, 'in_progress');
        // Invalidate queries to refresh task list
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        setActiveTask({
          id: currentTask.id,
          text: currentTask.text,
          status: 'in_progress',
          priority: 'medium',
          category: currentTask.category?.toLowerCase() || 'other',
          estimated_minutes: currentTask.estimated_minutes || timeAvailable,
          subtasks: [],
          created_at: new Date().toISOString(),
          tags: currentTask.category ? [currentTask.category] : [],
          subtasks_generated: false,
          is_dummy: currentTask.is_dummy,
        } as Task);
        setStep('proceed_choice');
      } else {
        // Task doesn't exist (quickwin) - create a new task
        const result = await addTaskMutation.mutateAsync(currentTask);
        if (result?.success && result?.task_id) {
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
      }
    } catch (error) {
      console.error('Failed to add/update task:', error);
    }
  };

  // Handle skip - go back to landing to select new mood/time
  const handleSkip = () => {
    // Add skipped task to excluded list so it won't be suggested again immediately
    if (currentTask?.id && !excludedTaskIds.includes(currentTask.id)) {
      setExcludedTaskIds(prev => [...prev, currentTask.id]);
    }
    setCurrentTask(null);
    setStep('landing');
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

  // Handle subtask toggle
  const toggleSubtask = (id: string) => {
    setSubtasks((prev) => {
      const updated = prev.map((s) => (s.id === id ? { ...s, completed: !s.completed } : s));
      const allCompleted = updated.length > 0 && updated.every((s) => s.completed);
      if (allCompleted && activeTask) {
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
    // Keep excludedTaskIds so we don't suggest the same tasks again
  };

  // Render based on current step
  const renderStep = () => {
    switch (step) {
      case 'landing':
        return (
          <div className="w-full max-w-lg flex flex-col items-center">
            <p className="text-center text-[18px] text-gray-500 mb-4">Good Afternoon</p>
            <h1 className="text-[42px] font-sans font-bold text-center mb-2 text-[#1a1a1a] leading-none tracking-tight">
              Make it count.
            </h1>
            <p className="text-gray-400 text-[18px] text-center mb-12">What's your vibe right now?</p>

            {/* Time Available */}
            <div className="mb-10 w-full px-4">
              <div className="flex justify-between items-center mb-6">
                <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">
                  TIME AVAILABLE: {timeAvailable}m
                </p>
              </div>
              <div className="relative pt-2 pb-2">
                <input
                  type="range"
                  min="2"
                  max="30"
                  step="1"
                  value={timeAvailable}
                  onChange={(e) => setTimeAvailable(Number(e.target.value))}
                  className="w-full h-[2px] bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#0066cc]"
                />
                <div className="flex justify-between mt-6 px-1">
                  <span className="text-[11px] font-bold text-gray-400">2m</span>
                  <span className="text-[11px] font-bold text-gray-400">15m</span>
                  <span className="text-[11px] font-bold text-gray-400">30m+</span>
                </div>
              </div>
            </div>

            {/* Current Mood */}
            <div className="mb-12 w-full px-4">
              <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest text-center mb-8">
                CURRENT MOOD
              </p>
              <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-4 max-w-full overflow-hidden">
                {MOODS.slice(0, 3).map((m) => (
                  <button
                    key={m.value}
                    onClick={() => setMood(m.value)}
                    className={`flex items-center justify-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 sm:py-3 rounded-full text-xs sm:text-[14px] font-medium transition-all border flex-shrink-0 ${
                      mood === m.value
                        ? 'bg-white border-gray-300 text-gray-900 shadow-sm scale-[1.02]'
                        : 'bg-white border-gray-100 text-gray-400 hover:border-gray-200'
                    }`}
                  >
                    <span className="truncate">{m.label}</span>
                    <span className={`flex-shrink-0 ${mood === m.value ? 'text-gray-900' : 'text-gray-400'}`}>
                      {m.value === 'enthusiastic' ? (
                        <svg width="14" height="14" className="sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <path d="M8 14s1.5 2 4 2 4-2 4-2"></path>
                          <line x1="9" y1="9" x2="9.01" y2="9"></line>
                          <line x1="15" y1="9" x2="15.01" y2="9"></line>
                        </svg>
                      ) : m.value === 'neutral' ? (
                        <svg width="14" height="14" className="sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <line x1="8" y1="15" x2="16" y2="15"></line>
                          <line x1="9" y1="9" x2="9.01" y2="9"></line>
                          <line x1="15" y1="9" x2="15.01" y2="9"></line>
                        </svg>
                      ) : (
                        <svg width="14" height="14" className="sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <path d="M16 16s-1.5-2-4-2-4 2-4 2"></path>
                          <line x1="9" y1="9" x2="9.01" y2="9"></line>
                          <line x1="15" y1="9" x2="15.01" y2="9"></line>
                        </svg>
                      )}
                    </span>
                  </button>
                ))}
              </div>
              <div className="flex justify-center gap-2 sm:gap-4 flex-wrap">
                {MOODS.slice(3).map((m) => (
                  <button
                    key={m.value}
                    onClick={() => setMood(m.value)}
                    className={`flex items-center justify-center gap-1 sm:gap-2 px-4 sm:px-8 py-2 sm:py-3 rounded-full text-xs sm:text-[14px] font-medium transition-all border flex-shrink-0 ${
                      mood === m.value
                        ? 'bg-white border-gray-300 text-gray-900 shadow-sm scale-[1.02]'
                        : 'bg-white border-gray-100 text-gray-400 hover:border-gray-200'
                    }`}
                  >
                    <span className="truncate">{m.label}</span>
                    <span className={`flex-shrink-0 ${mood === m.value ? 'text-gray-900' : 'text-gray-400'}`}>
                      {m.value === 'overwhelmed' ? (
                        <svg width="14" height="14" className="sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polyline>
                        </svg>
                      ) : (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="2" y="7" width="18" height="10" rx="2" ry="2"></rect>
                          <line x1="22" y1="11" x2="22" y2="13"></line>
                          <line x1="6" y1="11" x2="10" y2="11"></line>
                        </svg>
                      )}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Start Button */}
            <button
              onClick={fetchSuggestion}
              disabled={isLoadingTask}
              className="w-full py-5 bg-[#0066cc] hover:bg-[#0052a3] text-white font-bold rounded-full transition-all disabled:opacity-50 text-[17px] shadow-lg shadow-blue-100"
            >
              {isLoadingTask ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="spinner" style={{ width: '1.2rem', height: '1.2rem', borderWidth: '2px' }} />
                  Finding a task...
                </span>
              ) : "Let's go →"}
            </button>
          </div>
        );

      case 'suggestion':
        if (!currentTask) return null;
        return (
          <div className="w-full max-w-lg flex flex-col items-center animate-card-entrance">
            <h2 className="text-[18px] text-gray-500 mb-6 text-center">
              Why don't you take {currentTask.estimated_minutes || timeAvailable} minutes to...
            </h2>
            
            <h1 className="text-[42px] font-sans font-bold text-center mb-4 text-[#1a1a1a] leading-tight tracking-tight">
              {currentTask.text}?
            </h1>

            {currentTask.category && (
              <p className="text-gray-400 text-[16px] text-center mb-12">
                {currentTask.category}
              </p>
            )}
            
            <div className="flex gap-4 w-full px-4">
              <button
                onClick={handleSkip}
                className="flex-1 py-4 px-6 border border-gray-100 hover:border-gray-200 text-gray-500 font-bold rounded-full transition-all text-[15px] flex items-center justify-center gap-2"
              >
                <span>↻</span> Skip
              </button>
              
              <button
                onClick={handleLetsGo}
                disabled={addTaskMutation.isPending}
                className="flex-[2] py-4 px-8 bg-[#0066cc] hover:bg-[#0052a3] text-white font-bold rounded-full transition-all disabled:opacity-50 text-[15px] shadow-lg shadow-blue-100 flex items-center justify-center gap-2"
              >
                {addTaskMutation.isPending ? 'Adding...' : "Start Task →"}
              </button>
            </div>
          </div>
        );

      case 'proceed_choice':
        return (
          <div className="w-full max-w-lg flex flex-col items-center animate-fade-in">
            <h2 className="text-2xl md:text-3xl font-bold text-center text-gray-800 mb-2">
              How would you like to proceed?
            </h2>
            <p className="text-gray-500 text-center mb-8">Choose the path that feels right.</p>
            <button
              onClick={handleDirectStart}
              className="w-full p-5 mb-3 bg-blue-50 hover:bg-blue-100 rounded-2xl text-left transition-all border-2 border-transparent hover:border-blue-200"
            >
              <p className="text-blue-700 font-bold text-lg">Let's go</p>
              <p className="text-gray-500 text-sm">Start the timer and dive right in.</p>
            </button>
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

      case 'timer':
        return (
          <div className="w-full max-w-lg flex flex-col items-center animate-card-entrance">
            <h2 className="text-[24px] font-sans font-bold text-center text-[#001a41] mb-8 leading-tight">
              {activeTask?.text || currentTask?.text}
            </h2>
            <div className="text-[120px] font-sans font-bold text-[#0066cc] mb-12 tabular-nums leading-none">
              {formatTime(timeRemaining)}
            </div>
            <button
              onClick={handleComplete}
              disabled={completeTaskMutation.isPending}
              className="px-12 py-4 bg-[#10b981] text-white rounded-full font-bold text-[16px] hover:bg-[#059669] transition-all shadow-lg shadow-green-100 flex items-center gap-2"
            >
              {completeTaskMutation.isPending ? 'Completing...' : '✓ Done!'}
            </button>
          </div>
        );

      case 'breakdown_timer':
        const completedCount = subtasks.filter((s) => s.completed).length;
        return (
          <div className="w-full max-w-lg flex flex-col items-center animate-fade-in">
            <h2 className="text-[24px] font-sans font-bold text-center text-[#001a41] mb-8 leading-tight">
              {activeTask?.text || currentTask?.text}
            </h2>
            <div className="text-[80px] font-sans font-bold text-[#0066cc] mb-8 tabular-nums leading-none">
              {formatTime(timeRemaining)}
            </div>
            <div className="flex items-center justify-between text-[13px] font-medium text-gray-500 mb-2 w-full">
              <span>Progress</span>
              <span>{completedCount} of {subtasks.length}</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1.5 mb-8">
              <div
                className="bg-[#10b981] h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${subtasks.length > 0 ? (completedCount / subtasks.length) * 100 : 0}%` }}
              />
            </div>
            <div className="space-y-3 mb-8 w-full max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
              {subtasks.map((subtask) => (
                <button
                  key={subtask.id}
                  onClick={() => toggleSubtask(subtask.id)}
                  className={`w-full p-4 rounded-2xl text-left flex items-center gap-4 transition-all border ${
                    subtask.completed
                      ? 'bg-green-50 border-green-100 text-green-700'
                      : 'bg-white border-gray-100 text-[#4b5563] hover:border-gray-200'
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                      subtask.completed
                        ? 'bg-[#10b981] border-[#10b981] text-white'
                        : 'border-gray-200'
                    }`}
                  >
                    {subtask.completed && <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>}
                  </div>
                  <span className={`text-[15px] font-medium ${subtask.completed ? 'line-through opacity-60' : ''}`}>{subtask.text}</span>
                </button>
              ))}
            </div>
            <button
              onClick={handleComplete}
              className="text-[14px] font-medium text-gray-400 hover:text-gray-600 transition-colors"
            >
              Mark as done anyway
            </button>
          </div>
        );

      case 'completed':
        return (
          <div className="flex flex-col items-center max-w-2xl w-full animate-in fade-in zoom-in duration-500">
            <div className="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center mb-10 shadow-sm">
              <div className="text-[#0066cc]">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2L14.85 9.15L22 12L14.85 14.85L12 22L9.15 14.85L2 12L9.15 9.15L12 2Z" fill="currentColor"/>
                </svg>
              </div>
            </div>
            <h2 className="text-[36px] font-sans font-bold text-[#001a41] mb-4 text-center">Excellent work!</h2>
            <p className="text-[#4b5563] text-[16px] mb-12 text-center font-medium">You've successfully nudged yourself forward.</p>
            
            <div className="flex flex-col items-center gap-4 w-full max-w-sm">
              <button
                onClick={handleGetAnother}
                className="w-full py-4 bg-[#0066cc] text-white rounded-full font-bold text-[16px] hover:bg-[#0052a3] transition-all shadow-lg shadow-blue-100 flex items-center justify-center gap-2"
              >
                <span>↻</span> Get another quick win
              </button>
              <button
                onClick={onExit}
                className="w-full py-4 text-gray-400 hover:text-gray-600 font-bold text-[15px] transition-colors"
              >
                ✕ I'm done for now
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center p-4 relative">
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
          className="absolute top-0 left-4 text-gray-400 hover:text-gray-600 flex items-center gap-2 transition-all text-[15px] font-medium z-10"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <span>Back</span>
        </button>
      )}
      <div className="w-full flex justify-center">
        {renderStep()}
      </div>
    </div>
  );
}
