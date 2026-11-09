"use client";

import React, { useState } from "react";
import { Heart } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

interface LikeButtonProps {
  targetType: "blog" | "comment";
  targetId: number;
  initialLiked?: boolean;
  initialCount?: number;
  size?: "sm" | "md";
  showCount?: boolean;
}

export function LikeButton({
  targetType,
  targetId,
  initialLiked = false,
  initialCount = 0,
  size = "md",
  showCount = true,
}: LikeButtonProps) {
  const { isAuthenticated } = useAuth();
  const [liked, setLiked] = useState<boolean>(initialLiked);
  const [count, setCount] = useState<number>(initialCount);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleToggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isAuthenticated) {
      window.location.href = "/login";
      return;
    }
    if (isLoading) return;

    // Optimistic update
    const nextLiked = !liked;
    const nextCount = nextLiked ? count + 1 : Math.max(0, count - 1);
    setLiked(nextLiked);
    setCount(nextCount);
    setIsLoading(true);

    try {
      const res = await api.reactions.toggle(targetType, targetId);
      setLiked(res.liked);
      setCount(res.likes_count);
    } catch {
      // Revert on failure
      setLiked(liked);
      setCount(count);
    } finally {
      setIsLoading(false);
    }
  };

  const isSmall = size === "sm";

  return (
    <button
      onClick={handleToggle}
      disabled={isLoading}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full transition-all focus:outline-none select-none cursor-pointer",
        liked
          ? "text-rose-600 bg-rose-50 hover:opacity-90"
          : "text-slate-500 hover:opacity-90 hover:opacity-90",
        isSmall ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm"
      )}
      title={liked ? "Unlike" : "Like"}
    >
      <Heart
        className={cn(
          isSmall ? "h-3.5 w-3.5" : "h-4 w-4",
          liked ? "fill-rose-600 text-rose-600" : "text-current"
        )}
      />
      {showCount && <span className="font-medium">{count}</span>}
    </button>
  );
}

