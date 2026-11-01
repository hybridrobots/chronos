import { create } from "zustand";
import type {
  LearningSnapshot,
  OrganismState,
  Paradox,
  Relationship,
  ScreenId,
  SimSnapshot,
  Timeline,
} from "../types";

interface ChronosState {
  connected: boolean;
  simTime: number;
  simState: string;
  speed: number;
  timelines: Timeline[];
  relationships: Relationship[];
  paradoxes: Paradox[];
  organism: OrganismState | null;
  config: Record<string, unknown>;
  cycleStats: Record<string, unknown>;
  normalizedWeights: Record<string, number>;
  learning: LearningSnapshot | null;
  selectedTimelineId: string | null;
  screen: ScreenId;
  applySnapshot: (snap: SimSnapshot) => void;
  setConnected: (v: boolean) => void;
  selectTimeline: (id: string | null) => void;
  setScreen: (s: ScreenId) => void;
}

const emptyOrganism = (): OrganismState => ({
  resources: {
    computational_energy: 0,
    max_energy: 1000,
    timeline_capacity: 200,
    branching_budget: 0,
    max_branching_budget: 50,
    memory_capacity: 10000,
    memory_used: 0,
    mutation_budget: 0,
    max_mutation_budget: 30,
    interaction_budget: 0,
    max_interaction_budget: 40,
  },
  health: 1,
  stability: 1,
  diversity: 0,
  total_complexity: 0,
  active_timeline_count: 0,
  total_timeline_count: 0,
  paradox_count: 0,
  unresolved_paradox_count: 0,
  mean_weight: 0,
  mean_growth: 0,
  mean_decay: 0,
  generation_depth: 0,
  age: 0,
  total_events: 0,
  total_interactions: 0,
  total_convergences: 0,
  total_branches: 0,
  cycle_count: 0,
  mean_fitness: 0,
  mean_fitness_ema: 0,
  total_reward: 0,
  total_thinks: 0,
  best_fitness: 0,
  learning_cycles: 0,
  metabolic_throttle: 1,
  homeostasis_mode: "thrive",
});

export const useChronosStore = create<ChronosState>((set) => ({
  connected: false,
  simTime: 0,
  simState: "stopped",
  speed: 1,
  timelines: [],
  relationships: [],
  paradoxes: [],
  organism: emptyOrganism(),
  config: {},
  cycleStats: {},
  normalizedWeights: {},
  learning: null,
  selectedTimelineId: null,
  screen: "universe",

  applySnapshot: (snap) =>
    set({
      simTime: snap.sim_time,
      simState: snap.state,
      speed: snap.speed,
      timelines: snap.timelines ?? [],
      relationships: snap.relationships ?? [],
      paradoxes: snap.paradoxes ?? [],
      organism: snap.organism ?? emptyOrganism(),
      config: snap.config ?? {},
      cycleStats: snap.cycle_stats ?? {},
      normalizedWeights: snap.normalized_weights ?? {},
      learning: snap.learning ?? null,
    }),

  setConnected: (v) => set({ connected: v }),
  selectTimeline: (id) => set({ selectedTimelineId: id }),
  setScreen: (s) => set({ screen: s }),
}));
