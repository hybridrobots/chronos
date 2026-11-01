# CHRONOS

### Living Multiverse · Autonomous Timeline Evolution · Decision Counsel

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](./backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-local%20API-009688?logo=fastapi&logoColor=white)](./backend/app/main.py)
[![React](https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=black)](./frontend/package.json)
[![Three.js](https://img.shields.io/badge/Three.js-R3F-000000?logo=threedotjs&logoColor=white)](./frontend/src/viz)
[![SQLite](https://img.shields.io/badge/SQLite-offline%20persistence-003B57?logo=sqlite&logoColor=white)](./backend/app/persistence)
[![Tests](https://img.shields.io/badge/pytest-33%20passing-2ea44f)](./backend/tests)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

> A locally running **artificial digital organism** that explores possibility the way life does: by trying, tracking, keeping what holds, and letting the rest fade — across a branching multiverse you can see, steer, and consult.

**Not a dashboard. Not a cloud toy.** Chronos is a full-stack, offline-first systems demo: simulation science + product UX + responsible AI framing.

---

## The idea

Life rarely learns from a single straight line. It learns by **variation under constraint**.

You try a path. You feel the cost. Some branches thrive; some thin out; some contradict each other until you resolve the tension — or live with it. Memory remains even when a chapter ends. Attention and energy are finite, so the organism cannot expand forever without consequence.

**Chronos treats that process as software.**

It is not trained once on a static dataset and then frozen. It is a **living learning system**: every cycle it generates possibilities (events, mutations, branches, interactions), scores what happens, updates its internal “weight” of each timeline, and adapts. The multiverse is the training ground. The organism *is* the learner.

In the interface you watch that as a glowing wireframe cosmos of timelines. In Decision Counsel you can plant a *real* human problem into that cosmos — several named options become competing lineages — and after enough generations Chronos reports which path held up best **inside the simulation**, under growth, decay, conflict, and scarcity.

That recommendation is a **mirror**, not an oracle: relative viability among the worlds Chronos could grow, not a claim about what will happen in your life. The point of the piece is philosophical and practical at once — *learning by living through alternatives* — implemented as a runnable system.

---

## The math (how the organism learns by trying)

Chronos does not “know” the right future in advance. It **probes**, **measures**, and **metabolizes**.

### 1. Influence of a timeline — exponential growth & decay

Each timeline carries a raw influence weight. Between birth and the present simulation time \(t\):

\[
W(t) = W_0 \cdot e^{(g - d)\, t}
\]

| Symbol | Meaning |
|--------|---------|
| \(W_0\) | Initial weight at birth |
| \(g\) | Growth coefficient (expansion pressure) |
| \(d\) | Decay coefficient (erosion pressure) |
| \(t\) | Elapsed **simulation** time (not wall-clock) |

- If \(g > d\), the line tends to swell in influence.  
- If \(d > g\), it fades toward archival.  
- Population pressure softens effective \(g\) as the multiverse fills — unbounded explosion is not allowed.

**Important:** \(W\) is an internal influence measure. Chronos **never** treats it as the objective probability of a real universe.

### 2. Relative shares — comparing paths without claiming fate

When Decision Counsel (or the UI) needs comparable “odds” among options, Chronos converts path viability scores \(v_i\) into **relative shares** via a softmax:

\[
p_i = \frac{e^{v_i / \tau}}{\sum_j e^{v_j / \tau}}
\]

Here \(\tau\) is a temperature (softness). The \(p_i\) **sum to 1**, so they look like probabilities — but they only mean: *among these simulated lineages, under these rules, how much relative support did each path earn?* They are not forecasts of real-world outcomes.

Viability \(v_i\) blends, roughly:

- fitness EMA (learned performance),  
- stability,  
- weight (presence),  
- generational depth,  
- a **scarcity stress** term so fragile paths lose support when the organism is hungry or overcrowded.

### 3. Learning loop — think → act → score → metabolize

Each cycle a policy spends computational energy to **think** (choose an action: observe, mutate, branch, interact, rewrite, stabilize), then:

\[
r \in [-1, 1]
\]

is a fitness reward from stability, diversity, goal alignment, paradox penalties, and energy efficiency — plus homeostasis pressure (punish reckless branching when the body is in crisis; reward steadying).

Metabolism closes the loop:

\[
W \leftarrow W \cdot e^{\eta\, r \cdot \ldots}
\]

Positive reward can refund energy; coefficients \(g, d\) nudge; fitness EMA updates. **Trying changes the organism.** That is the learning.

### 4. Homeostasis — survival as a control law

Health is a weighted blend of stability, diversity, energy headroom, population headroom, paradox load, and memory headroom. Stress produces a throttle \(\tau_{\mathrm{meta}} \in [0,1]\) that slows thinking and branching, accelerates rest regen, and archives weak lines. Modes move:

`thrive` → `balance` → `conserve` → `crisis`

So the multiverse remains a **bounded living system**, not an infinite spreadsheet.

---

## Real-life usage examples

Use Chronos when you want structure for choices that feel like many worlds — not when you want a crystal ball.

### Personal decisions
| Situation | How to use Chronos |
|-----------|-------------------|
| **Stay vs leave** (job, city, relationship) | Decision Counsel with 2–3 named paths; let generations run; read relative shares *and* the margin (close races stay “tentative”) |
| **Letting go** | One path = keep feeding the hope; one = archive it but keep the lessons; one = pause. Watch which lineage stays viable under scarcity |
| **“Can I do both?”** | Raise concurrent branches / interactions in the Lab until health/throttle protest — a visceral lesson in overcommitment |
| **Reinterpreting the past** | Rewrite a key event on one timeline; compare stability vs the untouched parent — practice changing the *story* |

### Strategy & consulting workshops
| Situation | How to use Chronos |
|-----------|-------------------|
| **Portfolio / WIP overload** | Demo homeostasis: expansion until soft/hard caps; weak initiatives archived; discuss real kill-criteria |
| **Conflicting requirements** | Induce paradoxes; walk the four resolutions (isolate, fork, correct, preserve) as stakeholder strategies |
| **Policy A/B** | Same seed, two Lab configs (aggressive vs conservative); snapshot both; compare health and decision shares |
| **Decision theater** | Project Decision Counsel live; capture snapshots `before` / `after` for the workshop record |

### Learning & research demos
| Situation | How to use Chronos |
|-----------|-------------------|
| **Teach adaptive systems** | Show open-loop growth vs reward-shaped metabolism vs homeostasis in one running organism |
| **Show responsible AI** | Point at disclaimers: fiction events, relative shares ≠ life odds; human remains the decider |
| **Prototype “Phase B”** | Argue where an LLM would plug in (propose actions) while Chronos keeps fitness, energy, and selection |

**Suggested 15-minute personal ritual:** write one sentence decision → Counsel with 3 options → run to completion → note recommendation *and* whether the race was close → decide offline, on your own authority.

---

## Why this repo exists

This project is a **portfolio artifact** for AI engineering / consulting work: it shows how to take an ambitious brief and ship a working system with clear architecture, tests, and ethical boundaries.

| Consulting signal | How Chronos demonstrates it |
|-------------------|-----------------------------|
| Translate vague vision → executable architecture | 15+ independent engines behind documented interfaces |
| Full-stack delivery | Python sim + FastAPI/WebSocket + React/Three.js + SQLite |
| Adaptive systems design | Fitness loop, homeostasis, resource metabolism |
| Responsible product language | Explicit non-prediction disclaimers on weights & counsel |
| Operability | Pause/resume, snapshots, recovery, one-command start |
| Quality bar | Automated tests for core temporal & learning mechanics |

---

## Demo in 60 seconds

```bash
chmod +x start.sh && ./start.sh
```

Open **http://127.0.0.1:8000**

1. **Living Universe** — watch wireframe timelines branch and pulse.  
2. **Decision Counsel** — enter a real dilemma + 2–6 options; let paths compete; read the recommendation.  
3. **Organism Health** — see throttle/mode as the body self-regulates under load.  
4. Close the browser — the organism **keeps evolving** while the backend runs.

```bash
./start.sh dev   # Vite UI :5173 + API :8000
```

---

## What it does

### Core organism
- Continuous simulation loop (sim-time ≠ wall-clock)
- Timeline **branching**, **rewriting** (versioned history), **cross-timeline interaction**
- Exponential growth/decay with capacity pressure: \(W(t) = W_0 \cdot e^{(g-d)t}\)
- Causal conflict → **paradox detection** + four resolution strategies
- Convergence, autonomous seeded events, SQLite persistence & snapshots

### Learning (Phase A)
Think → act → score → metabolize:

- ε-greedy **policy** over observe / mutate / branch / interact / rewrite / stabilize  
- **Fitness** rewards stability, diversity, goal alignment; penalizes paradoxes & waste  
- Rewards reshape weight, coefficients, and energy refunds  

### Homeostasis (self-sustaining)
The organism is designed to **survive indefinitely**, not boom-and-crash:

- Metabolic **throttle** from energy / population / memory / health stress  
- Rest when hungry; hard/soft population caps; archive weak lineages  
- Modes: `thrive` → `balance` → `conserve` → `crisis`

### Decision Counsel
Interactive deliberation for life (or strategy) decisions:

1. State a problem and candidate paths  
2. Chronos seeds competing lineages and evolves them  
3. **Relative viability shares** update each cycle (softmax of simulated fitness/stability/weight under scarcity)  
4. After enough generations — or on demand — Chronos **recommends a path** with rationale  

> **Responsible framing:** shares are *not* real-world probabilities. They are relative support **inside the simulation**. The human decides.

---

## Screens

| Screen | Purpose |
|--------|---------|
| **Living Universe** | Immersive wireframe 3D multiverse + live controls |
| **Decision Counsel** | Problem in → competing paths → recommendation |
| **Timeline Explorer** | Genealogy, events, versions, divergence |
| **Temporal Observatory** | Paradoxes, rewrites, interactions, reward stream |
| **Organism Health** | Population, metabolism, throttle, fitness |
| **Simulation Laboratory** | Speed, seeds, budgets, homeostasis & learning knobs |

---

## Architecture

```
chronos/
├── backend/app/
│   ├── engines/       # Registry, genesis, branch, growth/decay, causality,
│   │                  # paradoxes, fitness, policy, homeostasis, decision…
│   ├── models/        # Timeline, paradox, organism, learning, decision
│   ├── simulation/    # Autonomous controller (UI-independent)
│   ├── persistence/   # SQLite autosave, snapshots, migrations
│   ├── api/           # REST control & inspection
│   └── websocket/     # Live organism broadcast
├── frontend/src/
│   ├── viz/           # React Three Fiber multiverse
│   ├── screens/       # Six product surfaces
│   ├── store/         # Zustand
│   └── api/           # REST + WebSocket client
├── backend/tests/     # Core · learning · homeostasis · decision
├── data/              # Local SQLite (gitignored)
└── start.sh           # One-command local launch
```

**Design principle:** the simulation engine is independent of the visual interface. Disconnect the UI; the organism continues.

### Stack

| Layer | Choice |
|-------|--------|
| Simulation | Python, NumPy |
| API | FastAPI, WebSockets |
| Persistence | SQLite (aiosqlite), WAL |
| UI | React 18, TypeScript, Vite, Zustand |
| 3D | Three.js, React Three Fiber, Drei |

**No cloud runtime dependency. No paid APIs required.**

---

## Quick start

### Requirements
- Python **3.10+**
- Node.js **18+** (build / dev)
- Local disk for SQLite

### One command
```bash
chmod +x start.sh
./start.sh        # builds UI if needed, serves everything on :8000
./start.sh dev    # hot-reload frontend + API
```

### Manual

**Backend**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev       # http://127.0.0.1:5173 (proxies /api and /ws)
npm run build     # dist/ served by FastAPI in production mode
```

### Tests
```bash
cd backend && source .venv/bin/activate
pytest tests/ -v
```

---

## API (sketch)

| Endpoint | Role |
|----------|------|
| `GET /api/state` | Live organism snapshot |
| `GET /api/organism` · `/homeostasis` · `/learning` | Vitals |
| `POST /api/decision/start` | Begin deliberation |
| `GET /api/decision` | Active session + shares |
| `POST /api/decision/{id}/conclude` | Force recommendation |
| `POST /api/control/{pause,resume,reset,speed}` | Runtime control |
| `POST /api/persistence/{save,snapshot}` | Durability |
| `WS /ws` | Streaming state for custom clients |

Interactive docs when the server is up: `http://127.0.0.1:8000/docs`

---

## Temporal mechanisms

| Mechanism | Behavior |
|-----------|----------|
| **Branching** | Parent preserved; child inherits history; divergence recorded |
| **Rewriting** | Prior event versions kept; causal ripple; audit trail |
| **Interaction** | Influence transfer; feedback-loop prevention |
| **Paradox resolution** | Isolation · auto-branch · causal correction · preservation |

---

## Configuration highlights

Tunable in **Simulation Laboratory** or `POST /api/config`:

- `random_seed` — reproducibility  
- Growth / decay / branching / interaction rates  
- Resource budgets & timeline capacity  
- `learning_enabled`, `learning_rate`, `think_cost`  
- Homeostasis soft/hard population & energy rest thresholds  
- Paradox default strategy  

Data: `data/chronos.db` · Logs: `logs/chronos.log`

---

## Engineering notes (for reviewers)

- **Modular engines** with narrow responsibilities — easy to extend (e.g. LLM policy as Phase B cognition).  
- **Bounded growth**: population caps, memory archival, WebSocket throttling, instanced rendering.  
- **Graceful shutdown** with final autosave; restart recovery from SQLite.  
- **Tests** cover branching, rewriting, growth/decay, paradoxes (all four resolutions), persistence, learning, homeostasis, and decision counsel.

---

## Responsible use

Chronos is an **experimental simulation and deliberation aid**.

- Timeline events are **fiction generated by rules**, not facts about history.  
- Weights and Decision Counsel shares are **relative simulated influence**, not forecasts of real outcomes.  
- Do not use outputs as medical, legal, financial, or psychological advice.  
- You remain accountable for decisions you make after using the tool.

---

## Roadmap ideas

- [ ] LLM-backed policy proposals on the same fitness/metabolism substrate (Phase B)  
- [ ] Export deliberation reports (Markdown/PDF) for workshops  
- [ ] Path-colored 3D highlighting during Decision Counsel  
- [ ] Optional Docker Compose one-liner for demos  

---

## License

Released under the [MIT License](./LICENSE) — use, fork, and demo freely; attribution appreciated.

---

## Author

Built as a **working systems demo** for AI development & consulting engagements: ambitious product narrative, disciplined architecture, local operability, and honest AI boundaries.

If you’re evaluating collaboration — clone it, run `./start.sh`, open Decision Counsel, and stress the organism in the Laboratory. The code is the pitch.
