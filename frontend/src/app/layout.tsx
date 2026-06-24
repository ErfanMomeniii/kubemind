import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KubeMind",
  description: "AI Operations Intelligence Platform for Kubernetes",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
