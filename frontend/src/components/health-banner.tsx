"use client";

import { clsx } from "clsx";
import type { HealthSummary } from "@/lib/dashboard-schemas";

const STATUS_COLOR: Record<HealthSummary["status"], string> = {
  Healthy: "bg-green-100 text-green-800",
  Degraded: "bg-yellow-100 text-yellow-800",
  Critical: "bg-red-100 text-red-800",
  Unknown: "bg-gray-100 text-gray-800",
};

const STATUS_DOT: Record<HealthSummary["status"], string> = {
  Healthy: "bg-green-500",
  Degraded: "bg-yellow-500",
  Critical: "bg-red-500",
  Unknown: "bg-gray-400",
};

export function HealthBanner({ health, stale }: { health: HealthSummary; stale: boolean }) {
  return (
    <div className={clsx("rounded-lg border p-4", STATUS_COLOR[health.status])}>
      <div className="flex items-center gap-3">
        <span className={clsx("h-3 w-3 rounded-full", STATUS_DOT[health.status])} />
        <span className="text-2xl font-bold">{health.status}</span>
        {health.availability !== null && (
          <span className="text-sm opacity-80">
            {(health.availability * 100).toFixed(2)}% availability
          </span>
        )}
        {stale && <span className="text-xs opacity-70">data stale</span>}
      </div>
      <p className="mt-2 text-xs opacity-60">score {health.score}</p>
    </div>
  );
}
