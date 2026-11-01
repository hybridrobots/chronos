import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { Timeline } from "../types";
import { statusColor, statusEmissiveIntensity } from "./colors";
import { useChronosStore } from "../store/useChronosStore";

interface Props {
  timelines: Timeline[];
}

export function TimelineNodes({ timelines }: Props) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const selectTimeline = useChronosStore((s) => s.selectTimeline);
  const selectedId = useChronosStore((s) => s.selectedTimelineId);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);

  const count = Math.min(timelines.length, 500);

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const t = clock.getElapsedTime();

    for (let i = 0; i < count; i++) {
      const tl = timelines[i];
      const [x, y, z] = tl.position;
      // Organic pulse based on weight & status
      const base = 0.15 + Math.min(1.2, Math.sqrt(tl.current_weight) * 0.25);
      const pulse =
        statusEmissiveIntensity(tl.status) *
        (1 + 0.08 * Math.sin(t * 2 + i * 0.7));
      const scale = base * (0.85 + 0.15 * pulse);
      const selected = tl.id === selectedId ? 1.4 : 1.0;

      dummy.position.set(x, y, z);
      dummy.scale.setScalar(scale * selected);
      dummy.rotation.set(t * 0.1 + i, t * 0.15, 0);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);

      color.set(statusColor(tl.status, tl.color_hue));
      if (tl.id === selectedId) color.offsetHSL(0, 0.1, 0.15);
      mesh.setColorAt(i, color);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  const handleClick = (e: { stopPropagation: () => void; instanceId?: number }) => {
    e.stopPropagation();
    const idx = e.instanceId;
    if (idx != null && timelines[idx]) {
      selectTimeline(timelines[idx].id);
    }
  };

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, count]}
      onClick={handleClick}
      frustumCulled={false}
    >
      <icosahedronGeometry args={[1, 2]} />
      <meshStandardMaterial
        wireframe
        toneMapped={false}
        roughness={0.2}
        metalness={0.35}
        emissive="#0a2030"
        emissiveIntensity={0.9}
        transparent
        opacity={0.9}
      />
    </instancedMesh>
  );
}
