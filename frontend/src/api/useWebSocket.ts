import { useEffect, useRef } from "react";
import { useChronosStore } from "../store/useChronosStore";
import type { SimSnapshot } from "../types";

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  return `${proto}://${host}/ws`;
}

export function useWebSocket() {
  const applySnapshot = useChronosStore((s) => s.applySnapshot);
  const setConnected = useChronosStore((s) => s.setConnected);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    let closed = false;

    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
        ws.send(JSON.stringify({ type: "get_state" }));
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as SimSnapshot;
          if (data.type === "state" || data.timelines) {
            applySnapshot(data);
          }
        } catch {
          /* ignore malformed */
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          const delay = Math.min(5000, 500 * 2 ** retryRef.current);
          retryRef.current += 1;
          setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    const ping = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 15000);

    return () => {
      closed = true;
      clearInterval(ping);
      wsRef.current?.close();
    };
  }, [applySnapshot, setConnected]);
}
