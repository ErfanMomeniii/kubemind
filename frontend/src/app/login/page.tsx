"use client";

import { AuthForm } from "@/components/auth-form";
import { useRedirectIfAuthed } from "@/lib/auth-guards";

export default function LoginPage() {
  useRedirectIfAuthed();
  return <AuthForm />;
}
