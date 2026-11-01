"""Interactive decision counsel — life problems explored as competing paths."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class DecisionStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


@dataclass
class DecisionPath:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    description: str = ""
    timeline_ids: list[str] = field(default_factory=list)
    # Simulated relative viability (NOT a real-world probability)
    viability: float = 0.0
    viability_ema: float = 0.0
    relative_share: float = 0.0  # normalized among paths, sums to 1
    mean_weight: float = 0.0
    mean_stability: float = 0.0
    mean_fitness: float = 0.0
    generation_depth: int = 0
    sample_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "timeline_ids": self.timeline_ids,
            "viability": self.viability,
            "viability_ema": self.viability_ema,
            "relative_share": self.relative_share,
            "mean_weight": self.mean_weight,
            "mean_stability": self.mean_stability,
            "mean_fitness": self.mean_fitness,
            "generation_depth": self.generation_depth,
            "sample_count": self.sample_count,
            "history": self.history[-50:],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionPath:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            label=data.get("label", ""),
            description=data.get("description", ""),
            timeline_ids=list(data.get("timeline_ids", [])),
            viability=float(data.get("viability", 0.0)),
            viability_ema=float(data.get("viability_ema", 0.0)),
            relative_share=float(data.get("relative_share", 0.0)),
            mean_weight=float(data.get("mean_weight", 0.0)),
            mean_stability=float(data.get("mean_stability", 0.0)),
            mean_fitness=float(data.get("mean_fitness", 0.0)),
            generation_depth=int(data.get("generation_depth", 0)),
            sample_count=int(data.get("sample_count", 0)),
            history=list(data.get("history", [])),
        )


@dataclass
class DecisionSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    problem: str = ""
    context: str = ""
    status: DecisionStatus = DecisionStatus.DRAFT
    paths: list[DecisionPath] = field(default_factory=list)
    target_generations: int = 5
    target_cycles: int = 80
    cycles_done: int = 0
    max_generation_seen: int = 0
    created_sim_time: float = 0.0
    completed_sim_time: float = 0.0
    recommendation_path_id: Optional[str] = None
    recommendation_summary: str = ""
    disclaimer: str = (
        "Relative viability scores are simulated influence within Chronos — "
        "not predictions or probabilities of real-life outcomes. You decide."
    )
    stress_tested: bool = True  # score under scarcity as well

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "problem": self.problem,
            "context": self.context,
            "status": self.status.value,
            "paths": [p.to_dict() for p in self.paths],
            "target_generations": self.target_generations,
            "target_cycles": self.target_cycles,
            "cycles_done": self.cycles_done,
            "max_generation_seen": self.max_generation_seen,
            "created_sim_time": self.created_sim_time,
            "completed_sim_time": self.completed_sim_time,
            "recommendation_path_id": self.recommendation_path_id,
            "recommendation_summary": self.recommendation_summary,
            "disclaimer": self.disclaimer,
            "stress_tested": self.stress_tested,
            "progress": min(
                1.0,
                max(
                    self.cycles_done / max(self.target_cycles, 1),
                    self.max_generation_seen / max(self.target_generations, 1),
                ),
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionSession:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            problem=data.get("problem", ""),
            context=data.get("context", ""),
            status=DecisionStatus(data.get("status", "draft")),
            paths=[DecisionPath.from_dict(p) for p in data.get("paths", [])],
            target_generations=int(data.get("target_generations", 5)),
            target_cycles=int(data.get("target_cycles", 80)),
            cycles_done=int(data.get("cycles_done", 0)),
            max_generation_seen=int(data.get("max_generation_seen", 0)),
            created_sim_time=float(data.get("created_sim_time", 0.0)),
            completed_sim_time=float(data.get("completed_sim_time", 0.0)),
            recommendation_path_id=data.get("recommendation_path_id"),
            recommendation_summary=data.get("recommendation_summary", ""),
            disclaimer=data.get(
                "disclaimer",
                cls.__dataclass_fields__["disclaimer"].default,  # type: ignore
            ),
            stress_tested=bool(data.get("stress_tested", True)),
        )
