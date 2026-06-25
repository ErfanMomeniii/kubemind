"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  configChangeListSchema,
  deploymentListSchema,
  type ConfigChange,
  type Deployment,
} from "@/lib/deployment-schemas";
import { useAuthStore } from "@/stores/auth-store";

async function fetchDeployments(clusterId: string): Promise<Deployment[]> {
  const resp = await apiFetch(`/api/v1/clusters/${clusterId}/deployments`);
  if (!resp.ok) throw new Error(`deployments fetch failed: ${resp.status}`);
  return deploymentListSchema.parse(await resp.json()).items;
}

async function fetchConfigChanges(clusterId: string): Promise<ConfigChange[]> {
  const resp = await apiFetch(`/api/v1/clusters/${clusterId}/config-changes`);
  if (!resp.ok) throw new Error(`config changes fetch failed: ${resp.status}`);
  return configChangeListSchema.parse(await resp.json()).items;
}

export function DeploymentsPage() {
  const clusterId = useAuthStore((s) => s.selectedClusterId);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const deployments = useQuery({
    queryKey: ["deployments", clusterId],
    queryFn: () => fetchDeployments(clusterId as string),
    enabled: !!clusterId,
    retry: false,
  });
  const configChanges = useQuery({
    queryKey: ["config-changes", clusterId],
    queryFn: () => fetchConfigChanges(clusterId as string),
    enabled: !!clusterId,
    retry: false,
  });

  async function sync() {
    if (!clusterId) return;
    setSyncing(true);
    setSyncResult(null);
    try {
      const resp = await apiFetch(`/api/v1/clusters/${clusterId}/sync`, {
        method: "POST",
      });
      if (!resp.ok) throw new Error(`sync failed: ${resp.status}`);
      const data = await resp.json();
      setSyncResult(`synced: ${data.deployments} deployments, ${data.config_changes} config changes`);
      queryClient.invalidateQueries({ queryKey: ["deployments", clusterId] });
      queryClient.invalidateQueries({ queryKey: ["config-changes", clusterId] });
    } catch (err) {
      setSyncResult(err instanceof Error ? err.message : "sync failed");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Deployments</h1>
        <button
          className="rounded bg-black p-2 text-white disabled:opacity-50"
          onClick={sync}
          disabled={!clusterId || syncing}
        >
          {syncing ? "Syncing…" : "Sync now"}
        </button>
      </div>

      {syncResult && <p className="mb-4 text-sm text-gray-600">{syncResult}</p>}

      {!clusterId && <p className="text-gray-500">Select a cluster on the Dashboard first.</p>}

      {clusterId && (
        <div className="grid grid-cols-2 gap-4">
          <section className="rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Recent deployments
            </h2>
            {deployments.isLoading && <p className="text-sm text-gray-500">Loading…</p>}
            {deployments.error && (
              <p className="text-sm text-red-600">{deployments.error.message}</p>
            )}
            {deployments.data && deployments.data.length === 0 && (
              <p className="text-sm text-gray-500">none — click Sync now</p>
            )}
            {deployments.data && deployments.data.length > 0 && (
              <ul className="space-y-2 text-sm">
                {deployments.data.map((d) => (
                  <li key={d.id} className="border-b pb-2">
                    <div className="font-medium">
                      {d.namespace}/{d.service}
                    </div>
                    <div className="text-gray-600">
                      {d.version} · {d.replicasReady ?? 0}/{d.replicasDesired ?? 0} · {d.status}
                    </div>
                    <div className="text-xs text-gray-400">
                      {new Date(d.startedAt).toLocaleString()}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Config changes
            </h2>
            {configChanges.isLoading && <p className="text-sm text-gray-500">Loading…</p>}
            {configChanges.error && (
              <p className="text-sm text-red-600">{configChanges.error.message}</p>
            )}
            {configChanges.data && configChanges.data.length === 0 && (
              <p className="text-sm text-gray-500">none</p>
            )}
            {configChanges.data && configChanges.data.length > 0 && (
              <ul className="space-y-2 text-sm">
                {configChanges.data.map((c) => (
                  <li key={c.id} className="border-b pb-2">
                    <div className="font-medium">
                      {c.kind} {c.namespace}/{c.name}
                    </div>
                    <div className="text-gray-600">{c.changeType}</div>
                    <div className="text-xs text-gray-400">
                      {new Date(c.detectedAt).toLocaleString()}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
