"""Exponential Growth Engine — W(t) = W0 * exp((g - d) * t) growth component."""

from __future__ import annotations

import numpy as np

from ..models.timeline import Timeline, TimelineStatus
from ..models.config import SimulationConfig
from .registry import TimelineRegistryEngine


class ExponentialGrowthEngine:
    """
    Applies exponential weight dynamics with resource constraints.

    Raw weights are kept separate from normalized relative probabilities.
    Weights are NOT interpreted as objective probabilities of real universes.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        config: SimulationConfig,
    ) -> None:
        self.registry = registry
        self.config = config

    def compute_weight(
        self,
        w0: float,
        growth: float,
        decay: float,
        elapsed: float,
    ) -> float:
        """W(t) = W0 * exp((g - d) * t), clamped to [min_weight, max_weight]."""
        net = growth - decay
        raw = w0 * float(np.exp(np.clip(net * elapsed, -20, 20)))
        return float(np.clip(raw, self.config.min_weight, self.config.max_weight))

    def apply_cycle(self, sim_time: float, dt: float) -> dict:
        """
        Update weights: blend open-loop exponential dynamics with reward shaping.

        When learning is enabled, fitness_ema modulates net growth so metabolism
        tracks thinking success rather than pure open-loop expansion.
        """
        timelines = self.registry.active_timelines()
        n = len(timelines)
        capacity = self.config.max_timelines
        # Logistic resource pressure: slows growth as population approaches capacity
        pressure = 1.0 - (n / max(capacity, 1)) * self.config.soft_capacity_ratio
        pressure = max(0.1, pressure)
        blend = (
            self.config.open_loop_growth_blend
            if self.config.learning_enabled
            else 1.0
        )
        blend = float(np.clip(blend, 0.0, 1.0))

        grown = 0
        for tl in timelines:
            elapsed = sim_time - tl.simulation_birth_time
            effective_growth = tl.growth_coefficient * pressure
            open_loop = self.compute_weight(
                tl.initial_weight,
                effective_growth,
                tl.decay_coefficient,
                elapsed,
            )
            # Reward-shaped component: grow/shrink from current weight by fitness
            fitness_drive = float(np.clip(tl.fitness_ema, -1.0, 1.0))
            reward_shaped = tl.current_weight * float(
                np.exp(np.clip(self.config.learning_rate * fitness_drive * dt * 2, -1, 1))
            )
            new_w = blend * open_loop + (1.0 - blend) * reward_shaped
            # Soft blend with previous to avoid jumps from pressure changes
            tl.current_weight = 0.7 * new_w + 0.3 * tl.current_weight
            tl.current_weight = float(
                np.clip(
                    tl.current_weight,
                    self.config.min_weight,
                    self.config.max_weight,
                )
            )
            tl.last_update_time = sim_time

            net_growing = (
                effective_growth > tl.decay_coefficient
                or (self.config.learning_enabled and tl.fitness_ema > 0.05)
            )
            if net_growing and tl.current_weight > tl.initial_weight * 0.8:
                if tl.status not in (
                    TimelineStatus.PARADOXICAL,
                    TimelineStatus.ISOLATED,
                    TimelineStatus.CONVERGING,
                ):
                    self.registry.update_status(tl.id, TimelineStatus.GROWING)
                    grown += 1

            # Complexity slowly accumulates with age and events
            tl.structural_complexity = min(
                10.0,
                tl.structural_complexity + 0.001 * dt * len(tl.active_events()),
            )

        return {
            "grown": grown,
            "pressure": pressure,
            "population": n,
            "open_loop_blend": blend,
        }

    def population_growth_rate(self) -> float:
        """Mean net growth coefficient across active timelines."""
        tls = self.registry.active_timelines()
        if not tls:
            return 0.0
        return float(
            np.mean([t.growth_coefficient - t.decay_coefficient for t in tls])
        )

    def normalized_weights(self) -> dict[str, float]:
        """
        Relative normalized weights (sum to 1).
        These are relative influence shares — NOT real-world probabilities.
        """
        tls = self.registry.active_timelines()
        total = sum(t.current_weight for t in tls) or 1.0
        return {t.id: t.current_weight / total for t in tls}
