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
import { Category } from "@/types";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";
import {
  FolderTree,
  Plus,
  Trash2,
  Edit2,
  ExternalLink,
  Search,
  AlertCircle,
} from "lucide-react";

const columnHelper = createColumnHelper<Category>();

export default function AdminCategoriesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["admin-categories"],
    queryFn: () => api.admin.categories(),
  });

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      api.categories.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] });
      setModalOpen(false);
      setName("");
      setDescription("");
      setError(null);
    },
    onError: (err: any) => setError(err?.message || "Failed to create category"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { name: string; description?: string } }) =>
      api.admin.updateCategory(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] });
      setEditingCategory(null);
      setName("");
      setDescription("");
      setError(null);
    },
    onError: (err: any) => setError(err?.message || "Failed to update category"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.admin.deleteCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] });
    },
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: "Category Name",
        cell: (info) => {
          const c = info.row.original;
          return (
            <div>
              <p className="font-semibold text-xs text-slate-900">
                {info.getValue()}
              </p>
              <p className="text-[11px] text-slate-400 font-mono">/{c.slug}</p>
            </div>
          );
        },
      }),
      columnHelper.accessor("description", {
        header: "Description",
        cell: (info) => (
          <p className="text-xs text-slate-600 max-w-sm line-clamp-2">
            {info.getValue() || "—"}
          </p>
        ),
      }),
      columnHelper.accessor("blog_count", {
        header: "Associated Blogs",
        cell: (info) => (
          <Badge variant="default" className="text-[11px]">
            {info.getValue() || 0} articles
          </Badge>
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
          const c = info.row.original;
          return (
            <div className="flex items-center justify-end gap-1.5">
              <Link
                href={`/categories/${c.slug}`}
                target="_blank"
                className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900"
                title="View on site"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
              <button
                onClick={() => {
                  setEditingCategory(c);
                  setName(c.name);
                  setDescription(c.description || "");
                  setError(null);
                }}
                className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                title="Edit category"
              >
                <Edit2 className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => {
                  if (confirm(`Delete category "${c.name}"? Articles tagged with this category will remain, but the category association will be deleted.`)) {
                    deleteMutation.mutate(c.id);
                  }
                }}
                className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                title="Delete category"
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

  const filteredCategories = useMemo(
    () =>
      categories.filter(
        (c) =>
          c.name.toLowerCase().includes(search.toLowerCase()) ||
          c.description?.toLowerCase().includes(search.toLowerCase())
      ),
    [categories, search]
  );

  const table = useReactTable({
    data: filteredCategories,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Category &amp; Taxonomy Management
          </h1>
          <p className="text-sm text-slate-500">
            Manage global content categories, modify slugs and descriptions, and monitor usage volume
          </p>
        </div>
        <Button
          onClick={() => {
            setModalOpen(true);
            setName("");
            setDescription("");
            setError(null);
          }}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Category
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Filter categories..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
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
                {filteredCategories.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                      No categories found.
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
      </div>

      {/* Add / Edit Dialog */}
      <Dialog
        open={modalOpen || !!editingCategory}
        onClose={() => {
          setModalOpen(false);
          setEditingCategory(null);
        }}
        title={editingCategory ? "Edit Category" : "Create New Category"}
        description="Provide a descriptive name and summary for this taxonomy tag."
      >
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase text-slate-600">Name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Distributed Consensus"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase text-slate-600">Description</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what articles should be classified under this topic..."
              className="min-h-[85px]"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setModalOpen(false);
                setEditingCategory(null);
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              isLoading={createMutation.isPending || updateMutation.isPending}
              disabled={!name.trim()}
              onClick={() => {
                if (editingCategory) {
                  updateMutation.mutate({
                    id: editingCategory.id,
                    payload: { name: name.trim(), description: description.trim() },
                  });
                } else {
                  createMutation.mutate({
                    name: name.trim(),
                    description: description.trim(),
                  });
                }
              }}
            >
              {editingCategory ? "Save Changes" : "Create Category"}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

