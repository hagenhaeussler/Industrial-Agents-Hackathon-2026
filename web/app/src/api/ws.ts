import { useEffect, useRef, useState } from 'react';
import { mockMode } from './client';
import type { ServerMessage } from './types';

export type Link = 'connecting' | 'live' | 'offline' | 'mock';

/**
 * `WS /ws/buildings/{id}` with reconnect backoff 0.5 s → 5 s (CONTRACTS §9).
 * `onReconnect` runs after every reconnect so the view reloads its snapshot and tour.
 */
export function useBuildingSocket(buildingId: string | null, onMessage: (message: ServerMessage) => void, onReconnect?: () => void): Link {
  const [link, setLink] = useState<Link>(mockMode ? 'mock' : 'connecting');
  const handlers = useRef({ onMessage, onReconnect });
  handlers.current = { onMessage, onReconnect };

  useEffect(() => {
    if (!buildingId || mockMode || typeof WebSocket === 'undefined') return;
    let socket: WebSocket | null = null;
    let delay = 500;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;
    let opened = false;
    const connect = () => {
      const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/buildings/${encodeURIComponent(buildingId)}`;
      socket = new WebSocket(url);
      socket.onopen = () => {
        setLink('live');
        delay = 500;
        if (opened) handlers.current.onReconnect?.();
        opened = true;
      };
      socket.onmessage = event => {
        try { handlers.current.onMessage(JSON.parse(String(event.data)) as ServerMessage); } catch { /* not ours: ignore */ }
      };
      socket.onclose = () => {
        if (closed) return;
        setLink('offline');
        timer = setTimeout(connect, delay);
        delay = Math.min(delay * 2, 5000);
      };
    };
    connect();
    return () => { closed = true; clearTimeout(timer); socket?.close(); };
  }, [buildingId]);

  return link;
}
