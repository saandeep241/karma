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

const API_BASE = '/api';

// Generic fetch wrapper with error handling
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || `API Error: ${response.status}`);
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

export async function getStoredSuggestion(): Promise<SuggestionResponse> {
  return apiFetch<SuggestionResponse>('/suggestion/from-storage');
}

// Quick Wins
export async function getQuickWin(): Promise<QuickWinResponse> {
  return apiFetch<QuickWinResponse>('/quickwin/get');
}

export async function completeQuickWin(quickwin: QuickWin): Promise<Task> {
  return apiFetch<Task>('/quickwin/complete', {
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
};

export default api;

