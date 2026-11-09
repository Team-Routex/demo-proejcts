"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Blog, Category, Tag } from "@/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Upload,
  Image as ImageIcon,
  Save,
  Send,
  AlertCircle,
  CheckCircle2,
  X,
  Tag as TagIcon,
} from "lucide-react";

interface BlogEditorProps {
  initialBlog?: Blog;
  isEditing?: boolean;
}

export function BlogEditor({ initialBlog, isEditing = false }: BlogEditorProps) {
  const router = useRouter();
  const [title, setTitle] = useState(initialBlog?.title || "");
  const [summary, setSummary] = useState(initialBlog?.summary || "");
  const [content, setContent] = useState(initialBlog?.content || "");
  const [featuredImage, setFeaturedImage] = useState(initialBlog?.featured_image || "");
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>(
    initialBlog?.categories?.map((c) => c.id) || []
  );
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>(
    initialBlog?.tags?.map((t) => t.id) || []
  );
  const [uploadingImage, setUploadingImage] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch available shared categories
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => api.categories.list(),
  });

  // Fetch available tags
  const { data: tags = [] } = useQuery<Tag[]>({
    queryKey: ["tags"],
    queryFn: () => api.tags.list(),
  });

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    setError(null);
    try {
      const url = await api.uploadFile(file);
      setFeaturedImage(url);
    } catch (err: any) {
      setError(err?.message || "Image upload failed");
    } finally {
      setUploadingImage(false);
    }
  };

  const toggleCategory = (id: number) => {
    setSelectedCategoryIds((prev) =>
      prev.includes(id) ? prev.filter((cId) => cId !== id) : [...prev, id]
    );
  };

  const toggleTag = (id: number) => {
    setSelectedTagIds((prev) =>
      prev.includes(id) ? prev.filter((tId) => tId !== id) : [...prev, id]
    );
  };

  const handleSave = async (action: "draft" | "submit") => {
    if (!title.trim()) {
      setError("Article title is required.");
      return;
    }
    if (!content.trim()) {
      setError("Article body content cannot be empty.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      if (isEditing && initialBlog) {
        await api.blogs.update(initialBlog.id, {
          title: title.trim(),
          summary: summary.trim(),
          content: content.trim(),
          featured_image: featuredImage.trim(),
          category_ids: selectedCategoryIds,
          tag_ids: selectedTagIds,
          action,
        });
      } else {
        await api.blogs.create({
          title: title.trim(),
          summary: summary.trim(),
          content: content.trim(),
          featured_image: featuredImage.trim(),
          category_ids: selectedCategoryIds,
          tag_ids: selectedTagIds,
          action,
        });
      }
      router.push("/dashboard/blogs");
    } catch (err: any) {
      setError(err?.message || "Failed to save blog post.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {initialBlog?.approval_status === "rejected" && (
        <div className="flex items-start gap-3 rounded-lg bg-rose-50 border border-rose-200 p-4 text-sm text-rose-800">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-600 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold">Editorial Review: Revision Requested</h4>
            <p className="text-xs text-rose-700">
              <strong>Rejection Reason:</strong>{" "}
              {initialBlog.rejection_reason || "Content does not meet publication guidelines."}
            </p>
            <p className="text-[11px] text-rose-600">
              Please revise your content and click &quot;Submit for Approval&quot; to resubmit for editorial review.
            </p>
          </div>
        </div>
      )}

      {initialBlog?.approval_status === "pending" && (
        <div className="flex items-center gap-3 rounded-lg bg-amber-50 border border-amber-200 p-4 text-xs text-amber-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
          <span>This article is currently <strong>in review</strong> by platform administrators.</span>
        </div>
      )}

      {initialBlog?.approval_status === "approved" && (
        <div className="flex items-center gap-3 rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-xs text-emerald-800">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>This article has been <strong>approved</strong> and is live on the public blog.</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Main writing column */}
        <div className="lg:col-span-8 space-y-6">
          <Card>
            <CardContent className="p-6 space-y-4">
              {/* Title */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Article Title
                </label>
                <Input
                  placeholder="Enter a compelling title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="text-lg font-semibold h-12"
                />
              </div>

              {/* Summary / Excerpt */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Summary / Excerpt (Optional)
                </label>
                <Textarea
                  placeholder="A short teaser (1-2 sentences) summarizing your insights..."
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  className="min-h-[75px]"
                />
              </div>

              {/* Main Content */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Content (Markdown Supported)
                  </label>
                  <span className="text-[11px] text-slate-400">
                    Supports ## Headings, lists, code
                  </span>
                </div>
                <Textarea
                  placeholder="Write your article here in markdown format...&#10;&#10;## Introduction&#10;In this article we will explore..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="min-h-[350px] font-mono text-sm leading-relaxed"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar settings column */}
        <div className="lg:col-span-4 space-y-6">
          {/* Publishing actions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Publication Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              <Button
                variant="outline"
                className="w-full gap-2 text-slate-700"
                onClick={() => handleSave("draft")}
                isLoading={isSubmitting}
              >
                <Save className="h-4 w-4" />
                Save as Draft
              </Button>
              <Button
                variant="primary"
                className="w-full gap-2"
                onClick={() => handleSave("submit")}
                isLoading={isSubmitting}
              >
                <Send className="h-4 w-4" />
                Submit for Approval
              </Button>
              <p className="text-[11px] text-slate-400 text-center leading-tight pt-1">
                Submitted articles will be reviewed by platform administrators before appearing publicly.
              </p>
            </CardContent>
          </Card>

          {/* Featured Image */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Featured Image</CardTitle>
              <CardDescription className="text-xs">
                Upload a cover photo or paste an external URL
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {featuredImage ? (
                <div className="relative aspect-video rounded-lg overflow-hidden border border-slate-200">
                  <img
                    src={featuredImage}
                    alt="Cover preview"
                    className="h-full w-full object-cover"
                  />
                  <button
                    onClick={() => setFeaturedImage("")}
                    className="absolute right-2 top-2 rounded-full bg-slate-900/70 p-1 text-white hover:opacity-90"
                    title="Remove image"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center aspect-video rounded-lg border-2 border-dashed border-slate-300 hover:opacity-90 cursor-pointer p-4 text-center transition-colors">
                  <Upload className="h-6 w-6 text-slate-400 mb-1" />
                  <span className="text-xs font-semibold text-slate-700">
                    {uploadingImage ? "Uploading image..." : "Upload Cover Image"}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-0.5">
                    PNG, JPG, WebP up to 5MB
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                    disabled={uploadingImage}
                  />
                </label>
              )}

              <Input
                placeholder="Or paste image URL directly..."
                value={featuredImage}
                onChange={(e) => setFeaturedImage(e.target.value)}
                className="text-xs"
              />
            </CardContent>
          </Card>

          {/* Categories */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Categories</CardTitle>
              <CardDescription className="text-xs">
                Classify your article into primary topics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {categories.length === 0 ? (
                  <p className="text-xs text-slate-400">Loading categories...</p>
                ) : (
                  categories.map((cat) => {
                    const isChecked = selectedCategoryIds.includes(cat.id);
                    return (
                      <label
                        key={cat.id}
                        onClick={() => toggleCategory(cat.id)}
                        className={`flex items-center justify-between p-2 rounded-lg border text-xs cursor-pointer transition-colors ${
                          isChecked
                            ? "border-[#f48840] bg-orange-50 text-orange-950 font-bold"
                            : "border-slate-200 hover:bg-[#f7f7f7]"
                        }`}
                      >
                        <span className="font-medium">{cat.name}</span>
                        {isChecked && <CheckCircle2 className="h-3.5 w-3.5 text-[#f48840]" />}
                      </label>
                    );
                  })
                )}
              </div>
            </CardContent>
          </Card>

          {/* Tags */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm flex items-center gap-1.5">
                    <TagIcon className="h-4 w-4 text-[#f48840]" />
                    <span>Tags</span>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Assign technical tags to help readers discover your post
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
                {tags.length === 0 ? (
                  <p className="text-xs text-slate-400">Loading tags...</p>
                ) : (
                  tags.map((t) => {
                    const isChecked = selectedTagIds.includes(t.id);
                    return (
                      <button
                        type="button"
                        key={t.id}
                        onClick={() => toggleTag(t.id)}
                        className={`px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider transition-colors cursor-pointer border ${
                          isChecked
                            ? "bg-[#f48840] text-white border-[#f48840] shadow-xs"
                            : "bg-[#f7f7f7] text-[#7a7a7a] border-[#eee] hover:border-[#f48840] hover:text-[#f48840]"
                        }`}
                      >
                        #{t.name}
                      </button>
                    );
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

