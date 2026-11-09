"use client";

import React from "react";
import Link from "next/link";
import { Blog } from "@/types";
import { LikeButton } from "./LikeButton";
import { formatDate } from "@/lib/utils";
import { Tag, FileText, Heart, MessageSquare } from "lucide-react";

interface BlogCardProps {
  blog: Blog;
}

export function BlogCard({ blog }: BlogCardProps) {
  const primaryCategory =
    blog.categories && blog.categories.length > 0 ? blog.categories[0] : null;

  return (
    <article className="border border-[#eee] bg-white overflow-hidden mb-10 transition-shadow hover:shadow-md">
      {/* Blog Thumb */}
      <Link href={`/blogs/${blog.slug}`} className="block relative aspect-video w-full overflow-hidden bg-[#f7f7f7] group">
        {blog.featured_image ? (
          <img
            src={blog.featured_image}
            alt={blog.title}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-slate-300">
            <FileText className="h-16 w-16 stroke-[1]" />
          </div>
        )}
      </Link>

      {/* Down Content */}
      <div className="p-8 sm:p-10">
        {/* Category Badge */}
        {primaryCategory ? (
          <Link
            href={`/categories/${primaryCategory.slug}`}
            className="inline-block text-sm sm:text-base font-black uppercase tracking-wider text-[#f48840] hover:text-[#fb9857] transition-colors"
          >
            {primaryCategory.name}
          </Link>
        ) : (
          <span className="inline-block text-sm sm:text-base font-black uppercase tracking-wider text-[#f48840]">
            General
          </span>
        )}

        {/* Post Title */}
        <Link href={`/blogs/${blog.slug}`} className="block mt-2 mb-3 group/title">
          <h3 className="text-xl sm:text-2xl font-black text-[#20232e] group-hover:text-[#f48840] transition-colors leading-snug">
            {blog.title}
          </h3>
        </Link>

        {/* Post Info Metadata (Author | Date | Comments | Likes) */}
        <ul className="flex flex-wrap items-center text-xs sm:text-sm font-normal text-[#aaa] gap-1 sm:gap-2 mb-5">
          <li>
            <Link
              href={`/author/${blog.author?.username || "admin"}`}
              className="text-[#aaa] hover:text-[#f48840] transition-colors font-medium"
            >
              {blog.author?.full_name || blog.author?.username || "Admin"}
            </Link>
          </li>
          <li className="text-[#ccc]">|</li>
          <li>{formatDate(blog.created_at)}</li>
          <li className="text-[#ccc]">|</li>
          <li className="flex items-center gap-1">
            <MessageSquare className="h-3.5 w-3.5" />
            <span>{blog.comments_count ?? 0} Comments</span>
          </li>
          <li className="text-[#ccc]">|</li>
          <li className="flex items-center gap-1 text-[#f48840]">
            <Heart className="h-3.5 w-3.5 fill-[#f48840]" />
            <span>{blog.likes_count ?? 0} Likes</span>
          </li>
        </ul>

        {/* Excerpt Paragraph with bottom border */}
        <p className="text-sm sm:text-base text-[#7a7a7a] leading-relaxed pb-6 border-b border-[#eee] line-clamp-3">
          {blog.summary || (blog.content ? blog.content.substring(0, 220) + "..." : "")}
        </p>

        {/* Post Options (Tags & Actions) */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
          {/* Post Tags */}
          <div className="flex items-center gap-2 text-xs sm:text-sm text-[#aaa]">
            <Tag className="h-4 w-4 text-[#f48840] shrink-0" />
            {blog.tags && blog.tags.length > 0 ? (
              <div className="flex flex-wrap items-center gap-1.5">
                {blog.tags.map((t) => (
                  <Link
                    key={t.id}
                    href={`/blogs?tag=${encodeURIComponent(t.slug)}`}
                    className="text-[#7a7a7a] hover:text-[#f48840] font-medium transition-colors"
                  >
                    #{t.name}
                  </Link>
                ))}
              </div>
            ) : blog.categories && blog.categories.length > 0 ? (
              <div className="flex flex-wrap items-center gap-1.5">
                {blog.categories.map((c, idx) => (
                  <span key={c.id}>
                    <Link
                      href={`/categories/${c.slug}`}
                      className="text-[#aaa] hover:text-[#f48840] transition-colors"
                    >
                      {c.name}
                    </Link>
                    {idx < (blog.categories?.length || 0) - 1 ? "," : ""}
                  </span>
                ))}
              </div>
            ) : (
              <span>Articles</span>
            )}
          </div>

          {/* Reactions / Read Story */}
          <div className="flex items-center gap-3">
            <LikeButton
              targetType="blog"
              targetId={blog.id}
              initialLiked={blog.has_liked}
              initialCount={blog.likes_count || 0}
              size="sm"
            />
            <Link
              href={`/blogs/${blog.slug}`}
              className="inline-block bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-bold uppercase tracking-wider px-4 py-2 transition-colors"
            >
              Read More
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
