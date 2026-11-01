import { MultiverseCanvas } from "../viz/MultiverseCanvas";
import { SimControls } from "../components/SimControls";
import { useChronosStore } from "../store/useChronosStore";

export function LivingUniverse() {
  const organism = useChronosStore((s) => s.organism);
  const cycleStats = useChronosStore((s) => s.cycleStats);

  return (
    <section className="screen universe-screen">
      <MultiverseCanvas />
      <div className="universe-hud">
        <div className="hud-vitals">
          <div>
            <span className="label">Health</span>
            <span className="value">
              {((organism?.health ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div>
            <span className="label">Timelines</span>
            <span className="value">{organism?.active_timeline_count ?? 0}</span>
          </div>
          <div>
            <span className="label">Diversity</span>
            <span className="value">
              {((organism?.diversity ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div>
            <span className="label">Branches</span>
            <span className="value">
              {String(cycleStats?.branches ?? 0)}
            </span>
          </div>
          <div>
            <span className="label">Fitness</span>
            <span className="value">
              {((organism?.mean_fitness_ema ?? 0) * 100).toFixed(0)}
            </span>
          </div>
          <div>
            <span className="label">Thinks</span>
            <span className="value">{organism?.total_thinks ?? 0}</span>
          </div>
          <div>
            <span className="label">Mode</span>
            <span className="value">
              {organism?.homeostasis_mode ?? "thrive"}
            </span>
          </div>
          <div>
            <span className="label">Throttle</span>
            <span className="value">
              {((organism?.metabolic_throttle ?? 1) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        <SimControls />
      </div>
    </section>
  );
}
