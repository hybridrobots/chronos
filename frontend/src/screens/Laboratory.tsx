import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useChronosStore } from "../store/useChronosStore";

type Field =
  | { key: string; label: string; min: number; max: number; step: number }
  | { key: string; label: string; type: "int" }
  | { key: string; label: string; type: "bool" }
  | { key: string; label: string; type: "select"; options: string[] };

const FIELDS: Field[] = [
  { key: "speed", label: "Simulation speed", min: 0.1, max: 20, step: 0.1 },
  { key: "default_growth", label: "Default growth", min: 0.001, max: 0.3, step: 0.001 },
  { key: "default_decay", label: "Default decay", min: 0, max: 0.2, step: 0.001 },
  { key: "base_branch_probability", label: "Branching probability", min: 0.01, max: 0.5, step: 0.01 },
  { key: "event_rate", label: "Event rate", min: 0, max: 1, step: 0.05 },
  { key: "interaction_rate", label: "Interaction rate", min: 0, max: 1, step: 0.05 },
  { key: "interaction_strength", label: "Interaction strength", min: 0.05, max: 1, step: 0.05 },
  { key: "convergence_rate", label: "Convergence rate", min: 0, max: 0.5, step: 0.01 },
  { key: "max_timelines", label: "Max timelines", type: "int" },
  { key: "timeline_capacity", label: "Timeline capacity", type: "int" },
  { key: "max_energy", label: "Max energy", type: "int" },
  { key: "branching_budget", label: "Branching budget", type: "int" },
  { key: "mutation_budget", label: "Mutation budget", type: "int" },
  { key: "interaction_budget", label: "Interaction budget", type: "int" },
  { key: "memory_capacity", label: "Memory capacity", type: "int" },
  { key: "random_seed", label: "Random seed", type: "int" },
  {
    key: "default_resolution_strategy",
    label: "Default paradox resolution",
    type: "select",
    options: ["isolation", "auto_branch", "causal_correction", "preservation"],
  },
  { key: "auto_resolve", label: "Auto-resolve paradoxes", type: "bool" },
  { key: "learning_enabled", label: "Learning / fitness loop", type: "bool" },
  { key: "learning_rate", label: "Learning rate", min: 0.01, max: 0.5, step: 0.01 },
  { key: "think_cost", label: "Think energy cost", min: 0.5, max: 5, step: 0.1 },
  { key: "max_thinks_per_cycle", label: "Max thinks / cycle", type: "int" },
  { key: "policy_exploration", label: "Policy exploration ε", min: 0, max: 0.8, step: 0.05 },
  { key: "open_loop_growth_blend", label: "Open-loop growth blend", min: 0, max: 1, step: 0.05 },
  { key: "goal_stability_target", label: "Goal stability", min: 0.2, max: 1, step: 0.05 },
  { key: "goal_complexity_target", label: "Goal complexity", min: 0.5, max: 5, step: 0.1 },
  { key: "homeostasis_enabled", label: "Homeostasis (self-sustain)", type: "bool" },
  { key: "homeostasis_health_target", label: "Health target", min: 0.4, max: 0.95, step: 0.01 },
  { key: "energy_rest_threshold", label: "Energy rest threshold", min: 0.15, max: 0.7, step: 0.05 },
  { key: "homeostasis_soft_pop_ratio", label: "Soft population cap", min: 0.3, max: 0.9, step: 0.05 },
  { key: "homeostasis_hard_pop_ratio", label: "Hard population cap", min: 0.5, max: 1, step: 0.05 },
  { key: "homeostasis_memory_soft_ratio", label: "Memory soft cap", min: 0.4, max: 0.95, step: 0.05 },
];

export function Laboratory() {
  const config = useChronosStore((s) => s.config);
  const [local, setLocal] = useState<Record<string, unknown>>({});
  const [snapshots, setSnapshots] = useState<
    { id: number; name: string; sim_time: number; created_at: number }[]
  >([]);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    setLocal({ ...config });
  }, [config]);

  useEffect(() => {
    api.listSnapshots().then((s) => setSnapshots(s as typeof snapshots));
  }, []);

  const setField = (key: string, value: unknown) =>
    setLocal((prev) => ({ ...prev, [key]: value }));

  const apply = async () => {
    await api.updateConfig(local);
    if (typeof local.speed === "number") await api.setSpeed(local.speed as number);
    setMsg("Configuration applied to the living organism.");
  };

  return (
    <section className="screen panel-screen">
      <header className="screen-header">
        <h1>Simulation Laboratory</h1>
        <p>Tune metabolism, mutation, branching, resources, and paradox policy.</p>
      </header>
      <div className="lab-layout">
        <div className="obs-card lab-form">
          {FIELDS.map((f) => {
            const val = local[f.key];
            if ("type" in f && f.type === "bool") {
              return (
                <label key={f.key} className="lab-field checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(val)}
                    onChange={(e) => setField(f.key, e.target.checked)}
                  />
                  {f.label}
                </label>
              );
            }
            if ("type" in f && f.type === "select") {
              return (
                <label key={f.key} className="lab-field">
                  {f.label}
                  <select
                    value={String(val ?? "")}
                    onChange={(e) => setField(f.key, e.target.value)}
                  >
                    {f.options.map((o) => (
                      <option key={o} value={o}>
                        {o}
                      </option>
                    ))}
                  </select>
                </label>
              );
            }
            if ("type" in f && f.type === "int") {
              return (
                <label key={f.key} className="lab-field">
                  {f.label}
                  <input
                    type="number"
                    value={Number(val ?? 0)}
                    onChange={(e) => setField(f.key, parseInt(e.target.value, 10))}
                  />
                </label>
              );
            }
            if ("min" in f) {
              return (
                <label key={f.key} className="lab-field">
                  {f.label}: {Number(val ?? 0).toFixed(3)}
                  <input
                    type="range"
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    value={Number(val ?? 0)}
                    onChange={(e) => setField(f.key, parseFloat(e.target.value))}
                  />
                </label>
              );
            }
            return null;
          })}
          <div className="control-row">
            <button onClick={apply}>Apply</button>
            <button onClick={() => api.save()}>Save Now</button>
            <button
              onClick={async () => {
                await api.snapshot(`lab-${Date.now()}`);
                const s = await api.listSnapshots();
                setSnapshots(s as typeof snapshots);
                setMsg("Snapshot created.");
              }}
            >
              Create Snapshot
            </button>
            <button
              className="danger"
              onClick={() => {
                const seed = Number(local.random_seed ?? 42);
                if (confirm(`Reset organism with seed ${seed}?`)) {
                  api.reset(seed);
                }
              }}
            >
              Reset with Seed
            </button>
          </div>
          {msg && <p className="msg">{msg}</p>}
        </div>
        <div className="obs-card">
          <h3>Snapshots</h3>
          <ul className="event-list tall">
            {snapshots.map((s) => (
              <li key={s.id}>
                <span>{s.name}</span>
                <span className="mono">t={s.sim_time.toFixed(1)}</span>
                <button
                  className="mini"
                  onClick={() => api.restore(s.id).then(() => setMsg("Restored."))}
                >
                  Restore
                </button>
              </li>
            ))}
            {snapshots.length === 0 && (
              <li className="muted">No snapshots yet.</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
