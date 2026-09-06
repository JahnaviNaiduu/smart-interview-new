"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { getInterviews } from "@/lib/api";
import { statusClass, statusLabel, formatRelative, roundLabel } from "@/lib/utils";
import toast from "react-hot-toast";

const FILTERS = ["all", "pending", "candidate_notified", "booked", "cancelled"];

export default function RequestsPage() {
  const [interviews, setInterviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    setLoading(true);
    getInterviews(filter === "all" ? undefined : filter)
      .then(setInterviews)
      .catch(() => toast.error("Failed to load interviews"))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="flex min-h-screen bg-glow">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs capitalize transition-all ${
                    filter === f ? "bg-white/12 text-white border border-white/20" : "text-white/35 hover:text-white/60"
                  }`}
                >
                  {f === "all" ? "All" : f.replace("_", " ")}
                </button>
              ))}
            </div>
            <Link href="/requests/new" className="btn-primary text-xs px-4 py-2">+ New Interview</Link>
          </div>

          <GlassCard className="!p-0 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-48"><LoadingSpinner /></div>
            ) : interviews.length === 0 ? (
              <EmptyState
                icon="◇"
                title="No interviews found"
                description={filter !== "all" ? "Try a different filter" : "Create your first interview request"}
                action={filter === "all" ? <Link href="/requests/new" className="btn-primary text-sm">Create Interview</Link> : undefined}
              />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.07]">
                    {["Candidate", "Job Title", "Round", "Duration", "Status", "Created", ""].map((h) => (
                      <th key={h} className="text-left px-5 py-3 text-white/30 text-xs font-medium uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {interviews.map((iv) => (
                    <tr key={iv.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-3.5 text-white/80 font-medium">{iv.candidate?.name || "—"}</td>
                      <td className="px-5 py-3.5 text-white/60">{iv.job_title}</td>
                      <td className="px-5 py-3.5 text-white/50">{roundLabel(iv.round_type)}</td>
                      <td className="px-5 py-3.5 text-white/40 text-xs">{iv.duration_minutes}m</td>
                      <td className="px-5 py-3.5">
                        <span className={statusClass(iv.status)}>{statusLabel(iv.status)}</span>
                      </td>
                      <td className="px-5 py-3.5 text-white/25 text-xs">{formatRelative(iv.created_at)}</td>
                      <td className="px-5 py-3.5">
                        <Link href={`/requests/${iv.id}`} className="text-white/35 hover:text-white text-xs underline underline-offset-2 transition-colors">
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </GlassCard>
        </main>
      </div>
    </div>
  );
}
