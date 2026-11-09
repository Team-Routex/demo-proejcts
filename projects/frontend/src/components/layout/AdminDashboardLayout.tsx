"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  LayoutDashboard,
  Users,
  FileText,
  MessageSquare,
  FolderTree,
  Tag as TagIcon,
  Globe,
  LogOut,
  Bell,
  Search,
  PenSquare,
  Shield,
  Loader2,
  AlertTriangle,
  Menu,
  X,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/ui/Avatar";

const NAV_GROUPS = [
  {
    title: "MENU",
    items: [
      { label: "Overview & Analytics", href: "/admin", icon: LayoutDashboard },
      { label: "Blog Moderation", href: "/admin/blogs", icon: FileText },
      { label: "Category Management", href: "/admin/categories", icon: FolderTree },
      { label: "Tags Management", href: "/admin/tags", icon: TagIcon },
    ],
  },
  {
    title: "COMMUNITY & USERS",
    items: [
      { label: "User Management", href: "/admin/users", icon: Users },
      { label: "Comments & Discussion", href: "/admin/comments", icon: MessageSquare },
    ],
  },
  {
    title: "SHORTCUTS",
    items: [
      { label: "Public Blog Site", href: "/", icon: Globe },
      { label: "User Dashboard", href: "/dashboard", icon: LayoutDashboard },
    ],
  },
];

