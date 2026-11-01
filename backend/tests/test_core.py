"""Core Chronos engine tests — branching, growth, paradoxes, persistence, reproducibility."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import numpy as np
import pytest

from app.models.config import SimulationConfig
from app.models.paradox import Paradox, ParadoxStatus, ResolutionStrategy
from app.models.organism import ResourcePool
from app.models.timeline import EventType, TimelineStatus
from app.engines.registry import TimelineRegistryEngine
from app.engines.genesis import TimelineGenesisEngine
from app.engines.growth import ExponentialGrowthEngine
from app.engines.decay import ExponentialDecayEngine
from app.engines.branching import TimelineBranchingEngine
from app.engines.alteration import TemporalAlterationEngine
from app.engines.interaction import CrossTimelineInteractionEngine
from app.engines.causality import CausalDependencyEngine
from app.engines.convergence import TimelineConvergenceEngine
from app.engines.paradox_detection import ParadoxDetectionEngine
from app.engines.paradox_resolution import ParadoxResolutionEngine
from app.engines.memory import HistoricalMemoryEngine
from app.engines.events import AutonomousEventEngine
from app.simulation.controller import SimulationController
from app.persistence.engine import PersistenceEngine


@pytest.fixture
def config():
    return SimulationConfig(
        random_seed=12345,
        max_timelines=50,
        base_branch_probability=0.5,
        event_rate=0.8,
        timestep=0.1,
    )


@pytest.fixture
def rng():
    return np.random.default_rng(12345)


@pytest.fixture
def stack(config, rng):
    registry = TimelineRegistryEngine()
    genesis = TimelineGenesisEngine(registry, config, rng)
    growth = ExponentialGrowthEngine(registry, config)
    decay = ExponentialDecayEngine(registry, config)
    alteration = TemporalAlterationEngine(registry, config)
    causality = CausalDependencyEngine(registry, config)
    memory = HistoricalMemoryEngine(registry, config)
    events = AutonomousEventEngine(registry, causality, memory, config, rng)
    branching = TimelineBranchingEngine(registry, genesis, config, rng)
    interaction = CrossTimelineInteractionEngine(registry, config, rng)
    convergence = TimelineConvergenceEngine(registry, config, rng)
    paradox_det = ParadoxDetectionEngine(registry, causality, config)
    paradox_res = ParadoxResolutionEngine(
        registry, branching, alteration, decay, config, rng
    )
    resources = ResourcePool(
        computational_energy=1000,
        branching_budget=50,
        mutation_budget=30,
        interaction_budget=40,
        timeline_capacity=50,
    )
    return {
        "registry": registry,
        "genesis": genesis,
        "growth": growth,
        "decay": decay,
        "alteration": alteration,
        "causality": causality,
        "memory": memory,
        "events": events,
        "branching": branching,
        "interaction": interaction,
        "convergence": convergence,
        "paradox_det": paradox_det,
        "paradox_res": paradox_res,
        "resources": resources,
        "config": config,
        "rng": rng,
    }


def test_timeline_creation(stack):
    tl = stack["genesis"].create_primordial(0.0)
    assert tl.id
    assert tl.parent_id is None
    assert tl.generation == 0
    assert tl.status == TimelineStatus.ACTIVE
    assert any(e.event_type == EventType.GENESIS for e in tl.events)
    assert stack["registry"].count() == 1


def test_branching_preserves_parent(stack):
    parent = stack["genesis"].create_primordial(0.0)
    child = stack["branching"].branch(parent, 1.0, stack["resources"])
    assert child is not None
    assert child.parent_id == parent.id
    assert child.generation == 1
    assert stack["registry"].get(parent.id) is not None
    assert any(e.event_type == EventType.BRANCH_DIVERGENCE for e in child.events)
    # Parent still has its genesis event
    assert any(e.event_type == EventType.GENESIS for e in parent.events)


def test_historical_rewriting_preserves_versions(stack):
    tl = stack["genesis"].create_primordial(0.0)
    original = tl.events[0]
    new_evt = stack["alteration"].rewrite_event(
        tl.id, original.id, "Rewritten genesis narrative", sim_time=2.0
    )
    assert new_evt is not None
    assert original.is_active is False
    assert original.superseded_by == new_evt.id
    assert new_evt.version == original.version + 1
    assert tl.historical_version == 2
    versions = stack["alteration"].get_event_versions(tl.id, original.id)
    assert len(versions) >= 2


def test_event_preservation(stack):
    tl = stack["genesis"].create_primordial(0.0)
    evt = stack["events"].generate_event(tl, 1.0, stack["resources"])
    assert evt is not None
    assert evt in tl.events
    hist = stack["memory"].get_timeline_history(tl.id)
    assert any(e.id == evt.id for e in hist)


def test_exponential_growth(stack):
    growth = stack["growth"]
    w = growth.compute_weight(1.0, 0.1, 0.0, 10.0)
    expected = np.exp(1.0)
    assert abs(w - expected) < 0.01
    # Growth > decay increases weight over time
    w_early = growth.compute_weight(1.0, 0.05, 0.01, 1.0)
    w_late = growth.compute_weight(1.0, 0.05, 0.01, 20.0)
    assert w_late > w_early


def test_exponential_decay(stack):
    growth = stack["growth"]
    # When decay > growth, weight shrinks
    w_early = growth.compute_weight(1.0, 0.01, 0.05, 1.0)
    w_late = growth.compute_weight(1.0, 0.01, 0.05, 20.0)
    assert w_late < w_early


def test_cross_timeline_interactions(stack):
    a = stack["genesis"].create_primordial(0.0)
    b = stack["genesis"].create_child(a, 1.0)
    rel = stack["interaction"].interact(a, b, 2.0, stack["resources"])
    assert rel is not None
    assert rel.source_id == a.id
    assert rel.target_id == b.id
    assert rel.strength > 0
    assert any(e.event_type == EventType.INTERACTION for e in b.events)


def test_feedback_loop_prevention(stack):
    a = stack["genesis"].create_primordial(0.0)
    b = stack["genesis"].create_child(a, 1.0)
    stack["interaction"].interact(a, b, 2.0, stack["resources"])
    # A→B exists; B→A would create a cycle
    rel2 = stack["interaction"].interact(b, a, 3.0, stack["resources"])
    assert rel2 is None


def test_paradox_detection(stack):
    tl = stack["genesis"].create_primordial(0.0)
    # Inject contradictory events
    from app.models.timeline import TimelineEvent
    import time as _t

    e1 = TimelineEvent(
        timeline_id=tl.id,
        event_type=EventType.CAUSAL_CONFLICT,
        simulation_time=1.0,
        wall_timestamp=_t.time(),
        description="pos",
        payload={"domain": "energy", "polarity": 1},
    )
    e2 = TimelineEvent(
        timeline_id=tl.id,
        event_type=EventType.CAUSAL_CONFLICT,
        simulation_time=1.1,
        wall_timestamp=_t.time(),
        description="neg",
        payload={"domain": "energy", "polarity": -1},
        causal_deps=[e1.id],
    )
    e1.causal_deps = []
    tl.events.extend([e1, e2])
    # Share a dep for severity
    shared = TimelineEvent(
        timeline_id=tl.id,
        event_type=EventType.HISTORICAL_CHANGE,
        simulation_time=0.5,
        description="shared",
        payload={"domain": "energy", "polarity": 0},
    )
    tl.events.append(shared)
    e1.causal_deps = [shared.id]
    e2.causal_deps = [shared.id]

    conflicts = stack["causality"].detect_conflicts(tl)
    assert len(conflicts) >= 1
    paradoxes = stack["paradox_det"].detect_from_conflicts(conflicts, 2.0)
    assert len(paradoxes) >= 1
    assert paradoxes[0].status == ParadoxStatus.DETECTED


def _make_paradox(tl_id: str, severity: float = 0.6) -> Paradox:
    return Paradox(
        affected_timeline_ids=[tl_id],
        contradictory_events=[
            {"id": "e1", "polarity": "+"},
            {"id": "e2", "polarity": "-"},
        ],
        severity=severity,
        detection_time=1.0,
        status=ParadoxStatus.DETECTED,
        description="test paradox",
    )


def test_paradox_isolation(stack):
    tl = stack["genesis"].create_primordial(0.0)
    p = _make_paradox(tl.id, 0.9)
    stack["paradox_det"]._paradoxes[p.id] = p
    result = stack["paradox_res"].resolve(
        p, 2.0, stack["resources"], ResolutionStrategy.ISOLATION
    )
    assert result.status == ParadoxStatus.ISOLATED
    assert stack["registry"].get(tl.id).status == TimelineStatus.ISOLATED


def test_paradox_auto_branch(stack):
    tl = stack["genesis"].create_primordial(0.0)
    p = _make_paradox(tl.id, 0.6)
    before = stack["registry"].count()
    result = stack["paradox_res"].resolve(
        p, 2.0, stack["resources"], ResolutionStrategy.AUTO_BRANCH
    )
    assert result.status == ParadoxStatus.RESOLVED
    assert stack["registry"].count() >= before  # may branch


def test_paradox_causal_correction(stack):
    tl = stack["genesis"].create_primordial(0.0)
    from app.models.timeline import TimelineEvent
    import time as _t

    e_neg = TimelineEvent(
        timeline_id=tl.id,
        event_type=EventType.CAUSAL_CONFLICT,
        simulation_time=1.0,
        wall_timestamp=_t.time(),
        description="neg event",
        payload={"domain": "x", "polarity": -1},
    )
    tl.events.append(e_neg)
    p = _make_paradox(tl.id, 0.4)
    p.contradictory_events = [{"id": e_neg.id, "polarity": "-"}]
    result = stack["paradox_res"].resolve(
        p, 2.0, stack["resources"], ResolutionStrategy.CAUSAL_CORRECTION
    )
    assert result.status == ParadoxStatus.RESOLVED
    assert e_neg.is_active is False


def test_paradox_preservation(stack):
    tl = stack["genesis"].create_primordial(0.0)
    p = _make_paradox(tl.id, 0.2)
    result = stack["paradox_res"].resolve(
        p, 2.0, stack["resources"], ResolutionStrategy.PRESERVATION
    )
    assert result.status == ParadoxStatus.PRESERVED
    assert stack["registry"].get(tl.id).status == TimelineStatus.PARADOXICAL


def test_timeline_convergence(stack):
    a = stack["genesis"].create_primordial(0.0)
    b = stack["genesis"].create_child(a, 1.0)
    # Make them very similar
    b.growth_coefficient = a.growth_coefficient
    b.decay_coefficient = a.decay_coefficient
    b.structural_complexity = a.structural_complexity
    sim = stack["convergence"].similarity(a, b)
    assert sim > 0.5
    # Force threshold low for test
    stack["config"].convergence_similarity_threshold = 0.3
    rel = stack["convergence"].converge(a, b, 2.0)
    assert rel is not None


def test_resource_constraints(stack):
    resources = ResourcePool(
        computational_energy=0.5,
        branching_budget=0.0,
        mutation_budget=0.0,
        interaction_budget=0.0,
    )
    assert resources.can_branch() is False
    assert resources.can_mutate() is False
    assert resources.can_interact() is False
    parent = stack["genesis"].create_primordial(0.0)
    child = stack["branching"].branch(parent, 1.0, resources)
    assert child is None


def test_reproducibility_fixed_seed():
    results = []
    for _ in range(2):
        ctrl = SimulationController(SimulationConfig(random_seed=99, max_timelines=20))

        async def run_cycles(c=ctrl):
            await c.start()
            for _ in range(15):
                await c._cycle()
            await c.stop()
            return [t.current_weight for t in c.registry.active_timelines()]

        weights = asyncio.run(run_cycles())
        results.append(weights)

    assert len(results[0]) == len(results[1])
    for a, b in zip(results[0], results[1]):
        assert abs(a - b) < 1e-9


@pytest.mark.asyncio
async def test_persistence_and_restart():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        persist = PersistenceEngine(db)
        await persist.connect()

        ctrl = SimulationController(SimulationConfig(random_seed=7, max_timelines=30))
        await ctrl.start()
        for _ in range(10):
            await ctrl._cycle()
        export = ctrl.full_export()
        await persist.save_autosave(export)
        sid = await persist.create_snapshot("test", export)
        await ctrl.stop()

        # Restart
        ctrl2 = SimulationController()
        loaded = await persist.load_autosave()
        assert loaded is not None
        ctrl2.load_export(loaded)
        assert abs(ctrl2.sim_time - export["sim_time"]) < 1e-9
        assert ctrl2.registry.count() == len(
            [t for t in export["timelines"] if not t.get("archived")]
        ) or ctrl2.registry.count(active_only=False) == len(export["timelines"])

        snap = await persist.load_snapshot(sid)
        assert snap is not None
        integrity = await persist.integrity_check()
        assert integrity["ok"] is True
        await persist.close()


@pytest.mark.asyncio
async def test_simulation_controller_cycle():
    ctrl = SimulationController(
        SimulationConfig(
            random_seed=42,
            max_timelines=40,
            base_branch_probability=0.3,
            event_rate=0.5,
        )
    )
    await ctrl.start()
    assert ctrl.registry.count() >= 1
    for _ in range(20):
        await ctrl._cycle()
    assert ctrl.sim_time > 0
    assert ctrl.organism.cycle_count == 20
    snap = ctrl.snapshot()
    assert "timelines" in snap
    assert "organism" in snap
    await ctrl.pause()
    assert ctrl.state.value == "paused"
    await ctrl.resume()
    await ctrl.stop()
