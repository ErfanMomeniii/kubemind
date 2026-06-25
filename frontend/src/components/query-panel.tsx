"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  investigationResponseSchema,
  queryResponseSchema,
  type Investigation,
  type QueryResponse,
} from "@/lib/query-schemas";
import { useRecentQueries } from "@/lib/use-recent-queries";
import { useAuthStore } from "@/stores/auth-store";

const CONFIDENCE_COLOR: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

const SUGGESTED = [
  "Is production healthy?",
  "What changed today?",
  "Why is the API slow?",
  "Show risky services",
];

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function formatOutput(output: unknown): string {
  if (output === null || output === undefined) return "";
  if (typeof output === "string") return output;
  try {
    return JSON.stringify(output, null, 2);
  } catch {
    return String(output);
  }
}

export function QueryPanel() {
  const clusterId = useAuthStore((s) => s.selectedClusterId);
  const user = useAuthStore((s) => s.user);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const recentQueries = useRecentQueries(!!user);

  async function submit(q: string) {
    if (!q.trim() || !clusterId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setInvestigation(null);
    setText(q);
    try {
      const resp = await apiFetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cluster_id: clusterId, query: q }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body?.detail?.error?.message ?? resp.statusText);
      }
      const parsed = queryResponseSchema.parse(await resp.json());
      setResult(parsed);
      if (parsed.investigationId) {
        const invResp = await apiFetch(
          `/api/v1/query/investigations/${parsed.investigationId}`,
        );
        if (invResp.ok) {
          setInvestigation(investigationResponseSchema.parse(await invResp.json()));
        }
      }
      recentQueries.refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "query failed");
    } finally {
      setLoading(false);
    }
  }

  async function viewHistory(qid: string) {
    const resp = await apiFetch(`/api/v1/query/queries/${qid}`);
    if (!resp.ok) return;
    const parsed = queryResponseSchema.parse(await resp.json());
    setResult(parsed);
    setInvestigation(null);
    setText(parsed.text);
    if (parsed.investigationId) {
      const invResp = await apiFetch(`/api/v1/query/investigations/${parsed.investigationId}`);
      if (invResp.ok) {
        setInvestigation(investigationResponseSchema.parse(await invResp.json()));
      }
    }
  }

  if (!clusterId) {
    return <p className="text-gray-500">Select a cluster on the Dashboard first.</p>;
  }

  return (
    <div className="grid grid-cols-3 gap-6">
      <div className="col-span-2 space-y-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(text);
          }}
          className="flex gap-2"
        >
          <input
            className="flex-1 rounded border p-3"
            placeholder="Ask a question about your cluster…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={loading}
          />
          <button
            className="rounded bg-black px-6 py-3 text-white disabled:opacity-50"
            type="submit"
            disabled={loading || !text.trim()}
          >
            {loading ? "Investigating…" : "Ask"}
          </button>
        </form>

        {!result && !loading && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map((q) => (
              <button
                key={q}
                className="rounded-full border px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                onClick={() => submit(q)}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="rounded border p-6 text-center">
            <p className="text-gray-600">Agent investigating across k8s + Prometheus…</p>
            <p className="mt-2 text-xs text-gray-400">
              Planning → calling tools → evaluating evidence → composing answer
            </p>
          </div>
        )}

        {error && (
          <div className="rounded border border-red-300 bg-red-50 p-4 text-red-700">{error}</div>
        )}

        {result && !loading && (
          <div className="space-y-4">
            <div className="rounded border p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-semibold uppercase text-gray-500">Answer</span>
                {result.confidence && (
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${CONFIDENCE_COLOR[result.confidence]}`}
                  >
                    {result.confidence} confidence
                  </span>
                )}
              </div>
              <p className="whitespace-pre-wrap leading-relaxed">
                {result.answer ?? "(no answer)"}
              </p>
              {result.status === "failed" && (
                <p className="mt-2 text-sm text-red-600">Investigation failed.</p>
              )}
            </div>

            {investigation?.rootCause && (
              <div className="rounded border border-yellow-200 bg-yellow-50 p-4">
                <h3 className="mb-1 text-sm font-semibold uppercase text-yellow-800">
                  Likely root cause
                </h3>
                <p className="text-sm text-yellow-900">{investigation.rootCause}</p>
              </div>
            )}

            {investigation && investigation.evidence.length > 0 && (
              <div className="rounded border p-5">
                <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                  Evidence ({investigation.evidence.length} tool calls)
                </h3>
                <ul className="space-y-3">
                  {investigation.evidence.map((e, i) => (
                    <li key={i} className="border-l-2 border-gray-200 pl-3">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs">
                          {e.tool}
                        </span>
                        {e.reason && <span className="text-xs text-gray-500">{e.reason}</span>}
                      </div>
                      {e.input && Object.keys(e.input).length > 0 && (
                        <pre className="mt-1 overflow-x-auto text-xs text-gray-600">
                          {truncate(JSON.stringify(e.input), 200)}
                        </pre>
                      )}
                      <pre className="mt-1 max-h-40 overflow-auto rounded bg-gray-50 p-2 text-xs">
                        {truncate(formatOutput(e.output), 500)}
                      </pre>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      <aside className="col-span-1">
        <div className="rounded-lg border p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">History</h3>
          {recentQueries.isLoading && <p className="text-sm text-gray-500">Loading…</p>}
          {recentQueries.data && recentQueries.data.length === 0 && (
            <p className="text-sm text-gray-500">No questions yet.</p>
          )}
          {recentQueries.data && recentQueries.data.length > 0 && (
            <ul className="space-y-2">
              {recentQueries.data.map((q) => (
                <li key={q.id}>
                  <button
                    className="w-full rounded p-2 text-left text-sm hover:bg-gray-50"
                    onClick={() => viewHistory(q.id)}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{q.text}</span>
                      {q.confidence && (
                        <span
                          className={`ml-2 shrink-0 rounded px-1.5 py-0.5 text-xs ${CONFIDENCE_COLOR[q.confidence]}`}
                        >
                          {q.confidence}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(q.createdAt).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}

export function QueryPage() {
  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="mb-2 text-2xl font-bold">Ask KubeMind</h1>
      <p className="mb-6 text-sm text-gray-500">
        Ask any operational question in plain language. The AI agent investigates your cluster
        and returns an evidence-backed answer.
      </p>
      <QueryPanel />
    </main>
  );
}
