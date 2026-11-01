"""Exponential Decay Engine — manages timeline decline and archival."""

from __future__ import annotations

from ..models.timeline import Timeline, TimelineStatus, TimelineEvent, EventType
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine
import time


class ExponentialDecayEngine:
    """Detects and processes decaying timelines; archives without destroying history."""

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
    ) -> None:
        self.registry = registry
        self.config = config

    def apply_cycle(self, sim_time: float, dt: float) -> dict:
        decaying = 0
        archived = 0
        for tl in list(self.registry.active_timelines()):
            net = tl.growth_coefficient - tl.decay_coefficient
            is_decaying = (
                net < 0
                or tl.current_weight < tl.initial_weight * 0.3
                or tl.stability_score < 0.3
            )
            if is_decaying:
                if tl.status not in (
                    TimelineStatus.PARADOXICAL,
                    TimelineStatus.ISOLATED,
                    TimelineStatus.ARCHIVED,
                ):
                    self.registry.update_status(tl.id, TimelineStatus.DECAYING)
                    decaying += 1
                    # Stability erodes
                    tl.stability_score = max(0.0, tl.stability_score - 0.01 * dt)

            # Archive near-extinct timelines (preserve history)
            if tl.current_weight <= self.config.weight_floor_archive:
                if not tl.archived:
                    tl.events.append(
                        TimelineEvent(
                            timeline_id=tl.id,
                            event_type=EventType.DECAY,
                            simulation_time=sim_time,
                            wall_timestamp=time.time(),
                            description="Timeline archived due to weight floor",
                            payload={"final_weight": tl.current_weight},
                        )
                    )
                    self.registry.archive(tl.id)
                    archived += 1

        return {"decaying": decaying, "archived": archived}

    def force_decay(self, timeline: Timeline, factor: float = 0.5) -> None:
        """Externally accelerate decay (e.g. paradox isolation side-effect)."""
        timeline.decay_coefficient *= 1.0 + factor
        timeline.stability_score *= 1.0 - factor * 0.5
        timeline.current_weight *= 1.0 - factor * 0.3
