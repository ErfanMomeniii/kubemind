"use client";

import { useQuery } from "@tanstack/react-query";
import { authHeaders } from "@/lib/api";
import { clusterListSchema } from "@/lib/schemas";
import { useAuthStore } from "@/stores/auth-store";

async function fetchClusters(): Promise<{ items: unknown[]; hasMore: boolean }> {
  const resp = await fetch("/api/v1/clusters", { headers: { ...authHeaders() } });
  if (!resp.ok) throw new Error(`failed: ${resp.status}`);
  const data = clusterListSchema.parse(await resp.json());
  return { items: data.items, hasMore: data.hasMore };
}

export function DashboardContent() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { data, isLoading, error } = useQuery({
    queryKey: ["clusters"],
    queryFn: fetchClusters,
    enabled: !!user,
  });

  if (!user) return null;

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

      <section className="mb-6 rounded border p-4">
        <h2 className="mb-2 text-lg font-semibold">Production Status</h2>
        {isLoading && <p>Loading...</p>}
        {error && <p className="text-red-600">Error: {error.message}</p>}
        {data && data.items.length === 0 && (
          <p className="text-gray-600">No clusters connected. Connect your first cluster to get started.</p>
        )}
        {data && data.items.length > 0 && (
          <ul className="space-y-2">
            {data.items.map((c) => {
              const cluster = c as { id: string; name: string; displayName: string; status: string };
              return (
                <li key={cluster.id} className="flex items-center justify-between rounded border p-2">
                  <span>{cluster.displayName} ({cluster.name})</span>
                  <span className="text-sm">{cluster.status}</span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
