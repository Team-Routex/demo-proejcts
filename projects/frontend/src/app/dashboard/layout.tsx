import React from "react";
import { UserDashboardLayout } from "@/components/layout/UserDashboardLayout";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <UserDashboardLayout>{children}</UserDashboardLayout>;
}

