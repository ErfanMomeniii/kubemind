"use client";

import { useState } from "react";
import { authHeaders } from "@/lib/api";
import { queryResponseSchema, type QueryResponse } from "@/lib/query-schemas";
import { useAuthStore } from "@/stores/auth-store";

const CONFIDENCE_COLOR: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

export function QueryPanel({ clusterId }: { clusterId: string }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ cluster_id: clusterId, query: text }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body?.detail?.error?.message ?? resp.statusText);
      }
      const parsed = queryResponseSchema.parse(await resp.json());
      setResult(parsed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "query failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={submit} className="flex gap-2">
        <input
          className="flex-1 rounded border p-2"
          placeholder="Ask a question — e.g. 'Is production healthy?' or 'Why is the API slow?'"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={loading}
        />
        <button
          className="rounded bg-black p-2 text-white disabled:opacity-50"
          type="submit"
          disabled={loading || !text.trim()}
        >
          {loading ? "Investigating…" : "Ask"}
        </button>
      </form>

      {error && <p className="text-red-600">{error}</p>}

      {result && (
        <div className="rounded border p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm text-gray-500">Answer</span>
            {result.confidence && (
              <span className={`rounded px-2 py-0.5 text-xs ${CONFIDENCE_COLOR[result.confidence]}`}>
                {result.confidence} confidence
              </span>
            )}
          </div>
          <p className="whitespace-pre-wrap">{result.answer ?? "(no answer)"}</p>
          {result.status === "failed" && (
            <p className="mt-2 text-sm text-red-600">Investigation failed.</p>
          )}
        </div>
      )}
    </div>
  );
}

export function QueryPage() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [clusterId, setClusterId] = useState<string>("");

  if (!user) return null;

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Ask KubeMind</h1>
        <button
          className="rounded border p-2 text-sm"
          onClick={() => {
            logout();
            window.location.href = "/login";
          }}
        >
          Sign out
        </button>
      </header>

      <input
        className="mb-4 w-full rounded border p-2"
        placeholder="Cluster ID"
        value={clusterId}
        onChange={(e) => setClusterId(e.target.value)}
      />

      {clusterId ? (
        <QueryPanel clusterId={clusterId} />
      ) : (
        <p className="text-gray-500">Enter a cluster ID to start asking questions.</p>
      )}
    </main>
  );
}
