import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { BlogCard } from "@/components/blog/BlogCard";
import { Sidebar } from "@/components/blog/Sidebar";
import { Avatar } from "@/components/ui/Avatar";
import {
  CheckCircle,
  Globe,
  Eye,
  Heart,
  ChevronRight,
  BookOpen,
} from "lucide-react";

interface AuthorProfilePageProps {
  params: Promise<{ username: string }>;
}

export default async function AuthorProfilePage({ params }: AuthorProfilePageProps) {
  const { username } = await params;
  let blogs: any[] = [];

  try {
    const res = await api.blogs.list({ author: username, limit: 20 });
    blogs = res.items || [];
  } catch {
    // ignore
  }

  const author = blogs[0]?.author || {
    username,
    full_name: username.toUpperCase(),
    avatar_url: "",
    is_verified: false,
    bio: "",
    website: "",
  };

  const totalViews = blogs.reduce((acc, b) => acc + (b.views_count || 0), 0);
  const totalLikes = blogs.reduce((acc, b) => acc + (b.likes_count || 0), 0);

  return (
    <div className="bg-[#f7f7f7] min-h-screen py-10 sm:py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#aaa]">
          <Link href="/" className="hover:bg-slate-50 transition-colors">
            Home
          </Link>
          <ChevronRight className="h-3 w-3" />
          <Link href="/blogs" className="hover:bg-slate-50 transition-colors">
            Authors
          </Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-[#20232e] font-bold">
            @{author.username}
          </span>
        </div>

        {/* Author Header Card */}
        <div className="bg-white p-8 border border-[#eee] shadow-xs">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <Avatar
                src={author.avatar_url}
                name={author.full_name || author.username}
                size="xl"
              />
              <div>
                <h1 className="text-2xl font-black text-[#20232e] flex items-center gap-2">
                  <span>{author.full_name || author.username}</span>
                  {author.is_verified && (
                    <CheckCircle className="h-5 w-5 fill-[#f48840] text-white" />
                  )}
                </h1>
                <p className="text-xs font-semibold uppercase tracking-wider text-[#aaa]">
                  @{author.username}
                </p>
                {author.bio && (
                  <p className="mt-2 text-xs sm:text-sm text-[#7a7a7a] max-w-xl leading-relaxed">
                    {author.bio}
                  </p>
                )}
                {author.website && (
                  <a
                    href={author.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 mt-2 text-xs font-bold uppercase tracking-wider text-[#f48840] hover:text-[#fb9857]:underline"
                  >
                    <Globe className="h-3.5 w-3.5" />
                    <span>Website</span>
                  </a>
                )}
              </div>
            </div>

            {/* Author Stats */}
            <div className="flex items-center gap-6 border-t sm sm border-[#eee] pt-4 sm:pt-0 sm:pl-6 text-xs uppercase tracking-wider">
              <div className="text-center sm">
                <span className="block text-xl font-black text-[#20232e]">
                  {blogs.length}
                </span>
                <span className="text-[11px] text-[#aaa]">Articles</span>
              </div>
              <div className="text-center sm">
                <span className="block text-xl font-black text-[#f48840]">
                  {totalLikes}
                </span>
                <span className="text-[11px] text-[#aaa]">Likes</span>
              </div>
              <div className="text-center sm">
                <span className="block text-xl font-black text-[#20232e]">
                  {totalViews}
                </span>
                <span className="text-[11px] text-[#aaa]">Views</span>
              </div>
            </div>
          </div>
        </div>

        {/* 2-Column Stories + Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <main className="lg:col-span-8 space-y-6">
            <h2 className="stand-heading-rule">
              Published Stories by {author.full_name || author.username}
            </h2>
            {blogs.length === 0 ? (
              <div className="bg-white p-12 text-center border border-[#eee]">
                <BookOpen className="mx-auto h-12 w-12 text-[#aaa] mb-3" />
                <p className="text-sm text-[#7a7a7a]">No published stories found for this author.</p>
              </div>
            ) : (
              blogs.map((b) => <BlogCard key={b.id} blog={b} />)
            )}
          </main>

          <aside className="lg:col-span-4">
            <Sidebar />
          </aside>
        </div>
      </div>
    </div>
  );
}
