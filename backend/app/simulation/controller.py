"""Simulation Controller — autonomous organism loop, independent of the UI."""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Awaitable, Optional

import numpy as np

from ..models.config import SimulationConfig
from ..models.organism import OrganismState, ResourcePool
from ..models.timeline import TimelineStatus
from ..engines.registry import TimelineRegistryEngine
from ..engines.genesis import TimelineGenesisEngine
from ..engines.branching import TimelineBranchingEngine
from ..engines.growth import ExponentialGrowthEngine
from ..engines.decay import ExponentialDecayEngine
from ..engines.alteration import TemporalAlterationEngine
from ..engines.interaction import CrossTimelineInteractionEngine
from ..engines.causality import CausalDependencyEngine
from ..engines.convergence import TimelineConvergenceEngine
from ..engines.paradox_detection import ParadoxDetectionEngine
from ..engines.paradox_resolution import ParadoxResolutionEngine
from ..engines.health import OrganismHealthEngine
from ..engines.memory import HistoricalMemoryEngine
from ..engines.events import AutonomousEventEngine
from ..engines.reward_ledger import RewardLedger
from ..engines.fitness import FitnessEngine
from ..engines.policy import PolicyEngine
from ..engines.homeostasis import HomeostasisEngine
from ..engines.decision import DecisionEngine

logger = logging.getLogger("chronos.simulation")

UpdateCallback = Callable[[dict[str, Any]], Awaitable[None]]


