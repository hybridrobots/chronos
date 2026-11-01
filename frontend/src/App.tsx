import { Nav } from "./components/Nav";
import { useWebSocket } from "./api/useWebSocket";
import { useChronosStore } from "./store/useChronosStore";
import { LivingUniverse } from "./screens/LivingUniverse";
import { TimelineExplorer } from "./screens/TimelineExplorer";
import { Observatory } from "./screens/Observatory";
import { OrganismHealth } from "./screens/OrganismHealth";
import { Laboratory } from "./screens/Laboratory";
import { DecisionCounsel } from "./screens/DecisionCounsel";

export default function App() {
  useWebSocket();
  const screen = useChronosStore((s) => s.screen);

  return (
    <div className="app-shell">
      <Nav />
      <main className="app-main">
        {screen === "universe" && <LivingUniverse />}
        {screen === "counsel" && <DecisionCounsel />}
        {screen === "explorer" && <TimelineExplorer />}
        {screen === "observatory" && <Observatory />}
        {screen === "health" && <OrganismHealth />}
        {screen === "laboratory" && <Laboratory />}
      </main>
    </div>
  );
}
