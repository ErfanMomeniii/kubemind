"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { clusterListSchema } from "@/lib/schemas";
import { useDashboardQuery } from "@/lib/use-dashboard";
import { useRecentQueries } from "@/lib/use-recent-queries";
import { HealthBanner } from "@/components/health-banner";
import { DashboardDetails } from "@/components/dashboard-details";
import { useAuthStore } from "@/stores/auth-store";

async function fetchClusters() {
  const resp = await apiFetch("/api/v1/clusters");
  if (!resp.ok) throw new Error(`clusters fetch failed: ${resp.status}`);
  return clusterListSchema.parse(await resp.json());
}

async function fetchCount(url: string): Promise<number> {
  const resp = await apiFetch(url);
  if (!resp.ok) return 0;
  const data = await resp.json();
  return (data.items ?? []).length;
}

const CONFIDENCE_COLOR: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

export function DashboardContent() {
  const user = useAuthStore((s) => s.user);
  const selectedClusterId = useAuthStore((s) => s.selectedClusterId);
  const setSelectedClusterId = useAuthStore((s) => s.setSelectedClusterId);
  const { data: clusterData, isLoading: clustersLoading } = useQuery({
    queryKey: ["clusters"],
    queryFn: fetchClusters,
    enabled: !!user,
    retry: false,
  });
  const { data, isLoading, error } = useDashboardQuery(selectedClusterId);
  const recentQueries = useRecentQueries(!!user);

  const clusters = clusterData?.items ?? [];
  const selected = clusters.find((c) => c.id === selectedClusterId) ?? null;

  const deploymentsCount = useQuery({
    queryKey: ["deployments-count", selectedClusterId],
    queryFn: () => fetchCount(`/api/v1/clusters/${selectedClusterId}/deployments`),
    enabled: !!selectedClusterId,
  });
  const servicesCount = useQuery({
    queryKey: ["services-count", selectedClusterId],
    queryFn: () => fetchCount(`/api/v1/clusters/${selectedClusterId}/services`),
    enabled: !!selectedClusterId,
  });

  useEffect(() => {
    if (!selectedClusterId && clusters.length > 0) {
      setSelectedClusterId(clusters[0].id);
    }
  }, [clusters, selectedClusterId, setSelectedClusterId]);

  if (!user) return null;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="mb-4 text-2xl font-bold">Dashboard</h1>

      {clustersLoading && <p className="text-gray-500">Loading clusters…</p>}

      <div className="mb-4 flex items-center gap-3">
        <select
          className="rounded border p-2"
          value={selectedClusterId ?? ""}
          onChange={(e) => setSelectedClusterId(e.target.value || null)}
          disabled={clusters.length === 0}
        >
          {clusters.length === 0 && <option value="">no clusters connected</option>}
          {clusters.map((c) => (
            <option key={c.id} value={c.id}>
              {c.displayName}
            </option>
          ))}
        </select>
        {selected && (
          <span className="text-sm text-gray-500">
            {selected.serverUrl.replace("https://", "").replace("http://", "")} ·{" "}
            <span className={selected.status === "active" ? "text-green-600" : "text-gray-500"}>
              {selected.status}
            </span>
          </span>
        )}
      </div>

      {!selectedClusterId && !clustersLoading && (
        <p className="rounded border border-dashed p-8 text-center text-gray-500">
          Connect your first cluster to see health, incidents, and recent changes.
        </p>
      )}

      {selectedClusterId && (
        <div className="space-y-4">
          {isLoading && <p className="text-gray-500">Loading dashboard…</p>}
          {error && (
            <p className="rounded border border-red-300 bg-red-50 p-4 text-red-700">
              Error: {error.message}
            </p>
          )}

          {data && (
            <>
              <HealthBanner health={data.health} stale={data.dataStale} />

              <div className="grid grid-cols-3 gap-4">
                <StatCard
                  label="Deployments"
                  value={deploymentsCount.data ?? 0}
                  loading={deploymentsCount.isLoading}
                />
                <StatCard
                  label="Services"
                  value={servicesCount.data ?? 0}
                  loading={servicesCount.isLoading}
                />
                <StatCard label="Active incidents" value={data.incidents.critical.length} />
              </div>

              <DashboardDetails data={data} />

              <div className="rounded-lg border p-5">
                <h2 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                  Recent questions
                </h2>
                {recentQueries.isLoading && <p className="text-sm text-gray-500">Loading…</p>}
                {recentQueries.data && recentQueries.data.length === 0 && (
                  <p className="text-sm text-gray-500">
                    No questions yet. Try the{" "}
                    <a href="/query" className="text-blue-600 underline">
                      Ask AI
                    </a>{" "}
                    page.
                  </p>
                )}
                {recentQueries.data && recentQueries.data.length > 0 && (
                  <ul className="space-y-2 text-sm">
                    {recentQueries.data.map((q) => (
                      <li key={q.id} className="flex items-center justify-between border-b pb-1">
                        <span className="truncate">{q.text}</span>
                        <div className="flex items-center gap-2">
                          {q.confidence && (
                            <span
                              className={`rounded px-1.5 py-0.5 text-xs ${CONFIDENCE_COLOR[q.confidence]}`}
                            >
                              {q.confidence}
                            </span>
                          )}
                          <span className="text-xs text-gray-400">
                            {new Date(q.createdAt).toLocaleString()}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: number;
  loading?: boolean;
}) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-sm font-semibold uppercase text-gray-500">{label}</p>
      <p className="mt-1 text-3xl font-bold">{loading ? "…" : value}</p>
    </div>
  );
}
