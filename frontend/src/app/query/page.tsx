"use client";

import { QueryPage } from "@/components/query-panel";
import { useRequireAuth } from "@/lib/auth-guards";

export default function QueryRoute() {
  const { ready } = useRequireAuth();
  if (!ready) return null;
  return <QueryPage />;
}