export function AdminDashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated, isAdmin, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");

  const { data: unreadData } = useQuery({
    queryKey: ["admin-notifications-unread"],
    queryFn: () => api.notifications.unreadCount(),
    enabled: isAuthenticated && isAdmin,
    refetchInterval: 15000,
  });

  const unreadCount = unreadData?.unread_count || 0;

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      } else if (!isAdmin) {
        router.push("/dashboard");
      }
    }
  }, [isLoading, isAuthenticated, isAdmin, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex h-[75vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#f48840]" />
      </div>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center p-4">
        <div className="mx-auto max-w-md p-10 text-center bg-white border border-[#eee] shadow-xs">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-orange-50 text-[#f48840] mb-4">
            <Shield className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-black text-[#20232e] uppercase tracking-wide">
            Access Restricted
          </h2>
          <p className="mt-2 text-sm text-[#7a7a7a]">
            You must have administrator privileges to access this console.
          </p>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/login?redirect=/admin"
              className="w-full sm:w-auto inline-block bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-bold uppercase tracking-wider px-5 py-2.5 transition-colors"
            >
              Sign In As Admin
            </Link>
            <Link
              href="/"
              className="w-full sm:w-auto inline-block bg-white hover:bg-[#f7f7f7] border border-[#eee] text-[#20232e] text-xs font-bold uppercase tracking-wider px-5 py-2.5 transition-colors"
            >
              Return to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (globalSearch.trim()) {
      router.push(`/admin/blogs?search=${encodeURIComponent(globalSearch.trim())}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#f7f7f7] flex flex-col lg:flex-row">
      {/* Mobile Sidebar Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* TailAdmin Style Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 bg-white border-r border-[#eee] flex flex-col transition-transform duration-200 ease-in-out lg:static lg:translate-x-0",
          sidebarOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        )}
      >
        {/* Brand Header */}
        <div className="h-20 flex items-center justify-between px-6 border-b border-[#eee]">
          <Link href="/admin" className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f48840] text-white font-black text-xl shadow-xs">
              R
            </div>
            <div>
              <h2 className="text-lg font-black uppercase tracking-wider text-[#121212] leading-none">
                Raft Blog<span className="text-[#f48840]">.</span>
              </h2>
              <span className="text-[10px] font-bold tracking-widest text-[#aaa] uppercase block mt-1">
                Admin Console
              </span>
            </div>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1 text-slate-400 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Sidebar Nav Items */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {NAV_GROUPS.map((group, gIdx) => (
            <div key={gIdx}>
              <h3 className="px-3 text-[11px] font-black uppercase tracking-wider text-[#aaa] mb-2">
                {group.title}
              </h3>
              <nav className="space-y-1">
                {group.items.map((item) => {
                  const isActive =
                    item.href === "/admin"
                      ? pathname === "/admin"
                      : pathname.startsWith(item.href) && item.href !== "/";
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={cn(
                        "group flex items-center justify-between px-3.5 py-2.5 rounded-md text-xs font-bold uppercase tracking-wider transition-all",
                        isActive
                          ? "bg-[#f48840] text-white shadow-xs"
                          : "text-[#64748b] hover:bg-orange-50/70 hover:text-[#f48840]"
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <Icon
                          className={cn(
                            "h-4 w-4 transition-colors",
                            isActive
                              ? "text-white"
                              : "text-[#94a3b8] group-hover:text-[#f48840]"
                          )}
                        />
                        <span>{item.label}</span>
                      </div>
                      <ChevronRight
                        className={cn(
                          "h-3.5 w-3.5 opacity-0 -translate-x-1 transition-all group-hover:opacity-100 group-hover:translate-x-0",
                          isActive ? "opacity-100 translate-x-0 text-white" : "text-[#f48840]"
                        )}
                      />
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>

        {/* User Card & Logout at bottom of sidebar */}
        <div className="p-4 border-t border-[#eee] bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <Avatar
                src={user?.avatar_url}
                name={user?.full_name || user?.username}
                size="sm"
              />
              <div className="min-w-0">
                <p className="text-xs font-bold text-[#20232e] truncate">
                  {user?.full_name || user?.username}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="inline-block bg-orange-100 text-[#f48840] text-[9px] font-black uppercase px-1.5 py-0.5 rounded-xs">
                    Admin
                  </span>
                  <span className="text-[10px] text-[#aaa] truncate">
                    @{user?.username}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={logout}
              title="Sign Out"
              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors cursor-pointer"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Admin Content Wrapper */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* TailAdmin Top Bar */}
        <header className="sticky top-0 z-30 h-20 bg-white border-b border-[#eee] flex items-center justify-between px-4 sm:px-8 shadow-xs">
          <div className="flex items-center gap-4 flex-1">
            {/* Mobile menu trigger */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 text-[#20232e] hover:bg-[#f7f7f7] rounded-md"
            >
              <Menu className="h-6 w-6" />
            </button>

            {/* Quick search input */}
            <form onSubmit={handleSearchSubmit} className="relative max-w-md w-full hidden sm:block">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#aaa]" />
              <input
                type="text"
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                placeholder="Search telemetry, articles, authors, tags..."
                className="w-full pl-9 pr-4 py-2 border border-[#eee] bg-[#f7f7f7] text-xs text-[#20232e] placeholder-[#aaa] rounded-md focus:border-[#f48840] focus:outline-none transition-colors"
              />
            </form>
          </div>

          {/* Right Header Utilities */}
          <div className="flex items-center gap-4">
            {/* Create Story Shortcut */}
            <Link
              href="/dashboard/blogs/create"
              className="inline-flex items-center gap-1.5 bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-black uppercase tracking-wider px-4 py-2.5 rounded-md transition-colors shadow-xs"
            >
              <PenSquare className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Write Article</span>
            </Link>

            {/* Notification Bell */}
            <Link
              href="/dashboard/notifications"
              className="relative p-2 text-[#7a7a7a] hover:text-[#f48840] hover:bg-orange-50 rounded-md transition-colors"
              title="Notifications"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#f48840] px-1 text-[10px] font-bold text-white">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Link>

            {/* Public site pill */}
            <Link
              href="/"
              className="hidden md:inline-flex items-center gap-1 text-xs font-bold text-[#7a7a7a] hover:text-[#f48840] border border-[#eee] px-3 py-2 rounded-md transition-colors"
            >
              <Globe className="h-3.5 w-3.5" />
              <span>Public Site</span>
            </Link>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-4 sm:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
