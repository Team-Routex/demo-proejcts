"use client";

import React from "react";
import Link from "next/link";
import { TopBlog } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import { Eye, Heart, MessageSquare, Reply, ExternalLink } from "lucide-react";

interface TopBlogsTableProps {
  blogs: TopBlog[];
}

export function TopBlogsTable({ blogs }: TopBlogsTableProps) {
  const getApprovalBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <Badge variant="success">Approved</Badge>;
      case "pending":
        return <Badge variant="warning">Pending</Badge>;
      case "rejected":
        return <Badge variant="destructive">Rejected</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-slate-600">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-700">
          <tr>
            <th className="px-4 py-3">#</th>
            <th className="px-4 py-3">Blog Title</th>
            <th className="px-4 py-3">Author</th>
            <th className="px-4 py-3 text-center">Views</th>
            <th className="px-4 py-3 text-center">Likes</th>
            <th className="px-4 py-3 text-center">Comments</th>
            <th className="px-4 py-3 text-center">Replies</th>
            <th className="px-4 py-3">Published</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3 text-right">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {blogs.length === 0 ? (
            <tr>
              <td colSpan={10} className="px-4 py-8 text-center text-slate-400">
                No blog data recorded yet.
              </td>
            </tr>
          ) : (
            blogs.map((b, idx) => (
              <tr key={b.id} className="hover:bg-slate-50">
                <td className="px-4 py-3.5 font-bold text-slate-400">{idx + 1}</td>
                <td className="px-4 py-3.5 font-medium text-slate-900 max-w-xs truncate">
                  <Link
                    href={`/blogs/${b.slug}`}
                    className="hover:text-[#f48840] inline-flex items-center gap-1.5"
                    target="_blank"
                  >
                    <span>{b.title}</span>
                    <ExternalLink className="h-3 w-3 text-slate-400" />
                  </Link>
                </td>
                <td className="px-4 py-3.5 text-xs text-slate-700">
                  {b.author || b.author_name || b.author_username}
                </td>
                <td className="px-4 py-3.5 text-center font-medium text-slate-700">
                  <span className="inline-flex items-center gap-1">
                    <Eye className="h-3.5 w-3.5 text-slate-400" />
                    {(b as any).total_views ?? b.views_count ?? 0}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-center font-medium text-slate-700">
                  <span className="inline-flex items-center gap-1 text-rose-600">
                    <Heart className="h-3.5 w-3.5 fill-rose-500" />
                    {(b as any).total_likes ?? b.likes_count ?? 0}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-center font-medium text-slate-700">
                  <span className="inline-flex items-center gap-1 text-[#f48840]">
                    <MessageSquare className="h-3.5 w-3.5" />
                    {(b as any).total_comments ?? b.comments_count ?? 0}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-center font-medium text-slate-700">
                  <span className="inline-flex items-center gap-1 text-purple-600">
                    <Reply className="h-3.5 w-3.5" />
                    {(b as any).total_replies ?? b.replies_count ?? 0}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-xs whitespace-nowrap">
                  {formatDate((b as any).publication_date || b.created_at)}
                </td>
                <td className="px-4 py-3.5">{getApprovalBadge(b.approval_status)}</td>
                <td className="px-4 py-3.5 text-right font-bold text-[#f48840]">
                  {(b as any).engagement_score ?? ((b as any).total_views || 0) + ((b as any).total_likes || 0) * 3 + ((b as any).total_comments || 0) * 4}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
