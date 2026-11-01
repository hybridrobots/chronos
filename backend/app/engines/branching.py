"""Timeline Branching Engine — preserves parent, creates child, records divergence."""

from __future__ import annotations

from typing import Optional

import numpy as np

from ..models.timeline import Timeline
from ..models.config import SimulationConfig
from ..models.organism import ResourcePool
from .registry import TimelineRegistryEngine
from .genesis import TimelineGenesisEngine


class TimelineBranchingEngine:
    """
    Mechanism A — Timeline branching:
    Preserve original, create child, copy historical state, record divergence.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        genesis: TimelineGenesisEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> None:
        self.registry = registry
        self.genesis = genesis
        self.config = config
        self.rng = rng

    def _pop_ratio(self) -> float:
        return self.registry.count() / max(self.config.max_timelines, 1)

    def should_branch(
        self,
        timeline: Timeline,
        resources: ResourcePool,
        *,
        throttle: float = 1.0,
        allow_branch: bool = True,
    ) -> bool:
        if not allow_branch or throttle <= 0.05:
            return False
        if timeline.generation >= self.config.max_generation:
            return False
        if self.registry.count() >= self.config.max_timelines:
            return False
        # Hard stop at homeostasis hard population ratio
        if self._pop_ratio() >= self.config.homeostasis_hard_pop_ratio:
            return False
        if timeline.current_weight < self.config.branch_threshold_weight:
            return False
        if not resources.can_branch(self.config.branch_cost):
            return False
        # Soft limit + metabolic throttle
        ratio = self._pop_ratio()
        soft = self.config.homeostasis_soft_pop_ratio
        soft_factor = 1.0
        if ratio >= soft:
            soft_factor = max(
                0.0,
                1.0
                - (ratio - soft)
                / max(self.config.homeostasis_hard_pop_ratio - soft, 1e-6),
            )
        effective_p = (
            timeline.branching_probability
            * (1.0 - ratio * 0.7)
            * soft_factor
            * max(0.0, throttle)
        )
        effective_p *= self.config.base_branch_probability / 0.08
        return bool(self.rng.random() < effective_p)

    def branch(
        self,
        parent: Timeline,
        sim_time: float,
        resources: ResourcePool,
        mutation: Optional[dict] = None,
        *,
        allow_branch: bool = True,
    ) -> Optional[Timeline]:
        if not allow_branch:
            return None
        if self._pop_ratio() >= self.config.homeostasis_hard_pop_ratio:
            return None
        if not resources.spend_branch(self.config.branch_cost):
            return None
        if self.registry.count() >= self.config.max_timelines:
            return None
        child = self.genesis.create_child(parent, sim_time, mutation=mutation)
        return child

    def evaluate_all(
        self,
        sim_time: float,
        resources: ResourcePool,
        *,
        throttle: float = 1.0,
        allow_branch: bool = True,
    ) -> list[Timeline]:
        """Evaluate branching conditions across all active timelines."""
        new_branches: list[Timeline] = []
        if not allow_branch:
            return new_branches
        candidates = list(self.registry.active_timelines())
        # Prefer fit + heavy timelines
        candidates.sort(
            key=lambda t: (t.fitness_ema, t.current_weight), reverse=True
        )
        for tl in candidates:
            if self.registry.count() >= self.config.max_timelines:
                break
            if self._pop_ratio() >= self.config.homeostasis_hard_pop_ratio:
                break
            if self.should_branch(
                tl, resources, throttle=throttle, allow_branch=allow_branch
            ):
                child = self.branch(
                    tl, sim_time, resources, allow_branch=allow_branch
                )
                if child:
                    new_branches.append(child)
        return new_branches
