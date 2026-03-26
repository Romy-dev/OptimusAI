import { useEffect, useRef, useCallback, useState } from "react";

export interface WsEvent {
  id: string;
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [notifications, setNotifications] = useState<WsEvent[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws?token=${token}`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 5s
      reconnectTimer.current = setTimeout(connect, 5000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (e) => {
      try {
        const event: WsEvent = JSON.parse(e.data);
        setNotifications((prev) => [event, ...prev].slice(0, 50));
        setUnreadCount((c) => c + 1);
      } catch { /* ignore non-JSON */ }
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const markAllRead = useCallback(() => setUnreadCount(0), []);
  const clearNotifications = useCallback(() => {
    setNotifications([]);
    setUnreadCount(0);
  }, []);

  return { connected, notifications, unreadCount, markAllRead, clearNotifications };
}
