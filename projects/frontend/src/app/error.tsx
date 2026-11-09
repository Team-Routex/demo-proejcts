"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, RotateCcw, Home } from "lucide-react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App Error Boundary caught:", error);
  }, [error]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center bg-[#f7f7f7] px-4 py-12">
      <div className="max-w-md w-full bg-white border border-[#eee] p-8 text-center shadow-xs">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-50 text-[#f48840] mb-4">
          <AlertCircle className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-black text-[#20232e] uppercase tracking-wide">
          Unable to Load Content
        </h2>
        <p className="mt-2 text-sm text-[#7a7a7a] leading-relaxed">
          {error?.message || "An unexpected issue occurred while rendering this section."}
        </p>
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={() => reset()}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-bold uppercase tracking-wider px-5 py-2.5 transition-colors cursor-pointer"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Try Again</span>
          </button>
          <Link
            href="/"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white hover:bg-[#f7f7f7] border border-[#eee] text-[#20232e] text-xs font-bold uppercase tracking-wider px-5 py-2.5 transition-colors"
          >
            <Home className="h-3.5 w-3.5" />
            <span>Return Home</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

