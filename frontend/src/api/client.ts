// Karma API Client
import type {
  Task,
  QuickWin,
  Session,
  HealthCheckResponse,
  TaskAnalysisResponse,
  QuickWinResponse,
  TaskBreakdownResponse,
  SuggestionResponse,
  StatsData,
  AddTaskForm,
  UpdateContextForm,
  TaskStatus,
  SubtaskStatus,
} from '../types';

// Use VITE_API_URL if set (for production), otherwise use /api (for local dev with proxy)
const API_BASE = import.meta.env.VITE_API_URL || '/api';

// Log the API base URL for debugging (visible in browser console)
console.log('🔗 API Base URL configured:', API_BASE);
console.log('🔗 Full API URL example:', `${API_BASE}/tasks/stats`);

// Import token getter
import { getAuthToken } from './authToken';

// Generic fetch wrapper with error handling and authentication
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  // Log the actual URL being called (only in development or first few calls)
  if (import.meta.env.DEV || !(window as any).__api_logged) {
    console.log('🌐 API Call:', url);
    (window as any).__api_logged = true;
  }
  
  // Get auth token tettestestes
  const token = await getAuthToken();
  
  // Build headers with auth token if available
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // Handle 401 Unauthorized - authentication required
    if (response.status === 401) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(errorData.detail || 'Authentication required');
      (error as any).status = 401;
      (error as any).code = 'UNAUTHORIZED';
      throw error;
    }
    
    // Handle 403 Forbidden - usually means token is invalid/expired
    if (response.status === 403) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(errorData.detail || 'Invalid or expired authentication token');
      (error as any).status = 403;
      (error as any).code = 'FORBIDDEN';
      throw error;
    }
    
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.detail || errorData.message || `API Error: ${response.status}`);
    (error as any).status = response.status;
    throw error;
  }

  return response.json();
}

// Health Check
export async function checkHealth(): Promise<HealthCheckResponse> {
  return apiFetch<HealthCheckResponse>('/health');
}

// Session Management
export async function getSession(): Promise<Session> {
  return apiFetch<Session>('/session/current');
}

export async function updateContext(context: UpdateContextForm): Promise<Session> {
  return apiFetch<Session>('/session/context', {
    method: 'POST',
    body: JSON.stringify(context),
  });
}

// Task Management
interface TasksByDateResponse {
  tasks_by_date: Record<string, { tasks: Task[] }>;
  total_dates: number;
  stats: StatsData;
}

export async function getAllTasks(): Promise<Task[]> {
  const response = await apiFetch<TasksByDateResponse>('/tasks/all');
  
  // Flatten tasks from all dates into a single array
  const allTasks: Task[] = [];
  for (const dateData of Object.values(response.tasks_by_date)) {
    if (dateData.tasks) {
      allTasks.push(...dateData.tasks);
    }
  }
  return allTasks;
}

export async function getTask(taskId: string): Promise<Task> {
  return apiFetch<Task>(`/tasks/${taskId}`);
}

export async function addTask(task: AddTaskForm): Promise<Task> {
  return apiFetch<Task>('/tasks/add', {
    method: 'POST',
    body: JSON.stringify(task),
  });
}

export async function importTasks(texts: string[]): Promise<TaskAnalysisResponse> {
  // Join texts into a single string with newlines for the import endpoint
  const textContent = texts.join('\n');
  return apiFetch<TaskAnalysisResponse>('/todo/import', {
    method: 'POST',
    body: JSON.stringify({ text_content: textContent }),
  });
}

