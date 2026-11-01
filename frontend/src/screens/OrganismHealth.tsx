import { useChronosStore } from "../store/useChronosStore";

function Meter({
  label,
  value,
  max = 1,
}: {
  label: string;
  value: number;
  max?: number;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="meter">
      <div className="meter-label">
        <span>{label}</span>
        <span className="mono">
          {value.toFixed(2)}
          {max !== 1 ? ` / ${max}` : ""}
        </span>
      </div>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function OrganismHealth() {
  const organism = useChronosStore((s) => s.organism);
  const timelines = useChronosStore((s) => s.timelines);
  if (!organism) return null;
  const r = organism.resources;

  const statusCounts: Record<string, number> = {};
  for (const t of timelines) {
    statusCounts[t.status] = (statusCounts[t.status] || 0) + 1;
  }

  return (
    <section className="screen panel-screen">
      <header className="screen-header">
        <h1>Organism Health</h1>
        <p>Metabolism, population, resources, stability, and structural vitality.</p>
      </header>
      <div className="health-layout">
        <div className="health-hero">
          <div className="health-ring">
            <span className="huge">{(organism.health * 100).toFixed(0)}</span>
            <span className="label">vitality</span>
          </div>
          <div className="stat-stack">
            <div>
              <span className="label">Age</span>
              <span className="value">{organism.age.toFixed(1)}</span>
            </div>
            <div>
              <span className="label">Cycles</span>
              <span className="value">{organism.cycle_count}</span>
            </div>
            <div>
              <span className="label">Depth</span>
              <span className="value">{organism.generation_depth}</span>
            </div>
            <div>
              <span className="label">Events</span>
              <span className="value">{organism.total_events}</span>
            </div>
          </div>
        </div>

        <div className="obs-card">
          <h3>Population</h3>
          <Meter
            label="Active timelines"
            value={organism.active_timeline_count}
            max={r.timeline_capacity}
          />
          <Meter label="Mean weight" value={organism.mean_weight} max={10} />
          <Meter label="Stability" value={organism.stability} />
          <Meter label="Diversity" value={organism.diversity} />
          <Meter
            label="Total complexity"
            value={organism.total_complexity}
            max={50}
          />
          <div className="status-chips">
            {Object.entries(statusCounts).map(([k, v]) => (
              <span key={k} className={`chip status-${k}`}>
                {k}: {v}
              </span>
            ))}
          </div>
        </div>

        <div className="obs-card">
          <h3>Metabolism / Resources</h3>
          <Meter
            label="Computational energy"
            value={r.computational_energy}
            max={r.max_energy}
          />
          <Meter
            label="Branching budget"
            value={r.branching_budget}
            max={r.max_branching_budget}
          />
          <Meter
            label="Mutation budget"
            value={r.mutation_budget}
            max={r.max_mutation_budget}
          />
          <Meter
            label="Interaction budget"
            value={r.interaction_budget}
            max={r.max_interaction_budget}
          />
          <Meter
            label="Memory used"
            value={r.memory_used}
            max={r.memory_capacity}
          />
        </div>

        <div className="obs-card">
          <h3>Activity Totals</h3>
          <dl className="inspect-grid">
            <dt>Branches</dt>
            <dd>{organism.total_branches}</dd>
            <dt>Interactions</dt>
            <dd>{organism.total_interactions}</dd>
            <dt>Convergences</dt>
            <dd>{organism.total_convergences}</dd>
            <dt>Paradoxes</dt>
            <dd>
              {organism.paradox_count} ({organism.unresolved_paradox_count} open)
            </dd>
            <dt>Mean growth</dt>
            <dd>{organism.mean_growth.toFixed(4)}</dd>
            <dt>Mean decay</dt>
            <dd>{organism.mean_decay.toFixed(4)}</dd>
          </dl>
        </div>

        <div className="obs-card">
          <h3>Homeostasis</h3>
          <Meter
            label="Metabolic throttle"
            value={organism.metabolic_throttle ?? 1}
          />
          <dl className="inspect-grid">
            <dt>Mode</dt>
            <dd>{organism.homeostasis_mode ?? "thrive"}</dd>
            <dt>Population</dt>
            <dd>
              {organism.active_timeline_count} / {r.timeline_capacity}
            </dd>
            <dt>Energy</dt>
            <dd>
              {r.computational_energy.toFixed(0)} / {r.max_energy}
            </dd>
            <dt>Memory</dt>
            <dd>
              {r.memory_used} / {r.memory_capacity}
            </dd>
          </dl>
        </div>

        <div className="obs-card">
          <h3>Learning / Fitness</h3>
          <Meter label="Mean fitness" value={organism.mean_fitness ?? 0} max={1} />
          <Meter
            label="Fitness EMA"
            value={(organism.mean_fitness_ema ?? 0) + 1}
            max={2}
          />
          <Meter label="Best fitness" value={(organism.best_fitness ?? 0) + 1} max={2} />
          <dl className="inspect-grid">
            <dt>Thinks</dt>
            <dd>{organism.total_thinks ?? 0}</dd>
            <dt>Learning cycles</dt>
            <dd>{organism.learning_cycles ?? 0}</dd>
            <dt>Total reward</dt>
            <dd>{(organism.total_reward ?? 0).toFixed(2)}</dd>
          </dl>
        </div>
      </div>
    </section>
  );
}
