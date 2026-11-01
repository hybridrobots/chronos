"""Timeline data model — the fundamental unit of the multiverse organism."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TimelineStatus(str, Enum):
    NASCENT = "nascent"
    ACTIVE = "active"
    GROWING = "growing"
    DECAYING = "decaying"
    MUTATING = "mutating"
    CONVERGING = "converging"
    ISOLATED = "isolated"
    ARCHIVED = "archived"
    PARADOXICAL = "paradoxical"


class EventType(str, Enum):
    GENESIS = "genesis"
    HISTORICAL_CHANGE = "historical_change"
    TECHNOLOGICAL = "technological"
    SOCIAL = "social"
    ENVIRONMENTAL = "environmental"
    UNEXPECTED = "unexpected"
    INTERACTION = "interaction"
    CAUSAL_CONFLICT = "causal_conflict"
    BRANCH_DIVERGENCE = "branch_divergence"
    REWRITE = "rewrite"
    CONVERGENCE = "convergence"
    MUTATION = "mutation"
    DECAY = "decay"
    GROWTH = "growth"
    PARADOX = "paradox"
    RESOLUTION = "resolution"


@dataclass
class TimelineEvent:
    """A single historical event within a timeline. Never permanently deleted."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timeline_id: str = ""
    event_type: EventType = EventType.UNEXPECTED
    simulation_time: float = 0.0
    wall_timestamp: float = 0.0
    description: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    parent_event_id: Optional[str] = None
    superseded_by: Optional[str] = None
    is_active: bool = True
    causal_deps: list[str] = field(default_factory=list)
    influence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timeline_id": self.timeline_id,
            "event_type": self.event_type.value,
            "simulation_time": self.simulation_time,
            "wall_timestamp": self.wall_timestamp,
            "description": self.description,
            "payload": self.payload,
            "version": self.version,
            "parent_event_id": self.parent_event_id,
            "superseded_by": self.superseded_by,
            "is_active": self.is_active,
            "causal_deps": self.causal_deps,
            "influence": self.influence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEvent:
        return cls(
            id=data["id"],
            timeline_id=data["timeline_id"],
            event_type=EventType(data["event_type"]),
            simulation_time=data["simulation_time"],
            wall_timestamp=data.get("wall_timestamp", 0.0),
            description=data.get("description", ""),
            payload=data.get("payload", {}),
            version=data.get("version", 1),
            parent_event_id=data.get("parent_event_id"),
            superseded_by=data.get("superseded_by"),
            is_active=data.get("is_active", True),
            causal_deps=data.get("causal_deps", []),
            influence=data.get("influence", 1.0),
        )


@dataclass
class Timeline:
    """A single timeline within the multiverse organism."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    creation_timestamp: float = 0.0
    simulation_birth_time: float = 0.0
    generation: int = 0
    events: list[TimelineEvent] = field(default_factory=list)
    growth_coefficient: float = 0.05
    decay_coefficient: float = 0.02
    initial_weight: float = 1.0
    current_weight: float = 1.0
    influence_weight: float = 1.0
    stability_score: float = 1.0
    structural_complexity: float = 0.1
    branching_probability: float = 0.08
    mutation_history: list[dict[str, Any]] = field(default_factory=list)
    interaction_ids: list[str] = field(default_factory=list)
    convergence_ids: list[str] = field(default_factory=list)
    historical_version: int = 1
    status: TimelineStatus = TimelineStatus.NASCENT
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    color_hue: float = 0.5
    last_update_time: float = 0.0
    archived: bool = False
    # Learning / fitness state
    fitness: float = 0.0
    fitness_ema: float = 0.0
    cumulative_reward: float = 0.0
    last_reward: float = 0.0
    last_action: str = "observe"
    think_count: int = 0
    decision_session_id: Optional[str] = None
    decision_path_id: Optional[str] = None

    def active_events(self) -> list[TimelineEvent]:
        return [e for e in self.events if e.is_active]

    def to_dict(self, include_events: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "parent_id": self.parent_id,
            "creation_timestamp": self.creation_timestamp,
            "simulation_birth_time": self.simulation_birth_time,
            "generation": self.generation,
            "growth_coefficient": self.growth_coefficient,
            "decay_coefficient": self.decay_coefficient,
            "initial_weight": self.initial_weight,
            "current_weight": self.current_weight,
            "influence_weight": self.influence_weight,
            "stability_score": self.stability_score,
            "structural_complexity": self.structural_complexity,
            "branching_probability": self.branching_probability,
            "mutation_history": self.mutation_history,
            "interaction_ids": self.interaction_ids,
            "convergence_ids": self.convergence_ids,
            "historical_version": self.historical_version,
            "status": self.status.value,
            "position": list(self.position),
            "color_hue": self.color_hue,
            "last_update_time": self.last_update_time,
            "archived": self.archived,
            "event_count": len(self.events),
            "fitness": self.fitness,
            "fitness_ema": self.fitness_ema,
            "cumulative_reward": self.cumulative_reward,
            "last_reward": self.last_reward,
            "last_action": self.last_action,
            "think_count": self.think_count,
            "decision_session_id": self.decision_session_id,
            "decision_path_id": self.decision_path_id,
        }
        if include_events:
            d["events"] = [e.to_dict() for e in self.events]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Timeline:
        events = [TimelineEvent.from_dict(e) for e in data.get("events", [])]
        pos = data.get("position", [0.0, 0.0, 0.0])
        return cls(
            id=data["id"],
            parent_id=data.get("parent_id"),
            creation_timestamp=data.get("creation_timestamp", 0.0),
            simulation_birth_time=data.get("simulation_birth_time", 0.0),
            generation=data.get("generation", 0),
            events=events,
            growth_coefficient=data.get("growth_coefficient", 0.05),
            decay_coefficient=data.get("decay_coefficient", 0.02),
            initial_weight=data.get("initial_weight", 1.0),
            current_weight=data.get("current_weight", 1.0),
            influence_weight=data.get("influence_weight", 1.0),
            stability_score=data.get("stability_score", 1.0),
            structural_complexity=data.get("structural_complexity", 0.1),
            branching_probability=data.get("branching_probability", 0.08),
            mutation_history=data.get("mutation_history", []),
            interaction_ids=data.get("interaction_ids", []),
            convergence_ids=data.get("convergence_ids", []),
            historical_version=data.get("historical_version", 1),
            status=TimelineStatus(data.get("status", "nascent")),
            position=(float(pos[0]), float(pos[1]), float(pos[2])),
            color_hue=data.get("color_hue", 0.5),
            last_update_time=data.get("last_update_time", 0.0),
            archived=data.get("archived", False),
            fitness=data.get("fitness", 0.0),
            fitness_ema=data.get("fitness_ema", 0.0),
            cumulative_reward=data.get("cumulative_reward", 0.0),
            last_reward=data.get("last_reward", 0.0),
            last_action=data.get("last_action", "observe"),
            think_count=data.get("think_count", 0),
            decision_session_id=data.get("decision_session_id"),
            decision_path_id=data.get("decision_path_id"),
        )
