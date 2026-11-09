import React from "react";
import { AdminDashboardLayout } from "@/components/layout/AdminDashboardLayout";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminDashboardLayout>{children}</AdminDashboardLayout>;
}

