// Karma Frontend Types - Matching Backend Models

// Enums
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
export type TaskCategory = 
  | 'work' 
  | 'personal' 
  | 'health' 
  | 'learning' 
  | 'errands' 
  | 'creative' 
  | 'social' 
  | 'finance' 
  | 'home' 
  | 'other';
export type SubtaskStatus = 'pending' | 'in_progress' | 'completed' | 'skipped';

// Subtask Model
export interface Subtask {
  id: string;
  text: string;
  status: SubtaskStatus;
  estimated_minutes: number;
  order: number;
  progress?: number; // 0-100 percentage
}

// Energy level estimated by AI for a task (low | medium | high)
export type EnergyLevel = 'low' | 'medium' | 'high';

// Task Model
export interface Task {
  id: string;
  text: string;
  status: TaskStatus;
  priority: TaskPriority;
  category: TaskCategory;
  estimated_minutes: number;
  created_at: string;
  completed_at?: string;
  tags: string[];
  notes?: string;
  enrichment?: TaskEnrichment;
  subtasks: Subtask[];
  subtasks_generated: boolean;
  is_dummy: boolean;
  agent_reasoning?: string;
  /** AI-estimated energy level required for this task */
  energy_required?: EnergyLevel;
}

// Task Enrichment from AI research
export interface TaskEnrichment {
  summary?: string;
  steps?: string[];
  tips?: string[];
  resources?: Resource[];
  weather_info?: string;
  official_resources?: Resource[];
  research_timestamp?: string;
}

export interface Resource {
  title: string;
  url: string;
  description?: string;
}

// Quick Win Model
export interface QuickWin {
  id: string;
  text: string;
  category: TaskCategory;
  estimated_minutes: number;
  is_dummy: boolean;
}

// Session Context
export interface UserContext {
  available_minutes: number;
  energy_level: 'low' | 'medium' | 'high';
  location: 'home' | 'office' | 'commuting' | 'other';
  preferences: string[];
}

export interface Session {
  id: string;
  user_context: UserContext;
  tasks: Task[];
  completed_tasks: Task[];
  current_task?: Task;
  agent_reasoning?: string;
  current_reasoning?: string;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface HealthCheckResponse {
  status: string;
  app: string;
  version: string;
  ai_enabled: boolean;
  dummy_mode: boolean;
  agents: string[];
  capabilities: string[];
}

export interface TaskAnalysisResponse {
  tasks: Task[];
  reasoning: string;
}

export interface QuickWinResponse {
  quickwin: QuickWin;
  reasoning?: string;
}

export interface TaskBreakdownResponse {
  task_id: string;
  subtasks: Subtask[];
  reasoning?: string;
}

export interface TaskSuggestion {
  task: Task;
  reasoning: string;
  confidence_score?: number;
  is_generic_quickwin?: boolean;
  suggested_subtask?: Subtask;
  subtask_instruction?: string;
  subtask_estimated_minutes?: number;
}

export interface SuggestionResponse {
  session_id?: string;
  suggestion: TaskSuggestion;
  alternatives_available: boolean;
  message: string;
  has_subtask?: boolean;
  next_subtask?: Subtask;
  subtask_instruction?: string;
  subtask_estimated_minutes?: number;
}

export interface StatsData {
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  completed_today: number;
  completed_this_week: number;
  completion_rate: number;
  tasks_by_category: Record<TaskCategory, number>;
  tasks_by_priority: Record<TaskPriority, number>;
  average_completion_time_minutes: number;
  recent_completions?: Task[];
}

// Form Types
export interface AddTaskForm {
  text: string;
  priority?: TaskPriority;
  category?: TaskCategory;
  estimated_minutes?: number;
  tags?: string[];
}

export interface UpdateContextForm {
  available_minutes: number;
  energy_level: 'low' | 'medium' | 'high';
  location: 'home' | 'office' | 'commuting' | 'other';
}

// Component Props Types
export interface TaskCardProps {
  task: Task;
  onStatusChange?: (taskId: string, status: TaskStatus) => void;
  onSubtaskToggle?: (taskId: string, subtaskId: string) => void;
  onBreakdown?: (taskId: string) => void;
  onReResearch?: (taskId: string) => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export interface SubtaskListProps {
  subtasks: Subtask[];
  taskId: string;
  onToggle: (subtaskId: string) => void;
}

export interface QuickWinCardProps {
  quickwin: QuickWin;
  onAddTask: () => void;
  onSkip: () => void;
  isLoading?: boolean;
}

export interface NavItem {
  id: string;
  label: string;
  icon: string;
  path: string;
  badge?: number;
}

