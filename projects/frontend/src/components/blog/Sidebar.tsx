"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Search, ChevronRight } from "lucide-react";

interface SidebarProps {
  currentBlogId?: number;
}

export function Sidebar({ currentBlogId }: SidebarProps) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");

  const { data: recentRes } = useQuery({
    queryKey: ["recent-blogs-sidebar"],
    queryFn: () => api.blogs.list({ limit: 4, sort: "newest" }),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories-sidebar"],
    queryFn: () => api.categories.list(),
  });

  const { data: dbTags = [] } = useQuery({
    queryKey: ["tags-sidebar"],
    queryFn: () => api.tags.list(),
  });

  const recentBlogs = (recentRes?.items || []).filter(
    (b: any) => !currentBlogId || b.id !== currentBlogId
  ).slice(0, 3);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      router.push(`/blogs?q=${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  const tagsList = dbTags.length > 0 ? dbTags : [
    { id: 1, name: "Architecture", slug: "architecture" },
    { id: 2, name: "Consensus", slug: "consensus" },
    { id: 3, name: "Raft", slug: "raft" },
    { id: 4, name: "Distributed", slug: "distributed" },
    { id: 5, name: "Next.js", slug: "nextjs" },
    { id: 6, name: "Python", slug: "python" },
    { id: 7, name: "PostgreSQL", slug: "postgresql" },
    { id: 8, name: "Design", slug: "design" },
    { id: 9, name: "DevOps", slug: "devops" },
    { id: 10, name: "Performance", slug: "performance" },
  ];

  return (
    <aside className="space-y-12">
      {/* 1. Search Widget */}
      <div className="bg-white p-7 border border-[#eee] shadow-xs">
        <h2 className="stand-heading-rule flex items-center justify-between">
          <span>Search</span>
          <Search className="h-4 w-4 text-[#f48840]" />
        </h2>
        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            placeholder="Type to search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full border border-[#eee] bg-[#f7f7f7] px-4 py-3 text-sm text-[#20232e] placeholder-[#aaa] focus:border-[#f48840] focus:outline-none transition-colors"
          />
          <button
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-[#f48840] hover:bg-[#e0752d] text-white p-2 text-xs transition-colors cursor-pointer"
            title="Search"
          >
            <Search className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>

      {/* 2. Recent Posts Widget */}
      <div className="bg-white p-7 border border-[#eee] shadow-xs">
        <h2 className="stand-heading-rule">Recent Posts</h2>
        <div className="divide-y divide-[#eee]">
          {recentBlogs.length === 0 ? (
            <p className="text-xs text-[#aaa] py-2">No recent stories yet.</p>
          ) : (
            recentBlogs.map((b: any) => (
              <article key={b.id} className="py-4 first:pt-0 last:pb-0 group">
                <Link href={`/blogs/${b.slug}`} className="block">
                  <h4 className="text-sm font-bold text-[#20232e] group-hover:text-[#f48840] transition-colors line-clamp-2 leading-snug">
                    {b.title}
                  </h4>
                  <span className="block mt-1.5 text-[11px] font-semibold text-[#aaa] uppercase tracking-wide">
                    {formatDate(b.created_at)}
                  </span>
                </Link>
              </article>
            ))
          )}
        </div>
      </div>

      {/* 3. Categories Widget */}
      <div className="bg-white p-7 border border-[#eee] shadow-xs">
        <h2 className="stand-heading-rule">Categories</h2>
        <ul className="space-y-3">
          {categories.length === 0 ? (
            <li className="text-xs text-[#aaa]">No categories found.</li>
          ) : (
            categories.map((c: any) => (
              <li key={c.id}>
                <Link
                  href={`/categories/${c.slug}`}
                  className="flex items-center justify-between text-sm text-[#7a7a7a] hover:text-[#f48840] transition-colors group"
                >
                  <span className="flex items-center gap-2">
                    <ChevronRight className="h-3.5 w-3.5 text-[#f48840] transition-transform group-hover:translate-x-1" />
                    <span>{c.name}</span>
                  </span>
                  <span className="text-xs font-semibold text-[#aaa]">
                    ({c.blog_count ?? 0})
                  </span>
                </Link>
              </li>
            ))
          )}
        </ul>
      </div>

      {/* 4. Tag Clouds Widget */}
      <div className="bg-white p-7 border border-[#eee] shadow-xs">
        <h2 className="stand-heading-rule">Tag Clouds</h2>
        <div className="flex flex-wrap gap-2">
          {tagsList.map((tag: any) => (
            <Link
              key={tag.id || tag.slug}
              href={`/blogs?tag=${encodeURIComponent(tag.slug)}`}
              className="inline-block border border-[#eee] bg-[#f7f7f7] px-3 py-1.5 text-xs font-semibold text-[#7a7a7a] hover:bg-[#f48840] hover:text-white hover:border-[#f48840] transition-all uppercase tracking-wider"
            >
              #{tag.name}
            </Link>
          ))}
        </div>
      </div>
    </aside>
  );
}
