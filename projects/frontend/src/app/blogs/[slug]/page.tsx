import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { LikeButton } from "@/components/blog/LikeButton";
import { CommentSection } from "@/components/blog/CommentSection";
import { Sidebar } from "@/components/blog/Sidebar";
import { Avatar } from "@/components/ui/Avatar";
import { formatDate, estimateReadingTime } from "@/lib/utils";
import {
  Tag,
  Share2,
  Calendar,
  Eye,
  MessageSquare,
  Clock,
  ChevronRight,
  Globe,
  FileText,
  Heart,
} from "lucide-react";

interface BlogDetailsPageProps {
  params: Promise<{ slug: string }>;
}

export default async function BlogDetailsPage({ params }: BlogDetailsPageProps) {
  const { slug } = await params;
  let blog: any = null;
  let comments: any[] = [];

  try {
    blog = await api.blogs.get(slug);
    if (!blog) notFound();
    comments = await api.comments.list(blog.id);
  } catch (err) {
    notFound();
  }

  const readTime = estimateReadingTime(blog.content);
  const primaryCategory =
    blog.categories && blog.categories.length > 0 ? blog.categories[0] : null;

  return (
    <div className="bg-[#f7f7f7] min-h-screen py-10 sm:py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb Header */}
        <div className="mb-8 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#aaa]">
          <Link href="/" className="hover:text-[#f48840] transition-colors">
            Home
          </Link>
          <ChevronRight className="h-3 w-3" />
          <Link href="/blogs" className="hover:text-[#f48840] transition-colors">
            Blog
          </Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-[#20232e] truncate max-w-xs sm:max-w-md">
            {blog.title}
          </span>
        </div>

        {/* Stand Blog 2-Column Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Main Article Content (col-lg-8) */}
          <main className="lg:col-span-8">
            <article className="border border-[#eee] bg-white shadow-xs overflow-hidden">
              {/* Blog Thumb */}
              <div className="relative aspect-video w-full overflow-hidden bg-[#f7f7f7] border-b border-[#eee]">
                {blog.featured_image ? (
                  <img
                    src={blog.featured_image}
                    alt={blog.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-slate-300">
                    <FileText className="h-20 w-20 stroke-[1]" />
                  </div>
                )}
              </div>

              {/* Down Content */}
              <div className="p-8 sm:p-12">
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
                    Article
                  </span>
                )}

                {/* Article Full Title */}
                <h1 className="mt-2 mb-4 text-2xl sm:text-3xl md:text-4xl font-black text-[#20232e] leading-tight">
                  {blog.title}
                </h1>

                {/* Post Info Metadata (Author | Date | Comments | Likes | Views) */}
                <ul className="flex flex-wrap items-center text-xs sm:text-sm font-normal text-[#aaa] gap-1 sm:gap-2 mb-8 pb-6 border-b border-[#eee]">
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
                    <span>{comments.length} Comments</span>
                  </li>
                  <li className="text-[#ccc]">|</li>
                  <li className="flex items-center gap-1 text-[#f48840]">
                    <Heart className="h-3.5 w-3.5 fill-[#f48840]" />
                    <span>{blog.likes_count ?? 0} Likes</span>
                  </li>
                  <li className="text-[#ccc]">|</li>
                  <li className="flex items-center gap-1">
                    <Eye className="h-3.5 w-3.5" />
                    <span>{blog.views_count ?? 0} Views</span>
                  </li>
                  <li className="text-[#ccc]">|</li>
                  <li className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    <span>{readTime} min read</span>
                  </li>
                </ul>

                {/* Summary / Lead */}
                {blog.summary && (
                  <div className="stand-quote">
                    <p className="text-base sm:text-lg font-medium text-[#20232e] leading-relaxed">
                      "{blog.summary}"
                    </p>
                  </div>
                )}

                {/* Body Content with Stand Blog Typography */}
                <div className="prose prose-slate max-w-none text-slate-800">
                  {blog.content.split("\n\n").map((paragraph: string, idx: number) => {
                    const trimmed = paragraph.trim();
                    if (!trimmed) return null;

                    // Stand Blog styled quotes
                    if (trimmed.startsWith("> ")) {
                      return (
                        <div key={idx} className="stand-quote">
                          <p className="text-base font-normal italic text-[#20232e]">
                            {trimmed.replace(/^>\s*/, "")}
                          </p>
                        </div>
                      );
                    }

                    // Markdown headers
                    if (trimmed.startsWith("### ")) {
                      return (
                        <h3 key={idx} className="text-xl font-black mt-8 mb-3 text-[#20232e] uppercase tracking-wide">
                          {trimmed.replace("### ", "")}
                        </h3>
                      );
                    }
                    if (trimmed.startsWith("## ")) {
                      return (
                        <h2 key={idx} className="text-2xl font-black mt-10 mb-4 text-[#20232e] uppercase tracking-wide border-b border-[#eee] pb-2">
                          {trimmed.replace("## ", "")}
                        </h2>
                      );
                    }
                    if (trimmed.startsWith("# ")) {
                      return (
                        <h1 key={idx} className="text-3xl font-black mt-10 mb-5 text-[#20232e] uppercase tracking-wide">
                          {trimmed.replace("# ", "")}
                        </h1>
                      );
                    }

                    // Regular body paragraph
                    return (
                      <p key={idx} className="text-base text-[#7a7a7a] leading-[30px] mb-6 whitespace-pre-line">
                        {trimmed}
                      </p>
                    );
                  })}
                </div>

                {/* Post Options (Tags & Reactions) */}
                <div className="mt-10 pt-6 border-t border-[#eee] flex flex-wrap items-center justify-between gap-4">
                  {/* Tags */}
                  <div className="flex items-center gap-2 text-xs sm:text-sm text-[#aaa]">
                    <Tag className="h-4 w-4 text-[#f48840] shrink-0" />
                    {blog.tags && blog.tags.length > 0 ? (
                      <div className="flex flex-wrap items-center gap-2">
                        {blog.tags.map((t: any) => (
                          <Link
                            key={t.id}
                            href={`/blogs?tag=${encodeURIComponent(t.slug)}`}
                            className="bg-[#f7f7f7] border border-[#eee] px-2.5 py-1 text-xs font-semibold text-[#7a7a7a] hover:bg-[#f48840] hover:text-white hover:border-[#f48840] transition-all uppercase tracking-wider"
                          >
                            #{t.name}
                          </Link>
                        ))}
                      </div>
                    ) : blog.categories && blog.categories.length > 0 ? (
                      <div className="flex flex-wrap items-center gap-1.5">
                        {blog.categories.map((c: any, idx: number) => (
                          <span key={c.id}>
                            <Link
                              href={`/categories/${c.slug}`}
                              className="text-[#aaa] hover:text-[#f48840] transition-colors"
                            >
                              {c.name}
                            </Link>
                            {idx < blog.categories.length - 1 ? "," : ""}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span>Articles</span>
                    )}
                  </div>

                  {/* Reaction / Share */}
                  <div className="flex items-center gap-3">
                    <LikeButton
                      targetType="blog"
                      targetId={blog.id}
                      initialLiked={blog.has_liked}
                      initialCount={blog.likes_count || 0}
                      size="md"
                    />

                    {blog.author?.website && (
                      <a
                        href={blog.author.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[#7a7a7a] hover:text-[#f48840] transition-colors"
                      >
                        <Globe className="h-3.5 w-3.5" />
                        Website
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </article>

            {/* Comments and Reply Section */}
            <CommentSection blogId={blog.id} initialComments={comments} />
          </main>

          {/* Stand Blog Sidebar (col-lg-4) */}
          <aside className="lg:col-span-4 space-y-8">
            {/* Author Card Widget */}
            <div className="bg-white p-7 border border-[#eee] shadow-xs">
              <h2 className="stand-heading-rule">About The Author</h2>
              <div className="flex items-start gap-4">
                <Avatar
                  src={blog.author?.avatar_url}
                  name={blog.author?.full_name || blog.author?.username}
                  size="xl"
                />
                <div>
                  <h4 className="font-bold text-base text-[#20232e]">
                    {blog.author?.full_name || blog.author?.username}
                  </h4>
                  <p className="text-xs text-[#aaa] font-semibold mt-0.5">
                    @{blog.author?.username}
                  </p>
                  <p className="text-xs text-[#7a7a7a] mt-2 line-clamp-3 leading-relaxed">
                    {blog.author?.bio || "Author and contributor on the RaftFramework technical publishing platform."}
                  </p>
                  <Link
                    href={`/author/${blog.author?.username}`}
                    className="inline-block mt-3 text-xs font-bold uppercase tracking-wider text-[#f48840] hover:text-[#fb9857] transition-colors"
                  >
                    View All Stories &rarr;
                  </Link>
                </div>
              </div>
            </div>

            {/* Standard Sidebar Widgets */}
            <Sidebar currentBlogId={blog.id} />
          </aside>
        </div>
      </div>
    </div>
  );
}
