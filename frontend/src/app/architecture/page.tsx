"use client";

import { ArchitecturePage } from "@/components/architecture-page";
import { useRequireAuth } from "@/lib/auth-guards";

export default function ArchitectureRoute() {
  const { ready } = useRequireAuth();
  if (!ready) return null;
  return <ArchitecturePage />;
}
