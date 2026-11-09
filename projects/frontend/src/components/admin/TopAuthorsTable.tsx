"use client";

import React from "react";
import Link from "next/link";
import { TopAuthor } from "@/types";
import { Eye, Heart, MessageSquare, Reply, Award } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";

interface TopAuthorsTableProps {
  authors: TopAuthor[];
}

export function TopAuthorsTable({ authors }: TopAuthorsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-slate-600">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-700">
          <tr>
            <th className="px-4 py-3">Rank</th>
            <th className="px-4 py-3">Author</th>
            <th className="px-4 py-3 text-center">Total Blogs</th>
            <th className="px-4 py-3 text-center">Approved</th>
            <th className="px-4 py-3 text-center">Views</th>
            <th className="px-4 py-3 text-center">Likes</th>
            <th className="px-4 py-3 text-center">Comments</th>
            <th className="px-4 py-3 text-center">Replies</th>
            <th className="px-4 py-3 text-right">Engagement</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {authors.length === 0 ? (
            <tr>
              <td colSpan={9} className="px-4 py-8 text-center text-slate-400">
                No author interaction data recorded yet.
              </td>
            </tr>
          ) : (
            authors.map((a, idx) => (
              <tr key={a.id} className="hover:bg-slate-50">
                <td className="px-4 py-3.5 font-bold text-slate-400">
                  {idx === 0 ? (
                    <span className="flex items-center gap-1 text-amber-500 font-bold">
                      <Award className="h-4 w-4" /> #1
                    </span>
                  ) : (
                    `#${idx + 1}`
                  )}
                </td>
                <td className="px-4 py-3.5">
                  <Link
                    href={`/author/${a.username}`}
                    className="flex items-center gap-2.5 hover:opacity-90 group"
                  >
                    <Avatar
                      src={(a as any).profile_image || a.avatar_url}
                      name={(a as any).author_name || a.name || a.username}
                      size="sm"
                    />
                    <div>
                      <p className="font-semibold text-slate-900 text-xs group-hover:text-[#f48840]">
                        {(a as any).author_name || a.name || a.username}
                      </p>
                      <p className="text-[11px] text-slate-400">@{a.username}</p>
                    </div>
                  </Link>
                </td>
                <td className="px-4 py-3.5 text-center font-medium text-slate-800">
                  {a.total_blogs}
                </td>
                <td className="px-4 py-3.5 text-center font-medium text-emerald-600">
                  {a.approved_blogs}
                </td>
                <td className="px-4 py-3.5 text-center text-slate-700">
                  <span className="inline-flex items-center gap-1 text-xs">
                    <Eye className="h-3 w-3 text-slate-400" />
                    {a.total_views}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-center text-slate-700">
                  <span className="inline-flex items-center gap-1 text-xs text-rose-600">
                    <Heart className="h-3 w-3 fill-rose-500" />
                    {a.total_likes}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-center text-slate-700">
                  <span className="inline-flex items-center gap-1 text-xs text-[#f48840]">
                    <MessageSquare className="h-3 w-3" />
                    {a.total_comments}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-center text-slate-700">
                  <span className="inline-flex items-center gap-1 text-xs text-purple-600">
                    <Reply className="h-3 w-3" />
                    {a.total_replies}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-right font-bold text-[#f48840]">
                  {(a as any).total_engagement ?? (a.total_views + a.total_likes * 3 + a.total_comments * 4)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
