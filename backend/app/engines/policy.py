"""Policy Engine — evolutionary bandit that spends energy to think and act."""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np

from ..models.config import SimulationConfig
from ..models.learning import ActionType, ProposedAction
from ..models.organism import OrganismState, ResourcePool
from ..models.timeline import Timeline, TimelineEvent, EventType, TimelineStatus
from .registry import TimelineRegistryEngine
from .branching import TimelineBranchingEngine
from .alteration import TemporalAlterationEngine
from .interaction import CrossTimelineInteractionEngine
from .fitness import FitnessEngine
from .reward_ledger import RewardLedger
from .events import AutonomousEventEngine


class PolicyEngine:
    """
    Phase A learning policy: epsilon-greedy bandit over action types.

    Thinking costs computational energy. Successful strategies get higher
    selection weight via RewardLedger action means + timeline fitness_ema.
    """

    ACTIONS = [
        ActionType.OBSERVE,
        ActionType.MUTATE,
        ActionType.BRANCH,
        ActionType.INTERACT,
        ActionType.REWRITE,
        ActionType.STABILIZE,
    ]

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
        branching: TimelineBranchingEngine,
        alteration: TemporalAlterationEngine,
        interaction: CrossTimelineInteractionEngine,
        events: AutonomousEventEngine,
        fitness: FitnessEngine,
        ledger: RewardLedger,
        organism: OrganismState,
    ) -> None:
        self.registry = registry
        self.config = config
        self.rng = rng
        self.branching = branching
        self.alteration = alteration
        self.interaction = interaction
        self.events = events
        self.fitness = fitness
        self.ledger = ledger
        self.organism = organism
        # Softmax-friendly action values (initialized neutral)
        self._q: dict[str, float] = {a.value: 0.0 for a in self.ACTIONS}
        self._counts: dict[str, int] = {a.value: 0 for a in self.ACTIONS}

    def choose_action(
        self,
        *,
        throttle: float = 1.0,
        allow_branch: bool = True,
        mode: str = "thrive",
    ) -> ActionType:
        eps = self.config.policy_exploration * (0.5 + 0.5 * throttle)
        if self.rng.random() < eps:
            pool = list(self.ACTIONS)
            if not allow_branch or mode in ("conserve", "crisis"):
                pool = [a for a in pool if a != ActionType.BRANCH]
            if mode == "crisis":
                pool = [ActionType.STABILIZE, ActionType.OBSERVE, ActionType.REWRITE]
            return ActionType(str(self.rng.choice([a.value for a in pool])))
        # Prefer empirically rewarding actions, biased by metabolic mode
        ledger_stats = self.ledger.action_stats()
        scores = []
        for a in self.ACTIONS:
            q = self._q[a.value]
            mean = ledger_stats.get(a.value, {}).get("mean", 0.0)
            score = 0.6 * q + 0.4 * mean
            if mode in ("conserve", "crisis"):
                if a in (ActionType.STABILIZE, ActionType.OBSERVE):
                    score += 0.45
                elif a == ActionType.BRANCH:
                    score -= 1.0
                elif a in (ActionType.MUTATE, ActionType.INTERACT):
                    score -= 0.25
            elif not allow_branch and a == ActionType.BRANCH:
                score -= 2.0
            scores.append(score)
        scores_arr = np.array(scores, dtype=float)
        scores_arr = scores_arr - scores_arr.max()
        probs = np.exp(scores_arr)
        probs = probs / (probs.sum() or 1.0)
        idx = int(self.rng.choice(len(self.ACTIONS), p=probs))
        return self.ACTIONS[idx]

    def select_timeline(self) -> Optional[Timeline]:
        tls = self.registry.active_timelines()
        if not tls:
            return None
        # Softmax over fitness_ema (exploration via temperature)
        fits = np.array([max(t.fitness_ema, -0.5) + 0.5 for t in tls], dtype=float)
        fits = fits - fits.max()
        probs = np.exp(fits / 0.4)
        probs = probs / (probs.sum() or 1.0)
        idx = int(self.rng.choice(len(tls), p=probs))
        return tls[idx]

    def think_cycle(
        self,
        sim_time: float,
        resources: ResourcePool,
        diversity: float,
        *,
        throttle: float = 1.0,
        allow_think: bool = True,
        allow_branch: bool = True,
        mode: str = "thrive",
    ) -> dict[str, Any]:
        """Spend energy to propose and execute actions; score + metabolize."""
        if not self.config.learning_enabled or not allow_think:
            return {
                "thinks": 0,
                "rewards": [],
                "actions": [],
                "resting": not allow_think,
            }

        results: list[dict[str, Any]] = []
        rewards: list[float] = []
        max_n = max(0, int(round(self.config.max_thinks_per_cycle * throttle)))
        if max_n <= 0 and throttle > 0:
            max_n = 1

        for _ in range(max_n):
            cost = self.config.think_cost
            if not resources.spend_think(cost):
                break

            self.organism.total_thinks += 1
            action = self.choose_action(
                throttle=throttle, allow_branch=allow_branch, mode=mode
            )
            timeline = self.select_timeline()
            if not timeline:
                resources.refund_energy(cost * 0.5)
                break

            timeline.think_count += 1
            proposal = ProposedAction(
                action=action,
                timeline_id=timeline.id,
                think_cost=cost,
            )
            executed = self._execute(
                proposal,
                timeline,
                sim_time,
                resources,
                allow_branch=allow_branch,
            )
            paradox_hit = timeline.status in (
                TimelineStatus.PARADOXICAL,
                TimelineStatus.ISOLATED,
            )
            reward = self.fitness.score_timeline(
                timeline,
                action=action,
                energy_spent=cost,
                diversity=diversity,
                paradox_hit=paradox_hit,
                extras={"executed": executed.get("ok", False)},
            )
            # Small penalty if action failed to execute
            if not executed.get("ok", False) and action != ActionType.OBSERVE:
                reward = float(np.clip(reward - 0.15, -1.0, 1.0))

            record = self.fitness.metabolize(
                timeline,
                reward,
                resources,
                action=action,
                energy_spent=cost,
                sim_time=sim_time,
                details=executed,
            )
            self._update_q(action, reward)
            rewards.append(reward)
            results.append(
                {
                    "timeline_id": timeline.id,
                    "action": action.value,
                    "reward": reward,
                    "executed": executed,
                    "record_id": record.id,
                }
            )

        self.organism.learning_cycles += 1
        return {
            "thinks": len(results),
            "rewards": rewards,
            "mean_reward": float(np.mean(rewards)) if rewards else 0.0,
            "actions": results,
            "policy_q": dict(self._q),
        }

    def _update_q(self, action: ActionType, reward: float) -> None:
        key = action.value
        self._counts[key] = self._counts.get(key, 0) + 1
        n = self._counts[key]
        lr = 1.0 / n
        self._q[key] = (1 - lr) * self._q[key] + lr * reward

    def _execute(
        self,
        proposal: ProposedAction,
        timeline: Timeline,
        sim_time: float,
        resources: ResourcePool,
        *,
        allow_branch: bool = True,
    ) -> dict[str, Any]:
        action = proposal.action
        if action == ActionType.OBSERVE:
            # Cheap observation: generate a light event without mutation spend
            evt = self.events.generate_event(timeline, sim_time, resources=None)
            return {"ok": True, "event_id": evt.id if evt else None, "kind": "observe"}

        if action == ActionType.MUTATE:
            if not resources.spend_mutation(1.0):
                return {"ok": False, "reason": "no_mutation_budget"}
            self.events._apply_mutation(timeline, sim_time)
            timeline.events.append(
                TimelineEvent(
                    timeline_id=timeline.id,
                    event_type=EventType.MUTATION,
                    simulation_time=sim_time,
                    wall_timestamp=time.time(),
                    description="Policy-driven parameter mutation",
                    payload={"policy": True, "fictional": True},
                )
            )
            return {"ok": True, "kind": "mutate"}

        if action == ActionType.BRANCH:
            child = self.branching.branch(
                timeline,
                sim_time,
                resources,
                mutation={"policy": True, "parent_fitness": timeline.fitness_ema},
                allow_branch=allow_branch,
            )
            if not child:
                return {"ok": False, "reason": "branch_failed"}
            # Inherit policy prior: child starts near parent fitness EMA
            child.fitness_ema = timeline.fitness_ema * 0.5
            self.organism.total_branches += 1
            return {"ok": True, "kind": "branch", "child_id": child.id}

        if action == ActionType.INTERACT:
            others = [t for t in self.registry.active_timelines() if t.id != timeline.id]
            if not others:
                return {"ok": False, "reason": "no_peers"}
            # Prefer fit peers
            weights = np.array([max(0.01, t.fitness_ema + 0.5) for t in others])
            weights = weights / weights.sum()
            peer = others[int(self.rng.choice(len(others), p=weights))]
            rel = self.interaction.interact(timeline, peer, sim_time, resources)
            if not rel:
                return {"ok": False, "reason": "interact_failed"}
            self.organism.total_interactions += 1
            return {"ok": True, "kind": "interact", "peer_id": peer.id, "rel_id": rel.id}

        if action == ActionType.REWRITE:
            active = timeline.active_events()
            # Skip genesis-only rewrites when possible
            candidates = [e for e in active if e.event_type != EventType.GENESIS]
            if not candidates:
                candidates = active
            if not candidates:
                return {"ok": False, "reason": "no_events"}
            target = candidates[int(self.rng.integers(0, len(candidates)))]
            new_evt = self.alteration.rewrite_event(
                timeline.id,
                target.id,
                f"[policy rewrite] Refined narrative of {target.event_type.value}",
                new_payload={
                    **target.payload,
                    "polarity": 0,
                    "policy_rewrite": True,
                    "domain": target.payload.get("domain", "general"),
                },
                sim_time=sim_time,
            )
            return {
                "ok": new_evt is not None,
                "kind": "rewrite",
                "event_id": new_evt.id if new_evt else None,
            }

        if action == ActionType.STABILIZE:
            timeline.stability_score = min(1.0, timeline.stability_score + 0.05)
            timeline.decay_coefficient = max(0.0, timeline.decay_coefficient * 0.95)
            # Soft spend
            resources.computational_energy = max(
                0.0, resources.computational_energy - 0.3
            )
            self.registry.update_status(timeline.id, TimelineStatus.ACTIVE)
            timeline.events.append(
                TimelineEvent(
                    timeline_id=timeline.id,
                    event_type=EventType.GROWTH,
                    simulation_time=sim_time,
                    wall_timestamp=time.time(),
                    description="Policy stabilization — dampened decay, raised stability",
                    payload={"policy": True},
                )
            )
            return {"ok": True, "kind": "stabilize"}

        return {"ok": False, "reason": "unknown_action"}

    def export_state(self) -> dict[str, Any]:
        return {"q": dict(self._q), "counts": dict(self._counts)}

    def load_state(self, data: dict[str, Any]) -> None:
        if "q" in data:
            self._q.update({k: float(v) for k, v in data["q"].items()})
        if "counts" in data:
            self._counts.update({k: int(v) for k, v in data["counts"].items()})
