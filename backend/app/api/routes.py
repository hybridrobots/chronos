"""REST API — control, inspect, configure the living multiverse."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


class SpeedBody(BaseModel):
    speed: float = Field(ge=0.1, le=50.0)


class ConfigBody(BaseModel):
    updates: dict[str, Any]


class RewriteBody(BaseModel):
    timeline_id: str
    event_id: str
    description: str
    payload: Optional[dict[str, Any]] = None


class ResolveBody(BaseModel):
    paradox_id: str
    strategy: Optional[str] = None


class SnapshotBody(BaseModel):
    name: str = "manual"


class ResetBody(BaseModel):
    seed: Optional[int] = None


class DecisionPathIn(BaseModel):
    label: str
    description: str = ""


class DecisionStartBody(BaseModel):
    problem: str
    paths: list[DecisionPathIn]
    context: str = ""
    target_generations: int = 5
    target_cycles: int = 80
    seeds_per_path: int = 2
    stress_tested: bool = True


def _ctrl(request: Request):
    return request.app.state.controller


def _persist(request: Request):
    return request.app.state.persistence


@router.get("/health")
async def health():
    return {"status": "alive", "organism": "chronos"}


@router.get("/state")
async def get_state(request: Request):
    return _ctrl(request).snapshot()


@router.get("/organism")
async def get_organism(request: Request):
    return _ctrl(request).organism.to_dict()


@router.get("/timelines")
async def list_timelines(request: Request, include_archived: bool = False):
    reg = _ctrl(request).registry
    tls = reg.all_timelines() if include_archived else reg.active_timelines()
    return [t.to_dict(include_events=False) for t in tls]


@router.get("/timelines/{timeline_id}")
async def get_timeline(timeline_id: str, request: Request):
    tl = _ctrl(request).registry.get(timeline_id)
    if not tl:
        raise HTTPException(404, "Timeline not found")
    return tl.to_dict(include_events=True)


@router.get("/timelines/{timeline_id}/genealogy")
async def genealogy(timeline_id: str, request: Request):
    tree = _ctrl(request).registry.genealogy(timeline_id)
    if not tree:
        raise HTTPException(404, "Timeline not found")
    return tree


@router.get("/timelines/{timeline_id}/history")
async def timeline_history(
    timeline_id: str, request: Request, include_archived: bool = True
):
    events = _ctrl(request).memory.get_timeline_history(
        timeline_id, include_archived=include_archived
    )
    return [e.to_dict() for e in events]


@router.get("/paradoxes")
async def list_paradoxes(request: Request):
    return [p.to_dict() for p in _ctrl(request).paradox_detection.get_all()]


@router.get("/relationships")
async def list_relationships(request: Request):
    return [
        r.to_dict()
        for r in _ctrl(request).registry.get_relationships(active_only=True)
    ]


@router.get("/config")
async def get_config(request: Request):
    return _ctrl(request).config.to_dict()


@router.post("/config")
async def update_config(body: ConfigBody, request: Request):
    cfg = _ctrl(request).update_config(body.updates)
    return cfg.to_dict()


@router.post("/control/start")
async def start(request: Request):
    await _ctrl(request).start()
    return {"state": _ctrl(request).state.value}


@router.post("/control/pause")
async def pause(request: Request):
    await _ctrl(request).pause()
    return {"state": _ctrl(request).state.value}


@router.post("/control/resume")
async def resume(request: Request):
    await _ctrl(request).resume()
    return {"state": _ctrl(request).state.value}


@router.post("/control/stop")
async def stop(request: Request):
    await _ctrl(request).stop()
    return {"state": _ctrl(request).state.value}


@router.post("/control/reset")
async def reset(body: ResetBody, request: Request):
    await _ctrl(request).reset(seed=body.seed)
    await _ctrl(request).start()
    return {"state": _ctrl(request).state.value, "seed": _ctrl(request).config.random_seed}


@router.post("/control/speed")
async def set_speed(body: SpeedBody, request: Request):
    _ctrl(request).set_speed(body.speed)
    return {"speed": _ctrl(request).config.speed}


@router.post("/alterations/rewrite")
async def rewrite(body: RewriteBody, request: Request):
    ctrl = _ctrl(request)
    evt = ctrl.alteration.rewrite_event(
        body.timeline_id,
        body.event_id,
        body.description,
        body.payload,
        ctrl.sim_time,
    )
    if not evt:
        raise HTTPException(404, "Event not found")
    return evt.to_dict()


@router.post("/paradoxes/resolve")
async def resolve_paradox(body: ResolveBody, request: Request):
    from ..models.paradox import ResolutionStrategy

    ctrl = _ctrl(request)
    paradox = ctrl.paradox_detection.get(body.paradox_id)
    if not paradox:
        raise HTTPException(404, "Paradox not found")
    strategy = ResolutionStrategy(body.strategy) if body.strategy else None
    result = ctrl.paradox_resolution.resolve(
        paradox, ctrl.sim_time, ctrl.organism.resources, strategy
    )
    return result.to_dict()


@router.post("/persistence/save")
async def manual_save(request: Request):
    export = _ctrl(request).full_export()
    await _persist(request).save_autosave(export)
    return {"saved": True, "sim_time": export["sim_time"]}


@router.post("/persistence/snapshot")
async def create_snapshot(body: SnapshotBody, request: Request):
    export = _ctrl(request).full_export()
    sid = await _persist(request).create_snapshot(body.name, export)
    return {"snapshot_id": sid, "name": body.name}


@router.get("/persistence/snapshots")
async def list_snapshots(request: Request):
    return await _persist(request).list_snapshots()


@router.post("/persistence/restore/{snapshot_id}")
async def restore_snapshot(snapshot_id: int, request: Request):
    data = await _persist(request).load_snapshot(snapshot_id)
    if not data:
        raise HTTPException(404, "Snapshot not found")
    ctrl = _ctrl(request)
    was_running = ctrl.state.value == "running"
    await ctrl.stop()
    ctrl.load_export(data)
    if was_running:
        await ctrl.start()
    return {"restored": True, "sim_time": ctrl.sim_time}


@router.post("/persistence/load-autosave")
async def load_autosave(request: Request):
    data = await _persist(request).load_autosave()
    if not data:
        raise HTTPException(404, "No autosave found")
    ctrl = _ctrl(request)
    was_running = ctrl.state.value == "running"
    await ctrl.stop()
    ctrl.load_export(data)
    if was_running:
        await ctrl.start()
    return {"restored": True, "sim_time": ctrl.sim_time}


@router.get("/persistence/integrity")
async def integrity(request: Request):
    return await _persist(request).integrity_check()


@router.get("/observatory")
async def observatory(request: Request):
    ctrl = _ctrl(request)
    return {
        "paradoxes": [p.to_dict() for p in ctrl.paradox_detection.get_all()],
        "alterations": ctrl.alteration.get_alteration_log()[-50:],
        "interactions": ctrl.interaction.get_history()[-50:],
        "convergences": ctrl.convergence.get_history()[-50:],
        "conflicts": ctrl.causality.get_conflicts()[-50:],
        "memory_log": ctrl.memory.get_global_log(50),
    }


@router.get("/learning")
async def learning_state(request: Request):
    ctrl = _ctrl(request)
    return {
        "enabled": ctrl.config.learning_enabled,
        "organism": {
            "mean_fitness": ctrl.organism.mean_fitness,
            "mean_fitness_ema": ctrl.organism.mean_fitness_ema,
            "best_fitness": ctrl.organism.best_fitness,
            "total_reward": ctrl.organism.total_reward,
            "total_thinks": ctrl.organism.total_thinks,
            "learning_cycles": ctrl.organism.learning_cycles,
        },
        "policy": ctrl.policy.export_state(),
        "action_stats": ctrl.reward_ledger.action_stats(),
        "recent_rewards": [r.to_dict() for r in ctrl.reward_ledger.recent(40)],
        "last_cycle": ctrl._last_learning,
    }


@router.get("/homeostasis")
async def homeostasis_state(request: Request):
    ctrl = _ctrl(request)
    return {
        "enabled": ctrl.config.homeostasis_enabled,
        "mode": ctrl.organism.homeostasis_mode,
        "throttle": ctrl.organism.metabolic_throttle,
        "last": ctrl._last_metabolism,
        "health": ctrl.organism.health,
        "population": ctrl.organism.active_timeline_count,
        "capacity": ctrl.organism.resources.timeline_capacity,
        "energy": ctrl.organism.resources.computational_energy,
        "max_energy": ctrl.organism.resources.max_energy,
        "memory_used": ctrl.organism.resources.memory_used,
        "memory_capacity": ctrl.organism.resources.memory_capacity,
    }


@router.get("/decision")
async def decision_active(request: Request):
    ctrl = _ctrl(request)
    active = ctrl.decision.active()
    return {
        "active": active.to_dict() if active else None,
        "sessions": ctrl.decision.export_all()[-10:],
    }


@router.post("/decision/start")
async def decision_start(body: DecisionStartBody, request: Request):
    ctrl = _ctrl(request)
    try:
        session = ctrl.decision.start_session(
            body.problem,
            [p.model_dump() for p in body.paths],
            ctrl.sim_time,
            ctrl.organism.resources,
            context=body.context,
            target_generations=body.target_generations,
            target_cycles=body.target_cycles,
            seeds_per_path=body.seeds_per_path,
            stress_tested=body.stress_tested,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    # Ensure sim is running so deliberation progresses
    if ctrl.state.value != "running":
        await ctrl.start()
    return session.to_dict()


@router.post("/decision/{session_id}/conclude")
async def decision_conclude(session_id: str, request: Request):
    ctrl = _ctrl(request)
    session = ctrl.decision.force_recommend(session_id, ctrl.sim_time)
    if not session:
        raise HTTPException(404, "Decision session not found")
    return session.to_dict()


@router.post("/decision/{session_id}/cancel")
async def decision_cancel(session_id: str, request: Request):
    ctrl = _ctrl(request)
    session = ctrl.decision.cancel(session_id)
    if not session:
        raise HTTPException(404, "Decision session not found")
    return session.to_dict()
