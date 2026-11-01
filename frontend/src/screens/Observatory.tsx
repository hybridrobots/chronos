import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useChronosStore } from "../store/useChronosStore";

export function Observatory() {
  const paradoxes = useChronosStore((s) => s.paradoxes);
  const learning = useChronosStore((s) => s.learning);
  const [obs, setObs] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.observatory().then(setObs).catch(() => setObs(null));
    const id = setInterval(() => {
      api.observatory().then(setObs).catch(() => undefined);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const alterations = (obs?.alterations as unknown[]) ?? [];
  const interactions = (obs?.interactions as unknown[]) ?? [];
  const convergences = (obs?.convergences as unknown[]) ?? [];

  return (
    <section className="screen panel-screen">
      <header className="screen-header">
        <h1>Temporal Observatory</h1>
        <p>Paradoxes, alterations, causal tension, interactions, convergences.</p>
      </header>
      <div className="grid-4">
        <div className="obs-card">
          <h3>Paradoxes ({paradoxes.length})</h3>
          <ul className="event-list tall">
            {paradoxes.map((p) => (
              <li key={p.id}>
                <span className={`badge status-${p.status}`}>{p.status}</span>
                <span>sev {p.severity.toFixed(2)}</span>
                <span>{p.description}</span>
                <div className="row-actions">
                  {["isolation", "auto_branch", "causal_correction", "preservation"].map(
                    (s) => (
                      <button
                        key={s}
                        className="mini"
                        onClick={() => api.resolveParadox(p.id, s)}
                      >
                        {s}
                      </button>
                    )
                  )}
                </div>
              </li>
            ))}
            {paradoxes.length === 0 && (
              <li className="muted">No paradoxes detected.</li>
            )}
          </ul>
        </div>
        <div className="obs-card">
          <h3>Alterations</h3>
          <ul className="event-list tall">
            {(alterations as Record<string, unknown>[]).map((a, i) => (
              <li key={i}>
                <span className="mono">{String(a.timeline_id).slice(0, 8)}</span>
                <span>{String(a.description)}</span>
              </li>
            ))}
            {alterations.length === 0 && (
              <li className="muted">No rewrites yet.</li>
            )}
          </ul>
        </div>
        <div className="obs-card">
          <h3>Interactions</h3>
          <ul className="event-list tall">
            {(interactions as Record<string, unknown>[]).map((a, i) => (
              <li key={i}>
                <span className="mono">
                  {String(a.source_id).slice(0, 6)}→{String(a.target_id).slice(0, 6)}
                </span>
                <span>str {(a.strength as number)?.toFixed?.(3)}</span>
              </li>
            ))}
            {interactions.length === 0 && (
              <li className="muted">No interactions yet.</li>
            )}
          </ul>
        </div>
        <div className="obs-card">
          <h3>Convergences</h3>
          <ul className="event-list tall">
            {(convergences as Record<string, unknown>[]).map((a, i) => (
              <li key={i}>
                <span className="mono">
                  {String(a.a).slice(0, 6)}≈{String(a.b).slice(0, 6)}
                </span>
                <span>sim {(a.similarity as number)?.toFixed?.(3)}</span>
              </li>
            ))}
            {convergences.length === 0 && (
              <li className="muted">No convergences yet.</li>
            )}
          </ul>
        </div>
        <div className="obs-card">
          <h3>Learning Rewards</h3>
          <dl className="inspect-grid" style={{ marginBottom: "0.75rem" }}>
            {Object.entries(learning?.action_stats ?? {}).map(([action, s]) => (
              <div key={action} style={{ display: "contents" }}>
                <dt>{action}</dt>
                <dd>
                  n={s.count.toFixed(0)} · μ={s.mean.toFixed(3)}
                </dd>
              </div>
            ))}
          </dl>
          <ul className="event-list tall">
            {(learning?.recent_rewards ?? []).slice().reverse().map((r, i) => (
              <li key={`${r.timeline_id}-${r.sim_time}-${i}`}>
                <span className="evt-type">{r.action}</span>
                <span className="mono">{r.timeline_id.slice(0, 6)}</span>
                <span>r={r.reward.toFixed(3)}</span>
              </li>
            ))}
            {(learning?.recent_rewards?.length ?? 0) === 0 && (
              <li className="muted">No reward traces yet.</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
