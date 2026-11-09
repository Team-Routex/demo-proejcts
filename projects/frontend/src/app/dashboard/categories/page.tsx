"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Dialog } from "@/components/ui/Dialog";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { FolderTree, Plus, Search, ArrowRight, AlertCircle } from "lucide-react";

export default function UserCategoriesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.categories.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.categories.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setModalOpen(false);
      setName("");
      setDescription("");
      setError(null);
    },
    onError: (err: any) => {
      setError(err?.message || "Failed to create category");
    },
  });

  const filteredCategories = categories.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Platform Categories
          </h1>
          <p className="text-sm text-slate-500">
            Shared topics across the entire platform. Anyone can contribute a new topic.
          </p>
        </div>
        <Button onClick={() => setModalOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Create Category
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Filter categories..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      ) : filteredCategories.length === 0 ? (
        <div className="p-8 text-center text-slate-400 border rounded-xl">
          No categories match your search.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCategories.map((cat) => (
            <Card key={cat.id} className="hover:bg-slate-50 transition-colors">
              <CardHeader className="p-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{cat.name}</CardTitle>
                  <Badge variant="default" className="text-xs">
                    {cat.blog_count || 0} blogs
                  </Badge>
                </div>
                <CardDescription className="text-xs line-clamp-2 mt-1">
                  {cat.description || "Articles tagged with " + cat.name}
                </CardDescription>
                <div className="pt-2">
                  <Link
                    href={`/categories/${cat.slug}`}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-[#f48840] hover:underline"
                  >
                    <span>View articles</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Create New Category"
        description="Categories are shared globally across all authors on RaftBlog."
      >
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase text-slate-600">Category Name</label>
            <Input
              placeholder="e.g. Distributed Consensus"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase text-slate-600">Description</label>
            <Textarea
              placeholder="What kind of articles belong in this topic?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-[80px]"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              isLoading={createMutation.isPending}
              disabled={!name.trim()}
              onClick={() => createMutation.mutate({ name: name.trim(), description: description.trim() })}
            >
              Create Category
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

