"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getToken, isPublicPath } from "@/lib/auth";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

// Client-side gate: public routes (login + candidate token pages) render freely;
// every other route requires a stored token, otherwise we redirect to /login.
// This is UX only — the backend independently enforces authorization on every call.
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (isPublicPath(pathname)) {
      setReady(true);
      return;
    }
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-glow">
        <LoadingSpinner />
      </div>
    );
  }
  return <>{children}</>;
}
