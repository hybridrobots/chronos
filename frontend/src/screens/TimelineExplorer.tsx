import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useChronosStore } from "../store/useChronosStore";
import type { Timeline, TimelineEvent } from "../types";

export function TimelineExplorer() {
  const timelines = useChronosStore((s) => s.timelines);
  const selectedId = useChronosStore((s) => s.selectedTimelineId);
  const selectTimeline = useChronosStore((s) => s.selectTimeline);
  const [detail, setDetail] = useState<Timeline | null>(null);
  const [history, setHistory] = useState<TimelineEvent[]>([]);
  const [genealogy, setGenealogy] = useState<Record<string, unknown> | null>(
    null
  );

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setHistory([]);
      setGenealogy(null);
      return;
    }
    api.getTimeline(selectedId).then((d) => setDetail(d as unknown as Timeline));
    api.getHistory(selectedId).then((h) => setHistory(h as TimelineEvent[]));
    api
      .getGenealogy(selectedId)
      .then((g) => setGenealogy(g))
      .catch(() => setGenealogy(null));
  }, [selectedId]);

  const sorted = [...timelines].sort((a, b) => a.generation - b.generation);

  return (
    <section className="screen panel-screen">
      <header className="screen-header">
        <h1>Timeline Explorer</h1>
        <p>Genealogy, historical events, divergence, and versioned memory.</p>
      </header>
      <div className="split-view">
        <aside className="tl-list">
          {sorted.map((t) => (
            <button
              key={t.id}
              className={
                selectedId === t.id ? "tl-item selected" : "tl-item"
              }
              onClick={() => selectTimeline(t.id)}
            >
              <span className={`badge status-${t.status}`}>{t.status}</span>
              <span className="mono">{t.id.slice(0, 8)}</span>
              <span>gen {t.generation}</span>
              <span>w={t.current_weight.toFixed(2)}</span>
            </button>
          ))}
        </aside>
        <div className="tl-detail">
          {!detail ? (
            <p className="muted">Select a timeline to inspect its lineage.</p>
          ) : (
            <>
              <h2>
                {detail.id.slice(0, 8)}{" "}
                <span className={`status-${detail.status}`}>
                  {detail.status}
                </span>
              </h2>
              <div className="meta-row">
                <span>Parent: {detail.parent_id?.slice(0, 8) ?? "— origin —"}</span>
                <span>Version: {detail.historical_version}</span>
                <span>Born t={detail.simulation_birth_time.toFixed(1)}</span>
              </div>
              {genealogy && (
                <div className="genealogy-box">
                  <h3>Genealogy</h3>
                  <pre className="mono small">
                    {JSON.stringify(genealogy, null, 2)}
                  </pre>
                </div>
              )}
              <h3>Historical Events ({history.length})</h3>
              <ul className="event-list tall">
                {history.map((e) => (
                  <li key={e.id} className={e.is_active ? "" : "archived"}>
                    <span className="evt-type">{e.event_type}</span>
                    <span className="mono">t={e.simulation_time.toFixed(1)}</span>
                    <span>{e.description}</span>
                    {!e.is_active && <span className="tag">archived/v{e.version}</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
