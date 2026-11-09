"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Notification } from "@/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatTimeAgo } from "@/lib/utils";
import {
  Bell,
  CheckCheck,
  Check,
  MessageSquare,
  Heart,
  FileCheck,
  FileX,
  ExternalLink,
} from "lucide-react";

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["notifications", unreadOnly, page],
    queryFn: () =>
      api.notifications.list({
        unread_only: unreadOnly,
        page,
        limit: 15,
      }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => api.notifications.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => api.notifications.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "comment":
      case "reply":
        return (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-100 text-[#f48840]">
            <MessageSquare className="h-4 w-4" />
          </div>
        );
      case "like_blog":
      case "like_comment":
        return (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-100 text-rose-600">
            <Heart className="h-4 w-4" />
          </div>
        );
      case "blog_approved":
        return (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
            <FileCheck className="h-4 w-4" />
          </div>
        );
      case "blog_rejected":
        return (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
            <FileX className="h-4 w-4" />
          </div>
        );
      default:
        return (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
            <Bell className="h-4 w-4" />
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Notifications Center
          </h1>
          <p className="text-sm text-slate-500">
            Real-time alerts for comments, threaded replies, likes, and editorial updates
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setUnreadOnly(!unreadOnly)}
            className="text-xs"
          >
            {unreadOnly ? "Showing Unread" : "All Notifications"}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => markAllReadMutation.mutate()}
            isLoading={markAllReadMutation.isPending}
            className="gap-1.5 text-xs"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all read
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Bell className="mx-auto h-10 w-10 text-slate-300 mb-2" />
            <p className="text-sm">No notifications found.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {data.items.map((n) => (
              <div
                key={n.id}
                className={`flex items-start justify-between gap-4 p-4 transition-colors ${
                  !n.is_read
                    ? "bg-orange-50/50"
                    : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  {getNotificationIcon(n.type)}
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold text-slate-900">
                        {n.title}
                      </h4>
                      {!n.is_read && (
                        <span className="h-2 w-2 rounded-full bg-[#f48840]" />
                      )}
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {n.message}
                    </p>
                    <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400">
                      <span>{formatTimeAgo(n.created_at)}</span>
                      {n.type === "blog_rejected" && n.target_id ? (
                        <>
                          <span>•</span>
                          <Link
                            href={`/dashboard/blogs/${n.target_id}/edit`}
                            className="inline-flex items-center gap-1 font-bold text-rose-600 hover:underline"
                          >
                            <span>Revise & Resubmit</span>
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        </>
                      ) : n.target_slug ? (
                        <>
                          <span>•</span>
                          <Link
                            href={`/blogs/${n.target_slug}`}
                            className="inline-flex items-center gap-1 font-medium text-[#f48840] hover:underline"
                          >
                            <span>Open Article</span>
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        </>
                      ) : null}
                    </div>
                  </div>
                </div>

                {!n.is_read && (
                  <button
                    onClick={() => markReadMutation.mutate(n.id)}
                    className="rounded-lg p-1.5 text-slate-400 hover:text-slate-600 hover:text-slate-900 cursor-pointer"
                    title="Mark as read"
                  >
                    <Check className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

