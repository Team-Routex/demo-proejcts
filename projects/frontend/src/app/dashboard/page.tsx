"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Avatar } from "@/components/ui/Avatar";
import { formatDate } from "@/lib/utils";
import {
  BookOpen,
  CheckCircle2,
  Clock,
  XCircle,
  FileText,
  Eye,
  Heart,
  MessageSquare,
  PenSquare,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

export default function UserDashboardOverviewPage() {
  const { user, stats } = useAuth();

  // Fetch recent user blogs
  const { data: myBlogs, isLoading: loadingBlogs } = useQuery({
    queryKey: ["my-blogs-preview"],
    queryFn: () => api.blogs.myBlogs({ limit: 5 }),
  });

  // Fetch recent notifications
  const { data: notifs } = useQuery({
    queryKey: ["recent-notifications"],
    queryFn: () => api.notifications.list({ limit: 4 }),
  });

  const statCards = [
    {
      title: "Total Articles",
      value: stats?.total_blogs ?? 0,
      icon: BookOpen,
      color: "text-[#f48840] bg-orange-50",
    },
    {
      title: "Approved & Live",
      value: stats?.approved_blogs ?? 0,
      icon: CheckCircle2,
      color: "text-emerald-600 bg-emerald-50",
    },
    {
      title: "Pending Review",
      value: stats?.pending_blogs ?? 0,
      icon: Clock,
      color: "text-amber-600 bg-amber-50",
    },
    {
      title: "Drafts",
      value: stats?.draft_blogs ?? 0,
      icon: FileText,
      color: "text-slate-600 bg-slate-100",
    },
  ];

  const engagementCards = [
    {
      label: "Total Article Reads",
      value: stats?.total_views ?? 0,
      icon: Eye,
      color: "text-[#f48840]",
    },
    {
      label: "Likes Received",
      value: stats?.total_likes_received ?? 0,
      icon: Heart,
      color: "text-rose-500",
    },
    {
      label: "Comments Received",
      value: stats?.total_comments_received ?? 0,
      icon: MessageSquare,
      color: "text-purple-500",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-2xl bg-gradient-to-r from-[#f48840] to-[#e0752d] p-6 sm:p-8 text-white shadow-md">
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold tracking-tight">
            Welcome back, {user?.full_name || user?.username}!
          </h1>
          <p className="text-orange-50 text-sm max-w-xl">
            Here is what is happening with your publications, reader discussions, and real-time engagement today.
          </p>
        </div>
        <Link href="/dashboard/blogs/create">
          <Button variant="secondary" className="gap-2 font-bold text-[#f48840] hover:text-[#e0752d] shrink-0">
            <PenSquare className="h-4 w-4" />
            Write New Blog
          </Button>
        </Link>
      </div>

      {/* 4 Status Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((item, idx) => {
          const Icon = item.icon;
          return (
            <Card key={idx}>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500">
                    {item.title}
                  </p>
                  <p className="text-2xl font-extrabold text-slate-900 mt-1">
                    {item.value}
                  </p>
                </div>
                <div className={`p-3 rounded-xl ${item.color}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Engagement Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-[#f48840]" />
            Reader Engagement Overview
          </CardTitle>
          <CardDescription>
            Cumulative interaction metrics across all your published articles
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 divide-y sm sm divide-slate-100">
            {engagementCards.map((ec, i) => {
              const Icon = ec.icon;
              return (
                <div key={i} className={`flex items-center gap-4 ${i > 0 ? "pt-4 sm:pt-0 sm:pl-6" : ""}`}>
                  <div className={`p-3 rounded-xl bg-slate-50 ${ec.color}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">
                      {ec.value}
                    </p>
                    <p className="text-xs text-slate-500">{ec.label}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Blogs */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base">Recent Blogs</CardTitle>
              <CardDescription>Your latest drafts and submissions</CardDescription>
            </div>
            <Link href="/dashboard/blogs" className="text-xs font-semibold text-[#f48840] hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {loadingBlogs ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : !myBlogs || myBlogs.items.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-400">
                You haven't written any blogs yet.
              </p>
            ) : (
              myBlogs.items.map((blog) => (
                <div
                  key={blog.id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 p-3 hover:opacity-90 transition-colors"
                >
                  <div className="min-w-0 flex-1 pr-3">
                    <p className="font-semibold text-sm text-slate-900 truncate">
                      {blog.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px] text-slate-400">
                        {formatDate(blog.created_at)}
                      </span>
                      <span className="text-slate-300">•</span>
                      <span className="text-[11px] text-slate-500 flex items-center gap-1">
                        <Eye className="h-3 w-3" /> {blog.views_count}
                      </span>
                    </div>
                  </div>
                  <div>
                    {blog.approval_status === "approved" ? (
                      <Badge variant="success">Approved</Badge>
                    ) : blog.approval_status === "pending" ? (
                      <Badge variant="warning">Pending</Badge>
                    ) : blog.approval_status === "rejected" ? (
                      <Badge variant="destructive">Rejected</Badge>
                    ) : (
                      <Badge variant="secondary">Draft</Badge>
                    )}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Recent Notifications / Interactions */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base">Latest Interactions</CardTitle>
              <CardDescription>Comments and reactions received</CardDescription>
            </div>
            <Link href="/dashboard/notifications" className="text-xs font-semibold text-[#f48840] hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {!notifs || notifs.items.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-400">
                No recent interactions recorded.
              </p>
            ) : (
              notifs.items.map((n) => (
                <div
                  key={n.id}
                  className={`flex items-start gap-3 rounded-lg p-3 transition-colors ${
                    !n.is_read ? "bg-orange-50/60" : "hover:bg-slate-50"
                  }`}
                >
                  <Avatar
                    src={n.sender?.avatar_url}
                    name={n.sender?.full_name || "User"}
                    size="sm"
                    className="shrink-0 mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-900">
                      {n.title}
                    </p>
                    <p className="text-xs text-slate-600 truncate mt-0.5">
                      {n.message}
                    </p>
                    <span className="text-[10px] text-slate-400 mt-1 block">
                      {formatDate(n.created_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

