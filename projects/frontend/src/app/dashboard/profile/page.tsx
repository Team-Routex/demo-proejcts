"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Badge } from "@/components/ui/Badge";
import { Avatar } from "@/components/ui/Avatar";
import {
  User,
  Upload,
  CheckCircle,
  AlertCircle,
  Save,
  Globe,
} from "lucide-react";

export default function ProfileSettingsPage() {
  const { user, refreshUser } = useAuth();
  const [fullName, setFullName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [website, setWebsite] = useState("");
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setBio(user.bio || "");
      setAvatarUrl(user.avatar_url || "");
      setWebsite(user.website || "");
    }
  }, [user]);

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingAvatar(true);
    setError(null);
    try {
      const url = await api.uploadFile(file);
      setAvatarUrl(url);
    } catch (err: any) {
      setError(err?.message || "Failed to upload avatar image");
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await api.auth.updateProfile({
        full_name: fullName.trim(),
        bio: bio.trim(),
        avatar_url: avatarUrl.trim(),
        website: website.trim(),
      });
      await refreshUser();
      setSuccess(true);
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: any) {
      setError(err?.message || "Failed to update profile settings.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Profile Settings
        </h1>
        <p className="text-sm text-slate-500">
          Manage your public author identity, avatar, and biographical details
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Author Information</CardTitle>
              <CardDescription>
                This information appears on your published stories and public profile
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {user?.is_verified ? (
                <Badge variant="success" className="gap-1">
                  <CheckCircle className="h-3 w-3" /> Verified Author
                </Badge>
              ) : (
                <Badge variant="secondary">Standard Account</Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {success && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
              <CheckCircle className="h-4 w-4 shrink-0" />
              <span>Your profile changes have been saved successfully!</span>
            </div>
          )}

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSave} className="space-y-6">
            {/* Avatar section */}
            <div className="flex items-center gap-5">
              <Avatar
                src={avatarUrl}
                name={fullName || user?.username}
                size="xl"
              />
              <div className="space-y-2">
                <label className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:opacity-90 cursor-pointer">
                  <Upload className="h-3.5 w-3.5" />
                  <span>{uploadingAvatar ? "Uploading..." : "Upload New Avatar"}</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarUpload}
                    className="hidden"
                    disabled={uploadingAvatar}
                  />
                </label>
                <p className="text-[11px] text-slate-400">
                  Recommended size 200x200px. PNG, JPG or WebP.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-slate-600">
                  Full Name
                </label>
                <Input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your Full Name"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-slate-600">
                  Website URL
                </label>
                <Input
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  placeholder="https://yourportfolio.dev"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-slate-400">
                  Username (Read-only)
                </label>
                <Input value={user?.username || ""} disabled className="bg-slate-50 opacity-70" />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase text-slate-400">
                  Email Address (Read-only)
                </label>
                <Input value={user?.email || ""} disabled className="bg-slate-50 opacity-70" />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase text-slate-600">
                Bio / About You
              </label>
              <Textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Share a short bio about your engineering expertise and focus..."
                className="min-h-[100px]"
              />
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" isLoading={isSaving} className="gap-2">
                <Save className="h-4 w-4" />
                Save Changes
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

