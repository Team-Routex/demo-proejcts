"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { AnalyticsCharts } from "@/components/admin/AnalyticsCharts";
import { TopBlogsTable } from "@/components/admin/TopBlogsTable";
import { TopAuthorsTable } from "@/components/admin/TopAuthorsTable";
import {
  Users,
  FileText,
  Eye,
  Activity,
  TrendingUp,
  Award,
  ArrowUpRight,
} from "lucide-react";

export default function AdminOverviewPage() {
  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: () => api.admin.overview(),
  });

  const { data: topBlogs = [], isLoading: loadingBlogs } = useQuery({
    queryKey: ["admin-top-blogs"],
    queryFn: () => api.admin.topBlogs(5),
  });

  const { data: topAuthors = [], isLoading: loadingAuthors } = useQuery({
    queryKey: ["admin-top-authors"],
    queryFn: () => api.admin.topAuthors(5),
  });

  const cards = [
    {
      title: "Total Visits",
      value: overview?.total_visits ?? 0,
      description: "Recorded page view events",
      trend: "+12.5%",
      icon: Eye,
    },
    {
      title: "Total Interactions",
      value: overview?.total_interactions ?? 0,
      description: `${overview?.breakdown?.likes || 0} likes, ${overview?.breakdown?.comments || 0} comments`,
      trend: "+8.2%",
      icon: Activity,
    },
    {
      title: "Total Articles",
      value: overview?.total_blogs ?? 0,
      description: `${overview?.breakdown?.approved_blogs || 0} approved, ${overview?.breakdown?.pending_blogs || 0} pending`,
      trend: "+4.1%",
      icon: FileText,
    },
    {
      title: "Total Authors & Users",
      value: overview?.total_users ?? 0,
      description: "Registered across platform",
      trend: "+3.8%",
      icon: Users,
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-black uppercase tracking-widest text-[#f48840]">
            TailAdmin Analytics
          </span>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-[#20232e]">
            Dashboard Overview
          </h1>
          <p className="text-xs text-[#7a7a7a] mt-1">
            Real-time telemetry, editorial throughput, and reader engagement metrics
          </p>
        </div>
      </div>

      {/* TailAdmin 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <div
              key={i}
              className="bg-white border border-[#eee] rounded-xl p-6 shadow-xs hover:border-orange-200 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-orange-50 text-[#f48840] shadow-2xs">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="inline-flex items-center gap-0.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                  <ArrowUpRight className="h-3 w-3" />
                  {c.trend}
                </span>
              </div>

              <div className="mt-4">
                <h4 className="text-2xl sm:text-3xl font-black text-[#20232e]">
                  {loadingOverview ? (
                    <Skeleton className="h-9 w-24" />
                  ) : (
                    c.value.toLocaleString()
                  )}
                </h4>
                <p className="text-xs font-bold uppercase tracking-wider text-[#7a7a7a] mt-1">
                  {c.title}
                </p>
                <p className="text-[11px] text-[#aaa] mt-1 line-clamp-1">
                  {c.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Analytics Charts */}
      <AnalyticsCharts />

      {/* Top Five Blogs */}
      <Card className="border-[#eee] shadow-xs">
        <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-[#eee]">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-[#f48840]" />
              <span>Top 5 Performing Articles</span>
            </CardTitle>
            <CardDescription className="text-xs">
              Ranked by composite engagement score (views + 3×likes + 4×comments)
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingBlogs ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : (
            <TopBlogsTable blogs={topBlogs} />
          )}
        </CardContent>
      </Card>

      {/* Top Five Authors */}
      <Card className="border-[#eee] shadow-xs">
        <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-[#eee]">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Award className="h-4 w-4 text-[#f48840]" />
              <span>Top 5 Most Active &amp; Engaged Authors</span>
            </CardTitle>
            <CardDescription className="text-xs">
              Ranked by total engagement received across their published portfolio
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingAuthors ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : (
            <TopAuthorsTable authors={topAuthors} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
