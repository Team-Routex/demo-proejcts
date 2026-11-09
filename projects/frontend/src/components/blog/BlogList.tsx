"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { BlogCard } from "./BlogCard";
import { Sidebar } from "./Sidebar";
import { Skeleton } from "@/components/ui/Skeleton";
import { ChevronLeft, ChevronRight, SlidersHorizontal } from "lucide-react";

interface BlogListProps {
  initialCategory?: string;
  initialSearch?: string;
}

export function BlogList({ initialCategory, initialSearch = "" }: BlogListProps) {
  const searchParams = useSearchParams();
  const queryParam = searchParams.get("q") || initialSearch;
  const categoryParam = searchParams.get("category") || initialCategory || "";
  const tagParam = searchParams.get("tag") || "";

  const [search, setSearch] = useState(queryParam);
  const [debouncedSearch, setDebouncedSearch] = useState(queryParam);
  const [selectedCategory, setSelectedCategory] = useState(categoryParam);
  const [selectedTag, setSelectedTag] = useState(tagParam);
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (searchParams.get("q") !== null) {
      const q = searchParams.get("q") || "";
      setSearch(q);
      setDebouncedSearch(q);
      setPage(1);
    }
  }, [searchParams]);

  useEffect(() => {
    if (searchParams.get("tag") !== null) {
      setSelectedTag(searchParams.get("tag") || "");
      setPage(1);
    }
  }, [searchParams]);

  // Fetch categories for dropdown
  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.categories.list(),
  });

  // Fetch tags for dropdown/filter
  const { data: tags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.tags.list(),
  });

  // Fetch blogs
  const { data, isLoading, isError } = useQuery({
    queryKey: ["blogs", debouncedSearch, selectedCategory, selectedTag, sort, page],
    queryFn: () =>
      api.blogs.list({
        search: debouncedSearch,
        category: selectedCategory,
        tag: selectedTag,
        sort,
        page,
        limit: 6,
      }),
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setDebouncedSearch(search);
    setPage(1);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      {/* Main Column (col-lg-8) */}
      <main className="lg:col-span-8 space-y-8">
        {/* Filter / Search Bar */}
        <div className="bg-white p-5 border border-[#eee] shadow-xs flex flex-col sm:flex-row gap-4 items-stretch sm:items-center justify-between">
          <form onSubmit={handleSearchSubmit} className="relative flex-1">
            <input
              type="text"
              placeholder="Search articles by title or keyword..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full border border-[#eee] bg-[#f7f7f7] pl-3.5 pr-20 py-2.5 text-xs text-[#20232e] placeholder-[#aaa] focus:border-[#f48840] focus:outline-none"
            />
            <button
              type="submit"
              className="absolute right-1 top-1/2 -translate-y-1/2 bg-[#f48840] hover:bg-[#e0752d] text-white text-[11px] font-bold uppercase tracking-wider px-3 py-1.5 transition-colors cursor-pointer"
            >
              Filter
            </button>
          </form>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setPage(1);
              }}
              className="border border-[#eee] bg-[#f7f7f7] px-3 py-2 text-xs text-[#20232e] focus:border-[#f48840] focus:outline-none"
            >
              <option value="">All Categories</option>
              {categories.map((c: any) => (
                <option key={c.id} value={c.slug}>
                  {c.name} ({c.blog_count ?? 0})
                </option>
              ))}
            </select>

            <select
              value={selectedTag}
              onChange={(e) => {
                setSelectedTag(e.target.value);
                setPage(1);
              }}
              className="border border-[#eee] bg-[#f7f7f7] px-3 py-2 text-xs text-[#20232e] focus:border-[#f48840] focus:outline-none"
            >
              <option value="">All Tags</option>
              {tags.map((t: any) => (
                <option key={t.id} value={t.slug}>
                  #{t.name}
                </option>
              ))}
            </select>

            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
              className="border border-[#eee] bg-[#f7f7f7] px-3 py-2 text-xs text-[#20232e] focus:border-[#f48840] focus:outline-none"
            >
              <option value="newest">Newest</option>
              <option value="popular">Popular (Views)</option>
              <option value="likes">Most Liked</option>
              <option value="oldest">Oldest</option>
            </select>
          </div>
        </div>

        {/* Active Tag pill if filtered */}
        {selectedTag && (
          <div className="bg-orange-50 border border-orange-200 px-4 py-2.5 flex items-center justify-between text-xs text-orange-800">
            <span>
              Showing articles tagged with: <b>#{selectedTag}</b>
            </span>
            <button
              onClick={() => setSelectedTag("")}
              className="font-bold underline hover:text-orange-950 cursor-pointer"
            >
              Remove Tag Filter
            </button>
          </div>
        )}

        {/* Blog Post List */}
        {isLoading ? (
          <div className="space-y-6">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="border border-[#eee] bg-white p-6 space-y-4">
                <Skeleton className="h-64 w-full" />
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="border border-rose-200 bg-rose-50 p-8 text-center text-rose-700">
            <p className="font-bold">Unable to load stories.</p>
            <p className="text-xs mt-1">Please ensure the backend server is reachable.</p>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="bg-white p-12 text-center border border-[#eee]">
            <SlidersHorizontal className="mx-auto h-12 w-12 text-[#aaa] mb-3" />
            <h3 className="text-lg font-bold text-[#20232e]">No articles found</h3>
            <p className="mt-1 text-xs text-[#7a7a7a]">
              Try adjusting your search terms or clearing the selected category or tag filter.
            </p>
            {(selectedCategory || selectedTag || debouncedSearch) && (
              <button
                onClick={() => {
                  setSelectedCategory("");
                  setSelectedTag("");
                  setSearch("");
                  setDebouncedSearch("");
                  setPage(1);
                }}
                className="mt-4 bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-bold uppercase tracking-wider px-5 py-2.5 transition-colors cursor-pointer"
              >
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {data.items.map((blog) => (
              <BlogCard key={blog.id} blog={blog} />
            ))}

            {/* Stand Blog Numeric Pagination */}
            {data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-6">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="flex h-10 w-10 items-center justify-center border border-[#eee] bg-white text-sm font-bold text-[#20232e] hover:border-[#f48840] hover:text-[#f48840] disabled:opacity-40 transition-colors cursor-pointer"
                  title="Previous Page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>

                {Array.from({ length: data.total_pages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`flex h-10 w-10 items-center justify-center border text-sm font-bold transition-colors cursor-pointer ${
                      page === p
                        ? "border-[#f48840] bg-[#f48840] text-white"
                        : "border-[#eee] bg-white text-[#20232e] hover:text-[#f48840]:border-[#f48840] hover:text-[#f48840]"
                    }`}
                  >
                    {p}
                  </button>
                ))}

                <button
                  disabled={page >= data.total_pages}
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  className="flex h-10 w-10 items-center justify-center border border-[#eee] bg-white text-sm font-bold text-[#20232e] hover:text-[#f48840]:border-[#f48840] hover:text-[#f48840] disabled:opacity-40 transition-colors cursor-pointer"
                  title="Next Page"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Stand Blog Sidebar (col-lg-4) */}
      <aside className="lg:col-span-4">
        <Sidebar />
      </aside>
    </div>
  );
}
