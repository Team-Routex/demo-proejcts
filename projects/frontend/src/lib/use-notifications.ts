"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Notification } from "@/types";
import { api, getToken } from "./api";
import { useAuth } from "./auth-context";

export function useNotifications() {
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [latestNotification, setLatestNotification] = useState<Notification | null>(null);
  const [toastMessage, setToastMessage] = useState<{ title: string; message: string; id: number } | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    try {
      const data = await api.notifications.unreadCount();
      setUnreadCount(data.unread_count);
    } catch {
      // ignore
    }
  }, [user]);

  useEffect(() => {
    fetchUnreadCount();
  }, [fetchUnreadCount]);

  useEffect(() => {
    if (!user) {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      return;
    }

    const token = getToken();
    if (!token) return;

    let isSubscribed = true;

    function connect() {
      const wsProtocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsHost = typeof window !== "undefined" ? `${window.location.hostname}:8000` : "127.0.0.1:8000";
      const baseWs = process.env.NEXT_PUBLIC_WS_URL || `${wsProtocol}//${wsHost}`;
      const wsUrl = `${baseWs}/ws/notifications?token=${encodeURIComponent(token || "")}`;
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        // Authenticate frame just in case
        ws.send(JSON.stringify({ type: "auth", token }));
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "notification" && payload.data) {
            const notif: Notification = payload.data;
            setLatestNotification(notif);
            setUnreadCount((prev) => prev + 1);
            setToastMessage({
              id: Date.now(),
              title: notif.title || "New Notification",
              message: notif.message,
            });
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        if (isSubscribed) {
          reconnectTimeoutRef.current = setTimeout(connect, 4000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      isSubscribed = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [user]);

  const clearToast = () => setToastMessage(null);

  return {
    unreadCount,
    setUnreadCount,
    latestNotification,
    toastMessage,
    clearToast,
    refreshUnreadCount: fetchUnreadCount,
  };
}

