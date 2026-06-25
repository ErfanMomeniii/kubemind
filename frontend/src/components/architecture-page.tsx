"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  architectureGraphSchema,
  blastRadiusSchema,
  type BlastRadius,
} from "@/lib/architecture-schemas";
import { useAuthStore } from "@/stores/auth-store";

async function fetchGraph(clusterId: string) {
  const resp = await apiFetch(`/api/v1/clusters/${clusterId}/dependencies`);
  if (!resp.ok) throw new Error(`graph fetch failed: ${resp.status}`);
  return architectureGraphSchema.parse(await resp.json());
}

async function fetchBlastRadius(clusterId: string, service: string): Promise<BlastRadius> {
  const resp = await apiFetch(
    `/api/v1/clusters/${clusterId}/services/${encodeURIComponent(service)}/blast-radius`,
  );
  if (!resp.ok) throw new Error(`blast radius fetch failed: ${resp.status}`);
  return blastRadiusSchema.parse(await resp.json());
}

export function ArchitecturePage() {
  const clusterId = useAuthStore((s) => s.selectedClusterId);
  const [selected, setSelected] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const graph = useQuery({
    queryKey: ["architecture", clusterId],
    queryFn: () => fetchGraph(clusterId as string),
    enabled: !!clusterId,
    retry: false,
  });

  const blast = useQuery({
    queryKey: ["blast-radius", clusterId, selected],
    queryFn: () => fetchBlastRadius(clusterId as string, selected as string),
    enabled: !!clusterId && !!selected,
    retry: false,
  });

  async function sync() {
    if (!clusterId) return;
    setSyncing(true);
    setSyncResult(null);
    try {
      const resp = await apiFetch(`/api/v1/clusters/${clusterId}/architecture/sync`, {
        method: "POST",
      });
      if (!resp.ok) throw new Error(`sync failed: ${resp.status}`);
      const data = await resp.json();
      setSyncResult(`discovered ${data.services} services, ${data.dependencies} dependencies`);
      queryClient.invalidateQueries({ queryKey: ["architecture", clusterId] });
    } catch (err) {
      setSyncResult(err instanceof Error ? err.message : "sync failed");
    } finally {
      setSyncing(false);
    }
  }

  const services = graph.data?.services ?? [];
  const deps = graph.data?.dependencies ?? [];

  return (
    <main className="mx-auto max-w-6xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Architecture</h1>
        <button
          className="rounded bg-black p-2 text-white disabled:opacity-50"
          onClick={sync}
          disabled={!clusterId || syncing}
        >
          {syncing ? "Syncing…" : "Discover"}
        </button>
      </div>

      {syncResult && <p className="mb-4 text-sm text-gray-600">{syncResult}</p>}

      {!clusterId && <p className="text-gray-500">Select a cluster on the Dashboard first.</p>}

      {clusterId && (
        <div className="grid grid-cols-2 gap-4">
          <section className="rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Services ({services.length})
            </h2>
            {graph.isLoading && <p className="text-sm text-gray-500">Loading…</p>}
            {graph.error && <p className="text-sm text-red-600">{graph.error.message}</p>}
            {services.length === 0 && <p className="text-sm text-gray-500">none — click Discover</p>}
            <ul className="space-y-1 text-sm">
              {services.map((s) => (
                <li key={s.id}>
                  <button className="text-left hover:underline" onClick={() => setSelected(s.name)}>
                    {s.namespace}/{s.name}
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Dependencies ({deps.length})
            </h2>
            {deps.length === 0 && <p className="text-sm text-gray-500">none detected</p>}
            <ul className="space-y-1 text-sm">
              {deps.map((d) => (
                <li key={d.id} className="font-mono text-xs">
                  {d.fromService} → {d.toService}{" "}
                  <span className="text-gray-400">({d.toKind})</span>
                </li>
              ))}
            </ul>
          </section>

          {selected && (
            <section className="col-span-2 rounded-lg border p-4">
              <h2 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                Blast radius: {selected}
              </h2>
              {blast.isLoading && <p className="text-sm text-gray-500">Loading…</p>}
              {blast.error && <p className="text-sm text-red-600">{blast.error.message}</p>}
              {blast.data && (
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="font-semibold">Direct downstream</p>
                    <ul className="text-gray-600">
                      {blast.data.directDownstream.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                      {blast.data.directDownstream.length === 0 && <li>none</li>}
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold">All downstream</p>
                    <ul className="text-gray-600">
                      {blast.data.totalDownstream.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                      {blast.data.totalDownstream.length === 0 && <li>none</li>}
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold">Upstream (depends on)</p>
                    <ul className="text-gray-600">
                      {blast.data.upstream.map((u) => (
                        <li key={u}>{u}</li>
                      ))}
                      {blast.data.upstream.length === 0 && <li>none</li>}
                    </ul>
                  </div>
                </div>
              )}
              <p className="mt-3 text-sm text-gray-500">
                Affected services if {selected} goes down: {blast.data?.affectedCount ?? "?"}
              </p>
            </section>
          )}
        </div>
      )}
    </main>
  );
}
