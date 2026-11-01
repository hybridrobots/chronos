export type TimelineStatus =
  | "nascent"
  | "active"
  | "growing"
  | "decaying"
  | "mutating"
  | "converging"
  | "isolated"
  | "archived"
  | "paradoxical";

export interface TimelineEvent {
  id: string;
  timeline_id: string;
  event_type: string;
  simulation_time: number;
  wall_timestamp: number;
  description: string;
  payload: Record<string, unknown>;
  version: number;
  parent_event_id?: string | null;
  superseded_by?: string | null;
  is_active: boolean;
  causal_deps: string[];
  influence: number;
}

export interface Timeline {
  id: string;
  parent_id: string | null;
  creation_timestamp: number;
  simulation_birth_time: number;
  generation: number;
  growth_coefficient: number;
  decay_coefficient: number;
  initial_weight: number;
  current_weight: number;
  influence_weight: number;
  stability_score: number;
  structural_complexity: number;
  branching_probability: number;
  mutation_history: Record<string, unknown>[];
  interaction_ids: string[];
  convergence_ids: string[];
  historical_version: number;
  status: TimelineStatus;
  position: [number, number, number];
  color_hue: number;
  last_update_time: number;
  archived: boolean;
  event_count?: number;
  events?: TimelineEvent[];
  recent_events?: TimelineEvent[];
  fitness?: number;
  fitness_ema?: number;
  cumulative_reward?: number;
  last_reward?: number;
  last_action?: string;
  think_count?: number;
}

export interface Relationship {
  id: string;
  source_id: string;
  target_id: string;
  rel_type: string;
  strength: number;
  simulation_time: number;
  metadata: Record<string, unknown>;
  active: boolean;
}

export interface Paradox {
  id: string;
  affected_timeline_ids: string[];
  contradictory_events: Record<string, unknown>[];
  causal_dependencies: string[];
  severity: number;
  detection_time: number;
  wall_timestamp: number;
  resolution_strategy: string | null;
  status: string;
  description: string;
  resolution_record: Record<string, unknown>[];
  history: Record<string, unknown>[];
}

export interface ResourcePool {
  computational_energy: number;
  max_energy: number;
  timeline_capacity: number;
  branching_budget: number;
  max_branching_budget: number;
  memory_capacity: number;
  memory_used: number;
  mutation_budget: number;
  max_mutation_budget: number;
  interaction_budget: number;
  max_interaction_budget: number;
}

export interface OrganismState {
  resources: ResourcePool;
  health: number;
  stability: number;
  diversity: number;
  total_complexity: number;
  active_timeline_count: number;
  total_timeline_count: number;
  paradox_count: number;
  unresolved_paradox_count: number;
  mean_weight: number;
  mean_growth: number;
  mean_decay: number;
  generation_depth: number;
  age: number;
  total_events: number;
  total_interactions: number;
  total_convergences: number;
  total_branches: number;
  cycle_count: number;
  mean_fitness?: number;
  mean_fitness_ema?: number;
  total_reward?: number;
  total_thinks?: number;
  best_fitness?: number;
  learning_cycles?: number;
  metabolic_throttle?: number;
  homeostasis_mode?: string;
}

export interface LearningSnapshot {
  enabled?: boolean;
  last?: {
    thinks?: number;
    mean_reward?: number;
    policy_q?: Record<string, number>;
  };
  action_stats?: Record<string, { count: number; mean: number; last: number }>;
  recent_rewards?: {
    timeline_id: string;
    action: string;
    reward: number;
    sim_time: number;
  }[];
}

export interface SimSnapshot {
  type: string;
  sim_time: number;
  state: string;
  speed: number;
  timelines: Timeline[];
  relationships: Relationship[];
  paradoxes: Paradox[];
  organism: OrganismState;
  cycle_stats: Record<string, unknown>;
  normalized_weights: Record<string, number>;
  config: Record<string, unknown>;
  learning?: LearningSnapshot;
}

export type ScreenId =
  | "universe"
  | "explorer"
  | "observatory"
  | "health"
  | "laboratory"
  | "counsel";