class SimState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SimulationController:
    """
    Continuously evolving organism loop.

    Runs independently of the visual interface — continues when UI disconnects.
    Simulation time is separate from wall-clock time.
    """

    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()
        self.rng = np.random.default_rng(self.config.random_seed)

        self.sim_time: float = 0.0
        self.state = SimState.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._subscribers: list[UpdateCallback] = []
        self._last_ws_push: float = 0.0
        self._last_auto_save: float = 0.0
        self._persist_callback: Optional[Callable[[], Awaitable[None]]] = None

        # Engines
        self.registry = TimelineRegistryEngine()
        self.genesis = TimelineGenesisEngine(self.registry, self.config, self.rng)
        self.growth = ExponentialGrowthEngine(self.registry, self.config)
        self.decay = ExponentialDecayEngine(self.registry, self.config)
        self.alteration = TemporalAlterationEngine(self.registry, self.config)
        self.causality = CausalDependencyEngine(self.registry, self.config)
        self.memory = HistoricalMemoryEngine(self.registry, self.config)
        self.events = AutonomousEventEngine(
            self.registry, self.causality, self.memory, self.config, self.rng
        )
        self.branching = TimelineBranchingEngine(
            self.registry, self.genesis, self.config, self.rng
        )
        self.interaction = CrossTimelineInteractionEngine(
            self.registry, self.config, self.rng
        )
        self.convergence = TimelineConvergenceEngine(
            self.registry, self.config, self.rng
        )
        self.paradox_detection = ParadoxDetectionEngine(
            self.registry, self.causality, self.config
        )
        self.paradox_resolution = ParadoxResolutionEngine(
            self.registry,
            self.branching,
            self.alteration,
            self.decay,
            self.config,
            self.rng,
        )

        resources = ResourcePool(**self.config.apply_to_resources())  # type: ignore[arg-type]
        self.organism = OrganismState(resources=resources)
        self.health = OrganismHealthEngine(
            self.registry, self.paradox_detection, self.config, self.organism
        )

        # Learning loop: think → act → score → metabolize
        self.reward_ledger = RewardLedger()
        self.fitness = FitnessEngine(
            self.registry, self.config, self.reward_ledger, self.organism
        )
        self.policy = PolicyEngine(
            self.registry,
            self.config,
            self.rng,
            self.branching,
            self.alteration,
            self.interaction,
            self.events,
            self.fitness,
            self.reward_ledger,
            self.organism,
        )
        self.homeostasis = HomeostasisEngine(
            self.registry, self.config, self.organism, self.memory
        )
        self.decision = DecisionEngine(
            self.registry, self.genesis, self.config, self.rng, self.organism
        )

        self._cycle_stats: dict[str, Any] = {}
        self._last_learning: dict[str, Any] = {}
        self._last_metabolism: dict[str, Any] = {}

    def subscribe(self, callback: UpdateCallback) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: UpdateCallback) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def set_persist_callback(self, cb: Callable[[], Awaitable[None]]) -> None:
        self._persist_callback = cb

    async def start(self) -> None:
        if self.state == SimState.RUNNING:
            return
        if self.registry.count() == 0:
            self.genesis.create_primordial(self.sim_time)
            self.organism.total_branches = 0
            logger.info("Primordial timeline created")
        self.state = SimState.RUNNING
        self._task = asyncio.create_task(self._loop(), name="chronos-sim")
        logger.info("Simulation started at t=%.2f", self.sim_time)

    async def pause(self) -> None:
        self.state = SimState.PAUSED
        logger.info("Simulation paused at t=%.2f", self.sim_time)

    async def resume(self) -> None:
        if self.state == SimState.PAUSED:
            self.state = SimState.RUNNING
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._loop(), name="chronos-sim")
            logger.info("Simulation resumed at t=%.2f", self.sim_time)

    async def stop(self) -> None:
        self.state = SimState.STOPPED
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulation stopped")

    async def reset(self, seed: Optional[int] = None) -> None:
        await self.stop()
        if seed is not None:
            self.config.random_seed = seed
        self.rng = np.random.default_rng(self.config.random_seed)
        self.sim_time = 0.0
        self.registry.clear()
        self.paradox_detection.load([])
        self.memory.load_log([])
        resources = ResourcePool(**self.config.apply_to_resources())  # type: ignore[arg-type]
        self.organism = OrganismState(resources=resources)
        self.health.state = self.organism
        self.fitness.organism = self.organism
        self.policy.organism = self.organism
        self.homeostasis.organism = self.organism
        self.decision.organism = self.organism
        # Re-bind rng-dependent engines
        self.genesis.rng = self.rng
        self.branching.rng = self.rng
        self.interaction.rng = self.rng
        self.convergence.rng = self.rng
        self.events.rng = self.rng
        self.paradox_resolution.rng = self.rng
        self.policy.rng = self.rng
        self.reward_ledger.load([])
        self.policy.load_state(
            {"q": {a: 0.0 for a in self.policy._q}, "counts": {a: 0 for a in self.policy._counts}}
        )
        self._last_learning = {}
        self._last_metabolism = {}
        self.decision.load_all([])
        self.decision.rng = self.rng
        self.genesis.create_primordial(0.0)
        logger.info("Simulation reset (seed=%s)", self.config.random_seed)

    def set_speed(self, speed: float) -> None:
        self.config.speed = max(0.1, min(50.0, speed))

    def update_config(self, updates: dict[str, Any]) -> SimulationConfig:
        for k, v in updates.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        # Sync resource caps
        r = self.organism.resources
        r.max_energy = self.config.max_energy
        r.timeline_capacity = self.config.timeline_capacity
        r.max_branching_budget = self.config.branching_budget
        r.memory_capacity = self.config.memory_capacity
        r.max_mutation_budget = self.config.mutation_budget
        r.max_interaction_budget = self.config.interaction_budget
        return self.config

    async def _loop(self) -> None:
        """Main autonomous cycle — wall-clock gated, simulation-time advanced."""
        try:
            while self.state != SimState.STOPPED:
                if self.state == SimState.PAUSED:
                    await asyncio.sleep(0.05)
                    continue

                wall_start = time.monotonic()
                await self._cycle()

                # Pace wall-clock: timestep / speed
                target = self.config.timestep / max(self.config.speed, 0.1)
                elapsed = time.monotonic() - wall_start
                await asyncio.sleep(max(0.001, target - elapsed))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Simulation loop crashed — attempting recovery")
            self.state = SimState.PAUSED
            await self._publish({"type": "error", "message": "Simulation paused due to error"})

    async def _cycle(self) -> None:
        """One full organism metabolism cycle with homeostasis feedback."""
        dt = self.config.timestep
        self.sim_time += dt
        resources = self.organism.resources

        # 0. Health snapshot → metabolic throttle
        self.health.evaluate(self.sim_time)
        meta = self.homeostasis.evaluate()
        self._last_metabolism = meta.to_dict()

        # 1. Regenerate (faster while resting / conserving)
        resources.regenerate(
            dt,
            self.config.resource_regen_rate,
            multiplier=self.homeostasis.regen_multiplier(),
        )

        diversity = self.organism.diversity

        # 2. Policy thinking — gated by homeostasis
        learning_stats = self.policy.think_cycle(
            self.sim_time,
            resources,
            diversity,
            throttle=meta.throttle,
            allow_think=meta.allow_think,
            allow_branch=meta.allow_branch,
            mode=meta.mode,
        )
        self._last_learning = learning_stats

        # 3. Ambient events (throttled)
        new_events = self.events.generate_cycle(
            self.sim_time,
            resources,
            throttle=meta.throttle,
            allow_ambient=meta.allow_ambient_events,
        )

        # 4. Growth & decay
        growth_stats = self.growth.apply_cycle(self.sim_time, dt)
        decay_stats = self.decay.apply_cycle(self.sim_time, dt)

        # 5. Ambient branching (hard-capped by homeostasis)
        new_branches = self.branching.evaluate_all(
            self.sim_time,
            resources,
            throttle=meta.throttle,
            allow_branch=meta.allow_branch,
        )
        self.organism.total_branches += len(new_branches)

        # 6. Ambient interactions (skip in crisis)
        new_interactions: list = []
        if meta.mode != "crisis" and meta.throttle > 0.2:
            new_interactions = self.interaction.evaluate_all(self.sim_time, resources)
            self.organism.total_interactions += len(new_interactions)

        # 7. Causal conflicts → paradox detection
        conflicts = self.causality.scan_all()
        new_paradoxes = self.paradox_detection.detect_from_conflicts(
            conflicts, self.sim_time
        )
        new_paradoxes += self.paradox_detection.detect_cross_timeline(self.sim_time)

        # 8. Paradox resolution
        unresolved = self.paradox_detection.get_unresolved()
        resolved = self.paradox_resolution.resolve_all(
            unresolved, self.sim_time, resources
        )

        # 9. Convergence
        convergences = self.convergence.evaluate_all(self.sim_time)
        self.organism.total_convergences += len(convergences)

        # 10. Memory retention + cull weak lineages under pressure
        self.memory.apply_retention()
        culled = self.homeostasis.apply_pressure(self.sim_time)

        # Decision counsel scoring (if a session is running)
        decision_snap = None
        if self.decision.active():
            decision_snap = self.decision.tick(self.sim_time)
            if decision_snap:
                decision_snap = decision_snap.to_dict()

        # 11. Restore non-terminal statuses toward ACTIVE
        for tl in self.registry.active_timelines():
            if tl.status in (TimelineStatus.NASCENT, TimelineStatus.MUTATING):
                if self.sim_time - tl.last_update_time > 1.0 or tl.status == TimelineStatus.NASCENT:
                    if tl.status == TimelineStatus.NASCENT:
                        self.registry.update_status(tl.id, TimelineStatus.ACTIVE)

        # 12. Organism health + population aggregate fitness
        self.organism.cycle_count += 1
        self.health.evaluate(self.sim_time)
        meta_after = self.homeostasis.evaluate()
        self._last_metabolism = meta_after.to_dict()
        self._last_metabolism["archived_weak"] = culled
        fitness_stats = self.fitness.evaluate_population(self.organism.diversity)

        self._cycle_stats = {
            "sim_time": self.sim_time,
            "events": len(new_events),
            "branches": len(new_branches),
            "interactions": len(new_interactions),
            "paradoxes": len(new_paradoxes),
            "resolved": len(resolved),
            "convergences": len(convergences),
            "growth": growth_stats,
            "decay": decay_stats,
            "learning": {
                "thinks": learning_stats.get("thinks", 0),
                "mean_reward": learning_stats.get("mean_reward", 0.0),
                "fitness": fitness_stats,
            },
            "homeostasis": self._last_metabolism,
            "decision": decision_snap,
        }

        # 13. Publish visual updates (throttled)
        now = time.monotonic()
        if now - self._last_ws_push >= self.config.ws_update_interval:
            self._last_ws_push = now
            await self._publish(self.snapshot())

        # 14. Auto-save
        if (
            self._persist_callback
            and now - self._last_auto_save >= self.config.auto_save_interval
        ):
            self._last_auto_save = now
            try:
                await self._persist_callback()
            except Exception:
                logger.exception("Auto-save failed")

    async def _publish(self, data: dict[str, Any]) -> None:
        for cb in list(self._subscribers):
            try:
                await cb(data)
            except Exception:
                logger.exception("Subscriber callback failed")

    def snapshot(self) -> dict[str, Any]:
        """Full state snapshot for WebSocket / API consumers."""
        timelines = self.registry.active_timelines()
        # Cap payload size for performance — send summaries + limited events
        tl_data = []
        for t in timelines:
            d = t.to_dict(include_events=False)
            d["recent_events"] = [
                e.to_dict() for e in t.active_events()[-5:]
            ]
            tl_data.append(d)

        relationships = [
            r.to_dict()
            for r in self.registry.get_relationships(active_only=True)
        ]
        # Limit relationship payload
        if len(relationships) > 500:
            relationships = relationships[-500:]

        # Prefer unresolved paradoxes in the live feed; cap payload size
        all_p = self.paradox_detection.get_all()
        unresolved = [p for p in all_p if p.status.value in ("detected", "resolving", "preserved", "isolated")]
        resolved = [p for p in all_p if p.status.value == "resolved"]
        paradoxes = [p.to_dict() for p in (unresolved + resolved[-20:])[:80]]

        return {
            "type": "state",
            "sim_time": self.sim_time,
            "state": self.state.value,
            "speed": self.config.speed,
            "timelines": tl_data,
            "relationships": relationships,
            "paradoxes": paradoxes,
            "organism": self.organism.to_dict(),
            "cycle_stats": self._cycle_stats,
            "normalized_weights": self.growth.normalized_weights(),
            "config": self.config.to_dict(),
            "learning": {
                "enabled": self.config.learning_enabled,
                "last": {
                    "thinks": self._last_learning.get("thinks", 0),
                    "mean_reward": self._last_learning.get("mean_reward", 0.0),
                    "policy_q": self._last_learning.get("policy_q", {}),
                },
                "action_stats": self.reward_ledger.action_stats(),
                "recent_rewards": [
                    r.to_dict() for r in self.reward_ledger.recent(20)
                ],
            },
            "homeostasis": self._last_metabolism
            or {
                "throttle": self.organism.metabolic_throttle,
                "mode": self.organism.homeostasis_mode,
            },
            "decision": (
                self.decision.active().to_dict()
                if self.decision.active()
                else None
            ),
        }

    def full_export(self) -> dict[str, Any]:
        """Complete export including all events for persistence."""
        return {
            "sim_time": self.sim_time,
            "state": self.state.value,
            "config": self.config.to_dict(),
            "timelines": [t.to_dict(include_events=True) for t in self.registry.all_timelines()],
            "relationships": [
                r.to_dict()
                for r in self.registry.get_relationships(active_only=False)
            ],
            "paradoxes": [p.to_dict() for p in self.paradox_detection.get_all()],
            "organism": self.organism.to_dict(),
            "memory_log": self.memory.get_global_log(limit=5000),
            "alteration_log": self.alteration.get_alteration_log(),
            "interaction_history": self.interaction.get_history(),
            "convergence_history": self.convergence.get_history(),
            "reward_ledger": self.reward_ledger.to_list(5000),
            "policy_state": self.policy.export_state(),
            "decision_sessions": self.decision.export_all(),
        }

    def load_export(self, data: dict[str, Any]) -> None:
        """Restore from a full export."""
        from ..models.timeline import Timeline
        from ..models.relationships import Relationship
        from ..models.paradox import Paradox

        self.sim_time = data.get("sim_time", 0.0)
        if "config" in data:
            self.config = SimulationConfig.from_dict(data["config"])
            self.rng = np.random.default_rng(self.config.random_seed)

        timelines = [Timeline.from_dict(t) for t in data.get("timelines", [])]
        relationships = [
            Relationship.from_dict(r) for r in data.get("relationships", [])
        ]
        self.registry.load_state(timelines, relationships)

        paradoxes = [Paradox.from_dict(p) for p in data.get("paradoxes", [])]
        self.paradox_detection.load(paradoxes)

        if "organism" in data:
            self.organism = OrganismState.from_dict(data["organism"])
            self.health.state = self.organism
            self.fitness.organism = self.organism
            self.policy.organism = self.organism
            self.homeostasis.organism = self.organism

        self.memory.load_log(data.get("memory_log", []))
        self.reward_ledger.load(data.get("reward_ledger", []))
        self.policy.load_state(data.get("policy_state", {}))
        self.decision.load_all(data.get("decision_sessions", []))

        # Rebind rng + config on learning engines
        self.genesis.rng = self.rng
        self.branching.rng = self.rng
        self.interaction.rng = self.rng
        self.convergence.rng = self.rng
        self.events.rng = self.rng
        self.paradox_resolution.rng = self.rng
        self.policy.rng = self.rng
        self.fitness.config = self.config
        self.policy.config = self.config
        self.growth.config = self.config
        self.homeostasis.config = self.config
        self.decision.config = self.config
        self.decision.rng = self.rng
        self.decision.organism = self.organism

        logger.info(
            "Loaded export: %d timelines, t=%.2f",
            len(timelines),
            self.sim_time,
        )
