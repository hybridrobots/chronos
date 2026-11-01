"""Timeline Convergence Engine — draws similar branches together."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..models.timeline import Timeline, TimelineEvent, EventType, TimelineStatus
from ..models.relationships import Relationship, RelationshipType
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine


class TimelineConvergenceEngine:
    """Evaluates similarity between timelines and merges influence when converging."""

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> None:
        self.registry = registry
        self.config = config
        self.rng = rng
        self._history: list[dict] = []

    def similarity(self, a: Timeline, b: Timeline) -> float:
        """Heuristic similarity based on coefficients, complexity, and event overlap."""
        g_sim = 1.0 - min(1.0, abs(a.growth_coefficient - b.growth_coefficient) / 0.2)
        d_sim = 1.0 - min(1.0, abs(a.decay_coefficient - b.decay_coefficient) / 0.1)
        c_sim = 1.0 - min(
            1.0,
            abs(a.structural_complexity - b.structural_complexity) / 5.0,
        )
        # Event type overlap
        types_a = {e.event_type for e in a.active_events()}
        types_b = {e.event_type for e in b.active_events()}
        if types_a or types_b:
            overlap = len(types_a & types_b) / max(len(types_a | types_b), 1)
        else:
            overlap = 0.5
        # Same lineage bonus
        lineage = 0.2 if (a.parent_id and a.parent_id == b.parent_id) else 0.0
        return float(0.25 * g_sim + 0.2 * d_sim + 0.2 * c_sim + 0.25 * overlap + lineage)

    def converge(
        self,
        a: Timeline,
        b: Timeline,
        sim_time: float,
    ) -> Optional[Relationship]:
        sim = self.similarity(a, b)
        if sim < self.config.convergence_similarity_threshold:
            return None

        strength = sim * self.config.convergence_rate * 10
        rel = Relationship(
            source_id=a.id,
            target_id=b.id,
            rel_type=RelationshipType.CONVERGENCE,
            strength=strength,
            simulation_time=sim_time,
            metadata={"similarity": sim},
        )
        self.registry.add_relationship(rel)

        # Draw positions closer
        mid = (
            (a.position[0] + b.position[0]) / 2,
            (a.position[1] + b.position[1]) / 2,
            (a.position[2] + b.position[2]) / 2,
        )
        pull = 0.1 * sim
        a.position = (
            a.position[0] + (mid[0] - a.position[0]) * pull,
            a.position[1] + (mid[1] - a.position[1]) * pull,
            a.position[2] + (mid[2] - a.position[2]) * pull,
        )
        b.position = (
            b.position[0] + (mid[0] - b.position[0]) * pull,
            b.position[1] + (mid[1] - b.position[1]) * pull,
            b.position[2] + (mid[2] - b.position[2]) * pull,
        )

        # Blend influence
        avg_w = (a.current_weight + b.current_weight) / 2
        a.current_weight = 0.9 * a.current_weight + 0.1 * avg_w
        b.current_weight = 0.9 * b.current_weight + 0.1 * avg_w

        a.convergence_ids.append(rel.id)
        b.convergence_ids.append(rel.id)
        self.registry.update_status(a.id, TimelineStatus.CONVERGING)
        self.registry.update_status(b.id, TimelineStatus.CONVERGING)

        for tl in (a, b):
            tl.events.append(
                TimelineEvent(
                    timeline_id=tl.id,
                    event_type=EventType.CONVERGENCE,
                    simulation_time=sim_time,
                    wall_timestamp=time.time(),
                    description=f"Converging with twin (sim={sim:.3f})",
                    payload={
                        "partner": b.id if tl is a else a.id,
                        "similarity": sim,
                        "relationship_id": rel.id,
                    },
                )
            )

        self._history.append(
            {
                "a": a.id,
                "b": b.id,
                "similarity": sim,
                "sim_time": sim_time,
                "relationship_id": rel.id,
            }
        )
        return rel

    def evaluate_all(self, sim_time: float) -> list[Relationship]:
        created: list[Relationship] = []
        timelines = self.registry.active_timelines()
        if len(timelines) < 2:
            return created

        # Sample pairs rather than O(n²) every cycle for performance
        n = len(timelines)
        sample_size = min(n, 20)
        indices = self.rng.choice(n, size=sample_size, replace=False)
        sampled = [timelines[int(i)] for i in indices]

        checked = set()
        for i, a in enumerate(sampled):
            for b in sampled[i + 1 :]:
                pair = tuple(sorted([a.id, b.id]))
                if pair in checked:
                    continue
                checked.add(pair)
                if self.rng.random() > self.config.convergence_rate * 5:
                    continue
                rel = self.converge(a, b, sim_time)
                if rel:
                    created.append(rel)
                    if len(created) >= 2:
                        return created
        return created

    def get_history(self) -> list[dict]:
        return list(self._history)
