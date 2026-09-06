"use client";
import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/requests": "Interview Requests",
  "/requests/new": "New Interview Request",
  "/panelists": "Panelists",
  "/analytics": "Analytics",
};

export default function TopBar() {
  const path = usePathname();
  const title = Object.entries(titles)
    .reverse()
    .find(([k]) => path.startsWith(k) || path === k)?.[1] || "Smart Scheduler";

  return (
    <header className="h-14 flex items-center px-6 border-b border-white/[0.07] bg-white/[0.01] backdrop-blur-xl sticky top-0 z-30">
      <h1 className="text-white/80 text-sm font-medium">{title}</h1>
      <div className="ml-auto flex items-center gap-3">
        <div className="w-7 h-7 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-xs text-white/60">
          R
        </div>
      </div>
    </header>
  );
}
