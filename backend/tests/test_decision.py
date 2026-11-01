"""Decision Counsel — interactive problem deliberation tests."""

from __future__ import annotations

import pytest

from app.models.config import SimulationConfig
from app.simulation.controller import SimulationController


@pytest.mark.asyncio
async def test_decision_start_scores_and_recommends():
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=77,
            learning_enabled=True,
            homeostasis_enabled=True,
            max_timelines=80,
            max_thinks_per_cycle=2,
        )
    )
    await ctrl.start()
    session = ctrl.decision.start_session(
        "Should I stay in my current path or leave for something uncertain but more alive?",
        [
            {"label": "Stay", "description": "Stability, known costs"},
            {"label": "Leave", "description": "Risk, possible fit"},
            {"label": "Pause & prepare", "description": "Neither fully yet"},
        ],
        ctrl.sim_time,
        ctrl.organism.resources,
        target_generations=3,
        target_cycles=35,
        seeds_per_path=2,
    )
    assert session.status.value == "running"
    assert len(session.paths) == 3

    for _ in range(40):
        await ctrl._cycle()
        active = ctrl.decision.active()
        if active and active.status.value == "complete":
            break

    active = ctrl.decision.active()
    assert active is not None
    assert active.status.value == "complete"
    assert active.recommendation_path_id is not None
    assert abs(sum(p.relative_share for p in active.paths) - 1.0) < 1e-5
    assert "not" in active.recommendation_summary.lower() or "simulated" in active.recommendation_summary.lower()
    await ctrl.stop()


@pytest.mark.asyncio
async def test_decision_requires_two_paths():
    ctrl = SimulationController(SimulationConfig(random_seed=78))
    await ctrl.start()
    with pytest.raises(ValueError):
        ctrl.decision.start_session(
            "A real problem statement here",
            [{"label": "Only one"}],
            ctrl.sim_time,
            ctrl.organism.resources,
        )
    await ctrl.stop()


@pytest.mark.asyncio
async def test_force_conclude_early():
    ctrl = SimulationController(SimulationConfig(random_seed=79, max_timelines=60))
    await ctrl.start()
    session = ctrl.decision.start_session(
        "Is it time to let this chapter end?",
        [
            {"label": "Let go"},
            {"label": "Hold on"},
        ],
        ctrl.sim_time,
        ctrl.organism.resources,
        target_cycles=200,
        target_generations=10,
    )
    for _ in range(10):
        await ctrl._cycle()
    done = ctrl.decision.force_recommend(session.id, ctrl.sim_time)
    assert done is not None
    assert done.status.value == "complete"
    assert done.recommendation_path_id in {p.id for p in done.paths}
    await ctrl.stop()
