"""Homeostasis Engine — keeps the organism self-sustaining via metabolic throttle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..models.config import SimulationConfig
from ..models.organism import OrganismState
from ..models.timeline import TimelineStatus
from .registry import TimelineRegistryEngine
from .memory import HistoricalMemoryEngine


@dataclass
class MetabolicState:
    throttle: float = 1.0  # 0 = full rest, 1 = full activity
    allow_think: bool = True
    allow_branch: bool = True
    allow_ambient_events: bool = True
    mode: str = "thrive"  # thrive | balance | conserve | crisis
    energy_ratio: float = 1.0
    pop_ratio: float = 0.0
    mem_ratio: float = 0.0
    health: float = 1.0
    archived_weak: int = 0
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "throttle": self.throttle,
            "allow_think": self.allow_think,
            "allow_branch": self.allow_branch,
            "allow_ambient_events": self.allow_ambient_events,
            "mode": self.mode,
            "energy_ratio": self.energy_ratio,
            "pop_ratio": self.pop_ratio,
            "mem_ratio": self.mem_ratio,
            "health": self.health,
            "archived_weak": self.archived_weak,
            "details": self.details or {},
        }


class HomeostasisEngine:
    """
    Organism-level feedback control.

    When population, memory, or energy leave the viable band, throttle thinking
    and branching, prefer stabilization, and archive weak lineages to free slots.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
        organism: OrganismState,
        memory: HistoricalMemoryEngine,
    ) -> None:
        self.registry = registry
        self.config = config
        self.organism = organism
        self.memory = memory
        self.last: MetabolicState = MetabolicState()

    def evaluate(self) -> MetabolicState:
        if not self.config.homeostasis_enabled:
            self.last = MetabolicState(throttle=1.0, mode="thrive")
            return self.last

        r = self.organism.resources
        energy_ratio = r.computational_energy / max(r.max_energy, 1)
        pop_ratio = self.organism.active_timeline_count / max(
            r.timeline_capacity, self.config.max_timelines, 1
        )
        mem_ratio = r.memory_used / max(r.memory_capacity, 1)
        health = self.organism.health

        # Component pressures in [0, 1] (1 = stressed)
        energy_stress = float(
            np.clip(
                (self.config.energy_rest_threshold - energy_ratio)
                / max(self.config.energy_rest_threshold, 1e-6),
                0.0,
                1.0,
            )
        )
        soft = self.config.homeostasis_soft_pop_ratio
        hard = self.config.homeostasis_hard_pop_ratio
        if pop_ratio <= soft:
            pop_stress = 0.0
        elif pop_ratio >= hard:
            pop_stress = 1.0
        else:
            pop_stress = (pop_ratio - soft) / max(hard - soft, 1e-6)

        mem_soft = self.config.homeostasis_memory_soft_ratio
        if mem_ratio <= mem_soft:
            mem_stress = 0.0
        else:
            mem_stress = float(
                np.clip((mem_ratio - mem_soft) / max(1.0 - mem_soft, 1e-6), 0.0, 1.0)
            )

        health_target = self.config.homeostasis_health_target
        health_stress = float(
            np.clip((health_target - health) / max(health_target, 1e-6), 0.0, 1.0)
        )

        stress = float(
            np.clip(
                0.35 * energy_stress
                + 0.30 * pop_stress
                + 0.20 * mem_stress
                + 0.15 * health_stress,
                0.0,
                1.0,
            )
        )
        throttle = float(np.clip(1.0 - stress, 0.0, 1.0))

        # Mode bands
        if stress < 0.25:
            mode = "thrive"
        elif stress < 0.5:
            mode = "balance"
        elif stress < 0.75:
            mode = "conserve"
        else:
            mode = "crisis"

        allow_think = energy_ratio >= self.config.energy_rest_threshold * 0.5
        # Hard stop branching near capacity
        allow_branch = pop_ratio < hard and throttle > 0.2
        allow_ambient = throttle > 0.15 and energy_ratio > 0.25

        # Resting: boost energy regen slightly by leaving budget alone;
        # caller may amplify regen when mode is conserve/crisis
        state = MetabolicState(
            throttle=throttle,
            allow_think=allow_think,
            allow_branch=allow_branch,
            allow_ambient_events=allow_ambient,
            mode=mode,
            energy_ratio=energy_ratio,
            pop_ratio=pop_ratio,
            mem_ratio=mem_ratio,
            health=health,
            details={
                "energy_stress": energy_stress,
                "pop_stress": pop_stress,
                "mem_stress": mem_stress,
                "health_stress": health_stress,
                "stress": stress,
            },
        )
        self.last = state

        # Persist on organism for API/UI
        self.organism.metabolic_throttle = throttle
        self.organism.homeostasis_mode = mode
        return state

    def apply_pressure(self, sim_time: float) -> int:
        """Archive weakest lineages when over soft population / memory pressure."""
        if not self.config.homeostasis_enabled:
            return 0
        archived = 0
        state = self.last
        pop_ratio = state.pop_ratio
        soft = self.config.homeostasis_soft_pop_ratio

        # Population cull: free slots by archiving lowest fitness_ema / weight
        if pop_ratio >= soft:
            tls = self.registry.active_timelines()
            # Keep a minimum viable population
            min_keep = max(3, int(self.config.max_timelines * 0.15))
            excess_target = max(
                0,
                len(tls)
                - int(self.config.max_timelines * soft * 0.95),
            )
            # In crisis, cull more aggressively
            if state.mode == "crisis":
                excess_target = max(excess_target, len(tls) - min_keep)
            cull_n = min(
                excess_target,
                self.config.homeostasis_max_cull_per_cycle,
                max(0, len(tls) - min_keep),
            )
            if cull_n > 0:
                ranked = sorted(
                    tls,
                    key=lambda t: (
                        t.fitness_ema,
                        t.current_weight,
                        -t.generation,
                    ),
                )
                for tl in ranked[:cull_n]:
                    if tl.status == TimelineStatus.ARCHIVED:
                        continue
                    self.registry.archive(tl.id)
                    archived += 1

        # Memory pressure: tighter event archival
        if state.mem_ratio >= self.config.homeostasis_memory_soft_ratio:
            # Temporarily lower active event cap for retention pass
            old_cap = self.config.max_active_events_per_timeline
            self.config.max_active_events_per_timeline = max(
                20, int(old_cap * (0.4 + 0.4 * state.throttle))
            )
            self.memory.apply_retention()
            self.config.max_active_events_per_timeline = old_cap

        self.last.archived_weak = archived
        return archived

    def regen_multiplier(self) -> float:
        """Extra energy regen when conserving / in crisis."""
        if not self.config.homeostasis_enabled:
            return 1.0
        mode = self.last.mode
        if mode == "crisis":
            return 2.2
        if mode == "conserve":
            return 1.6
        if mode == "balance":
            return 1.2
        return 1.0
