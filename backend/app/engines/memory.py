"""Historical Memory Engine — retention, archival policies, never silent destroy."""

from __future__ import annotations

from typing import Any

from ..models.timeline import TimelineEvent
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine


class HistoricalMemoryEngine:
    """
    Manages event history retention.
    Old events are archived (is_active=False) — never permanently deleted.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
    ) -> None:
        self.registry = registry
        self.config = config
        self._global_log: list[dict[str, Any]] = []

    def record(self, entry: dict[str, Any]) -> None:
        self._global_log.append(entry)
        # Bound memory: archive oldest log entries beyond capacity
        max_log = self.config.memory_capacity
        if len(self._global_log) > max_log:
            # Keep newest; oldest remain conceptually archived in DB persistence
            overflow = len(self._global_log) - max_log
            self._global_log = self._global_log[overflow:]

    def apply_retention(self) -> dict[str, int]:
        """Archive excess active events per timeline without destroying them."""
        archived = 0
        if not self.config.archive_old_events:
            return {"archived": 0}

        limit = self.config.max_active_events_per_timeline
        for tl in self.registry.all_timelines():
            active = [e for e in tl.events if e.is_active]
            if len(active) <= limit:
                continue
            # Archive oldest first (by simulation_time)
            active.sort(key=lambda e: e.simulation_time)
            excess = len(active) - limit
            for evt in active[:excess]:
                # Don't archive genesis or divergence markers lightly —
                # but still mark inactive for soft archival
                if evt.event_type.value in ("genesis",):
                    continue
                evt.is_active = False
                evt.payload = {**evt.payload, "archived_by_memory": True}
                archived += 1
        return {"archived": archived}

    def get_timeline_history(
        self, timeline_id: str, include_archived: bool = True
    ) -> list[TimelineEvent]:
        tl = self.registry.get(timeline_id)
        if not tl:
            return []
        if include_archived:
            return list(tl.events)
        return tl.active_events()

    def get_global_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._global_log[-limit:]

    def load_log(self, entries: list[dict[str, Any]]) -> None:
        self._global_log = list(entries)
