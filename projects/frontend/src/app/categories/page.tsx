import React from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ArrowRight, Folder } from "lucide-react";

export const revalidate = 60;

export default async function CategoriesPage() {
  let categories: any[] = [];
  try {
    categories = await api.categories.list();
  } catch {
    // ignore
  }

  return (
    <div className="bg-[#f7f7f7] min-h-screen py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-10">
        {/* Header */}
        <div className="border-b border-[#eee] pb-6">
          <span className="text-xs font-black uppercase tracking-widest text-[#f48840]">
            Taxonomy
          </span>
          <h1 className="mt-1 text-3xl sm:text-4xl font-black text-[#20232e] uppercase tracking-wide">
            All Categories
          </h1>
          <p className="mt-2 text-sm text-[#7a7a7a] max-w-2xl">
            Browse published topics or explore articles categorized by discipline, architecture, and technology.
          </p>
        </div>

        {/* Grid of categories */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((cat) => (
            <Link key={cat.id} href={`/categories/${cat.slug}`} className="group block">
              <div className="bg-white p-7 border border-[#eee] h-full flex flex-col justify-between transition-all group-hover:-translate-y-1 group-hover:text-[#f48840] group-hover:text-[#f48840]">
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-bold text-lg text-[#20232e] group-hover:text-[#f48840] transition-colors">
                      {cat.name}
                    </h3>
                    <span className="bg-[#f7f7f7] text-[#f48840] text-xs font-bold px-2.5 py-1 border border-[#eee]">
                      {cat.blog_count || 0} Articles
                    </span>
                  </div>
                  <p className="mt-3 text-xs sm:text-sm text-[#7a7a7a] leading-relaxed line-clamp-3">
                    {cat.description || "Articles and discussions categorized under " + cat.name + "."}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-[#eee] flex items-center justify-between text-xs font-bold uppercase tracking-wider text-[#f48840] group-hover:text-[#f48840]">
                  <span>Explore Topic</span>
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
