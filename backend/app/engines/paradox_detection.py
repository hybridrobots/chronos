"""Paradox Detection Engine — identifies causal contradictions in the multiverse."""

from __future__ import annotations

import time
from typing import Any, Optional

from ..models.paradox import Paradox, ParadoxStatus
from ..models.timeline import TimelineStatus, EventType, TimelineEvent
from ..models.relationships import Relationship, RelationshipType
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine
from .causality import CausalDependencyEngine


class ParadoxDetectionEngine:
    """Scans for paradoxes from causal conflicts and contradictory event chains."""

    MAX_STORED = 200

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        causality: CausalDependencyEngine,
        config: SimulationConfig,
    ) -> None:
        self.registry = registry
        self.causality = causality
        self.config = config
        self._paradoxes: dict[str, Paradox] = {}
        # Fingerprints of conflicts already converted to paradoxes (lifetime)
        self._seen_keys: set[str] = set()

    def _fingerprint(self, timeline_id: str, domain: str, events: list[str]) -> str:
        return f"{timeline_id}|{domain}|{'|'.join(sorted(events))}"

    def detect_from_conflicts(
        self, conflicts: list[dict[str, Any]], sim_time: float
    ) -> list[Paradox]:
        detected = []
        sensitivity = self.config.paradox_detection_sensitivity
        for conflict in conflicts:
            if conflict["severity"] < sensitivity * 0.5:
                continue
            event_ids = conflict["positive_events"] + conflict["negative_events"]
            key = self._fingerprint(
                conflict["timeline_id"],
                str(conflict.get("domain", "")),
                event_ids,
            )
            if key in self._seen_keys:
                continue
            # Also skip if an open paradox already covers this timeline+domain
            domain = str(conflict.get("domain", ""))
            if any(
                p.status
                in (
                    ParadoxStatus.DETECTED,
                    ParadoxStatus.RESOLVING,
                    ParadoxStatus.PRESERVED,
                    ParadoxStatus.ISOLATED,
                )
                and conflict["timeline_id"] in p.affected_timeline_ids
                and domain in p.description
                for p in self._paradoxes.values()
            ):
                continue

            self._seen_keys.add(key)
            paradox = Paradox(
                affected_timeline_ids=[conflict["timeline_id"]],
                contradictory_events=[
                    {"id": eid, "polarity": "+"}
                    for eid in conflict["positive_events"]
                ]
                + [
                    {"id": eid, "polarity": "-"}
                    for eid in conflict["negative_events"]
                ],
                causal_dependencies=conflict.get("shared_deps", []),
                severity=conflict["severity"],
                detection_time=sim_time,
                wall_timestamp=time.time(),
                status=ParadoxStatus.DETECTED,
                description=(
                    f"Causal paradox in domain {domain} "
                    f"(severity={conflict['severity']:.2f})"
                ),
                history=[
                    {
                        "time": sim_time,
                        "action": "detected",
                        "conflict": {
                            "domain": domain,
                            "severity": conflict["severity"],
                        },
                    }
                ],
            )
            self._paradoxes[paradox.id] = paradox
            tl = self.registry.get(conflict["timeline_id"])
            if tl:
                self.registry.update_status(tl.id, TimelineStatus.PARADOXICAL)
                tl.events.append(
                    TimelineEvent(
                        timeline_id=tl.id,
                        event_type=EventType.PARADOX,
                        simulation_time=sim_time,
                        wall_timestamp=time.time(),
                        description=paradox.description,
                        payload={"paradox_id": paradox.id},
                    )
                )
                rel = Relationship(
                    source_id=tl.id,
                    target_id=tl.id,
                    rel_type=RelationshipType.PARADOX_LINK,
                    strength=paradox.severity,
                    simulation_time=sim_time,
                    metadata={"paradox_id": paradox.id},
                )
                self.registry.add_relationship(rel)
            detected.append(paradox)
            self._prune()
        return detected

    def detect_cross_timeline(self, sim_time: float) -> list[Paradox]:
        """Detect paradoxes arising from contradictory interactions between timelines."""
        detected = []
        interactions = self.registry.get_relationships(
            rel_type=RelationshipType.INTERACTION
        )
        pair_strength: dict[tuple[str, str], list[float]] = {}
        for rel in interactions:
            pair = tuple(sorted([rel.source_id, rel.target_id]))
            pair_strength.setdefault(pair, []).append(rel.strength)

        for (a, b), strengths in pair_strength.items():
            if len(strengths) < 3:
                continue
            if sum(strengths) <= self.config.feedback_loop_threshold * 3:
                continue
            severity = min(1.0, sum(strengths) / 6)
            if severity < self.config.paradox_detection_sensitivity * 0.5:
                continue
            key = f"cross|{a}|{b}"
            if key in self._seen_keys:
                continue
            self._seen_keys.add(key)
            paradox = Paradox(
                affected_timeline_ids=[a, b],
                contradictory_events=[],
                causal_dependencies=[],
                severity=severity,
                detection_time=sim_time,
                wall_timestamp=time.time(),
                status=ParadoxStatus.DETECTED,
                description=f"Cross-timeline feedback paradox between {a[:8]} and {b[:8]}",
                history=[{"time": sim_time, "action": "detected_cross"}],
            )
            self._paradoxes[paradox.id] = paradox
            detected.append(paradox)
            self._prune()
        return detected

    def _prune(self) -> None:
        """Bound stored paradoxes — keep unresolved + newest resolved."""
        if len(self._paradoxes) <= self.MAX_STORED:
            return
        unresolved = [
            p
            for p in self._paradoxes.values()
            if p.status
            in (
                ParadoxStatus.DETECTED,
                ParadoxStatus.RESOLVING,
                ParadoxStatus.PRESERVED,
                ParadoxStatus.ISOLATED,
            )
        ]
        resolved = [
            p
            for p in self._paradoxes.values()
            if p.status == ParadoxStatus.RESOLVED
        ]
        resolved.sort(key=lambda p: p.detection_time, reverse=True)
        keep = unresolved + resolved[: max(0, self.MAX_STORED - len(unresolved))]
        self._paradoxes = {p.id: p for p in keep}

    def get_all(self) -> list[Paradox]:
        return list(self._paradoxes.values())

    def get_unresolved(self) -> list[Paradox]:
        return [
            p
            for p in self._paradoxes.values()
            if p.status == ParadoxStatus.DETECTED
        ]

    def get(self, paradox_id: str) -> Optional[Paradox]:
        return self._paradoxes.get(paradox_id)

    def load(self, paradoxes: list[Paradox]) -> None:
        self._paradoxes = {p.id: p for p in paradoxes[-self.MAX_STORED :]}
        self._seen_keys = set()
        for p in paradoxes:
            for tid in p.affected_timeline_ids:
                ev_ids = [str(e.get("id", "")) for e in p.contradictory_events]
                self._seen_keys.add(
                    self._fingerprint(tid, "", ev_ids)
                )
                self._seen_keys.add(f"cross|{tid}")
