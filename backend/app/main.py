"""Chronos FastAPI application — local multiverse organism backend."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api.routes import router
from .persistence.engine import PersistenceEngine
from .simulation.controller import SimulationController
from .websocket.manager import ConnectionManager

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
FRONTEND_DIST = ROOT / "frontend" / "dist"

LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "chronos.log"),
    ],
)
logger = logging.getLogger("chronos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    controller = SimulationController()
    persistence = PersistenceEngine(DATA_DIR / "chronos.db")
    ws_manager = ConnectionManager()

    await persistence.connect()

    # Recovery: load autosave if present
    autosave = await persistence.load_autosave()
    if autosave:
        try:
            controller.load_export(autosave)
            logger.info("Recovered autosave at t=%.2f", controller.sim_time)
        except Exception:
            logger.exception("Failed to load autosave — starting fresh")

    async def on_update(data: dict) -> None:
        await ws_manager.broadcast(data)

    async def on_persist() -> None:
        await persistence.save_autosave(controller.full_export())

    controller.subscribe(on_update)
    controller.set_persist_callback(on_persist)

    app.state.controller = controller
    app.state.persistence = persistence
    app.state.ws_manager = ws_manager

    await controller.start()
    logger.info("Chronos organism is alive")

    yield

    # Graceful shutdown
    logger.info("Shutting down Chronos...")
    try:
        await persistence.save_autosave(controller.full_export())
    except Exception:
        logger.exception("Final save failed")
    await controller.stop()
    await persistence.close()
    logger.info("Chronos shutdown complete")


app = FastAPI(
    title="Chronos",
    description="Living Multiverse & Autonomous Timeline Evolution Simulator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    manager: ConnectionManager = app.state.ws_manager
    controller: SimulationController = app.state.controller
    await manager.connect(websocket)
    # Send current state immediately
    await manager.send(websocket, controller.snapshot())
    try:
        while True:
            # Receive client messages (ping / commands)
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "ping":
                await manager.send(websocket, {"type": "pong"})
            elif msg_type == "get_state":
                await manager.send(websocket, controller.snapshot())
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Serve frontend production build if present
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        index = FRONTEND_DIST / "index.html"
        if index.exists() and not full_path.startswith("api"):
            return FileResponse(index)
        return {"error": "not found"}
