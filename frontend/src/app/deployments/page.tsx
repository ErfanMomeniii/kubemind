"use client";

import { DeploymentsPage } from "@/components/deployments-page";
import { useRequireAuth } from "@/lib/auth-guards";

export default function DeploymentsRoute() {
  const { ready } = useRequireAuth();
  if (!ready) return null;
  return <DeploymentsPage />;
}
