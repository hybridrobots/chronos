"""Timeline Registry Engine — central index of all timelines and graph edges."""

from __future__ import annotations

from typing import Iterator, Optional

from ..models.timeline import Timeline, TimelineStatus
from ..models.relationships import Relationship, RelationshipType


class TimelineRegistryEngine:
    """
    Maintains the living registry of timelines and their graph relationships.
    Never permanently deletes timeline histories — archives instead.
    """

    def __init__(self) -> None:
        self._timelines: dict[str, Timeline] = {}
        self._relationships: dict[str, Relationship] = {}
        self._children: dict[str, list[str]] = {}
        self._by_status: dict[TimelineStatus, set[str]] = {
            s: set() for s in TimelineStatus
        }

    def register(self, timeline: Timeline) -> Timeline:
        self._timelines[timeline.id] = timeline
        self._by_status[timeline.status].add(timeline.id)
        if timeline.parent_id:
            self._children.setdefault(timeline.parent_id, []).append(timeline.id)
            rel = Relationship(
                source_id=timeline.parent_id,
                target_id=timeline.id,
                rel_type=RelationshipType.PARENT_CHILD,
                strength=1.0,
                simulation_time=timeline.simulation_birth_time,
            )
            self._relationships[rel.id] = rel
        return timeline

    def get(self, timeline_id: str) -> Optional[Timeline]:
        return self._timelines.get(timeline_id)

    def update_status(self, timeline_id: str, status: TimelineStatus) -> None:
        tl = self._timelines.get(timeline_id)
        if not tl:
            return
        self._by_status[tl.status].discard(timeline_id)
        tl.status = status
        self._by_status[status].add(timeline_id)

    def archive(self, timeline_id: str) -> None:
        tl = self._timelines.get(timeline_id)
        if tl:
            tl.archived = True
            self.update_status(timeline_id, TimelineStatus.ARCHIVED)

    def add_relationship(self, rel: Relationship) -> Relationship:
        self._relationships[rel.id] = rel
        return rel

    def get_relationships(
        self,
        timeline_id: Optional[str] = None,
        rel_type: Optional[RelationshipType] = None,
        active_only: bool = True,
    ) -> list[Relationship]:
        result = []
        for rel in self._relationships.values():
            if active_only and not rel.active:
                continue
            if timeline_id and rel.source_id != timeline_id and rel.target_id != timeline_id:
                continue
            if rel_type and rel.rel_type != rel_type:
                continue
            result.append(rel)
        return result

    def children_of(self, timeline_id: str) -> list[Timeline]:
        return [
            self._timelines[cid]
            for cid in self._children.get(timeline_id, [])
            if cid in self._timelines
        ]

    def ancestors(self, timeline_id: str) -> list[Timeline]:
        result = []
        current = self._timelines.get(timeline_id)
        while current and current.parent_id:
            parent = self._timelines.get(current.parent_id)
            if not parent:
                break
            result.append(parent)
            current = parent
        return result

    def active_timelines(self) -> list[Timeline]:
        return [
            t
            for t in self._timelines.values()
            if not t.archived and t.status != TimelineStatus.ARCHIVED
        ]

    def all_timelines(self) -> list[Timeline]:
        return list(self._timelines.values())

    def count(self, active_only: bool = True) -> int:
        if active_only:
            return len(self.active_timelines())
        return len(self._timelines)

    def by_status(self, status: TimelineStatus) -> list[Timeline]:
        return [
            self._timelines[tid]
            for tid in self._by_status.get(status, set())
            if tid in self._timelines
        ]

    def iter_active(self) -> Iterator[Timeline]:
        yield from self.active_timelines()

    def genealogy(self, timeline_id: str) -> dict:
        """Build a genealogy subtree rooted at timeline_id (or full forest)."""
        tl = self._timelines.get(timeline_id)
        if not tl:
            return {}
        return {
            "id": tl.id,
            "generation": tl.generation,
            "status": tl.status.value,
            "weight": tl.current_weight,
            "children": [
                self.genealogy(c.id) for c in self.children_of(timeline_id)
            ],
        }

    def clear(self) -> None:
        self._timelines.clear()
        self._relationships.clear()
        self._children.clear()
        self._by_status = {s: set() for s in TimelineStatus}

    def load_state(
        self,
        timelines: list[Timeline],
        relationships: list[Relationship],
    ) -> None:
        self.clear()
        for tl in timelines:
            self._timelines[tl.id] = tl
            self._by_status[tl.status].add(tl.id)
            if tl.parent_id:
                self._children.setdefault(tl.parent_id, []).append(tl.id)
        for rel in relationships:
            self._relationships[rel.id] = rel
