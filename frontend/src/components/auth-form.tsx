"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiLogin, apiRegister } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

type Mode = "login" | "register";

export function AuthForm() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res =
        mode === "login"
          ? await apiLogin(email, password)
          : await apiRegister(email, password, name, orgName);
      setAuth(
        {
          accessToken: res.tokens.accessToken,
          refreshToken: res.tokens.refreshToken,
        },
        {
          id: res.user.id,
          email: res.user.email,
          name: res.user.name,
          orgId: res.user.orgId,
        },
      );
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "auth failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto mt-20 max-w-md p-6">
      <h1 className="mb-6 text-2xl font-bold">
        {mode === "login" ? "Sign in to KubeMind" : "Create your KubeMind account"}
      </h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "register" && (
          <>
            <input
              className="w-full rounded border p-2"
              placeholder="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <input
              className="w-full rounded border p-2"
              placeholder="Organization name"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
            />
          </>
        )}
        <input
          className="w-full rounded border p-2"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="w-full rounded border p-2"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          className="w-full rounded bg-black p-2 text-white disabled:opacity-50"
          type="submit"
          disabled={loading}
        >
          {loading ? "..." : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
      <button
        className="mt-4 text-sm text-blue-600"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
      >
        {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
      </button>
    </div>
  );
}
