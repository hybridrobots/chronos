"""Organism metabolism and health state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourcePool:
    """Simulated computational resources of the organism."""

    computational_energy: float = 1000.0
    max_energy: float = 1000.0
    timeline_capacity: int = 200
    branching_budget: float = 50.0
    max_branching_budget: float = 50.0
    memory_capacity: int = 10000
    memory_used: int = 0
    mutation_budget: float = 30.0
    max_mutation_budget: float = 30.0
    interaction_budget: float = 40.0
    max_interaction_budget: float = 40.0

    def regenerate(
        self, dt: float, regen_rate: float = 0.05, multiplier: float = 1.0
    ) -> None:
        """Slowly regenerate expendable resources (multiplier for rest metabolism)."""
        m = max(0.1, multiplier)
        self.computational_energy = min(
            self.max_energy,
            self.computational_energy + self.max_energy * regen_rate * dt * m,
        )
        self.branching_budget = min(
            self.max_branching_budget,
            self.branching_budget + self.max_branching_budget * regen_rate * dt * 0.5 * m,
        )
        self.mutation_budget = min(
            self.max_mutation_budget,
            self.mutation_budget + self.max_mutation_budget * regen_rate * dt * 0.4 * m,
        )
        self.interaction_budget = min(
            self.max_interaction_budget,
            self.interaction_budget
            + self.max_interaction_budget * regen_rate * dt * 0.5 * m,
        )

    def can_branch(self, cost: float = 1.0) -> bool:
        return (
            self.branching_budget >= cost
            and self.computational_energy >= cost * 2
        )

    def can_mutate(self, cost: float = 1.0) -> bool:
        return self.mutation_budget >= cost and self.computational_energy >= cost

    def can_interact(self, cost: float = 0.5) -> bool:
        return self.interaction_budget >= cost and self.computational_energy >= cost

    def can_think(self, cost: float = 1.0) -> bool:
        return self.computational_energy >= cost

    def spend_think(self, cost: float = 1.0) -> bool:
        if not self.can_think(cost):
            return False
        self.computational_energy -= cost
        return True

    def refund_energy(self, amount: float) -> None:
        self.computational_energy = min(
            self.max_energy, self.computational_energy + max(0.0, amount)
        )

    def spend_branch(self, cost: float = 1.0) -> bool:
        if not self.can_branch(cost):
            return False
        self.branching_budget -= cost
        self.computational_energy -= cost * 2
        return True

    def spend_mutation(self, cost: float = 1.0) -> bool:
        if not self.can_mutate(cost):
            return False
        self.mutation_budget -= cost
        self.computational_energy -= cost
        return True

    def spend_interaction(self, cost: float = 0.5) -> bool:
        if not self.can_interact(cost):
            return False
        self.interaction_budget -= cost
        self.computational_energy -= cost
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "computational_energy": self.computational_energy,
            "max_energy": self.max_energy,
            "timeline_capacity": self.timeline_capacity,
            "branching_budget": self.branching_budget,
            "max_branching_budget": self.max_branching_budget,
            "memory_capacity": self.memory_capacity,
            "memory_used": self.memory_used,
            "mutation_budget": self.mutation_budget,
            "max_mutation_budget": self.max_mutation_budget,
            "interaction_budget": self.interaction_budget,
            "max_interaction_budget": self.max_interaction_budget,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourcePool:
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class OrganismState:
    """Overall health and metabolic state of the digital organism."""

    resources: ResourcePool = field(default_factory=ResourcePool)
    health: float = 1.0
    stability: float = 1.0
    diversity: float = 0.0
    total_complexity: float = 0.0
    active_timeline_count: int = 0
    total_timeline_count: int = 0
    paradox_count: int = 0
    unresolved_paradox_count: int = 0
    mean_weight: float = 1.0
    mean_growth: float = 0.0
    mean_decay: float = 0.0
    generation_depth: int = 0
    age: float = 0.0
    total_events: int = 0
    total_interactions: int = 0
    total_convergences: int = 0
    total_branches: int = 0
    cycle_count: int = 0
    mean_fitness: float = 0.0
    mean_fitness_ema: float = 0.0
    total_reward: float = 0.0
    total_thinks: int = 0
    best_fitness: float = 0.0
    learning_cycles: int = 0
    metabolic_throttle: float = 1.0
    homeostasis_mode: str = "thrive"

    def to_dict(self) -> dict[str, Any]:
        return {
            "resources": self.resources.to_dict(),
            "health": self.health,
            "stability": self.stability,
            "diversity": self.diversity,
            "total_complexity": self.total_complexity,
            "active_timeline_count": self.active_timeline_count,
            "total_timeline_count": self.total_timeline_count,
            "paradox_count": self.paradox_count,
            "unresolved_paradox_count": self.unresolved_paradox_count,
            "mean_weight": self.mean_weight,
            "mean_growth": self.mean_growth,
            "mean_decay": self.mean_decay,
            "generation_depth": self.generation_depth,
            "age": self.age,
            "total_events": self.total_events,
            "total_interactions": self.total_interactions,
            "total_convergences": self.total_convergences,
            "total_branches": self.total_branches,
            "cycle_count": self.cycle_count,
            "mean_fitness": self.mean_fitness,
            "mean_fitness_ema": self.mean_fitness_ema,
            "total_reward": self.total_reward,
            "total_thinks": self.total_thinks,
            "best_fitness": self.best_fitness,
            "learning_cycles": self.learning_cycles,
            "metabolic_throttle": self.metabolic_throttle,
            "homeostasis_mode": self.homeostasis_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrganismState:
        resources = ResourcePool.from_dict(data.get("resources", {}))
        state = cls(resources=resources)
        for k, v in data.items():
            if k != "resources" and hasattr(state, k):
                setattr(state, k, v)
        return state
