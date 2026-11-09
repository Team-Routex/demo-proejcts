import React, { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { BlogList } from "@/components/blog/BlogList";
import { Skeleton } from "@/components/ui/Skeleton";
import { ChevronRight, Folder } from "lucide-react";

interface CategoryDetailPageProps {
  params: Promise<{ slug: string }>;
}

export default async function CategoryDetailPage({ params }: CategoryDetailPageProps) {
  const { slug } = await params;
  let category: any = null;

  try {
    category = await api.categories.get(slug);
    if (!category) notFound();
  } catch {
    notFound();
  }

  return (
    <div className="bg-[#f7f7f7] min-h-screen py-10 sm:py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#aaa]">
          <Link href="/" className="hover:bg-slate-50 transition-colors">
            Home
          </Link>
          <ChevronRight className="h-3 w-3" />
          <Link href="/categories" className="hover:bg-slate-50 transition-colors">
            Categories
          </Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-[#20232e] font-bold">
            {category.name}
          </span>
        </div>

        {/* Category Header */}
        <div className="border-b border-[#eee] pb-6">
          <span className="text-xs font-black uppercase tracking-widest text-[#f48840]">
            Topic Category
          </span>
          <h1 className="mt-1 text-3xl sm:text-4xl font-black text-[#20232e] uppercase tracking-wide">
            {category.name}
          </h1>
          <p className="mt-2 text-sm text-[#7a7a7a] max-w-2xl leading-relaxed">
            {category.description || `Browse articles and insights in ${category.name}.`}
          </p>
        </div>

        {/* 2-Column Stand Blog layout */}
        <Suspense
          fallback={
            <div className="space-y-6">
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          }
        >
          <BlogList initialCategory={category.slug} />
        </Suspense>
      </div>
    </div>
  );
}
