"""Reward ledger — durable trace of think→act→score for reproducibility."""

from __future__ import annotations

from typing import Any

from ..models.learning import RewardRecord


class RewardLedger:
    """Bounded history of reward records. Never silently destroys — trims oldest."""

    def __init__(self, max_records: int = 5000) -> None:
        self.max_records = max_records
        self._records: list[RewardRecord] = []
        self._by_action: dict[str, list[float]] = {}

    def record(self, entry: RewardRecord) -> None:
        self._records.append(entry)
        self._by_action.setdefault(entry.action, []).append(entry.reward)
        if len(self._records) > self.max_records:
            overflow = len(self._records) - self.max_records
            self._records = self._records[overflow:]

    def recent(self, limit: int = 50) -> list[RewardRecord]:
        return self._records[-limit:]

    def mean_reward(self, action: str | None = None, window: int = 50) -> float:
        if action:
            vals = self._by_action.get(action, [])[-window:]
        else:
            vals = [r.reward for r in self._records[-window:]]
        if not vals:
            return 0.0
        return float(sum(vals) / len(vals))

    def action_stats(self) -> dict[str, dict[str, float]]:
        stats: dict[str, dict[str, float]] = {}
        for action, rewards in self._by_action.items():
            recent = rewards[-100:]
            if not recent:
                continue
            stats[action] = {
                "count": float(len(rewards)),
                "mean": float(sum(recent) / len(recent)),
                "last": float(recent[-1]),
            }
        return stats

    def to_list(self, limit: int = 5000) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._records[-limit:]]

    def load(self, entries: list[dict[str, Any]]) -> None:
        self._records = [RewardRecord.from_dict(e) for e in entries]
        self._by_action.clear()
        for r in self._records:
            self._by_action.setdefault(r.action, []).append(r.reward)
