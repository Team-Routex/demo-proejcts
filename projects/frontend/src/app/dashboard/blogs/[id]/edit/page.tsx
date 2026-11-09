"use client";

import React, { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { BlogEditor } from "@/components/blog/BlogEditor";
import { Skeleton } from "@/components/ui/Skeleton";

interface EditBlogPageProps {
  params: Promise<{ id: string }>;
}

export default function EditBlogPage({ params }: EditBlogPageProps) {
  const { id } = use(params);
  const blogId = parseInt(id, 10);

  // Fetch blogs to find matching ID
  const { data, isLoading } = useQuery({
    queryKey: ["edit-blog", blogId],
    queryFn: async () => {
      // Find from user's blogs
      const res = await api.blogs.myBlogs({ limit: 100 });
      return res.items.find((b) => b.id === blogId);
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 text-center text-slate-500">
        Article not found or you do not have permission to edit it.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Edit Article
        </h1>
        <p className="text-sm text-slate-500">
          Update article content, manage categories, or resubmit for review
        </p>
      </div>

      <BlogEditor initialBlog={data} isEditing={true} />
    </div>
  );
}

