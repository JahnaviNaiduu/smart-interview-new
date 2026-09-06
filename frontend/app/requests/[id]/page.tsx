"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { getInterview, cancelInterview, resendInvite, createBooking } from "@/lib/api";
import { statusClass, statusLabel, formatDateTime, roundLabel, scoreBar } from "@/lib/utils";
import toast from "react-hot-toast";
import clsx from "clsx";

const STATUS_STEPS = [
  { key: "pending", label: "Request Created" },
  { key: "slots_found", label: "Slots Found" },
  { key: "candidate_notified", label: "Candidate Notified" },
  { key: "booked", label: "Booked" },
];

function getStepIndex(status: string) {
  if (status === "cancelled") return -1;
  const i = STATUS_STEPS.findIndex((s) => s.key === status);
  return i === -1 ? STATUS_STEPS.length - 1 : i;
}

export default function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [interview, setInterview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [resending, setResending] = useState(false);

  const load = () => {
    getInterview(id)
      .then(setInterview)
      .catch(() => toast.error("Failed to load interview"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleCancel = async () => {
    if (!confirm("Cancel this interview request? All participants will be notified.")) return;
    setCancelling(true);
    try {
      await cancelInterview(id);
      toast.success("Interview cancelled");
      load();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setCancelling(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await resendInvite(id);
      toast.success("Invite resent to candidate");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setResending(false);
    }
  };

  if (loading) return (
    <div className="flex min-h-screen bg-glow">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopBar />
        <div className="flex-1 flex items-center justify-center"><LoadingSpinner size="lg" /></div>
      </div>
    </div>
  );

  if (!interview) return null;

  const stepIndex = getStepIndex(interview.status);
  const sortedSlots = [...(interview.slots || [])].sort((a, b) => (a.ai_rank || 99) - (b.ai_rank || 99));

  return (
    <div className="flex min-h-screen bg-glow">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-white text-xl font-light">{interview.job_title}</h1>
                <span className={statusClass(interview.status)}>{statusLabel(interview.status)}</span>
              </div>
              <p className="text-white/40 text-sm">{roundLabel(interview.round_type)} Interview · {interview.duration_minutes} min</p>
            </div>
            <div className="flex gap-2">
              {interview.status !== "cancelled" && interview.status !== "booked" && (
                <>
                  <button className="btn-ghost text-xs" onClick={handleResend} disabled={resending}>
                    {resending ? <LoadingSpinner size="sm" /> : "Resend Invite"}
                  </button>
                  <button className="btn-ghost text-xs text-white/40" onClick={handleCancel} disabled={cancelling}>
                    {cancelling ? <LoadingSpinner size="sm" /> : "Cancel"}
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Left: Info + Timeline */}
            <div className="space-y-4">
              <GlassCard className="!p-5 space-y-3">
                <p className="text-white/30 text-xs uppercase tracking-wider mb-3">Candidate</p>
                <p className="text-white font-medium">{interview.candidate?.name}</p>
                <p className="text-white/50 text-sm">{interview.candidate?.email}</p>
                <p className="text-white/30 text-xs">{interview.candidate?.timezone}</p>
              </GlassCard>

              <GlassCard className="!p-5">
                <p className="text-white/30 text-xs uppercase tracking-wider mb-4">Progress</p>
                <div className="space-y-3">
                  {STATUS_STEPS.map((s, i) => (
                    <div key={s.key} className="flex items-center gap-3">
                      <div className={clsx(
                        "w-5 h-5 rounded-full flex items-center justify-center text-xs shrink-0",
                        i < stepIndex ? "bg-white text-black" : i === stepIndex ? "border-2 border-white" : "border-2 border-white/15"
                      )}>
                        {i < stepIndex ? "✓" : ""}
                      </div>
                      <span className={clsx("text-xs", i <= stepIndex ? "text-white/70" : "text-white/25")}>{s.label}</span>
                    </div>
                  ))}
                  {interview.status === "cancelled" && (
                    <div className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full border-2 border-white/20 flex items-center justify-center text-xs">✕</div>
                      <span className="text-white/30 text-xs">Cancelled</span>
                    </div>
                  )}
                </div>
              </GlassCard>

              <GlassCard className="!p-5 space-y-2">
                <p className="text-white/30 text-xs uppercase tracking-wider mb-3">Details</p>
                {[
                  ["Recruiter", interview.recruiter_email],
                  ["Window", `${interview.window_start?.slice(0, 10)} → ${interview.window_end?.slice(0, 10)}`],
                  ["Buffer", `${interview.buffer_minutes} min`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-white/30">{k}</span>
                    <span className="text-white/60">{v}</span>
                  </div>
                ))}
              </GlassCard>
            </div>

            {/* Right: Slots */}
            <div className="md:col-span-2">
              <GlassCard className="!p-5">
                <p className="text-white/30 text-xs uppercase tracking-wider mb-4">
                  AI Ranked Slots ({sortedSlots.length} found)
                </p>
                {sortedSlots.length === 0 ? (
                  <div className="text-center py-8 text-white/30 text-sm">
                    No slots found. Widen the interview window or add more panelists.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {sortedSlots.map((slot: any) => (
                      <div
                        key={slot.id}
                        className={clsx(
                          "p-4 rounded-xl border transition-all",
                          slot.is_selected
                            ? "border-white/30 bg-white/08"
                            : "border-white/08 hover:border-white/15"
                        )}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-white/80 text-sm font-medium">{formatDateTime(slot.start_time)}</p>
                          <div className="flex items-center gap-2">
                            {slot.ai_score !== null && (
                              <span className="text-white/30 text-xs font-mono">{scoreBar(slot.ai_score)}</span>
                            )}
                            {slot.is_selected && (
                              <span className="badge badge-booked">Selected</span>
                            )}
                          </div>
                        </div>
                        {slot.ai_reasoning && (
                          <p className="text-white/30 text-xs mt-1">{slot.ai_reasoning}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </GlassCard>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
