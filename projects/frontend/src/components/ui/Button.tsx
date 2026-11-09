"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "destructive" | "ghost" | "link";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading = false, disabled, children, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f48840] disabled:pointer-events-none disabled:opacity-50 cursor-pointer select-none rounded-md";
    
    const variants = {
      primary: "bg-[#f48840] text-white hover:bg-[#e0752d] shadow-xs active:bg-[#c9631e]",
      secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200",
      outline: "border border-[#eee] bg-white hover:bg-[#f7f7f7] text-[#20232e]",
      destructive: "bg-red-600 text-white hover:bg-red-700 shadow-xs",
      ghost: "hover:bg-slate-100 text-[#20232e]",
      link: "text-[#f48840] underline-offset-4 hover:underline p-0 h-auto",
    };

    const sizes = {
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-10 px-4 text-sm gap-2",
      lg: "h-12 px-6 text-base gap-2.5",
      icon: "h-9 w-9 p-0",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Loader2 className="h-4 w-4 animate-spin text-current" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
