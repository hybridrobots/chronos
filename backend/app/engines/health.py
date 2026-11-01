"""Organism Health Engine — evaluates metabolic and structural vitality."""

from __future__ import annotations

import numpy as np

from ..models.organism import OrganismState
from ..models.timeline import TimelineStatus
from ..models.config import SimulationConfig
from ..models.paradox import ParadoxStatus
from .registry import TimelineRegistryEngine
from .paradox_detection import ParadoxDetectionEngine


class OrganismHealthEngine:
    """Computes organism-level health, diversity, stability, and resource pressure."""

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        paradox_engine: ParadoxDetectionEngine,
        config: SimulationConfig,
        state: OrganismState,
    ) -> None:
        self.registry = registry
        self.paradox_engine = paradox_engine
        self.config = config
        self.state = state

    def evaluate(self, sim_time: float) -> OrganismState:
        tls = self.registry.active_timelines()
        all_tls = self.registry.all_timelines()
        paradoxes = self.paradox_engine.get_all()

        self.state.active_timeline_count = len(tls)
        self.state.total_timeline_count = len(all_tls)
        self.state.paradox_count = len(paradoxes)
        self.state.unresolved_paradox_count = len(
            [
                p
                for p in paradoxes
                if p.status == ParadoxStatus.DETECTED
            ]
        )
        self.state.age = sim_time

        if tls:
            weights = np.array([t.current_weight for t in tls])
            growths = np.array([t.growth_coefficient for t in tls])
            decays = np.array([t.decay_coefficient for t in tls])
            complexities = np.array([t.structural_complexity for t in tls])
            stabilities = np.array([t.stability_score for t in tls])

            self.state.mean_weight = float(np.mean(weights))
            self.state.mean_growth = float(np.mean(growths))
            self.state.mean_decay = float(np.mean(decays))
            self.state.total_complexity = float(np.sum(complexities))
            self.state.stability = float(np.mean(stabilities))
            self.state.generation_depth = max(t.generation for t in tls)

            # Shannon-like diversity over normalized weights
            total_w = float(np.sum(weights)) or 1.0
            probs = weights / total_w
            probs = probs[probs > 0]
            shannon = -float(np.sum(probs * np.log(probs + 1e-12)))
            max_shannon = np.log(len(probs)) if len(probs) > 1 else 1.0
            self.state.diversity = float(shannon / max_shannon) if max_shannon > 0 else 0.0

            self.state.total_events = sum(len(t.events) for t in all_tls)
        else:
            self.state.mean_weight = 0.0
            self.state.stability = 0.0
            self.state.diversity = 0.0
            self.state.total_complexity = 0.0

        # Memory accounting
        mem = self.state.total_events + len(
            self.registry.get_relationships(active_only=False)
        )
        self.state.resources.memory_used = mem

        # Composite health
        energy_ratio = (
            self.state.resources.computational_energy
            / max(self.state.resources.max_energy, 1)
        )
        capacity_ratio = 1.0 - (
            self.state.active_timeline_count
            / max(self.state.resources.timeline_capacity, 1)
        )
        paradox_penalty = 1.0 - min(
            1.0, self.state.unresolved_paradox_count * 0.1
        )
        mem_ratio = 1.0 - min(
            1.0,
            self.state.resources.memory_used
            / max(self.state.resources.memory_capacity, 1),
        )

        self.state.health = float(
            np.clip(
                0.3 * self.state.stability
                + 0.2 * self.state.diversity
                + 0.2 * energy_ratio
                + 0.15 * capacity_ratio
                + 0.1 * paradox_penalty
                + 0.05 * mem_ratio,
                0.0,
                1.0,
            )
        )

        # Count status distribution side-effects
        growing = len(self.registry.by_status(TimelineStatus.GROWING))
        decaying = len(self.registry.by_status(TimelineStatus.DECAYING))
        _ = growing, decaying  # available for telemetry

        return self.state
