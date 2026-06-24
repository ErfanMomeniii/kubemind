"use client";

import type { DashboardResponse } from "@/lib/dashboard-schemas";

function formatAge(seconds: number | null): string {
  if (seconds === null) return "?";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

export function DashboardDetails({ data }: { data: DashboardResponse }) {
  const critical = data.incidents.critical;
  const warnings = data.warnings;
  const deployments = data.recentChanges.deployments;
  const anomalies = data.recentChanges.anomalies;
  const risk = data.topRisk;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <section className="rounded-lg border p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase text-gray-500">Critical</h2>
          {critical.length === 0 ? (
            <p className="text-green-700">0</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {critical.map((i) => (
                <li key={i.id}>
                  {i.title} <span className="text-gray-500">({formatAge(i.ageSeconds)})</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="rounded-lg border p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase text-gray-500">Warnings</h2>
          {warnings.length === 0 ? (
            <p className="text-gray-500">none</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {warnings.map((w, idx) => (
                <li key={idx}>
                  {w.title} {w.service && <span className="text-gray-500">({w.service})</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="rounded-lg border p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase text-gray-500">SLOs</h2>
          <p className="text-gray-500 text-sm">not configured</p>
        </section>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <section className="rounded-lg border p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase text-gray-500">
            Recent changes (24h)
          </h2>
          {deployments.length === 0 && anomalies.length === 0 ? (
            <p className="text-sm text-gray-500">none</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {deployments.map((d, idx) => (
                <li key={`d-${idx}`}>
                  <span className="font-medium">{d.service}</span>{" "}
                  {d.version && <span className="text-gray-600">{d.version}</span>}{" "}
                  <span className="text-gray-400">{new Date(d.startedAt).toLocaleString()}</span>
                </li>
              ))}
              {anomalies.map((a, idx) => (
                <li key={`a-${idx}`} className="text-yellow-700">
                  {a.service} restarted {a.count}x
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="rounded-lg border p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase text-gray-500">Top risk</h2>
          {risk.length === 0 ? (
            <p className="text-sm text-gray-500">no risk signals</p>
          ) : (
            <ol className="space-y-1 text-sm">
              {risk.map((r, idx) => (
                <li key={r.service} className="flex items-center justify-between">
                  <span>
                    {idx + 1}. {r.service}
                  </span>
                  <span className="font-mono text-gray-600">{r.score.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}
