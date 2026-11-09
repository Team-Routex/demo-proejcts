"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";

interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string | null;
  name?: string | null;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
}

const sizeClasses = {
  xs: "h-6 w-6 text-[10px]",
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-14 w-14 text-base",
  xl: "h-20 w-20 text-xl font-bold",
};

const bgColors = [
  "bg-[#f48840]",
  "bg-amber-600",
  "bg-emerald-600",
  "bg-indigo-600",
  "bg-rose-600",
  "bg-purple-600",
  "bg-teal-600",
];

function getInitials(name?: string | null): string {
  if (!name) return "U";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getColor(name?: string | null): string {
  if (!name) return bgColors[0];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return bgColors[Math.abs(hash) % bgColors.length];
}

export function Avatar({
  src,
  name,
  size = "md",
  className,
  ...props
}: AvatarProps) {
  const [imageError, setImageError] = useState(false);
  const initials = getInitials(name);
  const bgColor = getColor(name);
  const sizeClass = sizeClasses[size];

  if (src && !imageError) {
    return (
      <div
        className={cn(
          "relative shrink-0 overflow-hidden rounded-full border border-slate-200/80 bg-slate-100",
          sizeClass,
          className
        )}
        {...props}
      >
        <img
          src={src}
          alt={name || "User Avatar"}
          className="h-full w-full object-cover"
          onError={() => setImageError(true)}
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex shrink-0 select-none items-center justify-center rounded-full font-semibold text-white shadow-xs",
        bgColor,
        sizeClass,
        className
      )}
      title={name || "User"}
      {...props}
    >
      {initials}
    </div>
  );
}

