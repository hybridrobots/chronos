const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getState: () => req<Record<string, unknown>>("/state"),
  getOrganism: () => req<Record<string, unknown>>("/organism"),
  getTimelines: () => req<unknown[]>("/timelines"),
  getTimeline: (id: string) => req<Record<string, unknown>>(`/timelines/${id}`),
  getGenealogy: (id: string) =>
    req<Record<string, unknown>>(`/timelines/${id}/genealogy`),
  getHistory: (id: string) =>
    req<unknown[]>(`/timelines/${id}/history`),
  getParadoxes: () => req<unknown[]>("/paradoxes"),
  getConfig: () => req<Record<string, unknown>>("/config"),
  updateConfig: (updates: Record<string, unknown>) =>
    req<Record<string, unknown>>("/config", {
      method: "POST",
      body: JSON.stringify({ updates }),
    }),
  start: () => req("/control/start", { method: "POST" }),
  pause: () => req("/control/pause", { method: "POST" }),
  resume: () => req("/control/resume", { method: "POST" }),
  stop: () => req("/control/stop", { method: "POST" }),
  reset: (seed?: number) =>
    req("/control/reset", {
      method: "POST",
      body: JSON.stringify({ seed: seed ?? null }),
    }),
  setSpeed: (speed: number) =>
    req("/control/speed", {
      method: "POST",
      body: JSON.stringify({ speed }),
    }),
  rewrite: (timeline_id: string, event_id: string, description: string) =>
    req("/alterations/rewrite", {
      method: "POST",
      body: JSON.stringify({ timeline_id, event_id, description }),
    }),
  resolveParadox: (paradox_id: string, strategy?: string) =>
    req("/paradoxes/resolve", {
      method: "POST",
      body: JSON.stringify({ paradox_id, strategy }),
    }),
  save: () => req("/persistence/save", { method: "POST" }),
  snapshot: (name: string) =>
    req("/persistence/snapshot", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  listSnapshots: () => req<unknown[]>("/persistence/snapshots"),
  restore: (id: number) =>
    req(`/persistence/restore/${id}`, { method: "POST" }),
  loadAutosave: () => req("/persistence/load-autosave", { method: "POST" }),
  observatory: () => req<Record<string, unknown>>("/observatory"),
  learning: () => req<Record<string, unknown>>("/learning"),
  decision: () => req<Record<string, unknown>>("/decision"),
  startDecision: (body: Record<string, unknown>) =>
    req<Record<string, unknown>>("/decision/start", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  concludeDecision: (id: string) =>
    req<Record<string, unknown>>(`/decision/${id}/conclude`, { method: "POST" }),
  cancelDecision: (id: string) =>
    req<Record<string, unknown>>(`/decision/${id}/cancel`, { method: "POST" }),
};
