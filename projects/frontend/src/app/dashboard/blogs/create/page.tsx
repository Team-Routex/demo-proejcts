import React from "react";
import { BlogEditor } from "@/components/blog/BlogEditor";

export const metadata = {
  title: "Write New Blog — RaftBlog",
};

export default function CreateBlogPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Create New Article
        </h1>
        <p className="text-sm text-slate-500">
          Draft your manuscript, upload featured media, and submit for editorial review
        </p>
      </div>

      <BlogEditor />
    </div>
  );
}

