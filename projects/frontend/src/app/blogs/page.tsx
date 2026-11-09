import React, { Suspense } from "react";
import { BlogList } from "@/components/blog/BlogList";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata = {
  title: "Blog — Raft Blog",
  description: "Explore technical architecture, software engineering, and system design articles.",
};

export default function BlogsPage() {
  return (
    <div className="bg-[#f7f7f7] min-h-screen py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Page Banner Header */}
        <div className="border-b border-[#eee] pb-6">
          <span className="text-xs font-black uppercase tracking-widest text-[#f48840]">
            Publications
          </span>
          <h1 className="mt-1 text-3xl sm:text-4xl font-black text-[#20232e] uppercase tracking-wide">
            Blog
          </h1>
          <p className="mt-2 text-sm text-[#7a7a7a] max-w-2xl">
            Browse published articles, engineering guides, and software architecture articles.
          </p>
        </div>

        {/* 2-Column Blog List with Stand Blog Sidebar */}
        <Suspense
          fallback={
            <div className="space-y-6">
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          }
        >
          <BlogList />
        </Suspense>
      </div>
    </div>
  );
}
