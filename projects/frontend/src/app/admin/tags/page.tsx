"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Tag } from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";
import {
  Tag as TagIcon,
  Plus,
  Edit2,
  Trash2,
  Search,
  CheckCircle,
  AlertCircle,
  X,
  FileText,
} from "lucide-react";

export default function AdminTagsPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: tags = [], isLoading } = useQuery<Tag[]>({
    queryKey: ["admin-tags"],
    queryFn: () => api.admin.tags(),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingTag) {
        return api.admin.updateTag(editingTag.id, {
          name: name.trim(),
          slug: slug.trim() || undefined,
          description: description.trim(),
        });
      } else {
        return api.admin.createTag({
          name: name.trim(),
          slug: slug.trim() || undefined,
          description: description.trim(),
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tags"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["tags-sidebar"] });
      setModalOpen(false);
      setEditingTag(null);
      setName("");
      setSlug("");
      setDescription("");
      setSuccessMessage(editingTag ? "Tag updated successfully." : "New tag created successfully.");
      setTimeout(() => setSuccessMessage(null), 4000);
    },
    onError: (err: any) => {
      setErrorMessage(err?.message || "Failed to save tag.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      return api.admin.deleteTag(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tags"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["tags-sidebar"] });
      setDeleteConfirmId(null);
      setSuccessMessage("Tag deleted successfully.");
      setTimeout(() => setSuccessMessage(null), 4000);
    },
    onError: (err: any) => {
      setErrorMessage(err?.message || "Failed to delete tag.");
    },
  });

  const openCreateModal = () => {
    setEditingTag(null);
    setName("");
    setSlug("");
    setDescription("");
    setErrorMessage(null);
    setModalOpen(true);
  };

  const openEditModal = (t: Tag) => {
    setEditingTag(t);
    setName(t.name);
    setSlug(t.slug);
    setDescription(t.description || "");
    setErrorMessage(null);
    setModalOpen(true);
  };

  const handleNameChange = (val: string) => {
    setName(val);
    if (!editingTag) {
      setSlug(
        val
          .toLowerCase()
          .replace(/[^\w\s-]/g, "")
          .replace(/[\s_-]+/g, "-")
          .replace(/^-+|-+$/g, "")
      );
    }
  };

  const filteredTags = tags.filter((t) => {
    const q = searchTerm.toLowerCase().trim();
    if (!q) return true;
    return (
      t.name.toLowerCase().includes(q) ||
      t.slug.toLowerCase().includes(q) ||
      (t.description && t.description.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-black uppercase tracking-widest text-[#f48840]">
            Taxonomy &amp; Metadata
          </span>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-[#20232e]">
            Tags Management
          </h1>
          <p className="text-xs text-[#7a7a7a] mt-1">
            Organize article classification and discoverability using pure RaftSQLORM
          </p>
        </div>

        <Button
          onClick={openCreateModal}
          className="bg-[#f48840] hover:bg-[#e0752d] text-white gap-2 shadow-xs"
        >
          <Plus className="h-4 w-4" />
          <span>Add New Tag</span>
        </Button>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-xs font-bold text-emerald-800">
          <CheckCircle className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 p-4 text-xs font-bold text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Filter / Search Bar */}
      <div className="bg-white p-4 border border-[#eee] rounded-xl flex items-center justify-between shadow-xs">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#aaa]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search tags by name or slug..."
            className="w-full pl-9 pr-4 py-2 border border-[#eee] bg-[#f7f7f7] text-xs text-[#20232e] placeholder-[#aaa] rounded-md focus:border-[#f48840] focus:outline-none transition-colors"
          />
        </div>
        <div className="text-xs font-bold text-[#7a7a7a]">
          Total: <span className="text-[#f48840]">{tags.length}</span> tags
        </div>
      </div>

      {/* Tags Table */}
      <Card className="border-[#eee] shadow-xs">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="border-b border-[#eee] bg-slate-50 font-bold uppercase tracking-wider text-slate-700">
                <tr>
                  <th className="px-5 py-3.5">Tag Name</th>
                  <th className="px-5 py-3.5">Slug</th>
                  <th className="px-5 py-3.5">Description</th>
                  <th className="px-5 py-3.5 text-center">Linked Articles</th>
                  <th className="px-5 py-3.5">Created</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#eee]">
                {isLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan={6} className="px-5 py-4">
                        <Skeleton className="h-6 w-full" />
                      </td>
                    </tr>
                  ))
                ) : filteredTags.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                      <TagIcon className="mx-auto h-8 w-8 text-slate-300 mb-2" />
                      <p className="font-semibold text-slate-600">No tags found</p>
                      <p className="text-[11px] mt-1">Click "Add New Tag" to create one.</p>
                    </td>
                  </tr>
                ) : (
                  filteredTags.map((tag) => (
                    <tr key={tag.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-5 py-4 font-bold text-slate-900">
                        <span className="inline-flex items-center gap-1.5 bg-orange-50 text-[#f48840] px-2.5 py-1 rounded-md font-bold">
                          <TagIcon className="h-3 w-3" />
                          #{tag.name}
                        </span>
                      </td>
                      <td className="px-5 py-4 font-mono text-[11px] text-slate-500">
                        {tag.slug}
                      </td>
                      <td className="px-5 py-4 max-w-xs truncate text-slate-600">
                        {tag.description || <span className="text-slate-300 italic">None</span>}
                      </td>
                      <td className="px-5 py-4 text-center">
                        <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full font-bold">
                          <FileText className="h-3 w-3 text-slate-400" />
                          {tag.blog_count ?? 0}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-slate-400 text-[11px]">
                        {formatDate(tag.created_at)}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => openEditModal(tag)}
                            className="p-1.5 text-slate-400 hover:text-[#f48840] hover:bg-orange-50 rounded transition-colors cursor-pointer"
                            title="Edit Tag"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(tag.id)}
                            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors cursor-pointer"
                            title="Delete Tag"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Create / Edit Tag Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white border border-[#eee] rounded-xl max-w-md w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between p-5 border-b border-[#eee]">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-50 text-[#f48840]">
                  <TagIcon className="h-4 w-4" />
                </div>
                <h3 className="font-bold text-sm text-[#20232e]">
                  {editingTag ? "Edit Tag" : "Create New Tag"}
                </h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                saveMutation.mutate();
              }}
              className="p-5 space-y-4"
            >
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Tag Name *
                </label>
                <Input
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="e.g. Distributed Consensus"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Tag Slug
                </label>
                <Input
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  placeholder="e.g. distributed-consensus"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Description
                </label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of articles that fall under this tag..."
                  className="min-h-[80px]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#eee]">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setModalOpen(false)}
                  disabled={saveMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-[#f48840] hover:bg-[#e0752d] text-white"
                  isLoading={saveMutation.isPending}
                >
                  {editingTag ? "Save Changes" : "Create Tag"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white border border-[#eee] rounded-xl max-w-sm w-full p-6 shadow-2xl text-center space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600">
              <Trash2 className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900">Delete Tag</h3>
              <p className="text-xs text-slate-500 mt-1">
                Are you sure you want to permanently delete this tag? It will be removed from all associated articles.
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setDeleteConfirmId(null)}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => deleteMutation.mutate(deleteConfirmId)}
                isLoading={deleteMutation.isPending}
              >
                Yes, Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

