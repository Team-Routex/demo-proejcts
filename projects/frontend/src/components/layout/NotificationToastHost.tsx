"use client";

import React from "react";
import { useNotifications } from "@/lib/use-notifications";
import { ToastBanner } from "@/components/ui/Toast";

export function NotificationToastHost() {
  const { toastMessage, clearToast } = useNotifications();

  if (!toastMessage) return null;

  return (
    <ToastBanner
      title={toastMessage.title}
      message={toastMessage.message}
      onClose={clearToast}
    />
  );
}

