"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Avatar } from "@/components/ui/Avatar";
import {
  Menu,
  X,
  PenSquare,
  Bell,
  LayoutDashboard,
  LogOut,
  User,
  ChevronDown,
} from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const { data: unreadData } = useQuery({
    queryKey: ["notifications-unread-count"],
    queryFn: () => api.notifications.unreadCount(),
    enabled: isAuthenticated,
    refetchInterval: 15000,
  });

  const unreadCount = unreadData?.unread_count || 0;

  if (pathname?.startsWith("/admin") || pathname?.startsWith("/dashboard")) {
    return null;
  }

  const navLinks = [
    { label: "Home", href: "/" },
    { label: "Blog", href: "/blogs" },
    { label: "Categories", href: "/categories" },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#eee] bg-white shadow-xs">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Stand Blog Brand Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-wider text-[#121212]">
            Raft Blog<span className="text-[#f48840]">.</span>
          </h2>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`relative py-1 text-xs font-black uppercase tracking-widest transition-colors ${
                  isActive
                    ? "text-[#f48840]"
                    : "text-[#20232e] hover:text-[#f48840]:text-[#f48840]"
                }`}
              >
                {link.label}
                {isActive && (
                  <span className="absolute -bottom-2 left-0 right-0 h-0.5 bg-[#f48840]" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <>
              {/* Write Post Button */}
              <Link
                href="/dashboard/blogs/create"
                className="hidden sm:inline-flex items-center gap-1.5 bg-[#f48840] hover:bg-[#e0752d]:bg-[#e0752d] text-white text-xs font-black uppercase tracking-wider px-4 py-2.5 transition-colors shadow-xs"
              >
                <PenSquare className="h-3.5 w-3.5" />
                <span>Write</span>
              </Link>

              {/* Notifications */}
              <Link
                href="/dashboard/notifications"
                className="relative p-2 text-[#7a7a7a] hover:text-[#f48840]:text-[#f48840] transition-colors"
                title="Notifications"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#f48840] px-1 text-[10px] font-bold text-white">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </Link>

              {/* User Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2 p-1 focus:outline-none cursor-pointer group"
                >
                  <Avatar
                    src={user?.avatar_url}
                    name={user?.full_name || user?.username}
                    size="sm"
                  />
                  <ChevronDown className="h-3.5 w-3.5 text-[#aaa] group-hover:text-[#f48840] transition-colors" />
                </button>

                {dropdownOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setDropdownOpen(false)}
                    />
                    <div className="absolute right-0 mt-2 z-50 w-56 border border-[#eee] bg-white py-1.5 shadow-xl">
                      <div className="border-b border-[#eee] px-4 py-2.5">
                        <p className="text-xs font-bold text-[#20232e] truncate">
                          {user?.full_name || user?.username}
                        </p>
                        <p className="text-[11px] text-[#aaa] truncate">@{user?.username}</p>
                        {isAdmin && (
                          <span className="mt-1 inline-block bg-[#f48840] text-white text-[9px] font-black uppercase px-1.5 py-0.5">
                            Admin
                          </span>
                        )}
                      </div>

                      <div className="py-1 text-xs">
                        <Link
                          href="/dashboard"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-[#7a7a7a] hover:bg-[#f7f7f7] hover:text-[#f48840]"
                        >
                          <LayoutDashboard className="h-3.5 w-3.5" />
                          <span>User Dashboard</span>
                        </Link>
                        <Link
                          href="/dashboard/profile"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-[#7a7a7a] hover:bg-[#f7f7f7] hover:text-[#f48840]"
                        >
                          <User className="h-3.5 w-3.5" />
                          <span>Profile Settings</span>
                        </Link>

                        <button
                          onClick={() => {
                            setDropdownOpen(false);
                            logout();
                          }}
                          className="flex w-full items-center gap-2 px-4 py-2 text-rose-600 hover:bg-rose-50 cursor-pointer"
                        >
                          <LogOut className="h-3.5 w-3.5" />
                          <span>Sign Out</span>
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className="text-xs font-black uppercase tracking-wider text-[#20232e] hover:text-[#f48840]:text-[#f48840] transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="bg-[#f48840] hover:bg-[#e0752d]:bg-[#e0752d] text-white text-xs font-black uppercase tracking-wider px-4 py-2 transition-colors"
              >
                Sign Up
              </Link>
            </div>
          )}

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-[#20232e] focus:outline-none"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-[#eee] bg-white px-4 py-4">
          <nav className="flex flex-col space-y-3">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="text-xs font-black uppercase tracking-widest text-[#20232e] hover:text-[#f48840]:text-[#f48840]"
              >
                {link.label}
              </Link>
            ))}
            {isAuthenticated && (
              <Link
                href="/dashboard/blogs/create"
                onClick={() => setMobileMenuOpen(false)}
                className="text-xs font-black uppercase tracking-widest text-[#f48840]"
              >
                + Write An Article
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
