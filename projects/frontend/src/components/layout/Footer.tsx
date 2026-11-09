"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function Footer() {
  const pathname = usePathname();

  if (pathname?.startsWith("/admin") || pathname?.startsWith("/dashboard")) {
    return null;
  }

  return (
    <footer className="bg-white text-[#7a7a7a] border-t border-[#eee] mt-20">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          {/* Brand info */}
          <div className="md:col-span-2 space-y-4">
            <h2 className="text-2xl font-black uppercase tracking-wider text-[#121212]">
              Raft Blog<span className="text-[#f48840]">.</span>
            </h2>
            <p className="text-xs sm:text-sm text-[#7a7a7a] max-w-md leading-relaxed">
              A high-performance modern publishing platform built on RaftFramework ASGI &amp; RaftSQLORM with Next.js App Router, featuring real-time WebSocket notifications and threaded comments.
            </p>
            <div className="flex items-center gap-2 pt-2">
              <span className="bg-[#f7f7f7] border border-[#eee] px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-[#f48840]">
                RaftFramework 1.0.0
              </span>
              <span className="bg-[#f7f7f7] border border-[#eee] px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-emerald-600">
                RaftSQLORM Active
              </span>
            </div>
          </div>

          {/* Quick links */}
          <div>
            <h3 className="text-xs font-black uppercase tracking-widest text-[#20232e] border-b border-[#eee] pb-3 mb-4">
              Explore
            </h3>
            <ul className="space-y-2.5 text-xs uppercase tracking-wider font-semibold">
              <li>
                <Link href="/" className="hover:text-[#f48840] transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <Link href="/blogs" className="hover:text-[#f48840] transition-colors">
                  Blog
                </Link>
              </li>
              <li>
                <Link href="/categories" className="hover:text-[#f48840] transition-colors">
                  Categories
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="hover:text-[#f48840] transition-colors">
                  Dashboard
                </Link>
              </li>
            </ul>
          </div>

          {/* Account */}
          <div>
            <h3 className="text-xs font-black uppercase tracking-widest text-[#20232e] border-b border-[#eee] pb-3 mb-4">
              Community
            </h3>
            <ul className="space-y-2.5 text-xs uppercase tracking-wider font-semibold">
              <li>
                <Link href="/login" className="hover:text-[#f48840] transition-colors">
                  Sign In
                </Link>
              </li>
              <li>
                <Link href="/register" className="hover:text-[#f48840] transition-colors">
                  Register
                </Link>
              </li>
              <li>
                <Link href="/dashboard/blogs/create" className="hover:text-[#f48840] transition-colors">
                  Write An Article
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-12 pt-8 border-t border-[#eee] text-center text-xs text-[#aaa] flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>
            &copy; {new Date().getFullYear()} Raft Blog Platform. Inspired by Stand Blog styling.
          </p>
          <div className="flex items-center gap-4 text-xs font-medium">
            <Link href="/" className="hover:text-[#f48840] transition-colors">Privacy</Link>
            <span>•</span>
            <Link href="/" className="hover:text-[#f48840] transition-colors">Terms</Link>
            <span>•</span>
            <Link href="/" className="hover:text-[#f48840] transition-colors">Contact</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
