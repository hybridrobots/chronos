import { api } from "../api/client";
import { useChronosStore } from "../store/useChronosStore";

export function SimControls() {
  const simState = useChronosStore((s) => s.simState);
  const speed = useChronosStore((s) => s.speed);
  const selected = useChronosStore((s) => s.selectedTimelineId);
  const timelines = useChronosStore((s) => s.timelines);
  const selectTimeline = useChronosStore((s) => s.selectTimeline);

  const tl = timelines.find((t) => t.id === selected);

  return (
    <div className="sim-controls">
      <div className="control-row">
        {simState === "running" ? (
          <button onClick={() => api.pause()}>Pause</button>
        ) : (
          <button onClick={() => api.resume()}>Resume</button>
        )}
        <button onClick={() => api.save()}>Save</button>
        <button
          onClick={() => {
            const name = `snap-${Date.now()}`;
            api.snapshot(name);
          }}
        >
          Snapshot
        </button>
        <button
          className="danger"
          onClick={() => {
            if (confirm("Reset the organism?")) api.reset();
          }}
        >
          Reset
        </button>
      </div>
      <div className="control-row">
        <label className="mono">
          Speed {speed.toFixed(1)}×
          <input
            type="range"
            min={0.1}
            max={10}
            step={0.1}
            value={speed}
            onChange={(e) => api.setSpeed(parseFloat(e.target.value))}
          />
        </label>
      </div>
      {tl && (
        <div className="inspect-panel">
          <div className="inspect-header">
            <strong>Timeline {tl.id.slice(0, 8)}</strong>
            <button className="ghost" onClick={() => selectTimeline(null)}>
              ×
            </button>
          </div>
          <dl className="inspect-grid">
            <dt>Status</dt>
            <dd className={`status-${tl.status}`}>{tl.status}</dd>
            <dt>Generation</dt>
            <dd>{tl.generation}</dd>
            <dt>Weight</dt>
            <dd>{tl.current_weight.toFixed(3)}</dd>
            <dt>Growth / Decay</dt>
            <dd>
              {tl.growth_coefficient.toFixed(3)} / {tl.decay_coefficient.toFixed(3)}
            </dd>
            <dt>Stability</dt>
            <dd>{tl.stability_score.toFixed(3)}</dd>
            <dt>Complexity</dt>
            <dd>{tl.structural_complexity.toFixed(3)}</dd>
            <dt>Events</dt>
            <dd>{tl.event_count ?? tl.recent_events?.length ?? 0}</dd>
            <dt>Fitness EMA</dt>
            <dd>{(tl.fitness_ema ?? 0).toFixed(3)}</dd>
            <dt>Last action / reward</dt>
            <dd>
              {tl.last_action ?? "—"} / {(tl.last_reward ?? 0).toFixed(3)}
            </dd>
            <dt>Thinks</dt>
            <dd>{tl.think_count ?? 0}</dd>
          </dl>
          {tl.recent_events && tl.recent_events.length > 0 && (
            <ul className="event-list">
              {tl.recent_events.map((e) => (
                <li key={e.id}>
                  <span className="evt-type">{e.event_type}</span>
                  <span>{e.description}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
