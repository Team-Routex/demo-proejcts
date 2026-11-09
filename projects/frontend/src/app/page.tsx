import React from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { BlogCard } from "@/components/blog/BlogCard";
import { BannerSlider } from "@/components/blog/BannerSlider";
import { Sidebar } from "@/components/blog/Sidebar";
import { BookOpen, ArrowRight } from "lucide-react";

export const revalidate = 60;

export default async function HomePage() {
  let blogs: any[] = [];
  let featuredBlogs: any[] = [];

  try {
    const blogsRes = await api.blogs.list({ limit: 10, sort: "newest" });
    blogs = blogsRes.items || [];
    featuredBlogs = blogs.slice(0, 6);
  } catch (err) {
    // Graceful fallback
  }

  return (
    <div className="bg-[#f7f7f7] min-h-screen">
      {/* 1. Stand Blog Main Banner / Hero Carousel */}
      {featuredBlogs.length > 0 && <BannerSlider blogs={featuredBlogs} />}

      {/* 2. Stand Blog 2-Column Content Layout */}
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Main Blog Posts Column (col-lg-8) */}
          <main className="lg:col-span-8">
            <div className="mb-6 flex items-center justify-between border-b border-[#eee] pb-4">
              <h2 className="text-xl sm:text-2xl font-black uppercase tracking-wide text-[#20232e]">
                Recent Posts
              </h2>
              <Link
                href="/blogs"
                className="text-xs font-bold uppercase tracking-wider text-[#f48840] hover:text-[#fb9857] flex items-center gap-1 transition-colors"
              >
                <span>View All</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {blogs.length === 0 ? (
              <div className="bg-white p-12 text-center border border-[#eee]">
                <BookOpen className="mx-auto h-12 w-12 text-[#f48840] mb-3" />
                <h3 className="text-lg font-bold text-[#20232e]">
                  No published stories yet
                </h3>
                <p className="mt-1 text-sm text-[#7a7a7a]">
                  Sign in and publish the first technical article on the platform.
                </p>
                <Link
                  href="/dashboard/blogs/create"
                  className="mt-4 inline-block bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-bold uppercase tracking-wider px-6 py-3 transition-colors"
                >
                  Publish Story
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {blogs.map((blog) => (
                  <BlogCard key={blog.id} blog={blog} />
                ))}

                {/* View More Button */}
                <div className="text-center pt-4 pb-8">
                  <Link
                    href="/blogs"
                    className="inline-block bg-white hover:bg-[#f48840] text-[#f48840] border border-[#f48840] hover:text-white text-xs font-black uppercase tracking-widest px-8 py-3.5 transition-colors"
                  >
                    Load More Posts
                  </Link>
                </div>
              </div>
            )}
          </main>

          {/* Stand Blog Sidebar (col-lg-4) */}
          <aside className="lg:col-span-4">
            <Sidebar />
          </aside>
        </div>
      </div>

      {/* 3. Stand Blog Call to Action Section (Light-Based) */}
      <section className="bg-[#fff8f3] text-[#20232e] py-14 border-t border-[#ffe8d6]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 bg-white p-8 sm:p-12 border border-[#fed7aa] shadow-xs">
            <div className="space-y-2 text-center md:text-left">
              <span className="text-xs sm:text-sm font-black uppercase tracking-widest text-[#f48840]">
                RaftBlog Platform
              </span>
              <h2 className="text-2xl sm:text-3xl font-black text-[#20232e]">
                Share your technical insights with engineers worldwide.
              </h2>
              <p className="text-sm text-[#7a7a7a] max-w-2xl leading-relaxed">
                Join our community of backend developers, distributed systems architects, and software engineers.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 shrink-0">
              <Link
                href="/dashboard/blogs/create"
                className="bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-black uppercase tracking-wider px-6 py-3.5 transition-colors shadow-xs"
              >
                Write An Article
              </Link>
              <Link
                href="/blogs"
                className="bg-white hover:bg-[#f7f7f7] border border-[#eee] text-[#20232e] text-xs font-black uppercase tracking-wider px-6 py-3.5 transition-colors"
              >
                Explore Stories
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
