"use client";

import { useRequireAuth } from "@/lib/auth-guards";
import { DashboardContent } from "@/components/dashboard-content";

export default function Home() {
  const { ready } = useRequireAuth();
  if (!ready) return null;
  return <DashboardContent />;
}
