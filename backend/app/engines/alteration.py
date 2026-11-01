"""Temporal Alteration Engine — Mechanism B: timeline rewriting with audit history."""

from __future__ import annotations

import time
from typing import Any, Optional

from ..models.timeline import Timeline, TimelineEvent, EventType, TimelineStatus
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine


class TemporalAlterationEngine:
    """
    Mechanism B — Timeline rewriting:
    Modify a historical event, recalculate downstream deps, preserve prior versions.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
    ) -> None:
        self.registry = registry
        self.config = config
        self._alteration_log: list[dict[str, Any]] = []

    def rewrite_event(
        self,
        timeline_id: str,
        event_id: str,
        new_description: str,
        new_payload: Optional[dict] = None,
        sim_time: float = 0.0,
    ) -> Optional[TimelineEvent]:
        tl = self.registry.get(timeline_id)
        if not tl:
            return None

        original = None
        for evt in tl.events:
            if evt.id == event_id and evt.is_active:
                original = evt
                break
        if not original:
            return None

        # Preserve previous version — mark superseded, keep in history
        original.is_active = False
        new_evt = TimelineEvent(
            timeline_id=timeline_id,
            event_type=EventType.REWRITE,
            simulation_time=sim_time,
            wall_timestamp=time.time(),
            description=new_description,
            payload=new_payload or {**original.payload, "rewritten": True},
            version=original.version + 1,
            parent_event_id=original.id,
            influence=original.influence,
            causal_deps=list(original.causal_deps),
        )
        original.superseded_by = new_evt.id
        tl.events.append(new_evt)
        tl.historical_version += 1
        tl.mutation_history.append(
            {
                "time": sim_time,
                "type": "rewrite",
                "original_event": original.id,
                "new_event": new_evt.id,
            }
        )
        self.registry.update_status(timeline_id, TimelineStatus.MUTATING)

        # Recalculate affected downstream: events that depend on the original
        affected = self._recalculate_downstream(tl, original.id, sim_time)

        record = {
            "timeline_id": timeline_id,
            "original_event_id": original.id,
            "new_event_id": new_evt.id,
            "sim_time": sim_time,
            "affected_count": len(affected),
            "description": new_description,
        }
        self._alteration_log.append(record)
        return new_evt

    def _recalculate_downstream(
        self,
        timeline: Timeline,
        changed_event_id: str,
        sim_time: float,
    ) -> list[str]:
        affected = []
        for evt in timeline.active_events():
            if changed_event_id in evt.causal_deps:
                # Perturb influence as causal ripple
                evt.influence *= 0.9
                evt.payload = {
                    **evt.payload,
                    "causal_ripple_from": changed_event_id,
                    "ripple_time": sim_time,
                }
                affected.append(evt.id)
        # Stability hit from rewriting history
        timeline.stability_score = max(0.1, timeline.stability_score - 0.05)
        return affected

    def get_alteration_log(self) -> list[dict[str, Any]]:
        return list(self._alteration_log)

    def get_event_versions(
        self, timeline_id: str, event_id: str
    ) -> list[TimelineEvent]:
        """Walk the version chain for a fully audited history."""
        tl = self.registry.get(timeline_id)
        if not tl:
            return []
        by_id = {e.id: e for e in tl.events}
        versions = []
        current = by_id.get(event_id)
        # Walk back to root
        while current and current.parent_event_id and current.parent_event_id in by_id:
            parent = by_id[current.parent_event_id]
            if parent.event_type == EventType.REWRITE or not parent.is_active:
                current = parent
            else:
                break
        # Walk forward collecting versions
        while current:
            versions.append(current)
            if current.superseded_by and current.superseded_by in by_id:
                current = by_id[current.superseded_by]
            else:
                break
        return versions
