import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { Paradox, Timeline } from "../types";

interface Props {
  paradoxes: Paradox[];
  timelines: Timeline[];
}

export function ParadoxAnomalies({ paradoxes, timelines }: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const byId = new Map(timelines.map((t) => [t.id, t]));

  const unresolved = paradoxes.filter(
    (p) => p.status === "detected" || p.status === "resolving" || p.status === "preserved"
  );

  useFrame(({ clock }) => {
    const g = groupRef.current;
    if (!g) return;
    const t = clock.getElapsedTime();
    g.children.forEach((child, i) => {
      child.rotation.y = t * (1.5 + i * 0.2);
      child.rotation.x = Math.sin(t * 2 + i) * 0.4;
      const s = 0.6 + 0.3 * Math.sin(t * 5 + i);
      child.scale.setScalar(s);
    });
  });

  return (
    <group ref={groupRef}>
      {unresolved.map((p) => {
        const tl = byId.get(p.affected_timeline_ids[0]);
        if (!tl) return null;
        const pos = tl.position;
        return (
          <mesh key={p.id} position={[pos[0], pos[1] + 0.8, pos[2]]}>
            <octahedronGeometry args={[0.35, 0]} />
            <meshStandardMaterial
              color="#ff1744"
              emissive="#ff1744"
              emissiveIntensity={2}
              wireframe
              toneMapped={false}
              transparent
              opacity={0.85}
            />
          </mesh>
        );
      })}
    </group>
  );
}
