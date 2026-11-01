"""Autonomous Event Generation Engine — seeded, configurable, fully traceable."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..models.timeline import Timeline, TimelineEvent, EventType, TimelineStatus
from ..models.config import SimulationConfig
from ..models.organism import ResourcePool
from .registry import TimelineRegistryEngine
from .causality import CausalDependencyEngine
from .memory import HistoricalMemoryEngine


# Fictional event templates — NOT predictions or facts about real history
EVENT_TEMPLATES = {
    EventType.HISTORICAL_CHANGE: [
        "A pivotal cultural shift reshapes local norms",
        "An unexpected succession alters governance patterns",
        "A migratory wave redistributes populations",
        "An archival discovery revises accepted chronicles",
    ],
    EventType.TECHNOLOGICAL: [
        "A novel computational substrate emerges",
        "Energy conversion efficiency leaps forward",
        "Communication protocols spontaneously standardize",
        "Material synthesis unlocks new structural forms",
    ],
    EventType.SOCIAL: [
        "Coalition networks reorganize influence maps",
        "Belief systems fragment into competing schools",
        "Collective rituals intensify community cohesion",
        "Trade guilds establish cross-branch conventions",
    ],
    EventType.ENVIRONMENTAL: [
        "Climate oscillation stresses resource basins",
        "Geological upheaval redraws territorial boundaries",
        "Biosphere diversity pulses upward",
        "Atmospheric composition drifts measurably",
    ],
    EventType.UNEXPECTED: [
        "An anomalous signal appears in the causal fabric",
        "A forgotten structure reactivates spontaneously",
        "Probability gradients invert locally",
        "An unclassified phenomenon briefly manifests",
    ],
    EventType.MUTATION: [
        "Timeline parameters drift under mutational pressure",
        "Structural complexity spontaneously reorganizes",
        "Growth/decay coefficients undergo soft mutation",
        "Branching probability fluctuates unpredictably",
    ],
    EventType.CAUSAL_CONFLICT: [
        "Contradictory outcomes claim the same causal ancestor",
        "Event polarities collide within a shared domain",
        "Downstream effects disagree on upstream cause",
        "A closed causal loop threatens consistency",
    ],
}

DOMAINS = ["governance", "energy", "culture", "biosphere", "computation", "territory"]


class AutonomousEventEngine:
    """
    Configurable seeded event generation.
    Events are simulated narrative artifacts — not predictions about real history.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        causality: CausalDependencyEngine,
        memory: HistoricalMemoryEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> None:
        self.registry = registry
        self.causality = causality
        self.memory = memory
        self.config = config
        self.rng = rng

    def _pick_event_type(self) -> EventType:
        weights = self.config.event_types_weights
        types = list(weights.keys())
        probs = np.array([weights[t] for t in types], dtype=float)
        probs /= probs.sum()
        chosen = str(self.rng.choice(types, p=probs))
        return EventType(chosen)

    def generate_event(
        self,
        timeline: Timeline,
        sim_time: float,
        resources: Optional[ResourcePool] = None,
    ) -> Optional[TimelineEvent]:
        etype = self._pick_event_type()

        if etype == EventType.MUTATION:
            if resources and not resources.spend_mutation(1.0):
                etype = EventType.UNEXPECTED
            else:
                self._apply_mutation(timeline, sim_time)

        templates = EVENT_TEMPLATES.get(etype, EVENT_TEMPLATES[EventType.UNEXPECTED])
        description = str(self.rng.choice(templates))
        domain = str(self.rng.choice(DOMAINS))
        # Mostly neutral polarity — conflicts are rare by design
        polarity = int(self.rng.choice([-1, 0, 0, 0, 0, 1, 1]))

        # Causal conflicts get forced polarity extremes
        if etype == EventType.CAUSAL_CONFLICT:
            polarity = int(self.rng.choice([-1, 1]))

        evt = TimelineEvent(
            timeline_id=timeline.id,
            event_type=etype,
            simulation_time=sim_time,
            wall_timestamp=time.time(),
            description=description,
            payload={
                "domain": domain,
                "polarity": polarity,
                "fictional": True,
                "note": "Simulated event — not a real-world prediction",
            },
            influence=float(self.rng.uniform(0.3, 1.0)),
        )

        # Link to a recent prior event as causal dep
        active = timeline.active_events()
        if active:
            parent = active[int(self.rng.integers(0, len(active)))]
            evt.causal_deps.append(parent.id)
            self.causality.link_events(parent, evt, sim_time)

        timeline.events.append(evt)
        timeline.structural_complexity = min(
            10.0, timeline.structural_complexity + 0.05
        )

        self.memory.record(
            {
                "type": "event_generated",
                "timeline_id": timeline.id,
                "event_id": evt.id,
                "event_type": etype.value,
                "sim_time": sim_time,
            }
        )
        return evt

    def _apply_mutation(self, timeline: Timeline, sim_time: float) -> None:
        g_delta = float(self.rng.normal(0, self.config.growth_variance))
        d_delta = float(self.rng.normal(0, self.config.decay_variance))
        timeline.growth_coefficient = max(0.001, timeline.growth_coefficient + g_delta)
        timeline.decay_coefficient = max(0.0, timeline.decay_coefficient + d_delta)
        timeline.branching_probability = float(
            np.clip(
                timeline.branching_probability + self.rng.normal(0, 0.01),
                0.01,
                0.5,
            )
        )
        timeline.mutation_history.append(
            {
                "time": sim_time,
                "growth_delta": g_delta,
                "decay_delta": d_delta,
            }
        )
        self.registry.update_status(timeline.id, TimelineStatus.MUTATING)

    def generate_cycle(
        self,
        sim_time: float,
        resources: ResourcePool,
        *,
        throttle: float = 1.0,
        allow_ambient: bool = True,
    ) -> list[TimelineEvent]:
        generated: list[TimelineEvent] = []
        timelines = self.registry.active_timelines()
        if not timelines or not allow_ambient:
            return generated

        max_events = max(0, int(round(self.config.max_events_per_cycle * throttle)))
        # Bound by memory capacity (with soft stop before hard overflow)
        mem_ratio = resources.memory_used / max(resources.memory_capacity, 1)
        if mem_ratio >= self.config.homeostasis_memory_soft_ratio:
            return generated
        if resources.memory_used >= resources.memory_capacity:
            return generated

        for _ in range(max_events):
            if self.rng.random() > self.config.event_rate * max(0.05, throttle):
                continue
            weights = np.array([t.current_weight for t in timelines])
            weights = weights / (weights.sum() or 1.0)
            idx = int(self.rng.choice(len(timelines), p=weights))
            evt = self.generate_event(timelines[idx], sim_time, resources)
            if evt:
                generated.append(evt)
        return generated
