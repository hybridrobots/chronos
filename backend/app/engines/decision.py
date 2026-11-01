"""Decision Counsel Engine — explore life problems as competing simulated paths."""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np

from ..models.config import SimulationConfig
from ..models.decision import DecisionPath, DecisionSession, DecisionStatus
from ..models.timeline import Timeline, TimelineEvent, EventType, TimelineStatus
from ..models.organism import ResourcePool, OrganismState
from .registry import TimelineRegistryEngine
from .genesis import TimelineGenesisEngine


class DecisionEngine:
    """
    Spawns tagged path lineages, scores relative viability each cycle,
    and recommends a path after enough generations/cycles.

    Scores are organism-internal relative shares — never real-life odds.
    """

    def __init__(
        self,
        registry: TimelineRegistryEngine,
        genesis: TimelineGenesisEngine,
        config: SimulationConfig,
        rng: np.random.Generator,
        organism: OrganismState,
    ) -> None:
        self.registry = registry
        self.genesis = genesis
        self.config = config
        self.rng = rng
        self.organism = organism
        self.sessions: dict[str, DecisionSession] = {}
        self.active_session_id: Optional[str] = None

    def start_session(
        self,
        problem: str,
        paths: list[dict[str, str]],
        sim_time: float,
        resources: ResourcePool,
        *,
        context: str = "",
        target_generations: int = 5,
        target_cycles: int = 80,
        seeds_per_path: int = 2,
        stress_tested: bool = True,
    ) -> DecisionSession:
        problem = (problem or "").strip()
        if len(problem) < 8:
            raise ValueError("Problem must be at least 8 characters")
        if len(paths) < 2:
            raise ValueError("Provide at least 2 paths/options")
        if len(paths) > 6:
            raise ValueError("At most 6 paths")

        # Cancel previous running session
        if self.active_session_id and self.active_session_id in self.sessions:
            prev = self.sessions[self.active_session_id]
            if prev.status == DecisionStatus.RUNNING:
                prev.status = DecisionStatus.CANCELLED

        roots = self.registry.active_timelines()
        if not roots:
            root = self.genesis.create_primordial(sim_time)
        else:
            # Prefer highest fitness as deliberation root
            root = max(roots, key=lambda t: (t.fitness_ema, t.current_weight))

        session = DecisionSession(
            problem=problem,
            context=context.strip(),
            status=DecisionStatus.RUNNING,
            target_generations=max(2, min(12, target_generations)),
            target_cycles=max(20, min(400, target_cycles)),
            created_sim_time=sim_time,
            stress_tested=stress_tested,
        )

        for raw in paths:
            label = (raw.get("label") or "").strip()
            if not label:
                continue
            path = DecisionPath(
                label=label[:80],
                description=(raw.get("description") or "")[:400],
            )
            for i in range(max(1, min(4, seeds_per_path))):
                child = self.genesis.create_child(
                    root,
                    sim_time,
                    mutation={
                        "decision": True,
                        "path_label": path.label,
                        "seed_index": i,
                    },
                )
                child.decision_session_id = session.id
                child.decision_path_id = path.id
                # Slight trait skew so paths diverge under selection
                skew = float(self.rng.normal(0, 0.015))
                child.growth_coefficient = max(0.001, child.growth_coefficient + skew)
                child.decay_coefficient = max(0.0, child.decay_coefficient - skew * 0.5)
                child.stability_score = float(
                    np.clip(child.stability_score + float(self.rng.normal(0, 0.05)), 0.1, 1.0)
                )
                child.events.append(
                    TimelineEvent(
                        timeline_id=child.id,
                        event_type=EventType.UNEXPECTED,
                        simulation_time=sim_time,
                        wall_timestamp=time.time(),
                        description=f"Decision path seeded: {path.label}",
                        payload={
                            "decision_session_id": session.id,
                            "decision_path_id": path.id,
                            "problem_excerpt": problem[:120],
                            "fictional": True,
                            "note": "Simulated deliberation path — not a life prediction",
                        },
                    )
                )
                self.registry.update_status(child.id, TimelineStatus.ACTIVE)
                path.timeline_ids.append(child.id)
                # Soft resource spend for deliberation
                resources.spend_think(min(resources.computational_energy, 0.5))
            session.paths.append(path)

        if len(session.paths) < 2:
            raise ValueError("Need at least 2 valid path labels")

        self.sessions[session.id] = session
        self.active_session_id = session.id
        return session

    def get(self, session_id: str) -> Optional[DecisionSession]:
        return self.sessions.get(session_id)

    def active(self) -> Optional[DecisionSession]:
        if not self.active_session_id:
            return None
        return self.sessions.get(self.active_session_id)

    def cancel(self, session_id: str) -> Optional[DecisionSession]:
        s = self.sessions.get(session_id)
        if not s:
            return None
        s.status = DecisionStatus.CANCELLED
        if self.active_session_id == session_id:
            self.active_session_id = None
        return s

    def tick(self, sim_time: float) -> Optional[DecisionSession]:
        """Update scores each sim cycle; complete when targets met."""
        session = self.active()
        if not session or session.status != DecisionStatus.RUNNING:
            return session

        session.cycles_done += 1
        max_gen = 0
        stress = 0.0
        if session.stress_tested:
            # Scarcity penalty from organism vitals
            energy_r = self.organism.resources.computational_energy / max(
                self.organism.resources.max_energy, 1
            )
            throttle = getattr(self.organism, "metabolic_throttle", 1.0)
            stress = float(np.clip(1.0 - 0.5 * energy_r - 0.5 * throttle, 0.0, 1.0))

        raw_scores: list[float] = []
        for path in session.paths:
            tls = [
                self.registry.get(tid)
                for tid in path.timeline_ids
                if self.registry.get(tid) is not None
            ]
            # Include descendants tagged with same path
            for tl in self.registry.active_timelines():
                if (
                    tl.decision_path_id == path.id
                    and tl.id not in path.timeline_ids
                ):
                    path.timeline_ids.append(tl.id)
                    tls.append(tl)
            # Also inherit path tag for children of path seeds
            for tid in list(path.timeline_ids):
                for child in self.registry.children_of(tid):
                    if not child.decision_path_id:
                        child.decision_path_id = path.id
                        child.decision_session_id = session.id
                    if child.id not in path.timeline_ids:
                        path.timeline_ids.append(child.id)
                        tls.append(child)

            active = [t for t in tls if t and not t.archived]
            path.sample_count = len(active)
            if not active:
                path.viability = 0.0
                path.mean_weight = 0.0
                path.mean_stability = 0.0
                path.mean_fitness = 0.0
                path.generation_depth = 0
                raw_scores.append(0.01)
                continue

            weights = np.array([t.current_weight for t in active], dtype=float)
            stabs = np.array([t.stability_score for t in active], dtype=float)
            fits = np.array([t.fitness_ema for t in active], dtype=float)
            gens = [t.generation for t in active]
            path.mean_weight = float(np.mean(weights))
            path.mean_stability = float(np.mean(stabs))
            path.mean_fitness = float(np.mean(fits))
            path.generation_depth = int(max(gens))
            max_gen = max(max_gen, path.generation_depth)

            # Viability: fitness + stability + log-weight, penalize stress fragility
            base = (
                0.40 * (path.mean_fitness + 1.0) / 2.0
                + 0.30 * path.mean_stability
                + 0.20 * float(np.tanh(path.mean_weight / 3.0))
                + 0.10 * min(1.0, path.generation_depth / max(session.target_generations, 1))
            )
            # Paths that stay stable under stress score higher
            fragility = float(np.std(stabs)) if len(stabs) > 1 else 0.0
            viability = base * (1.0 - 0.35 * stress) - 0.1 * fragility
            path.viability = float(np.clip(viability, 0.0, 1.0))
            alpha = 0.25
            path.viability_ema = (1 - alpha) * path.viability_ema + alpha * path.viability
            raw_scores.append(max(1e-6, path.viability_ema))

            path.history.append(
                {
                    "sim_time": sim_time,
                    "viability": path.viability,
                    "viability_ema": path.viability_ema,
                    "samples": path.sample_count,
                }
            )

        session.max_generation_seen = max_gen
        # Softmax → relative shares (NOT real probabilities)
        arr = np.array(raw_scores, dtype=float)
        arr = arr - arr.max()
        ex = np.exp(arr / 0.35)
        shares = ex / (ex.sum() or 1.0)
        for path, share in zip(session.paths, shares):
            path.relative_share = float(share)

        # Propagate tags on new branches from path parents
        self._tag_new_descendants(session)

        if (
            session.cycles_done >= session.target_cycles
            or session.max_generation_seen >= session.target_generations
        ):
            self._recommend(session, sim_time)

        return session

    def _tag_new_descendants(self, session: DecisionSession) -> None:
        for path in session.paths:
            for tid in list(path.timeline_ids):
                for child in self.registry.children_of(tid):
                    if child.decision_session_id and child.decision_session_id != session.id:
                        continue
                    child.decision_session_id = session.id
                    child.decision_path_id = path.id
                    if child.id not in path.timeline_ids:
                        path.timeline_ids.append(child.id)

    def _recommend(self, session: DecisionSession, sim_time: float) -> None:
        if not session.paths:
            return
        ranked = sorted(session.paths, key=lambda p: p.relative_share, reverse=True)
        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None
        margin = best.relative_share - (second.relative_share if second else 0.0)

        confidence = "tentative"
        if margin >= 0.18 and session.cycles_done >= session.target_cycles * 0.6:
            confidence = "clearer"
        if margin >= 0.28 and best.viability_ema >= 0.45:
            confidence = "stronger (still simulated)"

        lines = [
            f"Recommended path (simulated): «{best.label}».",
            f"Relative share among options: {best.relative_share * 100:.1f}% "
            f"(viability EMA {best.viability_ema:.3f}).",
        ]
        if second:
            lines.append(
                f"Next: «{second.label}» at {second.relative_share * 100:.1f}% "
                f"(margin {margin * 100:.1f} pts)."
            )
        lines.append(f"Signal strength: {confidence}.")
        lines.append(
            "These are relative viability shares inside Chronos under growth, "
            "decay, fitness, and scarcity stress — not odds that a choice will "
            "succeed in your life. Use them as a structured mirror, then decide."
        )
        if session.context:
            lines.append(f"Your context note was held in deliberation: {session.context[:200]}")

        session.recommendation_path_id = best.id
        session.recommendation_summary = " ".join(lines)
        session.status = DecisionStatus.COMPLETE
        session.completed_sim_time = sim_time
        if self.active_session_id == session.id:
            # keep as active for UI until replaced
            pass

    def force_recommend(self, session_id: str, sim_time: float) -> Optional[DecisionSession]:
        s = self.sessions.get(session_id)
        if not s:
            return None
        if s.status == DecisionStatus.RUNNING:
            self._recommend(s, sim_time)
        return s

    def export_all(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.sessions.values()]

    def load_all(self, items: list[dict[str, Any]]) -> None:
        self.sessions = {
            d["id"]: DecisionSession.from_dict(d) for d in items if "id" in d
        }
        running = [
            s
            for s in self.sessions.values()
            if s.status == DecisionStatus.RUNNING
        ]
        self.active_session_id = running[-1].id if running else None
