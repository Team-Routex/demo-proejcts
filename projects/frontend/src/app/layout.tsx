import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { AuthProvider } from "@/lib/auth-context";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { NotificationToastHost } from "@/components/layout/NotificationToastHost";

export const metadata: Metadata = {
  title: "Raft Blog — Modern Publishing on RaftFramework & Next.js",
  description:
    "A full-stack, production-oriented blog application built with RaftFramework ASGI, RaftSQLORM, and Next.js.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body
        className="min-h-full flex flex-col bg-[#f7f7f7] text-[#20232e] antialiased"
        suppressHydrationWarning
      >
        <QueryProvider>
          <AuthProvider>
            <Navbar />
            <main className="flex-1">{children}</main>
            <Footer />
            <NotificationToastHost />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