export async function updateTaskStatus(
  taskId: string,
  status: TaskStatus
): Promise<Task> {
  return apiFetch<Task>(`/tasks/${taskId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  });
}

export async function deleteTask(taskId: string): Promise<{ success: boolean }> {
  return apiFetch<{ success: boolean }>(`/tasks/${taskId}`, {
    method: 'DELETE',
  });
}

export async function deleteAllTasks(): Promise<{ success: boolean; deleted_count: number }> {
  return apiFetch<{ success: boolean; deleted_count: number }>('/tasks/delete-all', {
    method: 'DELETE',
  });
}

// Task Breakdown (Subtasks)
export async function breakdownTask(taskId: string): Promise<TaskBreakdownResponse> {
  return apiFetch<TaskBreakdownResponse>(`/tasks/${taskId}/breakdown`, {
    method: 'POST',
  });
}

export async function getTaskSubtasks(taskId: string): Promise<{ subtasks: import('../types').Subtask[] }> {
  return apiFetch<{ subtasks: import('../types').Subtask[] }>(`/tasks/${taskId}/subtasks`);
}

export async function updateSubtaskStatus(
  taskId: string,
  subtaskId: string,
  status: SubtaskStatus
): Promise<{ success: boolean }> {
  return apiFetch<{ success: boolean }>(
    `/task/subtask/status`,
    {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId, subtask_id: subtaskId, status }),
    }
  );
}

export async function updateSubtaskProgress(
  taskId: string,
  subtaskId: string,
  progress: number
): Promise<{ success: boolean; parent_completed: boolean }> {
  return apiFetch<{ success: boolean; parent_completed: boolean }>(
    `/task/subtask/progress`,
    {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId, subtask_id: subtaskId, progress }),
    }
  );
}

export async function addSubtask(
  taskId: string,
  text: string,
  estimatedMinutes: number = 5
): Promise<{ success: boolean; subtask: import('../types').Subtask }> {
  return apiFetch<{ success: boolean; subtask: import('../types').Subtask }>(
    `/task/subtask/add`,
    {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId, text, estimated_minutes: estimatedMinutes }),
    }
  );
}

// Task Re-research
export async function reResearchTask(taskId: string): Promise<Task> {
  return apiFetch<Task>(`/tasks/${taskId}/reresearch`, {
    method: 'POST',
  });
}

// Suggestions
export async function getSuggestion(): Promise<SuggestionResponse> {
  return apiFetch<SuggestionResponse>('/suggestion/get');
}

export async function getStoredSuggestion(request: {
  time_available: number;
  energy_level: string;
  emotional_state?: string;
  excluded_task_ids?: string[];
}): Promise<SuggestionResponse> {
  return apiFetch<SuggestionResponse>('/suggestion/from-storage', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Quick Wins
export async function getQuickWin(minutes?: number, mood?: string): Promise<QuickWinResponse> {
  const params = new URLSearchParams();
  if (minutes) params.append('minutes', minutes.toString());
  if (mood) params.append('mood', mood);
  const endpoint = `/quickwin/get${params.toString() ? `?${params.toString()}` : ''}`;
  return apiFetch<QuickWinResponse>(endpoint);
}

export async function completeQuickWin(quickwin: QuickWin): Promise<{ success: boolean; task_id: string; message: string }> {
  return apiFetch<{ success: boolean; task_id: string; message: string }>('/quickwin/complete', {
    method: 'POST',
    body: JSON.stringify(quickwin),
  });
}

// Stats
export async function getStats(): Promise<StatsData> {
  return apiFetch<StatsData>('/tasks/stats');
}

// Learning Insights
export async function getLearningInsights(): Promise<{ insights: string[] }> {
  return apiFetch<{ insights: string[] }>('/session/insights');
}

// Continuable Tasks (in-progress and almost done)
export interface SubtaskProgress {
  completed: number;
  total: number;
  percentage: number;
}

export interface ContinuableTask extends Task {
  subtask_progress?: SubtaskProgress;
}

export interface ContinuableTasksResponse {
  in_progress: ContinuableTask[];
  almost_done: ContinuableTask[];
  total_continuable: number;
}

export async function getContinuableTasks(): Promise<ContinuableTasksResponse> {
  return apiFetch<ContinuableTasksResponse>('/tasks/continuable');
}

export async function getInProgressTasks(): Promise<{ tasks: Task[]; count: number }> {
  return apiFetch<{ tasks: Task[]; count: number }>('/tasks/in-progress');
}

// Presentation API
export interface Slide {
  id: number;
  title: string;
  type: string;
  content: string;
  code: string | null;
  notes: string | null;
}

export interface Presentation {
  title: string;
  subtitle: string;
  slides: Slide[];
}

export interface CodeExecutionResult {
  success: boolean;
  output: string;
  error: string | null;
  figures: string[];
}

export async function getPresentation(): Promise<Presentation> {
  return apiFetch<Presentation>('/presentation/slides');
}

export async function executeCode(code: string, sessionId: string = 'default'): Promise<CodeExecutionResult> {
  return apiFetch<CodeExecutionResult>('/presentation/execute', {
    method: 'POST',
    body: JSON.stringify({ code, session_id: sessionId }),
  });
}

export async function resetPresentationSession(sessionId: string = 'default'): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/presentation/reset?session_id=${sessionId}`, {
    method: 'POST',
  });
}

// Admin API functions
export async function checkAdmin(): Promise<{
  is_admin: boolean;
  user_id: string;
  email: string | null;
}> {
  return apiFetch('/admin/check');
}

export async function getAllUserTokenLimits(): Promise<{
  users: Array<{
    user_id: string;
    monthly_limit: number;
    tokens_used_this_month: number;
    tokens_remaining: number;
    usage_percentage: number;
    current_month: string;
    last_reset_at: string;
    usage_stats: any;
  }>;
  total_users: number;
  default_limit: number;
}> {
  return apiFetch('/admin/users/token-limits');
}

export async function updateUserTokenLimit(
  userId: string,
  newLimit: number
): Promise<{ success: boolean; message: string; limit_info: any }> {
  return apiFetch(`/tokens/limit/${userId}`, {
    method: 'POST',
    body: JSON.stringify({ new_limit: newLimit }),
  });
}

export async function resetUserTokenUsage(
  userId: string
): Promise<{ success: boolean; message: string; limit_info: any }> {
  return apiFetch(`/tokens/reset/${userId}`, {
    method: 'POST',
  });
}

export async function getTokenLimit(): Promise<{
  user_id: string;
  monthly_limit: number;
  tokens_used_this_month: number;
  tokens_remaining: number;
  usage_percentage: number;
  current_month: string;
}> {
  return apiFetch('/tokens/limit');
}

// Export all functions as a single API object for convenience
export const api = {
  checkHealth,
  getSession,
  updateContext,
  getAllTasks,
  getTask,
  addTask,
  importTasks,
  updateTaskStatus,
  deleteTask,
  deleteAllTasks,
  breakdownTask,
  getTaskSubtasks,
  updateSubtaskStatus,
  updateSubtaskProgress,
  addSubtask,
  reResearchTask,
  getSuggestion,
  getStoredSuggestion,
  getQuickWin,
  completeQuickWin,
  getStats,
  getLearningInsights,
  getContinuableTasks,
  getInProgressTasks,
  // Presentation
  getPresentation,
  executeCode,
  resetPresentationSession,
  // Admin
  checkAdmin,
  getAllUserTokenLimits,
  updateUserTokenLimit,
  resetUserTokenUsage,
  getTokenLimit,
};

export default api;

