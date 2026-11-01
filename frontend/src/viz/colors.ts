import type { TimelineStatus } from "../types";

/** Hue-based glow palette: cyan / violet / blue / magenta */
export function hueToColor(hue: number, sat = 0.7, light = 0.55): string {
  const h = ((hue % 1) + 1) % 1;
  // Map to cyan(0.5)→blue(0.6)→violet(0.75)→magenta(0.85)
  const mapped = 0.48 + h * 0.4;
  return hslToHex(mapped * 360, sat, light);
}

function hslToHex(h: number, s: number, l: number): string {
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

export function statusColor(status: TimelineStatus, hue: number): string {
  switch (status) {
    case "growing":
      return hueToColor(hue, 0.85, 0.6);
    case "decaying":
      return hueToColor(hue, 0.35, 0.28);
    case "mutating":
      return "#e040fb";
    case "paradoxical":
      return "#ff1744";
    case "isolated":
      return "#546e7a";
    case "converging":
      return "#00e5ff";
    case "nascent":
      return "#80d8ff";
    default:
      return hueToColor(hue);
  }
}

export function statusEmissiveIntensity(status: TimelineStatus): number {
  switch (status) {
    case "growing":
      return 1.4;
    case "decaying":
      return 0.25;
    case "mutating":
      return 1.8;
    case "paradoxical":
      return 2.2;
    case "converging":
      return 1.5;
    case "nascent":
      return 1.1;
    case "isolated":
      return 0.15;
    default:
      return 0.8;
  }
}
