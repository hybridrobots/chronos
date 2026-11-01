"""Paradox detection and resolution data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ParadoxStatus(str, Enum):
    DETECTED = "detected"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    PRESERVED = "preserved"
    ISOLATED = "isolated"


class ResolutionStrategy(str, Enum):
    ISOLATION = "isolation"
    AUTO_BRANCH = "auto_branch"
    CAUSAL_CORRECTION = "causal_correction"
    PRESERVATION = "preservation"


@dataclass
class Paradox:
    """A causal paradox detected within the multiverse."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    affected_timeline_ids: list[str] = field(default_factory=list)
    contradictory_events: list[dict[str, Any]] = field(default_factory=list)
    causal_dependencies: list[str] = field(default_factory=list)
    severity: float = 0.5
    detection_time: float = 0.0
    wall_timestamp: float = 0.0
    resolution_strategy: Optional[ResolutionStrategy] = None
    status: ParadoxStatus = ParadoxStatus.DETECTED
    description: str = ""
    resolution_record: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "affected_timeline_ids": self.affected_timeline_ids,
            "contradictory_events": self.contradictory_events,
            "causal_dependencies": self.causal_dependencies,
            "severity": self.severity,
            "detection_time": self.detection_time,
            "wall_timestamp": self.wall_timestamp,
            "resolution_strategy": (
                self.resolution_strategy.value if self.resolution_strategy else None
            ),
            "status": self.status.value,
            "description": self.description,
            "resolution_record": self.resolution_record,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Paradox:
        strategy = data.get("resolution_strategy")
        return cls(
            id=data["id"],
            affected_timeline_ids=data.get("affected_timeline_ids", []),
            contradictory_events=data.get("contradictory_events", []),
            causal_dependencies=data.get("causal_dependencies", []),
            severity=data.get("severity", 0.5),
            detection_time=data.get("detection_time", 0.0),
            wall_timestamp=data.get("wall_timestamp", 0.0),
            resolution_strategy=(
                ResolutionStrategy(strategy) if strategy else None
            ),
            status=ParadoxStatus(data.get("status", "detected")),
            description=data.get("description", ""),
            resolution_record=data.get("resolution_record", []),
            history=data.get("history", []),
        )
