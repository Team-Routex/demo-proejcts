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
import { Blog } from "@/types";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";
import {
  Search,
  Check,
  X,
  Trash2,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Eye,
  Heart,
  MessageSquare,
} from "lucide-react";

const columnHelper = createColumnHelper<Blog>();

export default function AdminBlogsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [rejectBlog, setRejectBlog] = useState<Blog | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-blogs-table", search, statusFilter, page],
    queryFn: () =>
      api.admin.blogs({
        search,
        status: statusFilter,
        page,
        limit: 10,
      }),
  });

  const moderateMutation = useMutation({
    mutationFn: ({
      id,
      action,
      rejection_reason,
    }: {
      id: number;
      action: "approve" | "reject";
      rejection_reason?: string;
    }) => api.admin.moderateBlog(id, action, rejection_reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-blogs-table"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
      setRejectBlog(null);
      setRejectionReason("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.admin.deleteBlog(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-blogs-table"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("title", {
        header: "Article Title",
        cell: (info) => {
          const b = info.row.original;
          return (
            <div className="max-w-xs sm:max-w-md">
              <p className="font-semibold text-xs text-slate-900 line-clamp-1">
                {info.getValue()}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                Author: {typeof b.author === "object" ? (b.author?.full_name || b.author?.username) : (b.author || "Unknown")}
              </p>
            </div>
          );
        },
      }),
      columnHelper.accessor("approval_status", {
        header: "Review Status",
        cell: (info) => {
          const s = info.getValue();
          switch (s) {
            case "approved":
              return <Badge variant="success">Approved</Badge>;
            case "pending":
              return <Badge variant="warning">Pending</Badge>;
            case "rejected":
              return <Badge variant="destructive">Rejected</Badge>;
            default:
              return <Badge variant="secondary">Draft</Badge>;
          }
        },
      }),
      columnHelper.accessor("publication_status", {
        header: "Published",
        cell: (info) => (
          <span className="capitalize text-xs text-slate-500">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor("views_count", {
        header: "Engagement",
        cell: (info) => {
          const b = info.row.original;
          return (
            <div className="flex items-center gap-2 text-[11px] text-slate-500">
              <span className="flex items-center gap-0.5">
                <Eye className="h-3 w-3" /> {b.views_count}
              </span>
              <span className="flex items-center gap-0.5 text-rose-600">
                <Heart className="h-3 w-3" /> {b.likes_count || 0}
              </span>
              <span className="flex items-center gap-0.5 text-[#f48840]">
                <MessageSquare className="h-3 w-3" /> {b.comments_count || 0}
              </span>
            </div>
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
        header: () => <div className="text-right">Moderation</div>,
        cell: (info) => {
          const b = info.row.original;
          return (
            <div className="flex items-center justify-end gap-1.5">
              {b.approval_status !== "approved" && (
                <button
                  onClick={() => moderateMutation.mutate({ id: b.id, action: "approve" })}
                  className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                  title="Approve article"
                >
                  <Check className="h-4 w-4" />
                </button>
              )}
              {b.approval_status !== "rejected" && (
                <button
                  onClick={() => {
                    setRejectBlog(b);
                    setRejectionReason("");
                  }}
                  className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                  title="Reject article with feedback"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
              {b.approval_status === "approved" && (
                <Link
                  href={`/blogs/${b.slug}`}
                  target="_blank"
                  className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900"
                  title="Open live article"
                >
                  <ExternalLink className="h-4 w-4" />
                </Link>
              )}
              <button
                onClick={() => {
                  if (confirm(`Permanently delete "${b.title}"?`)) {
                    deleteMutation.mutate(b.id);
                  }
                }}
                className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                title="Delete article"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          );
        },
      }),
    ],
    [moderateMutation, deleteMutation]
  );

  const items = useMemo(() => data?.items || [], [data]);

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const filterTabs = [
    { label: "All Blogs", value: "" },
    { label: "Pending Approval", value: "pending" },
    { label: "Approved", value: "approved" },
    { label: "Rejected", value: "rejected" },
    { label: "Drafts", value: "draft" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Editorial Blog Moderation
        </h1>
        <p className="text-sm text-slate-500">
          Review submissions, approve manuscripts, provide feedback on rejections, or delete articles
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        {filterTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => {
              setStatusFilter(tab.value);
              setPage(1);
            }}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors cursor-pointer ${
              statusFilter === tab.value
                ? "bg-[#f48840] text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:text-[#f48840] hover:bg-orange-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search by article title..."
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
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                      No blogs found for this filter.
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
              Page {data.page} of {data.total_pages} ({data.total} total blogs)
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

      {/* Reject Modal */}
      <Dialog
        open={!!rejectBlog}
        onClose={() => setRejectBlog(null)}
        title="Reject Article Submission"
        description={`Provide constructive feedback for the author regarding "${rejectBlog?.title}"`}
      >
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase text-slate-600">Rejection Reason</label>
            <Textarea
              placeholder="Explain why this article cannot be published in its current form..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              className="min-h-[100px]"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setRejectBlog(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              isLoading={moderateMutation.isPending}
              disabled={!rejectionReason.trim()}
              onClick={() => {
                if (rejectBlog) {
                  moderateMutation.mutate({
                    id: rejectBlog.id,
                    action: "reject",
                    rejection_reason: rejectionReason.trim(),
                  });
                }
              }}
            >
              Reject Article
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

