"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { getAnalytics, getNotifications } from "@/lib/api";
import toast from "react-hot-toast";

export default function AnalyticsPage() {
  const [stats, setStats] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAnalytics(), getNotifications()])
      .then(([s, n]) => { setStats(s); setNotifications(n); })
      .catch(() => toast.error("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  const metricCards = stats ? [
    { label: "Total Requests", value: stats.total_requests },
    { label: "Successfully Booked", value: stats.booked },
    { label: "Cancellation Rate", value: `${stats.cancellation_rate}%` },
    { label: "Booking Rate", value: `${stats.booking_rate}%` },
    { label: "Emails Sent", value: stats.notifications_sent },
    { label: "Email Failures", value: stats.notifications_failed },
  ] : [];

  return (
    <div className="flex min-h-screen bg-glow">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {metricCards.map((m) => (
                  <GlassCard key={m.label} className="!p-5">
                    <p className="text-white/35 text-xs uppercase tracking-wider mb-2">{m.label}</p>
                    <p className="text-white text-3xl font-light">{m.value}</p>
                  </GlassCard>
                ))}
              </div>

              {/* Status Distribution */}
              {stats && (
                <GlassCard className="!p-5">
                  <p className="text-white/35 text-xs uppercase tracking-wider mb-5">Request Distribution</p>
                  <div className="space-y-3">
                    {[
                      ["Booked", stats.booked, stats.total_requests],
                      ["Pending", stats.pending, stats.total_requests],
                      ["Cancelled", stats.cancelled, stats.total_requests],
                      ["Rescheduling", stats.rescheduling, stats.total_requests],
                    ].map(([label, count, total]) => {
                      const pct = total ? Math.round((count as number / (total as number)) * 100) : 0;
                      return (
                        <div key={label as string} className="flex items-center gap-4">
                          <span className="text-white/40 text-xs w-24 shrink-0">{label}</span>
                          <div className="flex-1 h-1.5 bg-white/08 rounded-full overflow-hidden">
                            <div className="h-full bg-white/60 rounded-full transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-white/30 text-xs w-8 text-right">{count}</span>
                        </div>
                      );
                    })}
                  </div>
                </GlassCard>
              )}

              {/* Notification Audit Log */}
              <GlassCard className="!p-0 overflow-hidden">
                <div className="px-5 py-4 border-b border-white/[0.07]">
                  <p className="text-white/40 text-xs uppercase tracking-wider">Notification Audit Log</p>
                </div>
                {notifications.length === 0 ? (
                  <div className="py-10 text-center text-white/25 text-sm">No notifications yet</div>
                ) : (
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        {["Recipient", "Type", "Status", "Sent At"].map((h) => (
                          <th key={h} className="text-left px-5 py-2.5 text-white/25 font-medium uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {notifications.slice(0, 30).map((n) => (
                        <tr key={n.id} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                          <td className="px-5 py-2.5 text-white/60">{n.recipient_email}</td>
                          <td className="px-5 py-2.5 text-white/40">{n.notification_type}</td>
                          <td className="px-5 py-2.5">
                            <span className={`badge ${n.status === "sent" ? "badge-booked" : n.status === "failed" ? "badge-cancelled" : "badge-pending"}`}>
                              {n.status}
                            </span>
                          </td>
                          <td className="px-5 py-2.5 text-white/25">
                            {n.sent_at ? new Date(n.sent_at).toLocaleString() : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </GlassCard>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
