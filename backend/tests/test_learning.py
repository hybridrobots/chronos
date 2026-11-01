"""Tests for fitness / reward / policy learning loop."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from app.models.config import SimulationConfig
from app.models.learning import ActionType
from app.models.organism import ResourcePool
from app.simulation.controller import SimulationController


@pytest.mark.asyncio
async def test_policy_thinks_and_records_rewards():
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=7,
            learning_enabled=True,
            max_thinks_per_cycle=3,
            think_cost=1.0,
            max_timelines=40,
        )
    )
    await ctrl.start()
    for _ in range(12):
        await ctrl._cycle()
    await ctrl.stop()

    assert ctrl.organism.total_thinks > 0
    assert ctrl.organism.learning_cycles == 12
    assert len(ctrl.reward_ledger.recent(100)) > 0
    assert any(t.think_count > 0 for t in ctrl.registry.active_timelines())


@pytest.mark.asyncio
async def test_positive_reward_increases_weight():
    ctrl = SimulationController(
        SimulationConfig(random_seed=11, learning_enabled=True, learning_rate=0.3)
    )
    await ctrl.start()
    tl = ctrl.registry.active_timelines()[0]
    before = tl.current_weight
    resources = ctrl.organism.resources
    record = ctrl.fitness.metabolize(
        tl,
        reward=0.8,
        resources=resources,
        action=ActionType.STABILIZE,
        energy_spent=1.5,
        sim_time=1.0,
    )
    assert record.reward == 0.8
    assert tl.current_weight > before
    assert tl.fitness_ema > 0
    assert record.energy_refunded > 0
    await ctrl.stop()


@pytest.mark.asyncio
async def test_negative_reward_damps_lineage():
    ctrl = SimulationController(
        SimulationConfig(random_seed=13, learning_enabled=True, learning_rate=0.3)
    )
    await ctrl.start()
    tl = ctrl.registry.active_timelines()[0]
    before_w = tl.current_weight
    before_decay = tl.decay_coefficient
    ctrl.fitness.metabolize(
        tl,
        reward=-0.7,
        resources=ctrl.organism.resources,
        action=ActionType.MUTATE,
        energy_spent=1.0,
        sim_time=1.0,
    )
    assert tl.current_weight < before_w
    assert tl.decay_coefficient >= before_decay
    await ctrl.stop()


@pytest.mark.asyncio
async def test_learning_disabled_skips_think():
    ctrl = SimulationController(
        SimulationConfig(random_seed=17, learning_enabled=False, max_timelines=20)
    )
    await ctrl.start()
    for _ in range(5):
        await ctrl._cycle()
    await ctrl.stop()
    assert ctrl.organism.total_thinks == 0
    assert ctrl._last_learning.get("thinks", 0) == 0


@pytest.mark.asyncio
async def test_policy_q_updates_with_experience():
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=19,
            learning_enabled=True,
            max_thinks_per_cycle=4,
            policy_exploration=0.1,
        )
    )
    await ctrl.start()
    q0 = dict(ctrl.policy._q)
    for _ in range(20):
        await ctrl._cycle()
    await ctrl.stop()
    # At least some action values should have moved from neutral
    assert any(abs(ctrl.policy._q[k] - q0.get(k, 0.0)) > 1e-6 for k in ctrl.policy._q)
    stats = ctrl.reward_ledger.action_stats()
    assert len(stats) >= 1


@pytest.mark.asyncio
async def test_export_includes_learning_state():
    ctrl = SimulationController(
        SimulationConfig(random_seed=23, learning_enabled=True, max_thinks_per_cycle=2)
    )
    await ctrl.start()
    for _ in range(5):
        await ctrl._cycle()
    export = ctrl.full_export()
    assert "reward_ledger" in export
    assert "policy_state" in export
    snap = ctrl.snapshot()
    assert "learning" in snap
    assert snap["learning"]["enabled"] is True

    ctrl2 = SimulationController()
    ctrl2.load_export(export)
    assert len(ctrl2.reward_ledger.recent(100)) == len(export["reward_ledger"])
    await ctrl.stop()


def test_fitness_score_bounded():
    ctrl = SimulationController(SimulationConfig(random_seed=29))
    asyncio.run(ctrl.start())
    tl = ctrl.registry.active_timelines()[0]
    r = ctrl.fitness.score_timeline(
        tl, action=ActionType.OBSERVE, energy_spent=1.0, diversity=0.5
    )
    assert -1.0 <= r <= 1.0
    asyncio.run(ctrl.stop())


@pytest.mark.asyncio
async def test_think_requires_energy():
    ctrl = SimulationController(
        SimulationConfig(random_seed=31, learning_enabled=True, think_cost=100)
    )
    await ctrl.start()
    ctrl.organism.resources.computational_energy = 50  # less than think_cost
    stats = ctrl.policy.think_cycle(1.0, ctrl.organism.resources, 0.2)
    assert stats["thinks"] == 0
    await ctrl.stop()
