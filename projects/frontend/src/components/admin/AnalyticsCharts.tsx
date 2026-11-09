"use client";

import React, { useState, useId } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Users, FileText, Activity } from "lucide-react";

export function AnalyticsCharts() {
  const [days, setDays] = useState<number>(30);
  const [hoveredReg, setHoveredReg] = useState<number | null>(null);
  const [hoveredBlog, setHoveredBlog] = useState<number | null>(null);
  const [hoveredInter, setHoveredInter] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-analytics", days],
    queryFn: () => api.admin.analytics(days),
  });

  const regData = data?.user_registrations || [];
  const blogData = data?.blog_publishing || [];
  const interData = data?.user_interactions || [];

  const totalUsersInPeriod = regData.reduce((acc, curr) => acc + curr.count, 0);
  const totalApprovedInPeriod = blogData.reduce((acc, curr) => acc + curr.approved_count, 0);
  const totalPendingInPeriod = blogData.reduce((acc, curr) => acc + curr.pending_count, 0);
  const totalInteractionsInPeriod = interData.reduce((acc, curr) => acc + curr.total, 0);

  return (
    <div className="space-y-6">
      {/* Date Range Selector Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Platform Analytics &amp; Trends
          </h2>
          <p className="text-xs text-slate-500">
            Historical activity across users, editorial pipeline, and reader engagement
          </p>
        </div>

        <div className="flex items-center gap-1 self-start sm:self-auto rounded-lg border border-slate-200 bg-white p-1 text-xs">
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`rounded-md px-3 py-1 font-bold transition-colors cursor-pointer ${
                days === d
                  ? "bg-[#f48840] text-white shadow-xs"
                  : "text-slate-600 hover:text-[#f48840] hover:bg-orange-50"
              }`}
            >
              {d} Days
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: User Registrations */}
        <Card className="border-[#eee] shadow-xs">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="rounded-md bg-orange-50 p-1.5 text-[#f48840]">
                  <Users className="h-4 w-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">User Registration Analytics</CardTitle>
                  <CardDescription className="text-xs">
                    New user account signups over time
                  </CardDescription>
                </div>
              </div>
              <div className="text-right">
                <span className="text-lg font-bold text-slate-900">
                  {isLoading ? "—" : totalUsersInPeriod}
                </span>
                <span className="block text-[11px] text-slate-400">Total in period</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {isLoading ? (
              <Skeleton className="h-56 w-full" />
            ) : (
              <BarChartSVG
                data={regData.map((d) => ({ label: d.day, value: d.count }))}
                hoveredIndex={hoveredReg}
                setHoveredIndex={setHoveredReg}
                color="#f48840"
                valueLabel="New Signups"
              />
            )}
          </CardContent>
        </Card>

        {/* Chart 2: Blog Publishing (Approved vs Pending) */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="rounded-md bg-emerald-50 p-1.5 text-emerald-600">
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">Blog Publishing Analytics</CardTitle>
                  <CardDescription className="text-xs">
                    Approved vs pending submissions over time
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-3 text-right text-xs">
                <div>
                  <span className="font-bold text-emerald-600">
                    {isLoading ? "—" : totalApprovedInPeriod}
                  </span>
                  <span className="block text-[10px] text-slate-400">Approved</span>
                </div>
                <div>
                  <span className="font-bold text-amber-500">
                    {isLoading ? "—" : totalPendingInPeriod}
                  </span>
                  <span className="block text-[10px] text-slate-400">Pending</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {isLoading ? (
              <Skeleton className="h-56 w-full" />
            ) : (
              <DoubleBarChartSVG
                data={blogData.map((d) => ({
                  label: d.day,
                  val1: d.approved_count,
                  val2: d.pending_count,
                }))}
                hoveredIndex={hoveredBlog}
                setHoveredIndex={setHoveredBlog}
                label1="Approved"
                color1="#10b981"
                label2="Pending"
                color2="#f59e0b"
              />
            )}
          </CardContent>
        </Card>

        {/* Chart 3: User Interaction Analytics (Full width) */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="rounded-md bg-rose-50 p-1.5 text-rose-600">
                  <Activity className="h-4 w-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">User Interaction Analytics</CardTitle>
                  <CardDescription className="text-xs">
                    Reader engagement over time: likes, comments, and threaded replies
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
                  <span className="text-slate-600">Likes</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#f48840]" />
                  <span className="text-slate-600">Comments</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-purple-600" />
                  <span className="text-slate-600">Replies</span>
                </div>
                <div className="border-l border-slate-200 pl-3">
                  <span className="font-bold text-slate-900">
                    {isLoading ? "—" : totalInteractionsInPeriod}
                  </span>
                  <span className="text-[11px] text-slate-400 ml-1">Total interactions</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <MultiLineChartSVG
                data={interData}
                hoveredIndex={hoveredInter}
                setHoveredIndex={setHoveredInter}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// Simple, Crisp, Native SVG Charts (Zero SSR/Hydration Issues)
// -------------------------------------------------------------

function BarChartSVG({
  data,
  hoveredIndex,
  setHoveredIndex,
  color,
  valueLabel,
}: {
  data: Array<{ label: string; value: number }>;
  hoveredIndex: number | null;
  setHoveredIndex: (idx: number | null) => void;
  color: string;
  valueLabel: string;
}) {
  if (data.length === 0) {
    return <EmptyChartPlaceholder message="No registration events in this time range." />;
  }

  const maxValue = Math.max(...data.map((d) => d.value), 4);
  const height = 200;
  const paddingBottom = 28;
  const paddingTop = 20;
  const chartHeight = height - paddingBottom - paddingTop;

  return (
    <div className="relative">
      <svg
        className="w-full h-52 overflow-visible select-none"
        viewBox={`0 0 ${data.length * 28 + 20} ${height}`}
        preserveAspectRatio="none"
        onMouseLeave={() => setHoveredIndex(null)}
      >
        {/* Horizontal grid lines */}
        {[0, 0.5, 1].map((pct, idx) => {
          const y = paddingTop + chartHeight * (1 - pct);
          return (
            <line
              key={idx}
              x1="0"
              x2={data.length * 28 + 20}
              y1={y}
              y2={y}
              stroke="#e2e8f0"
              strokeDasharray="3 3"
              strokeWidth="1"
            />
          );
        })}

        {/* Bars */}
        {data.map((item, idx) => {
          const x = 12 + idx * 28;
          const barHeight = Math.max(3, (item.value / maxValue) * chartHeight);
          const y = paddingTop + chartHeight - barHeight;
          const isHovered = hoveredIndex === idx;

          return (
            <g
              key={idx}
              onMouseEnter={() => setHoveredIndex(idx)}
              className="cursor-pointer transition-opacity"
            >
              {/* Hit area */}
              <rect
                x={x - 4}
                y={paddingTop}
                width={24}
                height={chartHeight + paddingBottom}
                fill="transparent"
              />
              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={16}
                height={barHeight}
                rx={3}
                fill={color}
                opacity={isHovered ? 1 : 0.82}
              />
              {/* X label (sampled every few bars if many) */}
              {(data.length <= 14 || idx % Math.ceil(data.length / 7) === 0) && (
                <text
                  x={x + 8}
                  y={height - 8}
                  textAnchor="middle"
                  className="fill-slate-400 text-[9px] font-sans"
                >
                  {formatDayLabel(item.label)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Floating tooltip */}
      {hoveredIndex !== null && data[hoveredIndex] && (
        <div className="pointer-events-none absolute top-2 right-2 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 shadow-sm text-xs">
          <p className="font-semibold text-slate-800">
            {data[hoveredIndex].label}
          </p>
          <p className="text-slate-500">
            {valueLabel}: <span className="font-bold text-[#f48840]">{data[hoveredIndex].value}</span>
          </p>
        </div>
      )}
    </div>
  );
}

function DoubleBarChartSVG({
  data,
  hoveredIndex,
  setHoveredIndex,
  label1,
  color1,
  label2,
  color2,
}: {
  data: Array<{ label: string; val1: number; val2: number }>;
  hoveredIndex: number | null;
  setHoveredIndex: (idx: number | null) => void;
  label1: string;
  color1: string;
  label2: string;
  color2: string;
}) {
  if (data.length === 0) {
    return <EmptyChartPlaceholder message="No blog activity recorded in this time range." />;
  }

  const maxValue = Math.max(...data.map((d) => Math.max(d.val1, d.val2)), 3);
  const height = 200;
  const paddingBottom = 28;
  const paddingTop = 20;
  const chartHeight = height - paddingBottom - paddingTop;
  const slotWidth = 34;

  return (
    <div className="relative">
      <svg
        className="w-full h-52 overflow-visible select-none"
        viewBox={`0 0 ${data.length * slotWidth + 20} ${height}`}
        preserveAspectRatio="none"
        onMouseLeave={() => setHoveredIndex(null)}
      >
        {/* Horizontal grid lines */}
        {[0, 0.5, 1].map((pct, idx) => {
          const y = paddingTop + chartHeight * (1 - pct);
          return (
            <line
              key={idx}
              x1="0"
              x2={data.length * slotWidth + 20}
              y1={y}
              y2={y}
              stroke="#e2e8f0"
              strokeDasharray="3 3"
              strokeWidth="1"
            />
          );
        })}

        {/* Bars */}
        {data.map((item, idx) => {
          const x = 12 + idx * slotWidth;
          const h1 = Math.max(2, (item.val1 / maxValue) * chartHeight);
          const h2 = Math.max(2, (item.val2 / maxValue) * chartHeight);
          const y1 = paddingTop + chartHeight - h1;
          const y2 = paddingTop + chartHeight - h2;
          const isHovered = hoveredIndex === idx;

          return (
            <g
              key={idx}
              onMouseEnter={() => setHoveredIndex(idx)}
              className="cursor-pointer"
            >
              <rect
                x={x - 4}
                y={paddingTop}
                width={slotWidth}
                height={chartHeight + paddingBottom}
                fill="transparent"
              />
              {/* Bar 1 (Approved) */}
              <rect
                x={x}
                y={y1}
                width={10}
                height={h1}
                rx={2}
                fill={color1}
                opacity={isHovered ? 1 : 0.85}
              />
              {/* Bar 2 (Pending) */}
              <rect
                x={x + 12}
                y={y2}
                width={10}
                height={h2}
                rx={2}
                fill={color2}
                opacity={isHovered ? 1 : 0.85}
              />
              {/* X label */}
              {(data.length <= 14 || idx % Math.ceil(data.length / 7) === 0) && (
                <text
                  x={x + 11}
                  y={height - 8}
                  textAnchor="middle"
                  className="fill-slate-400 text-[9px] font-sans"
                >
                  {formatDayLabel(item.label)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Floating tooltip */}
      {hoveredIndex !== null && data[hoveredIndex] && (
        <div className="pointer-events-none absolute top-2 right-2 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 shadow-sm text-xs">
          <p className="font-semibold text-slate-800">
            {data[hoveredIndex].label}
          </p>
          <div className="flex items-center gap-3 mt-1 text-[11px]">
            <span className="text-emerald-600 font-medium">
              {label1}: <b>{data[hoveredIndex].val1}</b>
            </span>
            <span className="text-amber-500 font-medium">
              {label2}: <b>{data[hoveredIndex].val2}</b>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function MultiLineChartSVG({
  data,
  hoveredIndex,
  setHoveredIndex,
}: {
  data: Array<{ day: string; likes: number; comments: number; replies: number; total: number }>;
  hoveredIndex: number | null;
  setHoveredIndex: (idx: number | null) => void;
}) {
  if (data.length === 0) {
    return <EmptyChartPlaceholder message="No reader interaction events recorded yet." />;
  }

  const maxVal = Math.max(...data.map((d) => Math.max(d.likes, d.comments, d.replies)), 3);
  const height = 220;
  const paddingBottom = 28;
  const paddingTop = 20;
  const chartHeight = height - paddingBottom - paddingTop;
  const step = data.length > 1 ? 800 / (data.length - 1) : 400;
  const totalWidth = Math.max(800, (data.length - 1) * step);

  const getPoints = (key: "likes" | "comments" | "replies") => {
    return data
      .map((item, idx) => {
        const x = idx * step;
        const y = paddingTop + chartHeight - (item[key] / maxVal) * chartHeight;
        return `${x},${y}`;
      })
      .join(" ");
  };

  return (
    <div className="relative">
      <div className="overflow-x-auto">
        <svg
          className="w-full h-60 min-w-[600px] overflow-visible select-none"
          viewBox={`0 0 ${totalWidth} ${height}`}
          onMouseLeave={() => setHoveredIndex(null)}
        >
          {/* Horizontal grid lines */}
          {[0, 0.5, 1].map((pct, idx) => {
            const y = paddingTop + chartHeight * (1 - pct);
            return (
              <line
                key={idx}
                x1="0"
                x2={totalWidth}
                y1={y}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="3 3"
                strokeWidth="1"
              />
            );
          })}

          {/* Lines */}
          <polyline
            fill="none"
            stroke="#ef4444"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={getPoints("likes")}
          />
          <polyline
            fill="none"
            stroke="#f48840"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={getPoints("comments")}
          />
          <polyline
            fill="none"
            stroke="#8b5cf6"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={getPoints("replies")}
          />

          {/* Points & interactive columns */}
          {data.map((item, idx) => {
            const x = idx * step;
            const yLikes = paddingTop + chartHeight - (item.likes / maxVal) * chartHeight;
            const yComments = paddingTop + chartHeight - (item.comments / maxVal) * chartHeight;
            const yReplies = paddingTop + chartHeight - (item.replies / maxVal) * chartHeight;
            const isHovered = hoveredIndex === idx;

            return (
              <g
                key={idx}
                onMouseEnter={() => setHoveredIndex(idx)}
                className="cursor-pointer"
              >
                {/* Hit bar */}
                <rect
                  x={x - step / 2}
                  y={paddingTop}
                  width={step}
                  height={chartHeight + paddingBottom}
                  fill="transparent"
                />

                {isHovered && (
                  <line
                    x1={x}
                    x2={x}
                    y1={paddingTop}
                    y2={paddingTop + chartHeight}
                    stroke="#94a3b8"
                    strokeDasharray="2 2"
                    strokeWidth="1"
                  />
                )}

                {/* Circles */}
                <circle cx={x} cy={yLikes} r={isHovered ? 4.5 : 3} fill="#ef4444" />
                <circle cx={x} cy={yComments} r={isHovered ? 4.5 : 3} fill="#f48840" />
                <circle cx={x} cy={yReplies} r={isHovered ? 4.5 : 3} fill="#8b5cf6" />

                {/* X labels */}
                {(data.length <= 14 || idx % Math.ceil(data.length / 8) === 0) && (
                  <text
                    x={x}
                    y={height - 8}
                    textAnchor="middle"
                    className="fill-slate-400 text-[10px] font-sans"
                  >
                    {formatDayLabel(item.day)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Floating tooltip */}
      {hoveredIndex !== null && data[hoveredIndex] && (
        <div className="pointer-events-none absolute top-2 right-2 rounded-md border border-slate-200 bg-white p-2.5 shadow-sm text-xs">
          <p className="font-semibold text-slate-800 mb-1">
            {data[hoveredIndex].day}
          </p>
          <div className="space-y-0.5 text-[11px]">
            <p className="text-rose-600">
              Likes: <b>{data[hoveredIndex].likes}</b>
            </p>
            <p className="text-[#f48840]">
              Top Comments: <b>{data[hoveredIndex].comments}</b>
            </p>
            <p className="text-purple-600">
              Threaded Replies: <b>{data[hoveredIndex].replies}</b>
            </p>
            <p className="border-t border-slate-100 pt-1 mt-1 font-semibold text-slate-700">
              Total: {data[hoveredIndex].total}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyChartPlaceholder({ message }: { message: string }) {
  return (
    <div className="flex h-52 items-center justify-center rounded-lg border border-dashed border-slate-200 p-6 text-center text-xs text-slate-400">
      {message}
    </div>
  );
}

function formatDayLabel(dayStr: string): string {
  if (!dayStr) return "";
  const parts = dayStr.split("-");
  if (parts.length >= 3) {
    return `${parts[1]}/${parts[2]}`;
  }
  return dayStr;
}
