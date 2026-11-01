"""Graph relationships between timelines."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RelationshipType(str, Enum):
    PARENT_CHILD = "parent_child"
    INTERACTION = "interaction"
    CONVERGENCE = "convergence"
    CAUSAL = "causal"
    PARADOX_LINK = "paradox_link"


@dataclass
class Relationship:
    """A directed or undirected edge in the timeline graph."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    rel_type: RelationshipType = RelationshipType.INTERACTION
    strength: float = 1.0
    simulation_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "rel_type": self.rel_type.value,
            "strength": self.strength,
            "simulation_time": self.simulation_time,
            "metadata": self.metadata,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            rel_type=RelationshipType(data["rel_type"]),
            strength=data.get("strength", 1.0),
            simulation_time=data.get("simulation_time", 0.0),
            metadata=data.get("metadata", {}),
            active=data.get("active", True),
        )
