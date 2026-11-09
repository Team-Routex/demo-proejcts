"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from "@tanstack/react-table";
import { api } from "@/lib/api";
import { Comment } from "@/types";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { Avatar } from "@/components/ui/Avatar";
import { formatDate } from "@/lib/utils";
import {
  Search,
  Trash2,
  ExternalLink,
  MessageSquare,
  CornerDownRight,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const columnHelper = createColumnHelper<Comment>();

export default function AdminCommentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-comments-table", search, page],
    queryFn: () =>
      api.admin.comments({
        search,
        page,
        limit: 12,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.admin.deleteComment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-comments-table"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("content", {
        header: "Comment Content",
        cell: (info) => {
          const c = info.row.original;
          return (
            <div className="max-w-md">
              <div className="flex items-center gap-1.5 mb-1">
                {c.parent_id ? (
                  <Badge variant="secondary" className="gap-1 text-[10px] py-0 px-1.5">
                    <CornerDownRight className="h-3 w-3" /> Threaded Reply
                  </Badge>
                ) : (
                  <Badge variant="default" className="gap-1 text-[10px] py-0 px-1.5">
                    <MessageSquare className="h-3 w-3" /> Top-Level
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-800 line-clamp-2 leading-relaxed">
                {info.getValue()}
              </p>
            </div>
          );
        },
      }),
      columnHelper.accessor("user", {
        header: "Author",
        cell: (info) => {
          const u = info.getValue();
          return (
            <div className="flex items-center gap-2">
              <Avatar
                src={u?.avatar_url}
                name={u?.full_name || u?.username}
                size="xs"
              />
              <span className="text-xs font-semibold text-slate-900">
                {u?.full_name || u?.username || "Unknown"}
              </span>
            </div>
          );
        },
      }),
      columnHelper.accessor("blog_id", {
        header: "Blog Post",
        cell: (info) => {
          const c = info.row.original as any;
          return c.blog_slug ? (
            <Link
              href={`/blogs/${c.blog_slug}`}
              target="_blank"
              className="text-xs font-medium text-[#f48840] hover:underline max-w-[180px] truncate inline-flex items-center gap-1"
            >
              <span>{c.blog_title || `Blog #${c.blog_id}`}</span>
              <ExternalLink className="h-3 w-3 text-slate-400 shrink-0" />
            </Link>
          ) : (
            <span className="text-xs text-slate-500">
              {c.blog_title || `Blog #${c.blog_id}`}
            </span>
          );
        },
      }),
      columnHelper.accessor("created_at", {
        header: "Date",
        cell: (info) => (
          <span className="text-xs text-slate-500 whitespace-nowrap">
            {formatDate(info.getValue())}
          </span>
        ),
      }),
      columnHelper.display({
        id: "actions",
        header: () => <div className="text-right">Actions</div>,
        cell: (info) => {
          const c = info.row.original;
          return (
            <div className="flex items-center justify-end gap-1.5">
              <button
                onClick={() => {
                  if (confirm("Delete this comment permanently?")) {
                    deleteMutation.mutate(c.id);
                  }
                }}
                className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                title="Moderate / Delete comment"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        },
      }),
    ],
    [deleteMutation]
  );

  const items = useMemo(() => data?.items || [], [data]);

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Comment &amp; Discussion Moderation
        </h1>
        <p className="text-sm text-slate-500">
          Audit user feedback, threaded replies, and prune abusive or inappropriate contributions
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search by comment keyword..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="pl-9 text-xs"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-700">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-4 py-3.5">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                      No comments found.
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      className="hover:bg-slate-50 transition-colors"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3.5">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
            <span className="text-xs text-slate-500">
              Page {data.page} of {data.total_pages} ({data.total} total comments)
            </span>
            <div className="flex gap-1.5">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

