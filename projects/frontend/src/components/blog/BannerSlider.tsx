"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Blog } from "@/types";
import { formatDate } from "@/lib/utils";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";

interface BannerSliderProps {
  blogs: Blog[];
}

export function BannerSlider({ blogs }: BannerSliderProps) {
  if (!blogs || blogs.length === 0) return null;

  const [currentIndex, setCurrentIndex] = useState(0);
  const items = blogs.slice(0, 6);

  const prevSlide = () => {
    setCurrentIndex((prev) => (prev === 0 ? Math.max(0, items.length - 1) : prev - 1));
  };

  const nextSlide = () => {
    setCurrentIndex((prev) => (prev >= items.length - 1 ? 0 : prev + 1));
  };

  // Determine items to display: take 3 starting from currentIndex, wrapping around if needed
  const displayItems = [];
  for (let i = 0; i < Math.min(3, items.length); i++) {
    const idx = (currentIndex + i) % items.length;
    displayItems.push({ blog: items[idx], displayKey: `slide-${items[idx].id}-${i}` });
  }

  return (
    <div className="relative w-full bg-white border-b border-[#eee] py-8 sm:py-10 select-none">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Slider Controls */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#f48840]" />
            <span className="text-xs font-black uppercase tracking-widest text-[#f48840]">
              Featured Articles
            </span>
          </div>

          {items.length > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={prevSlide}
                aria-label="Previous slide"
                className="flex h-9 w-9 items-center justify-center border border-[#eee] bg-[#f7f7f7] text-[#20232e] hover:text-[#f48840]:bg-[#f48840] hover:bg-[#e0752d]:text-white hover:border-[#f48840] transition-colors cursor-pointer"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={nextSlide}
                aria-label="Next slide"
                className="flex h-9 w-9 items-center justify-center border border-[#eee] bg-[#f7f7f7] text-[#20232e] hover:text-[#f48840]:bg-[#f48840] hover:bg-[#e0752d]:text-white hover:border-[#f48840] transition-colors cursor-pointer"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        {/* Carousel Grid - Light Styled Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayItems.map(({ blog, displayKey }) => {
            const categoryName =
              blog.categories && blog.categories.length > 0
                ? blog.categories[0].name
                : "Engineering";

            return (
              <div
                key={displayKey}
                className="group flex flex-col border border-[#eee] bg-white shadow-xs hover:shadow-md transition-shadow overflow-hidden"
              >
                {/* Thumbnail */}
                <Link
                  href={`/blogs/${blog.slug}`}
                  className="relative aspect-video w-full overflow-hidden bg-[#f7f7f7] block"
                >
                  {blog.featured_image ? (
                    <img
                      src={blog.featured_image}
                      alt={blog.title}
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-slate-300">
                      <FileText className="h-14 w-14 stroke-[1]" />
                    </div>
                  )}
                </Link>

                {/* Content */}
                <div className="p-6 flex flex-col flex-1 justify-between">
                  <div>
                    {/* Category */}
                    <span className="text-xs font-black uppercase tracking-wider text-[#f48840]">
                      {categoryName}
                    </span>

                    {/* Title */}
                    <Link href={`/blogs/${blog.slug}`} className="block mt-2 group-hover:text-[#f48840] transition-colors">
                      <h3 className="text-base sm:text-lg font-black text-[#20232e] leading-snug line-clamp-2">
                        {blog.title}
                      </h3>
                    </Link>
                  </div>

                  {/* Stand Blog Metadata line with pipes */}
                  <ul className="stand-post-info text-[11px] font-bold uppercase tracking-wider text-[#aaa] mt-4 pt-3 border-t border-[#f2f2f2]">
                    <li className="text-[#20232e] hover:text-[#f48840]">
                      <Link href={`/author/${blog.author?.username || "admin"}`}>
                        {blog.author?.full_name || blog.author?.username || "Admin"}
                      </Link>
                    </li>
                    <li>{formatDate(blog.created_at)}</li>
                    <li>{blog.comments_count || 0} Comments</li>
                  </ul>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
