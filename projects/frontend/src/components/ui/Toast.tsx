"use client";

import React, { useEffect } from "react";
import { Bell, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ToastProps {
  title: string;
  message: string;
  onClose: () => void;
  duration?: number;
}

export function ToastBanner({ title, message, onClose, duration = 5000 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [onClose, duration]);

  return (
    <div className="fixed bottom-5 right-5 z-50 flex max-w-sm items-start gap-3 rounded-xl border border-orange-200 bg-white p-4 shadow-xl transition-all animate-in slide-in-from-bottom-5">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-orange-100 text-[#f48840]">
        <Bell className="h-5 w-5" />
      </div>
      <div className="flex-1 pr-2">
        <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
        <p className="mt-0.5 text-xs text-slate-600 leading-relaxed">{message}</p>
      </div>
      <button
        onClick={onClose}
        className="shrink-0 rounded-md p-1 text-slate-400 hover:text-slate-600:bg-slate-100 hover:text-slate-600 transition-colors cursor-pointer"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

