"""Fitness Engine — scores timelines; metabolizes reward into weight and coefficients."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from ..models.config import SimulationConfig
from ..models.learning import ActionType, RewardRecord
from ..models.organism import OrganismState, ResourcePool
from ..models.timeline import Timeline, TimelineStatus
from .registry import TimelineRegistryEngine
from .reward_ledger import RewardLedger


class FitnessEngine:
    """
    Evaluate fitness against organism goals and close the learning loop.

    Reward shapes metabolism: weight, growth/decay coeffs, energy refunds.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
        ledger: RewardLedger,
        organism: OrganismState,
    ) -> None:
        self.registry = registry
        self.config = config
        self.ledger = ledger
        self.organism = organism

    def score_timeline(
        self,
        timeline: Timeline,
        *,
        action: ActionType = ActionType.OBSERVE,
        energy_spent: float = 0.0,
        diversity: float = 0.0,
        paradox_hit: bool = False,
        extras: Optional[dict[str, Any]] = None,
    ) -> float:
        """
        Composite reward in [-1, 1].

        Soft goal: approach target stability/complexity, contribute diversity,
        avoid paradoxes, think efficiently.
        """
        w = self.config.fitness_weights
        stab_err = abs(timeline.stability_score - self.config.goal_stability_target)
        stab_score = 1.0 - min(1.0, stab_err / 0.75)

        c_err = abs(timeline.structural_complexity - self.config.goal_complexity_target)
        c_score = 1.0 - min(1.0, c_err / max(self.config.goal_complexity_target, 0.5))

        # Goal alignment: prefer balanced net growth (not explosive, not collapsing)
        net = timeline.growth_coefficient - timeline.decay_coefficient
        goal_align = 1.0 - min(1.0, abs(net - 0.03) / 0.15)

        paradox_pen = 1.0 if paradox_hit or timeline.status == TimelineStatus.PARADOXICAL else 0.0
        if timeline.status == TimelineStatus.ISOLATED:
            paradox_pen = max(paradox_pen, 0.7)

        # Energy efficiency: reward thinking that doesn't waste relative to outcome
        if energy_spent <= 0:
            efficiency = 0.5
        else:
            efficiency = float(np.clip(1.0 - energy_spent / (self.config.think_cost * 3), 0.0, 1.0))

        # Action-specific shaping
        action_bonus = 0.0
        if action == ActionType.STABILIZE and timeline.stability_score >= self.config.goal_stability_target:
            action_bonus = 0.15
        elif action == ActionType.MUTATE and 0.5 <= timeline.structural_complexity <= 3.5:
            action_bonus = 0.08
        elif action == ActionType.BRANCH and timeline.fitness_ema > 0.2:
            action_bonus = 0.1
        elif action == ActionType.INTERACT and diversity > 0.3:
            action_bonus = 0.08
        elif action == ActionType.REWRITE and timeline.historical_version > 1:
            action_bonus = 0.05

        # Organism survival signal — punish expansion when stressed; reward rest
        homeo = 0.0
        hw = self.config.homeostasis_fitness_weight
        if self.config.homeostasis_enabled and hw > 0:
            health = self.organism.health
            target = self.config.homeostasis_health_target
            health_term = float(np.clip(1.0 - abs(health - target) / 0.5, -1.0, 1.0))
            throttle = getattr(self.organism, "metabolic_throttle", 1.0)
            mode = getattr(self.organism, "homeostasis_mode", "thrive")
            if mode in ("conserve", "crisis"):
                if action in (ActionType.STABILIZE, ActionType.OBSERVE):
                    homeo = 0.35 + 0.2 * health_term
                elif action == ActionType.BRANCH:
                    homeo = -0.55
                elif action in (ActionType.MUTATE, ActionType.INTERACT):
                    homeo = -0.2
                else:
                    homeo = 0.05 * health_term
            elif mode == "balance":
                if action == ActionType.BRANCH and throttle < 0.5:
                    homeo = -0.25
                else:
                    homeo = 0.15 * health_term
            else:
                homeo = 0.1 * health_term
            homeo *= hw

        raw = (
            w.get("stability", 0.25) * stab_score
            + w.get("diversity", 0.15) * diversity
            + w.get("complexity", 0.1) * c_score
            + w.get("goal_alignment", 0.25) * goal_align
            + w.get("energy_efficiency", 0.1) * efficiency
            - w.get("paradox_penalty", 0.15) * paradox_pen
            + action_bonus
            + homeo
        )
        # Map roughly [−0.15, 1.15] → [-1, 1]
        reward = float(np.clip(raw * 1.4 - 0.3, -1.0, 1.0))
        if extras:
            reward = float(np.clip(reward + float(extras.get("delta", 0.0)), -1.0, 1.0))
        return reward

    def metabolize(
        self,
        timeline: Timeline,
        reward: float,
        resources: ResourcePool,
        *,
        action: ActionType,
        energy_spent: float,
        sim_time: float,
        details: Optional[dict[str, Any]] = None,
    ) -> RewardRecord:
        """Apply reward to fitness EMA, weight, coefficients; refund energy if positive."""
        alpha = self.config.fitness_ema_alpha
        timeline.last_reward = reward
        timeline.last_action = action.value
        timeline.fitness = reward
        timeline.fitness_ema = (1 - alpha) * timeline.fitness_ema + alpha * reward
        timeline.cumulative_reward += reward

        # Reward-shaped weight update: W ← W * exp(η * r * scale)
        eta = self.config.learning_rate
        timeline.current_weight *= float(np.exp(np.clip(eta * reward * 0.5, -2, 2)))
        timeline.current_weight = float(
            np.clip(
                timeline.current_weight,
                self.config.min_weight,
                self.config.max_weight,
            )
        )
        timeline.influence_weight = 0.8 * timeline.influence_weight + 0.2 * timeline.current_weight

        # Nudge coefficients toward successful strategies
        if reward > 0.05:
            timeline.growth_coefficient = min(
                0.3, timeline.growth_coefficient + 0.002 * reward
            )
            timeline.decay_coefficient = max(
                0.0, timeline.decay_coefficient - 0.001 * reward
            )
            timeline.stability_score = min(1.0, timeline.stability_score + 0.01 * reward)
        elif reward < -0.05:
            timeline.decay_coefficient = min(
                0.25, timeline.decay_coefficient + 0.002 * abs(reward)
            )
            timeline.growth_coefficient = max(
                0.001, timeline.growth_coefficient - 0.001 * abs(reward)
            )
            timeline.stability_score = max(0.0, timeline.stability_score - 0.01 * abs(reward))

        # Branching bias toward fit lineages
        timeline.branching_probability = float(
            np.clip(
                self.config.base_branch_probability
                * (0.5 + max(0.0, timeline.fitness_ema)),
                0.01,
                0.5,
            )
        )

        refund = 0.0
        if reward > 0 and energy_spent > 0:
            refund = energy_spent * self.config.reward_refund_ratio * reward
            resources.refund_energy(refund)
            # Small budget top-ups for successful thinkers
            resources.mutation_budget = min(
                resources.max_mutation_budget,
                resources.mutation_budget + 0.15 * reward,
            )

        record = RewardRecord(
            timeline_id=timeline.id,
            action=action.value,
            reward=reward,
            sim_time=sim_time,
            energy_spent=energy_spent,
            energy_refunded=refund,
            details=details or {},
        )
        self.ledger.record(record)
        self.organism.total_reward += reward
        return record

    def evaluate_population(self, diversity: float) -> dict[str, float]:
        tls = self.registry.active_timelines()
        if not tls:
            self.organism.mean_fitness = 0.0
            return {"mean": 0.0, "best": 0.0, "n": 0}
        fits = [t.fitness_ema for t in tls]
        mean = float(np.mean(fits))
        best = float(np.max(fits))
        self.organism.mean_fitness = float(np.mean([t.fitness for t in tls]))
        self.organism.mean_fitness_ema = mean
        self.organism.best_fitness = max(self.organism.best_fitness, best)
        # Mild diversity pressure recorded for observability
        _ = diversity
        return {"mean": mean, "best": best, "n": float(len(tls))}
