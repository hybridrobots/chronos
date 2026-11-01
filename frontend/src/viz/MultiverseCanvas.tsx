import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  Stars,
  AdaptiveDpr,
  AdaptiveEvents,
} from "@react-three/drei";
import { useChronosStore } from "../store/useChronosStore";
import { TimelineNodes } from "./TimelineNodes";
import { Filaments } from "./Filaments";
import { CosmicDust, EventSparks } from "./Particles";
import { ParadoxAnomalies } from "./ParadoxAnomalies";

function SceneContent() {
  const timelines = useChronosStore((s) => s.timelines);
  const relationships = useChronosStore((s) => s.relationships);
  const paradoxes = useChronosStore((s) => s.paradoxes);

  const visible = useMemo(
    () => timelines.filter((t) => !t.archived).slice(0, 400),
    [timelines]
  );

  return (
    <>
      <color attach="background" args={["#03050a"]} />
      <fog attach="fog" args={["#03050a", 25, 90]} />

      <ambientLight intensity={0.15} />
      <pointLight position={[10, 15, 10]} intensity={0.8} color="#26c6da" />
      <pointLight position={[-12, -8, -10]} intensity={0.5} color="#7c4dff" />
      <pointLight position={[0, 5, -15]} intensity={0.35} color="#e040fb" />

      <Stars
        radius={80}
        depth={40}
        count={2500}
        factor={3}
        saturation={0.4}
        fade
        speed={0.3}
      />

      <CosmicDust timelines={visible} />
      <Filaments timelines={visible} relationships={relationships} />
      <TimelineNodes timelines={visible} />
      <EventSparks timelines={visible} />
      <ParadoxAnomalies paradoxes={paradoxes} timelines={visible} />

      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={3}
        maxDistance={80}
        autoRotate
        autoRotateSpeed={0.25}
      />

      <AdaptiveDpr pixelated />
      <AdaptiveEvents />
    </>
  );
}

export function MultiverseCanvas() {
  return (
    <div className="multiverse-canvas">
      <Canvas
        camera={{ position: [12, 8, 16], fov: 50, near: 0.1, far: 200 }}
        dpr={[1, 1.75]}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
        }}
      >
        <Suspense fallback={null}>
          <SceneContent />
        </Suspense>
      </Canvas>
    </div>
  );
}
