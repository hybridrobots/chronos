import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { Timeline } from "../types";

interface Props {
  timelines: Timeline[];
}

export function CosmicDust({ timelines }: Props) {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 1200;

  const { positions, velocities } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 8 + Math.random() * 40;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.6;
      positions[i * 3 + 2] = r * Math.cos(phi);
      velocities[i * 3] = (Math.random() - 0.5) * 0.01;
      velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.01;
      velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.01;
    }
    return { positions, velocities };
  }, []);

  useFrame(() => {
    const pts = pointsRef.current;
    if (!pts) return;
    const attr = pts.geometry.attributes.position as THREE.BufferAttribute;
    const arr = attr.array as Float32Array;
    for (let i = 0; i < count; i++) {
      arr[i * 3] += velocities[i * 3];
      arr[i * 3 + 1] += velocities[i * 3 + 1];
      arr[i * 3 + 2] += velocities[i * 3 + 2];
      // Soft wrap
      for (let c = 0; c < 3; c++) {
        if (Math.abs(arr[i * 3 + c]) > 50) arr[i * 3 + c] *= -0.95;
      }
    }
    attr.needsUpdate = true;
  });

  // Activity-linked opacity
  const activity = Math.min(1, timelines.length / 40);

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        color="#7c4dff"
        transparent
        opacity={0.25 + activity * 0.35}
        depthWrite={false}
        sizeAttenuation
        toneMapped={false}
      />
    </points>
  );
}

export function EventSparks({ timelines }: Props) {
  const ref = useRef<THREE.Points>(null);
  const sparks = useMemo(() => {
    const list: [number, number, number, number][] = [];
    for (const tl of timelines) {
      const recent = tl.recent_events ?? [];
      for (const ev of recent.slice(-2)) {
        const jitter = (n: number) => n + (Math.random() - 0.5) * 0.4;
        list.push([
          jitter(tl.position[0]),
          jitter(tl.position[1]),
          jitter(tl.position[2]),
          ev.event_type === "paradox" ? 1 : 0,
        ]);
      }
    }
    return list.slice(0, 200);
  }, [timelines]);

  const positions = useMemo(() => {
    const arr = new Float32Array(Math.max(sparks.length, 1) * 3);
    sparks.forEach((s, i) => {
      arr[i * 3] = s[0];
      arr[i * 3 + 1] = s[1];
      arr[i * 3 + 2] = s[2];
    });
    return arr;
  }, [sparks]);

  useFrame(({ clock }) => {
    const pts = ref.current;
    if (!pts) return;
    const mat = pts.material as THREE.PointsMaterial;
    mat.opacity = 0.4 + 0.4 * Math.sin(clock.getElapsedTime() * 4);
  });

  if (sparks.length === 0) return null;

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.18}
        color="#00e5ff"
        transparent
        opacity={0.7}
        depthWrite={false}
        toneMapped={false}
      />
    </points>
  );
}
