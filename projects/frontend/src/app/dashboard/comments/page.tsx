"use client";

import React from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";
import { MessageSquare, ExternalLink, Trash2, CheckCircle } from "lucide-react";

export default function UserCommentsPage() {
  const queryClient = useQueryClient();

  // Fetch user blogs to see comments on their blogs
  const { data: myBlogs, isLoading } = useQuery({
    queryKey: ["my-blogs-comments"],
    queryFn: () => api.blogs.myBlogs({ limit: 50 }),
  });

  const deleteCommentMutation = useMutation({
    mutationFn: (id: number) => api.comments.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-blogs-comments"] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Comments &amp; Reader Discussions
        </h1>
        <p className="text-sm text-slate-500">
          Monitor discussions and reader replies across all your published articles
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !myBlogs || myBlogs.items.length === 0 ? (
        <div className="p-12 text-center border rounded-xl bg-white text-slate-400">
          You haven't published any articles yet.
        </div>
      ) : (
        <div className="space-y-4">
          {myBlogs.items.map((blog) => (
            <Card key={blog.id}>
              <CardHeader className="p-4 sm:p-5 flex flex-row items-center justify-between border-b border-slate-100">
                <div>
                  <Link
                    href={`/blogs/${blog.slug}`}
                    className="font-bold text-sm sm:text-base text-slate-900 hover:opacity-90 flex items-center gap-1.5"
                    target="_blank"
                  >
                    <span>{blog.title}</span>
                    <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
                  </Link>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Published {formatDate(blog.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#f48840] bg-orange-50 px-2.5 py-1 rounded-full">
                    <MessageSquare className="h-3 w-3" />
                    {blog.comments_count || 0} comments
                  </span>
                </div>
              </CardHeader>
              <CardContent className="p-4 sm:p-5">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Manage comments directly on the article page</span>
                  <Link href={`/blogs/${blog.slug}#comments`} target="_blank">
                    <Button size="sm" variant="outline" className="text-xs h-7">
                      View Discussion Thread
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

