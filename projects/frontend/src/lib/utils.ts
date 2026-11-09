import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string | undefined | null): string {
  if (!dateString) return "";
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return String(dateString);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return String(dateString);
  }
}

export function formatTimeAgo(dateString: string | undefined | null): string {
  if (!dateString) return "";
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return "";
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diffSec < 60) return "just now";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
    return formatDate(dateString);
  } catch {
    return "";
  }
}

export function estimateReadingTime(content: string = ""): number {
  const words = content.trim().split(/\s+/).length;
  return Math.max(1, Math.ceil(words / 200));
}

export function truncate(text: string = "", max: number = 120): string {
  if (text.length <= max) return text;
  return text.substring(0, max).trim() + "...";
}

