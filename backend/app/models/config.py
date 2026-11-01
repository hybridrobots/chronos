"""Simulation configuration — all tunable organism parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .paradox import ResolutionStrategy


@dataclass
class SimulationConfig:
    """Full configuration for the Chronos simulation organism."""

    # Timing
    timestep: float = 0.1
    speed: float = 1.0
    auto_save_interval: float = 30.0

    # Randomness
    random_seed: int = 42

    # Growth / Decay
    default_growth: float = 0.05
    default_decay: float = 0.02
    growth_variance: float = 0.02
    decay_variance: float = 0.01
    max_weight: float = 100.0
    min_weight: float = 0.001
    weight_floor_archive: float = 0.01

    # Branching
    base_branch_probability: float = 0.08
    branch_threshold_weight: float = 0.5
    max_generation: int = 20
    branch_cost: float = 1.0

    # Population limits
    max_timelines: int = 200
    soft_capacity_ratio: float = 0.8

    # Events
    event_rate: float = 0.3
    max_events_per_cycle: int = 5
    event_types_weights: dict[str, float] = field(
        default_factory=lambda: {
            "historical_change": 0.2,
            "technological": 0.15,
            "social": 0.15,
            "environmental": 0.15,
            "unexpected": 0.15,
            "mutation": 0.1,
            "causal_conflict": 0.04,
        }
    )

    # Interactions
    interaction_rate: float = 0.1
    interaction_strength: float = 0.3
    max_interactions_per_cycle: int = 3
    feedback_loop_threshold: float = 0.9

    # Convergence
    convergence_similarity_threshold: float = 0.82
    convergence_rate: float = 0.03

    # Paradoxes
    paradox_detection_sensitivity: float = 0.5
    default_resolution_strategy: str = ResolutionStrategy.AUTO_BRANCH.value
    resolution_strategies_enabled: list[str] = field(
        default_factory=lambda: [
            ResolutionStrategy.ISOLATION.value,
            ResolutionStrategy.AUTO_BRANCH.value,
            ResolutionStrategy.CAUSAL_CORRECTION.value,
            ResolutionStrategy.PRESERVATION.value,
        ]
    )
    auto_resolve: bool = True

    # Resources
    max_energy: float = 1000.0
    timeline_capacity: int = 200
    branching_budget: float = 50.0
    memory_capacity: int = 10000
    mutation_budget: float = 30.0
    interaction_budget: float = 40.0
    resource_regen_rate: float = 0.05

    # History retention (never silent destroy — archive instead)
    max_active_events_per_timeline: int = 200
    archive_old_events: bool = True

    # Visualization update throttle (seconds wall-clock)
    ws_update_interval: float = 0.1

    # Learning / fitness loop
    learning_enabled: bool = True
    learning_rate: float = 0.15
    fitness_ema_alpha: float = 0.2
    think_cost: float = 1.5
    max_thinks_per_cycle: int = 4
    reward_refund_ratio: float = 0.5
    open_loop_growth_blend: float = 0.35  # rest is reward-shaped
    fitness_weights: dict[str, float] = field(
        default_factory=lambda: {
            "stability": 0.25,
            "diversity": 0.15,
            "complexity": 0.1,
            "goal_alignment": 0.25,
            "paradox_penalty": 0.15,
            "energy_efficiency": 0.1,
        }
    )
    # Soft goal: prefer moderate complexity + high stability (not unbounded growth)
    goal_complexity_target: float = 2.0
    goal_stability_target: float = 0.75
    policy_exploration: float = 0.25  # epsilon for bandit exploration

    # Homeostasis / self-sustaining metabolism
    homeostasis_enabled: bool = True
    homeostasis_health_target: float = 0.72
    energy_rest_threshold: float = 0.40  # rest thinks below this energy ratio
    homeostasis_soft_pop_ratio: float = 0.65
    homeostasis_hard_pop_ratio: float = 0.85
    homeostasis_memory_soft_ratio: float = 0.75
    homeostasis_max_cull_per_cycle: int = 3
    homeostasis_fitness_weight: float = 0.35  # organism survival in reward

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestep": self.timestep,
            "speed": self.speed,
            "auto_save_interval": self.auto_save_interval,
            "random_seed": self.random_seed,
            "default_growth": self.default_growth,
            "default_decay": self.default_decay,
            "growth_variance": self.growth_variance,
            "decay_variance": self.decay_variance,
            "max_weight": self.max_weight,
            "min_weight": self.min_weight,
            "weight_floor_archive": self.weight_floor_archive,
            "base_branch_probability": self.base_branch_probability,
            "branch_threshold_weight": self.branch_threshold_weight,
            "max_generation": self.max_generation,
            "branch_cost": self.branch_cost,
            "max_timelines": self.max_timelines,
            "soft_capacity_ratio": self.soft_capacity_ratio,
            "event_rate": self.event_rate,
            "max_events_per_cycle": self.max_events_per_cycle,
            "event_types_weights": self.event_types_weights,
            "interaction_rate": self.interaction_rate,
            "interaction_strength": self.interaction_strength,
            "max_interactions_per_cycle": self.max_interactions_per_cycle,
            "feedback_loop_threshold": self.feedback_loop_threshold,
            "convergence_similarity_threshold": self.convergence_similarity_threshold,
            "convergence_rate": self.convergence_rate,
            "paradox_detection_sensitivity": self.paradox_detection_sensitivity,
            "default_resolution_strategy": self.default_resolution_strategy,
            "resolution_strategies_enabled": self.resolution_strategies_enabled,
            "auto_resolve": self.auto_resolve,
            "max_energy": self.max_energy,
            "timeline_capacity": self.timeline_capacity,
            "branching_budget": self.branching_budget,
            "memory_capacity": self.memory_capacity,
            "mutation_budget": self.mutation_budget,
            "interaction_budget": self.interaction_budget,
            "resource_regen_rate": self.resource_regen_rate,
            "max_active_events_per_timeline": self.max_active_events_per_timeline,
            "archive_old_events": self.archive_old_events,
            "ws_update_interval": self.ws_update_interval,
            "learning_enabled": self.learning_enabled,
            "learning_rate": self.learning_rate,
            "fitness_ema_alpha": self.fitness_ema_alpha,
            "think_cost": self.think_cost,
            "max_thinks_per_cycle": self.max_thinks_per_cycle,
            "reward_refund_ratio": self.reward_refund_ratio,
            "open_loop_growth_blend": self.open_loop_growth_blend,
            "fitness_weights": self.fitness_weights,
            "goal_complexity_target": self.goal_complexity_target,
            "goal_stability_target": self.goal_stability_target,
            "policy_exploration": self.policy_exploration,
            "homeostasis_enabled": self.homeostasis_enabled,
            "homeostasis_health_target": self.homeostasis_health_target,
            "energy_rest_threshold": self.energy_rest_threshold,
            "homeostasis_soft_pop_ratio": self.homeostasis_soft_pop_ratio,
            "homeostasis_hard_pop_ratio": self.homeostasis_hard_pop_ratio,
            "homeostasis_memory_soft_ratio": self.homeostasis_memory_soft_ratio,
            "homeostasis_max_cull_per_cycle": self.homeostasis_max_cull_per_cycle,
            "homeostasis_fitness_weight": self.homeostasis_fitness_weight,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationConfig:
        cfg = cls()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg

    def apply_to_resources(self) -> dict[str, float | int]:
        return {
            "max_energy": self.max_energy,
            "computational_energy": self.max_energy,
            "timeline_capacity": self.timeline_capacity,
            "branching_budget": self.branching_budget,
            "max_branching_budget": self.branching_budget,
            "memory_capacity": self.memory_capacity,
            "mutation_budget": self.mutation_budget,
            "max_mutation_budget": self.mutation_budget,
            "interaction_budget": self.interaction_budget,
            "max_interaction_budget": self.interaction_budget,
        }
