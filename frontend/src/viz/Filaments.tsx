import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import type { Relationship, Timeline } from "../types";

interface Props {
  timelines: Timeline[];
  relationships: Relationship[];
}

function curvePoints(
  a: THREE.Vector3,
  b: THREE.Vector3,
  segments = 16
): [number, number, number][] {
  const mid = a.clone().lerp(b, 0.5);
  const dir = b.clone().sub(a);
  const perp = new THREE.Vector3(-dir.z, dir.y * 0.3, dir.x).normalize();
  mid.add(perp.multiplyScalar(dir.length() * 0.15));
  const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
  return curve.getPoints(segments).map((p) => [p.x, p.y, p.z]);
}

const REL_COLORS: Record<string, string> = {
  parent_child: "#26c6da",
  interaction: "#7c4dff",
  convergence: "#00e5ff",
  causal: "#448aff",
  paradox_link: "#ff1744",
};

export function Filaments({ timelines, relationships }: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const byId = useMemo(() => {
    const m = new Map<string, Timeline>();
    timelines.forEach((t) => m.set(t.id, t));
    return m;
  }, [timelines]);

  const lines = useMemo(() => {
    const result: {
      key: string;
      points: [number, number, number][];
      color: string;
      opacity: number;
    }[] = [];

    for (const tl of timelines) {
      if (!tl.parent_id) continue;
      const parent = byId.get(tl.parent_id);
      if (!parent) continue;
      const a = new THREE.Vector3(...parent.position);
      const b = new THREE.Vector3(...tl.position);
      result.push({
        key: `pc-${tl.id}`,
        points: curvePoints(a, b),
        color: REL_COLORS.parent_child,
        opacity: 0.35 + Math.min(0.4, tl.current_weight * 0.05),
      });
    }

    const limited = relationships
      .filter((r) => r.rel_type !== "parent_child")
      .slice(-120);
    for (const rel of limited) {
      const src = byId.get(rel.source_id);
      const tgt = byId.get(rel.target_id);
      if (!src || !tgt) continue;
      const a = new THREE.Vector3(...src.position);
      const b = new THREE.Vector3(...tgt.position);
      result.push({
        key: rel.id,
        points: curvePoints(a, b, 12),
        color: REL_COLORS[rel.rel_type] || "#80d8ff",
        opacity: 0.2 + rel.strength * 0.4,
      });
    }
    return result;
  }, [timelines, relationships, byId]);

  useFrame(({ clock }) => {
    const g = groupRef.current;
    if (!g) return;
    const pulse = 0.75 + 0.25 * Math.sin(clock.getElapsedTime() * 1.5);
    g.children.forEach((child) => {
      const mat = (child as THREE.Line).material as THREE.LineBasicMaterial;
      if (mat && "opacity" in mat) {
        mat.opacity = Math.min(1, (mat.userData.baseOpacity ?? 0.4) * pulse);
      }
    });
  });

  return (
    <group ref={groupRef}>
      {lines.map((line) => (
        <Line
          key={line.key}
          points={line.points}
          color={line.color}
          transparent
          opacity={line.opacity}
          lineWidth={1}
          depthWrite={false}
          userData={{ baseOpacity: line.opacity }}
        />
      ))}
    </group>
  );
}
