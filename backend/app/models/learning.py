"""Fitness, reward, and policy action models for the learning loop."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ActionType(str, Enum):
    OBSERVE = "observe"
    MUTATE = "mutate"
    BRANCH = "branch"
    INTERACT = "interact"
    REWRITE = "rewrite"
    STABILIZE = "stabilize"


@dataclass
class RewardRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timeline_id: str = ""
    action: str = ActionType.OBSERVE.value
    reward: float = 0.0
    sim_time: float = 0.0
    energy_spent: float = 0.0
    energy_refunded: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timeline_id": self.timeline_id,
            "action": self.action,
            "reward": self.reward,
            "sim_time": self.sim_time,
            "energy_spent": self.energy_spent,
            "energy_refunded": self.energy_refunded,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RewardRecord:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timeline_id=data.get("timeline_id", ""),
            action=data.get("action", ActionType.OBSERVE.value),
            reward=float(data.get("reward", 0.0)),
            sim_time=float(data.get("sim_time", 0.0)),
            energy_spent=float(data.get("energy_spent", 0.0)),
            energy_refunded=float(data.get("energy_refunded", 0.0)),
            details=data.get("details", {}),
        )


@dataclass
class ProposedAction:
    action: ActionType
    timeline_id: str
    target_id: Optional[str] = None
    think_cost: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
