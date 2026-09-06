"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { getInterviews, getAnalytics } from "@/lib/api";
import { statusClass, statusLabel, formatRelative, roundLabel } from "@/lib/utils";
import toast from "react-hot-toast";

export default function Dashboard() {
  const [interviews, setInterviews] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getInterviews(), getAnalytics()])
      .then(([ivs, s]) => { setInterviews(ivs.slice(0, 8)); setStats(s); })
      .catch(() => toast.error("Failed to load dashboard data"))
      .finally(() => setLoading(false));
  }, []);

  const statCards = [
    { label: "Total Requests", value: stats?.total_requests ?? "—" },
    { label: "Booked", value: stats?.booked ?? "—" },
    { label: "Awaiting Candidate", value: stats?.pending ?? "—" },
    { label: "Booking Rate", value: stats ? `${stats.booking_rate}%` : "—" },
  ];

  return (
    <div className="flex min-h-screen bg-glow">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 space-y-6">
          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {statCards.map((s) => (
              <GlassCard key={s.label} className="!p-5">
                <p className="text-white/40 text-xs uppercase tracking-wider mb-2">{s.label}</p>
                {loading ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <p className="text-white text-3xl font-light">{s.value}</p>
                )}
              </GlassCard>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <h2 className="text-white/60 text-sm font-medium uppercase tracking-wider">Recent Requests</h2>
            <Link href="/requests/new" className="btn-primary text-xs px-4 py-2">
              + New Interview
            </Link>
          </div>

          <GlassCard className="!p-0 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-40">
                <LoadingSpinner />
              </div>
            ) : interviews.length === 0 ? (
              <EmptyState
                icon="◇"
                title="No interview requests yet"
                description="Create your first interview request to get started"
                action={<Link href="/requests/new" className="btn-primary text-sm">Create Interview</Link>}
              />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.07]">
                    {["Candidate", "Job Title", "Round", "Status", "Created", ""].map((h) => (
                      <th key={h} className="text-left px-5 py-3 text-white/30 text-xs font-medium uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {interviews.map((iv) => (
                    <tr key={iv.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-3.5 text-white/80">{iv.candidate?.name || "—"}</td>
                      <td className="px-5 py-3.5 text-white/60">{iv.job_title}</td>
                      <td className="px-5 py-3.5 text-white/50">{roundLabel(iv.round_type)}</td>
                      <td className="px-5 py-3.5">
                        <span className={statusClass(iv.status)}>{statusLabel(iv.status)}</span>
                      </td>
                      <td className="px-5 py-3.5 text-white/30 text-xs">{formatRelative(iv.created_at)}</td>
                      <td className="px-5 py-3.5">
                        <Link href={`/requests/${iv.id}`} className="text-white/40 hover:text-white text-xs underline underline-offset-2 transition-colors">
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </GlassCard>

          {!loading && interviews.length > 0 && (
            <div className="text-center">
              <Link href="/requests" className="text-white/30 text-xs hover:text-white/60 transition-colors underline underline-offset-2">
                View all interview requests
              </Link>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
