"""Timeline Genesis Engine — creates the primordial timeline and seed events."""

from __future__ import annotations

import math
import time
from typing import Optional

import numpy as np

from ..models.timeline import Timeline, TimelineEvent, TimelineStatus, EventType
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine


class TimelineGenesisEngine:
    """Responsible for birthing new root or seed timelines into the multiverse."""

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> None:
        self.registry = registry
        self.config = config
        self.rng = rng

    def create_primordial(self, sim_time: float = 0.0) -> Timeline:
        """Create the original root timeline of the organism."""
        hue = float(self.rng.uniform(0.45, 0.75))
        tl = Timeline(
            parent_id=None,
            creation_timestamp=time.time(),
            simulation_birth_time=sim_time,
            generation=0,
            growth_coefficient=self.config.default_growth,
            decay_coefficient=self.config.default_decay,
            initial_weight=1.0,
            current_weight=1.0,
            influence_weight=1.0,
            stability_score=1.0,
            structural_complexity=0.1,
            branching_probability=self.config.base_branch_probability,
            status=TimelineStatus.ACTIVE,
            position=(0.0, 0.0, 0.0),
            color_hue=hue,
            last_update_time=sim_time,
        )
        genesis_event = TimelineEvent(
            timeline_id=tl.id,
            event_type=EventType.GENESIS,
            simulation_time=sim_time,
            wall_timestamp=time.time(),
            description="Primordial timeline genesis — the origin of the organism",
            payload={"origin": True},
            influence=1.0,
        )
        tl.events.append(genesis_event)
        self.registry.register(tl)
        return tl

    def create_child(
        self,
        parent: Timeline,
        sim_time: float,
        position_offset: Optional[tuple[float, float, float]] = None,
        mutation: Optional[dict] = None,
    ) -> Timeline:
        """Spawn a child timeline from a parent with copied historical state."""
        g_var = self.config.growth_variance
        d_var = self.config.decay_variance
        growth = max(
            0.001,
            parent.growth_coefficient
            + float(self.rng.normal(0, g_var)),
        )
        decay = max(
            0.0,
            parent.decay_coefficient
            + float(self.rng.normal(0, d_var)),
        )

        if position_offset is None:
            angle = float(self.rng.uniform(0, 2 * math.pi))
            elev = float(self.rng.uniform(-0.5, 0.5))
            radius = 2.0 + parent.generation * 0.5
            position_offset = (
                parent.position[0] + radius * math.cos(angle),
                parent.position[1] + elev * radius,
                parent.position[2] + radius * math.sin(angle),
            )

        hue = (parent.color_hue + float(self.rng.uniform(-0.08, 0.08))) % 1.0
        initial_w = parent.current_weight * float(self.rng.uniform(0.3, 0.6))

        child = Timeline(
            parent_id=parent.id,
            creation_timestamp=time.time(),
            simulation_birth_time=sim_time,
            generation=parent.generation + 1,
            growth_coefficient=growth,
            decay_coefficient=decay,
            initial_weight=initial_w,
            current_weight=initial_w,
            influence_weight=initial_w,
            stability_score=parent.stability_score * float(self.rng.uniform(0.8, 1.0)),
            structural_complexity=parent.structural_complexity * 0.8,
            branching_probability=max(
                0.01,
                parent.branching_probability
                * float(self.rng.uniform(0.7, 1.1)),
            ),
            status=TimelineStatus.NASCENT,
            position=position_offset,
            color_hue=hue,
            last_update_time=sim_time,
            historical_version=1,
        )

        # Copy relevant active historical state from parent
        for evt in parent.active_events():
            copied = TimelineEvent(
                timeline_id=child.id,
                event_type=evt.event_type,
                simulation_time=evt.simulation_time,
                wall_timestamp=time.time(),
                description=f"[inherited] {evt.description}",
                payload={**evt.payload, "inherited_from": evt.id},
                version=1,
                parent_event_id=evt.id,
                influence=evt.influence * 0.8,
            )
            child.events.append(copied)

        divergence = TimelineEvent(
            timeline_id=child.id,
            event_type=EventType.BRANCH_DIVERGENCE,
            simulation_time=sim_time,
            wall_timestamp=time.time(),
            description=f"Diverged from parent {parent.id[:8]}",
            payload={
                "parent_id": parent.id,
                "mutation": mutation or {},
            },
            influence=1.0,
        )
        child.events.append(divergence)

        if mutation:
            child.mutation_history.append(
                {"time": sim_time, "mutation": mutation}
            )

        self.registry.register(child)
        return child
