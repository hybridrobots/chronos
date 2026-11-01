"""Paradox Resolution Engine — four configurable resolution mechanisms."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..models.paradox import Paradox, ParadoxStatus, ResolutionStrategy
from ..models.timeline import TimelineStatus, TimelineEvent, EventType
from ..models.config import SimulationConfig
from ..models.organism import ResourcePool
from .registry import TimelineRegistryEngine
from .branching import TimelineBranchingEngine
from .alteration import TemporalAlterationEngine
from .decay import ExponentialDecayEngine


class ParadoxResolutionEngine:
    """
    Four mechanisms:
    A. Paradox isolation
    B. Automatic timeline branching
    C. Causal correction
    D. Paradox preservation
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        branching: TimelineBranchingEngine,
        alteration: TemporalAlterationEngine,
        decay: ExponentialDecayEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> None:
        self.registry = registry
        self.branching = branching
        self.alteration = alteration
        self.decay = decay
        self.config = config
        self.rng = rng

    def choose_strategy(self, paradox: Paradox) -> ResolutionStrategy:
        enabled = [
            ResolutionStrategy(s)
            for s in self.config.resolution_strategies_enabled
        ]
        if not enabled:
            return ResolutionStrategy.PRESERVATION

        # Severity-based preference with config default as fallback
        if paradox.severity >= 0.8 and ResolutionStrategy.ISOLATION in enabled:
            return ResolutionStrategy.ISOLATION
        if paradox.severity >= 0.5 and ResolutionStrategy.AUTO_BRANCH in enabled:
            return ResolutionStrategy.AUTO_BRANCH
        if paradox.severity >= 0.3 and ResolutionStrategy.CAUSAL_CORRECTION in enabled:
            return ResolutionStrategy.CAUSAL_CORRECTION
        if ResolutionStrategy.PRESERVATION in enabled:
            return ResolutionStrategy.PRESERVATION
        return enabled[0]

    def resolve(
        self,
        paradox: Paradox,
        sim_time: float,
        resources: ResourcePool,
        strategy: Optional[ResolutionStrategy] = None,
    ) -> Paradox:
        strategy = strategy or self.choose_strategy(paradox)
        if strategy.value not in self.config.resolution_strategies_enabled:
            strategy = ResolutionStrategy(
                self.config.default_resolution_strategy
            )

        paradox.status = ParadoxStatus.RESOLVING
        paradox.resolution_strategy = strategy
        paradox.history.append(
            {"time": sim_time, "action": "resolving", "strategy": strategy.value}
        )

        if strategy == ResolutionStrategy.ISOLATION:
            self._isolate(paradox, sim_time)
        elif strategy == ResolutionStrategy.AUTO_BRANCH:
            self._auto_branch(paradox, sim_time, resources)
        elif strategy == ResolutionStrategy.CAUSAL_CORRECTION:
            self._causal_correction(paradox, sim_time)
        elif strategy == ResolutionStrategy.PRESERVATION:
            self._preserve(paradox, sim_time)

        return paradox

    def _isolate(self, paradox: Paradox, sim_time: float) -> None:
        """A. Paradox isolation — quarantine affected timelines."""
        for tid in paradox.affected_timeline_ids:
            tl = self.registry.get(tid)
            if not tl:
                continue
            self.registry.update_status(tid, TimelineStatus.ISOLATED)
            self.decay.force_decay(tl, factor=0.4)
            tl.branching_probability *= 0.1
            tl.events.append(
                TimelineEvent(
                    timeline_id=tid,
                    event_type=EventType.RESOLUTION,
                    simulation_time=sim_time,
                    wall_timestamp=time.time(),
                    description=f"Isolated due to paradox {paradox.id[:8]}",
                    payload={"paradox_id": paradox.id, "strategy": "isolation"},
                )
            )
        paradox.status = ParadoxStatus.ISOLATED
        paradox.resolution_record.append(
            {"time": sim_time, "strategy": "isolation", "result": "quarantined"}
        )
        paradox.history.append({"time": sim_time, "action": "isolated"})

    def _auto_branch(
        self, paradox: Paradox, sim_time: float, resources: ResourcePool
    ) -> None:
        """B. Automatic timeline branching — fork to escape the paradox."""
        branched = []
        for tid in paradox.affected_timeline_ids:
            tl = self.registry.get(tid)
            if not tl:
                continue
            child = self.branching.branch(
                tl,
                sim_time,
                resources,
                mutation={"reason": "paradox_resolution", "paradox_id": paradox.id},
            )
            if child:
                branched.append(child.id)
                # Parent stays paradoxical briefly; child is clean
                self.registry.update_status(child.id, TimelineStatus.ACTIVE)
                child.stability_score = min(1.0, child.stability_score + 0.2)
            # Soften parent paradox state
            tl.stability_score = min(1.0, tl.stability_score + 0.1)
            if tl.status == TimelineStatus.PARADOXICAL:
                self.registry.update_status(tid, TimelineStatus.ACTIVE)
            tl.events.append(
                TimelineEvent(
                    timeline_id=tid,
                    event_type=EventType.RESOLUTION,
                    simulation_time=sim_time,
                    wall_timestamp=time.time(),
                    description=f"Auto-branched to resolve paradox {paradox.id[:8]}",
                    payload={
                        "paradox_id": paradox.id,
                        "strategy": "auto_branch",
                        "child_ids": branched,
                    },
                )
            )
        paradox.status = ParadoxStatus.RESOLVED
        paradox.resolution_record.append(
            {
                "time": sim_time,
                "strategy": "auto_branch",
                "branched": branched,
            }
        )
        paradox.history.append({"time": sim_time, "action": "auto_branched"})

    def _causal_correction(self, paradox: Paradox, sim_time: float) -> None:
        """C. Causal correction — rewrite contradictory events toward consistency."""
        for tid in paradox.affected_timeline_ids:
            tl = self.registry.get(tid)
            if not tl:
                continue
            # Neutralize negative polarity events among contradictions
            for ce in paradox.contradictory_events:
                if ce.get("polarity") == "-":
                    eid = ce.get("id")
                    if eid:
                        self.alteration.rewrite_event(
                            tid,
                            eid,
                            new_description=f"[corrected] Causal neutralization of {eid[:8]}",
                            new_payload={"polarity": 0, "corrected": True},
                            sim_time=sim_time,
                        )
            tl.stability_score = min(1.0, tl.stability_score + 0.15)
            if tl.status == TimelineStatus.PARADOXICAL:
                self.registry.update_status(tid, TimelineStatus.ACTIVE)
            tl.events.append(
                TimelineEvent(
                    timeline_id=tid,
                    event_type=EventType.RESOLUTION,
                    simulation_time=sim_time,
                    wall_timestamp=time.time(),
                    description=f"Causal correction for paradox {paradox.id[:8]}",
                    payload={"paradox_id": paradox.id, "strategy": "causal_correction"},
                )
            )
        paradox.status = ParadoxStatus.RESOLVED
        paradox.resolution_record.append(
            {"time": sim_time, "strategy": "causal_correction", "result": "neutralized"}
        )
        paradox.history.append({"time": sim_time, "action": "causally_corrected"})

    def _preserve(self, paradox: Paradox, sim_time: float) -> None:
        """D. Paradox preservation — keep the paradox visible and unresolved-as-feature."""
        for tid in paradox.affected_timeline_ids:
            tl = self.registry.get(tid)
            if not tl:
                continue
            # Mark as paradoxical but stable enough to persist
            self.registry.update_status(tid, TimelineStatus.PARADOXICAL)
            tl.events.append(
                TimelineEvent(
                    timeline_id=tid,
                    event_type=EventType.RESOLUTION,
                    simulation_time=sim_time,
                    wall_timestamp=time.time(),
                    description=f"Paradox {paradox.id[:8]} preserved as ontological feature",
                    payload={"paradox_id": paradox.id, "strategy": "preservation"},
                )
            )
        paradox.status = ParadoxStatus.PRESERVED
        paradox.resolution_record.append(
            {"time": sim_time, "strategy": "preservation", "result": "kept_visible"}
        )
        paradox.history.append({"time": sim_time, "action": "preserved"})

    def resolve_all(
        self,
        paradoxes: list[Paradox],
        sim_time: float,
        resources: ResourcePool,
    ) -> list[Paradox]:
        resolved = []
        for p in paradoxes:
            if p.status != ParadoxStatus.DETECTED:
                continue
            if not self.config.auto_resolve:
                continue
            resolved.append(self.resolve(p, sim_time, resources))
        return resolved
