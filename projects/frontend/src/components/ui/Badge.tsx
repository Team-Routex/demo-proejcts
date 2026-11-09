import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "warning" | "destructive";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-orange-100 text-[#f48840] border-transparent",
    secondary: "bg-slate-100 text-slate-700 border-transparent",
    outline: "border border-slate-300 text-slate-700",
    success: "bg-emerald-100 text-emerald-800 border-transparent",
    warning: "bg-amber-100 text-amber-800 border-transparent",
    destructive: "bg-rose-100 text-rose-800 border-transparent",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

