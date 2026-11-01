"""Cross-Timeline Interaction Engine — Mechanism C with feedback-loop prevention."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..models.timeline import Timeline, TimelineEvent, EventType
from ..models.relationships import Relationship, RelationshipType
from ..models.config import SimulationConfig
from ..models.organism import ResourcePool
from .registry import TimelineRegistryEngine


class CrossTimelineInteractionEngine:
    """
    Mechanism C — Timeline interaction:
    Configurable influence between timelines; track strength; prevent feedback loops.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> None:
        self.registry = registry
        self.config = config
        self.rng = rng
        self._interaction_graph: dict[str, set[str]] = {}  # for cycle detection
        self._history: list[dict] = []

    def _would_create_cycle(self, source_id: str, target_id: str) -> bool:
        """DFS to detect if adding source→target creates a feedback loop."""
        if source_id == target_id:
            return True
        visited = set()
        stack = [target_id]
        while stack:
            node = stack.pop()
            if node == source_id:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self._interaction_graph.get(node, set()))
        return False

    def interact(
        self,
        source: Timeline,
        target: Timeline,
        sim_time: float,
        resources: ResourcePool,
        strength: Optional[float] = None,
    ) -> Optional[Relationship]:
        if not resources.spend_interaction(0.5):
            return None
        if self._would_create_cycle(source.id, target.id):
            return None

        strength = strength if strength is not None else self.config.interaction_strength
        strength *= float(self.rng.uniform(0.5, 1.5))
        strength = min(strength, self.config.feedback_loop_threshold)

        rel = Relationship(
            source_id=source.id,
            target_id=target.id,
            rel_type=RelationshipType.INTERACTION,
            strength=strength,
            simulation_time=sim_time,
            metadata={"type": "influence_transfer"},
        )
        self.registry.add_relationship(rel)

        # Apply influence: source bleeds a fraction of weight into target
        transfer = source.current_weight * strength * 0.05
        source.current_weight = max(
            self.config.min_weight, source.current_weight - transfer * 0.3
        )
        target.current_weight += transfer
        target.influence_weight += transfer * 0.5

        source.interaction_ids.append(rel.id)
        target.interaction_ids.append(rel.id)

        self._interaction_graph.setdefault(source.id, set()).add(target.id)

        evt = TimelineEvent(
            timeline_id=target.id,
            event_type=EventType.INTERACTION,
            simulation_time=sim_time,
            wall_timestamp=time.time(),
            description=f"Influenced by timeline {source.id[:8]} (strength={strength:.3f})",
            payload={
                "source_id": source.id,
                "strength": strength,
                "transfer": transfer,
                "relationship_id": rel.id,
            },
            influence=strength,
        )
        target.events.append(evt)

        record = {
            "relationship_id": rel.id,
            "source_id": source.id,
            "target_id": target.id,
            "strength": strength,
            "sim_time": sim_time,
        }
        self._history.append(record)
        return rel

    def evaluate_all(
        self,
        sim_time: float,
        resources: ResourcePool,
    ) -> list[Relationship]:
        created: list[Relationship] = []
        timelines = self.registry.active_timelines()
        if len(timelines) < 2:
            return created

        max_n = self.config.max_interactions_per_cycle
        for _ in range(max_n):
            if self.rng.random() > self.config.interaction_rate:
                continue
            if not resources.can_interact(0.5):
                break
            pair = self.rng.choice(len(timelines), size=2, replace=False)
            src, tgt = timelines[int(pair[0])], timelines[int(pair[1])]
            rel = self.interact(src, tgt, sim_time, resources)
            if rel:
                created.append(rel)
        return created

    def get_history(self) -> list[dict]:
        return list(self._history)
