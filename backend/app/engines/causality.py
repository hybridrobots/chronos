"""Causal Dependency Engine — tracks and validates causal chains across events."""

from __future__ import annotations

from typing import Any

from ..models.timeline import Timeline, TimelineEvent
from ..models.relationships import Relationship, RelationshipType
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine


class CausalDependencyEngine:
    """Builds and validates causal dependency graphs within and across timelines."""

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
    ) -> None:
        self.registry = registry
        self.config = config
        self._conflicts: list[dict[str, Any]] = []

    def link_events(
        self,
        cause: TimelineEvent,
        effect: TimelineEvent,
        sim_time: float,
        record_edge: bool = False,
    ) -> None:
        if cause.id not in effect.causal_deps:
            effect.causal_deps.append(cause.id)
        # Edges are optional — event.causal_deps already encode the graph.
        # Recording every link as a Relationship unbounded the edge table.
        if record_edge and cause.timeline_id != effect.timeline_id:
            rel = Relationship(
                source_id=cause.timeline_id,
                target_id=effect.timeline_id,
                rel_type=RelationshipType.CAUSAL,
                strength=1.0,
                simulation_time=sim_time,
                metadata={
                    "cause_event": cause.id,
                    "effect_event": effect.id,
                },
            )
            self.registry.add_relationship(rel)

    def detect_conflicts(self, timeline: Timeline) -> list[dict[str, Any]]:
        """
        Detect causal conflicts: events that claim contradictory outcomes
        with overlapping causal ancestry.
        """
        conflicts = []
        active = timeline.active_events()
        # Group by coarse type+payload key for contradiction detection
        by_key: dict[str, list[TimelineEvent]] = {}
        for evt in active:
            key = f"{evt.event_type.value}:{evt.payload.get('domain', 'general')}"
            by_key.setdefault(key, []).append(evt)

        for key, events in by_key.items():
            if len(events) < 2:
                continue
            # Check for contradictory polarity flags
            positives = [e for e in events if e.payload.get("polarity", 0) > 0]
            negatives = [e for e in events if e.payload.get("polarity", 0) < 0]
            if positives and negatives:
                # Shared causal ancestors amplify conflict severity
                pos_deps = set()
                for e in positives:
                    pos_deps.update(e.causal_deps)
                neg_deps = set()
                for e in negatives:
                    neg_deps.update(e.causal_deps)
                shared = pos_deps & neg_deps
                severity = 0.4 + 0.3 * min(len(shared), 2) + 0.1 * len(positives + negatives)
                # Require shared causal ancestry for a true paradox signal
                if not shared and severity < 0.7:
                    continue
                conflicts.append(
                    {
                        "timeline_id": timeline.id,
                        "domain": key,
                        "positive_events": [e.id for e in positives[-3:]],
                        "negative_events": [e.id for e in negatives[-3:]],
                        "shared_deps": list(shared),
                        "severity": min(1.0, severity),
                    }
                )
        # Bound in-memory conflict log
        self._conflicts.extend(conflicts)
        if len(self._conflicts) > 200:
            self._conflicts = self._conflicts[-200:]
        return conflicts

    def scan_all(self) -> list[dict[str, Any]]:
        all_conflicts = []
        # Sample timelines for performance under large populations
        timelines = self.registry.active_timelines()
        if len(timelines) > 40:
            step = max(1, len(timelines) // 30)
            timelines = timelines[::step]
        for tl in timelines:
            all_conflicts.extend(self.detect_conflicts(tl))
        return all_conflicts

    def get_dependency_chain(
        self, timeline_id: str, event_id: str
    ) -> list[str]:
        tl = self.registry.get(timeline_id)
        if not tl:
            return []
        by_id = {e.id: e for e in tl.events}
        chain = []
        stack = [event_id]
        seen = set()
        while stack:
            eid = stack.pop()
            if eid in seen or eid not in by_id:
                continue
            seen.add(eid)
            chain.append(eid)
            stack.extend(by_id[eid].causal_deps)
        return chain

    def get_conflicts(self) -> list[dict[str, Any]]:
        return list(self._conflicts)
