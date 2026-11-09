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
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";
import {
  PenSquare,
  Trash2,
  Send,
  Eye,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Plus,
  AlertCircle,
} from "lucide-react";

const columnHelper = createColumnHelper<Blog>();

export default function MyBlogsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  const { data, isLoading } = useQuery({
    queryKey: ["my-blogs-table", statusFilter, page],
    queryFn: () =>
      api.blogs.myBlogs({
        status: statusFilter,
        page,
        limit: 10,
      }),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.blogs.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-blogs-table"] });
      queryClient.invalidateQueries({ queryKey: ["my-blogs-preview"] });
    },
  });

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: (id: number) => api.blogs.submit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-blogs-table"] });
      queryClient.invalidateQueries({ queryKey: ["my-blogs-preview"] });
    },
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("title", {
        header: "Title",
        cell: (info) => {
          const blog = info.row.original;
          return (
            <div className="max-w-md">
              <Link
                href={`/dashboard/blogs/${blog.id}/edit`}
                className="font-semibold text-slate-900 hover:opacity-90 line-clamp-1"
              >
                {info.getValue()}
              </Link>
              {blog.approval_status === "rejected" && (
                <div className="mt-1 flex items-start gap-1 rounded bg-rose-50 border border-rose-200 px-2 py-1 text-xs text-rose-700">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-rose-500" />
                  <div>
                    <span className="font-bold">Rejection Reason: </span>
                    <span>{blog.rejection_reason || "Content does not meet publication guidelines."}</span>
                  </div>
                </div>
              )}
            </div>
          );
        },
      }),
      columnHelper.accessor("publication_status", {
        header: "Publication",
        cell: (info) => (
          <span className="capitalize text-xs text-slate-600">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor("approval_status", {
        header: "Review Status",
        cell: (info) => {
          const val = info.getValue();
          switch (val) {
            case "approved":
              return <Badge variant="success">Approved</Badge>;
            case "pending":
              return <Badge variant="warning">In Review</Badge>;
            case "rejected":
              return <Badge variant="destructive">Rejected</Badge>;
            default:
              return <Badge variant="secondary">Draft</Badge>;
          }
        },
      }),
      columnHelper.accessor("views_count", {
        header: "Reads",
        cell: (info) => (
          <span className="inline-flex items-center gap-1 text-xs text-slate-600">
            <Eye className="h-3 w-3 text-slate-400" />
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor("created_at", {
        header: "Created",
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
          const blog = info.row.original;
          return (
            <div className="flex items-center justify-end gap-1.5">
              {blog.approval_status === "approved" && (
                <Link
                  href={`/blogs/${blog.slug}`}
                  target="_blank"
                  className="rounded p-1.5 text-slate-400 hover:text-slate-600 hover:text-slate-900"
                  title="View on public site"
                >
                  <ExternalLink className="h-4 w-4" />
                </Link>
              )}
              {(blog.approval_status === "rejected" ||
                blog.publication_status === "draft") && (
                <button
                  onClick={() => {
                    if (confirm("Submit this blog for administrative review?")) {
                      submitMutation.mutate(blog.id);
                    }
                  }}
                  className="rounded p-1.5 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                  title="Submit for review"
                >
                  <Send className="h-4 w-4" />
                </button>
              )}
              <Link
                href={`/dashboard/blogs/${blog.id}/edit`}
                className="rounded p-1.5 text-slate-400 hover:text-slate-600 hover:text-slate-900"
                title="Edit blog"
              >
                <PenSquare className="h-4 w-4" />
              </Link>
              <button
                onClick={() => {
                  if (confirm("Are you sure you want to delete this blog?")) {
                    deleteMutation.mutate(blog.id);
                  }
                }}
                className="rounded p-1.5 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                title="Delete blog"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          );
        },
      }),
    ],
    [deleteMutation, submitMutation]
  );

  const items = useMemo(() => data?.items || [], [data]);

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const filterTabs = [
    { label: "All Stories", value: "" },
    { label: "Approved", value: "approved" },
    { label: "In Review", value: "pending" },
    { label: "Drafts", value: "draft" },
    { label: "Rejected", value: "rejected" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            My Blog Publications
          </h1>
          <p className="text-sm text-slate-500">
            Manage your draft manuscripts, submit for review, or view live engagement
          </p>
        </div>
        <Link href="/dashboard/blogs/create">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Write New Blog
          </Button>
        </Link>
      </div>

      {/* Filter Tabs */}
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
                ? "bg-[#f48840] text-white"
                : "bg-slate-100 text-slate-600 hover:text-slate-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-slate-500 text-sm">No blogs found in this category.</p>
            <Link href="/dashboard/blogs/create" className="mt-3 inline-block">
              <Button size="sm">Create your first blog</Button>
            </Link>
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
                {table.getRowModel().rows.map((row) => (
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
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination footer */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
            <span className="text-xs text-slate-500">
              Page {data.page} of {data.total_pages} ({data.total} total)
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

