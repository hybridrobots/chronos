import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useChronosStore } from "../store/useChronosStore";

interface PathForm {
  label: string;
  description: string;
}

interface DecisionPath {
  id: string;
  label: string;
  description: string;
  relative_share: number;
  viability: number;
  viability_ema: number;
  mean_stability: number;
  mean_fitness: number;
  generation_depth: number;
  sample_count: number;
}

interface DecisionSession {
  id: string;
  problem: string;
  context: string;
  status: string;
  paths: DecisionPath[];
  target_generations: number;
  target_cycles: number;
  cycles_done: number;
  max_generation_seen: number;
  progress: number;
  recommendation_path_id: string | null;
  recommendation_summary: string;
  disclaimer: string;
}

const EMPTY_PATHS: PathForm[] = [
  { label: "", description: "" },
  { label: "", description: "" },
];

export function DecisionCounsel() {
  const cycleDecision = useChronosStore(
    (s) => (s.cycleStats as { decision?: DecisionSession })?.decision
  );
  const [problem, setProblem] = useState("");
  const [context, setContext] = useState("");
  const [paths, setPaths] = useState<PathForm[]>(EMPTY_PATHS);
  const [generations, setGenerations] = useState(5);
  const [cycles, setCycles] = useState(60);
  const [session, setSession] = useState<DecisionSession | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = (await api.decision()) as {
        active: DecisionSession | null;
      };
      if (data.active) setSession(data.active);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    if (cycleDecision?.id) setSession(cycleDecision);
  }, [cycleDecision]);

  const updatePath = (i: number, patch: Partial<PathForm>) => {
    setPaths((prev) => prev.map((p, idx) => (idx === i ? { ...p, ...patch } : p)));
  };

  const start = async () => {
    setError("");
    setBusy(true);
    try {
      const cleaned = paths.filter((p) => p.label.trim());
      const started = (await api.startDecision({
        problem,
        context,
        paths: cleaned,
        target_generations: generations,
        target_cycles: cycles,
        seeds_per_path: 2,
        stress_tested: true,
      })) as unknown as DecisionSession;
      setSession(started);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const conclude = async () => {
    if (!session) return;
    setBusy(true);
    try {
      const done = (await api.concludeDecision(
        session.id
      )) as unknown as DecisionSession;
      setSession(done);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!session) return;
    setBusy(true);
    try {
      await api.cancelDecision(session.id);
      setSession(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const recommended = session?.paths.find(
    (p) => p.id === session.recommendation_path_id
  );

  return (
    <section className="screen panel-screen">
      <header className="screen-header">
        <h1>Decision Counsel</h1>
        <p>
          Describe a real decision. Chronos grows competing paths, scores relative
          viability across generations, then recommends — as a simulated mirror,
          not a prophecy.
        </p>
      </header>

      <div className="lab-layout">
        <div className="obs-card lab-form" style={{ gridTemplateColumns: "1fr" }}>
          <label className="lab-field">
            Your problem / decision
            <textarea
              rows={3}
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              placeholder="e.g. Should I leave this job for a riskier path that fits me better?"
              style={{
                background: "rgba(0,0,0,0.35)",
                border: "1px solid var(--border)",
                padding: "0.5rem",
                color: "inherit",
                resize: "vertical",
              }}
            />
          </label>
          <label className="lab-field">
            Context (optional)
            <textarea
              rows={2}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Constraints: money, health, people who matter, season of life…"
              style={{
                background: "rgba(0,0,0,0.35)",
                border: "1px solid var(--border)",
                padding: "0.5rem",
                color: "inherit",
                resize: "vertical",
              }}
            />
          </label>

          <div>
            <div className="meter-label" style={{ marginBottom: "0.5rem" }}>
              <span>Paths / options</span>
              <button
                type="button"
                className="mini"
                onClick={() =>
                  setPaths((p) =>
                    p.length >= 6 ? p : [...p, { label: "", description: "" }]
                  )
                }
              >
                + path
              </button>
            </div>
            {paths.map((p, i) => (
              <div key={i} style={{ marginBottom: "0.75rem" }}>
                <input
                  placeholder={`Option ${i + 1} label`}
                  value={p.label}
                  onChange={(e) => updatePath(i, { label: e.target.value })}
                  style={{
                    width: "100%",
                    marginBottom: "0.35rem",
                    background: "rgba(0,0,0,0.35)",
                    border: "1px solid var(--border)",
                    padding: "0.4rem 0.5rem",
                    color: "inherit",
                  }}
                />
                <input
                  placeholder="Short description (optional)"
                  value={p.description}
                  onChange={(e) => updatePath(i, { description: e.target.value })}
                  style={{
                    width: "100%",
                    background: "rgba(0,0,0,0.35)",
                    border: "1px solid var(--border)",
                    padding: "0.4rem 0.5rem",
                    color: "inherit",
                  }}
                />
              </div>
            ))}
          </div>

          <div className="control-row">
            <label className="lab-field" style={{ flex: 1 }}>
              Generations to wait: {generations}
              <input
                type="range"
                min={3}
                max={10}
                value={generations}
                onChange={(e) => setGenerations(parseInt(e.target.value, 10))}
              />
            </label>
            <label className="lab-field" style={{ flex: 1 }}>
              Sim cycles: {cycles}
              <input
                type="range"
                min={30}
                max={200}
                step={10}
                value={cycles}
                onChange={(e) => setCycles(parseInt(e.target.value, 10))}
              />
            </label>
          </div>

          <div className="control-row">
            <button disabled={busy} onClick={start}>
              Begin deliberation
            </button>
            {session?.status === "running" && (
              <>
                <button disabled={busy} onClick={conclude}>
                  Recommend now
                </button>
                <button className="danger" disabled={busy} onClick={cancel}>
                  Cancel
                </button>
              </>
            )}
          </div>
          {error && <p className="msg" style={{ color: "var(--danger)" }}>{error}</p>}
          <p className="muted" style={{ gridColumn: "1 / -1" }}>
            Relative shares are softmax-normalized viability inside the organism
            (fitness, stability, weight, scarcity stress). They are not chances
            that a choice will succeed in the real world.
          </p>
        </div>

        <div className="obs-card">
          {!session ? (
            <p className="muted">
              No active deliberation. Enter a problem and at least two options.
            </p>
          ) : (
            <>
              <h3>
                {session.status === "complete" ? "Recommendation" : "Deliberating…"}
              </h3>
              <p style={{ color: "var(--text-dim)", marginTop: 0 }}>
                {session.problem}
              </p>
              <div className="meter" style={{ marginBottom: "1rem" }}>
                <div className="meter-label">
                  <span>Progress</span>
                  <span className="mono">
                    gen {session.max_generation_seen}/{session.target_generations} ·
                    cyc {session.cycles_done}/{session.target_cycles}
                  </span>
                </div>
                <div className="meter-track">
                  <div
                    className="meter-fill"
                    style={{ width: `${Math.min(100, session.progress * 100)}%` }}
                  />
                </div>
              </div>

              <ul className="event-list tall">
                {[...session.paths]
                  .sort((a, b) => b.relative_share - a.relative_share)
                  .map((p) => (
                    <li key={p.id}>
                      <strong
                        style={{
                          color:
                            p.id === session.recommendation_path_id
                              ? "var(--cyan-bright)"
                              : "inherit",
                        }}
                      >
                        {p.label}
                      </strong>
                      <span className="mono">
                        {(p.relative_share * 100).toFixed(1)}% share
                      </span>
                      <span>viab {p.viability_ema.toFixed(3)}</span>
                      <span>stab {p.mean_stability.toFixed(2)}</span>
                      <span>depth {p.generation_depth}</span>
                      <div className="meter-track" style={{ width: "100%", marginTop: 4 }}>
                        <div
                          className="meter-fill"
                          style={{ width: `${p.relative_share * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
              </ul>

              {session.status === "complete" && (
                <div
                  style={{
                    marginTop: "1rem",
                    padding: "0.85rem",
                    border: "1px solid var(--cyan)",
                    background: "rgba(0, 229, 255, 0.06)",
                  }}
                >
                  {recommended && (
                    <div
                      className="brand-mark"
                      style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}
                    >
                      → {recommended.label}
                    </div>
                  )}
                  <p style={{ margin: 0, lineHeight: 1.5 }}>
                    {session.recommendation_summary}
                  </p>
                </div>
              )}
              <p className="muted" style={{ marginTop: "1rem", fontSize: "0.75rem" }}>
                {session.disclaimer}
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
