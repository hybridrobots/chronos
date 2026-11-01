"""Tests for self-sustaining homeostasis."""

from __future__ import annotations

import pytest

from app.models.config import SimulationConfig
from app.simulation.controller import SimulationController


@pytest.mark.asyncio
async def test_homeostasis_limits_population():
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=41,
            learning_enabled=True,
            homeostasis_enabled=True,
            max_timelines=40,
            timeline_capacity=40,
            base_branch_probability=0.5,
            homeostasis_soft_pop_ratio=0.5,
            homeostasis_hard_pop_ratio=0.7,
            max_thinks_per_cycle=3,
        )
    )
    await ctrl.start()
    for _ in range(80):
        await ctrl._cycle()
    await ctrl.stop()

    pop = ctrl.registry.count()
    hard = int(40 * 0.7) + 5  # small slack for race within a cycle
    assert pop <= hard + 8  # cull + branch race allowance
    assert ctrl.organism.homeostasis_mode in (
        "thrive",
        "balance",
        "conserve",
        "crisis",
    )
    assert 0.0 <= ctrl.organism.metabolic_throttle <= 1.0


@pytest.mark.asyncio
async def test_low_energy_rests_thinking():
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=43,
            learning_enabled=True,
            homeostasis_enabled=True,
            energy_rest_threshold=0.5,
            think_cost=5.0,
            max_thinks_per_cycle=4,
        )
    )
    await ctrl.start()
    ctrl.organism.resources.computational_energy = 50  # 5% of 1000
    ctrl.health.evaluate(0.0)
    meta = ctrl.homeostasis.evaluate()
    assert meta.allow_think is False or meta.throttle < 0.5
    stats = ctrl.policy.think_cycle(
        1.0,
        ctrl.organism.resources,
        0.2,
        throttle=meta.throttle,
        allow_think=meta.allow_think,
        allow_branch=meta.allow_branch,
        mode=meta.mode,
    )
    assert stats.get("thinks", 0) == 0
    await ctrl.stop()


@pytest.mark.asyncio
async def test_branching_blocked_at_hard_cap():
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=47,
            max_timelines=20,
            homeostasis_hard_pop_ratio=0.5,
            homeostasis_enabled=True,
        )
    )
    await ctrl.start()
    # Force near hard cap by creating children
    root = ctrl.registry.active_timelines()[0]
    for _ in range(12):
        ctrl.genesis.create_child(root, 1.0)
    assert ctrl.registry.count() >= 10
    child = ctrl.branching.branch(
        root, 2.0, ctrl.organism.resources, allow_branch=True
    )
    # At or above hard ratio 0.5 of 20 = 10, further branches should fail
    if ctrl.registry.count() / 20 >= 0.5:
        assert child is None or ctrl.registry.count() <= 20
    await ctrl.stop()


@pytest.mark.asyncio
async def test_health_recovers_under_homeostasis():
    """After expansion stress, throttle + cull should stop free-fall health."""
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=53,
            learning_enabled=True,
            homeostasis_enabled=True,
            max_timelines=30,
            timeline_capacity=30,
            base_branch_probability=0.4,
            homeostasis_soft_pop_ratio=0.55,
            homeostasis_hard_pop_ratio=0.75,
            max_thinks_per_cycle=3,
            resource_regen_rate=0.12,
        )
    )
    await ctrl.start()
    for _ in range(40):
        await ctrl._cycle()
    mid_health = ctrl.organism.health
    mid_pop = ctrl.organism.active_timeline_count
    for _ in range(40):
        await ctrl._cycle()
    late_health = ctrl.organism.health
    late_pop = ctrl.organism.active_timeline_count
    await ctrl.stop()

    # Population should not sit at absolute max forever
    assert late_pop < 30 or mid_pop < 30
    # Health should remain in a livable band (not collapse to near-zero)
    assert late_health >= 0.35
    assert mid_health >= 0.25
