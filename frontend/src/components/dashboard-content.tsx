"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { authHeaders } from "@/lib/api";
import { clusterListSchema } from "@/lib/schemas";
import { useDashboardQuery } from "@/lib/use-dashboard";
import { HealthBanner } from "@/components/health-banner";
import { DashboardDetails } from "@/components/dashboard-details";
import { useAuthStore } from "@/stores/auth-store";

async function fetchClusters() {
  const resp = await fetch("/api/v1/clusters", { headers: { ...authHeaders() } });
  if (!resp.ok) throw new Error(`clusters fetch failed: ${resp.status}`);
  return clusterListSchema.parse(await resp.json());
}

export function DashboardContent() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { data: clusterData } = useQuery({
    queryKey: ["clusters"],
    queryFn: fetchClusters,
    enabled: !!user,
  });
  const [selectedId, setSelectedId] = useState<string | null>(
    clusterData?.items[0]?.id ?? null,
  );
  const { data, isLoading, error } = useDashboardQuery(selectedId);

  if (!user) return null;

  const clusters = clusterData?.items ?? [];
  const activeId = selectedId ?? clusters[0]?.id ?? null;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">KubeMind</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user.email}</span>
          <button
            className="rounded border p-2 text-sm"
            onClick={() => {
              logout();
              window.location.href = "/login";
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="mb-4">
        <select
          className="rounded border p-2"
          value={activeId ?? ""}
          onChange={(e) => setSelectedId(e.target.value || null)}
          disabled={clusters.length === 0}
        >
          {clusters.length === 0 && <option value="">no clusters connected</option>}
          {clusters.map((c) => (
            <option key={c.id} value={c.id}>
              {c.displayName}
            </option>
          ))}
        </select>
      </div>

      {!activeId && (
        <p className="rounded border border-dashed p-8 text-center text-gray-500">
          Connect your first cluster to see health, incidents, and recent changes.
        </p>
      )}

      {activeId && isLoading && <p className="text-gray-500">Loading dashboard…</p>}
      {activeId && error && (
        <p className="rounded border border-red-300 bg-red-50 p-4 text-red-700">
          Error: {error.message}
        </p>
      )}
      {activeId && data && (
        <div className="space-y-4">
          <HealthBanner health={data.health} stale={data.dataStale} />
          <DashboardDetails data={data} />
        </div>
      )}
    </main>
  );
}
