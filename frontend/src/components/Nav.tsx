import { useChronosStore } from "../store/useChronosStore";
import type { ScreenId } from "../types";

const SCREENS: { id: ScreenId; label: string }[] = [
  { id: "universe", label: "Living Universe" },
  { id: "counsel", label: "Decision Counsel" },
  { id: "explorer", label: "Timeline Explorer" },
  { id: "observatory", label: "Temporal Observatory" },
  { id: "health", label: "Organism Health" },
  { id: "laboratory", label: "Simulation Laboratory" },
];

export function Nav() {
  const screen = useChronosStore((s) => s.screen);
  const setScreen = useChronosStore((s) => s.setScreen);
  const connected = useChronosStore((s) => s.connected);
  const simState = useChronosStore((s) => s.simState);
  const simTime = useChronosStore((s) => s.simTime);

  return (
    <header className="chronos-nav">
      <div className="brand">
        <span className="brand-mark">CHRONOS</span>
        <span className="brand-sub">living multiverse</span>
      </div>
      <nav className="nav-screens">
        {SCREENS.map((s) => (
          <button
            key={s.id}
            className={screen === s.id ? "nav-btn active" : "nav-btn"}
            onClick={() => setScreen(s.id)}
          >
            {s.label}
          </button>
        ))}
      </nav>
      <div className="nav-status">
        <span className={`pulse-dot ${connected ? "on" : "off"}`} />
        <span className="mono">
          {simState} · t={simTime.toFixed(1)}
        </span>
      </div>
    </header>
  );
}
