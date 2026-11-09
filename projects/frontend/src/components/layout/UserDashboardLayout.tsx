"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useNotifications } from "@/lib/use-notifications";
import {
  LayoutDashboard,
  BookOpen,
  PenSquare,
  FolderTree,
  MessageSquare,
  Bell,
  User,
  LogOut,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/ui/Avatar";

const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { label: "My Blogs", href: "/dashboard/blogs", icon: BookOpen },
  { label: "Create Blog", href: "/dashboard/blogs/create", icon: PenSquare },
  { label: "Categories", href: "/dashboard/categories", icon: FolderTree },
  { label: "Comments & Replies", href: "/dashboard/comments", icon: MessageSquare },
  { label: "Notifications", href: "/dashboard/notifications", icon: Bell, hasBadge: true },
  { label: "Profile Settings", href: "/dashboard/profile", icon: User },
];

export function UserDashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const { unreadCount } = useNotifications();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#f48840]" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-[#f7f7f7] flex flex-col">
      {/* Studio Top Bar */}
      <header className="sticky top-0 z-30 h-16 bg-white border-b border-[#eee] flex items-center justify-between px-4 sm:px-8 shadow-xs">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#f48840] text-white font-black text-lg shadow-xs">
              R
            </div>
            <div>
              <h2 className="text-base font-black uppercase tracking-wider text-[#121212] leading-none">
                Raft Blog<span className="text-[#f48840]">.</span>
              </h2>
              <span className="text-[10px] font-bold tracking-widest text-[#aaa] uppercase block mt-0.5">
                Author Studio
              </span>
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/blogs/create"
            className="inline-flex items-center gap-1.5 bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-black uppercase tracking-wider px-3.5 py-2 rounded-md transition-colors shadow-xs"
          >
            <PenSquare className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Write Article</span>
          </Link>

          <Link
            href="/dashboard/notifications"
            className="relative p-2 text-[#7a7a7a] hover:text-[#f48840] hover:bg-orange-50 rounded-md transition-colors"
            title="Notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#f48840] px-1 text-[10px] font-bold text-white">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </Link>

          <Link
            href="/"
            className="hidden md:inline-flex items-center gap-1 text-xs font-bold text-[#7a7a7a] hover:text-[#f48840] border border-[#eee] px-3 py-1.5 rounded-md transition-colors"
          >
            <span>Public Site</span>
          </Link>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 w-full flex-1">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
          {/* Sidebar */}
          <aside className="md:col-span-3">
            <div className="sticky top-20 rounded-xl border border-slate-200/90 bg-white p-4 shadow-xs">
            {/* User card snippet */}
            <div className="flex items-center gap-3 border-b border-slate-100 pb-4 mb-4">
              <Avatar
                src={user?.avatar_url}
                name={user?.full_name || user?.username}
                size="md"
              />
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-slate-900 truncate">
                  {user?.full_name || user?.username}
                </h4>
                <p className="text-xs text-slate-400 truncate">@{user?.username}</p>
                <span className="inline-block mt-1 text-[10px] font-semibold uppercase tracking-wider text-[#f48840]">
                  {user?.role}
                </span>
              </div>
            </div>

            {/* Navigation links */}
            <nav className="space-y-1">
              {NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-[#f48840] text-white shadow-xs"
                        : "text-[#7a7a7a] hover:bg-[#f7f7f7] hover:text-[#f48840]"
                    )}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={cn("h-4 w-4", isActive ? "text-white" : "text-[#aaa]")} />
                      <span>{item.label}</span>
                    </div>
                    {item.hasBadge && unreadCount > 0 && (
                      <span
                        className={cn(
                          "flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[11px] font-bold",
                          isActive ? "bg-white text-[#f48840]" : "bg-[#f48840] text-white"
                        )}
                      >
                        {unreadCount > 99 ? "99+" : unreadCount}
                      </span>
                    )}
                  </Link>
                );
              })}

              <div className="pt-2 mt-2 border-t border-[#eee]">
                <button
                  onClick={logout}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </nav>
          </div>
        </aside>

        {/* Content area */}
        <main className="md:col-span-9">{children}</main>
      </div>
    </div>
  </div>
);
}

