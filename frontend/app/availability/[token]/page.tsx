"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { getCandidateLinkData, submitCandidateAvailability, createBooking } from "@/lib/api";
import { formatDateShort, scoreBar, TIMEZONES } from "@/lib/utils";
import toast from "react-hot-toast";
import clsx from "clsx";

export default function CandidateAvailabilityPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string[]>([]);
  const [tz, setTz] = useState("UTC");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    getCandidateLinkData(token)
      .then((res) => {
        setData(res);
        // Default dropdown to candidate's stored timezone if available
        if (res?.candidate_timezone) {
          setTz(res.candidate_timezone);
        }
      })
      .catch(() => toast.error("Invalid or expired link"))
      .finally(() => setLoading(false));
  }, [token]);

  const toggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : prev.length < 3 ? [...prev, id] : prev
    );
  };

  const formatInTz = (utc: string) => {
    try {
      // Ensure backend string is treated strictly as UTC ISO string
      const formattedUtc = utc.endsWith("Z") || utc.includes("+") ? utc : `${utc}Z`;
      const d = new Date(formattedUtc);

      return d.toLocaleString("en-US", {
        timeZone: tz,
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return formatDateShort(utc);
    }
  };

  const handleSubmit = async () => {
    if (selected.length === 0) { toast.error("Please select at least one slot"); return; }
    setSubmitting(true);
    try {
      const result = await submitCandidateAvailability({ token, selected_slot_ids: selected, candidate_timezone: tz });
      // Auto-book the best slot
      await createBooking({ interview_request_id: result.interview_id, slot_id: result.best_slot_id });
      setDone(true);
    } catch (err: any) {
      toast.error(err.message || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-glow flex items-center justify-center">
      <LoadingSpinner size="lg" />
    </div>
  );

  if (done) return (
    <div className="min-h-screen bg-glow flex items-center justify-center p-4">
      <GlassCard className="max-w-md w-full text-center space-y-4 animate-fade-in">
        <div className="text-5xl text-white/80 font-light">✓</div>
        <h1 className="text-white text-xl font-light">You're confirmed!</h1>
        <p className="text-white/50 text-sm">Your interview has been booked. Check your email for the calendar invite and Google Meet link.</p>
      </GlassCard>
    </div>
  );

  if (!data) return (
    <div className="min-h-screen bg-glow flex items-center justify-center p-4">
      <GlassCard className="max-w-md w-full text-center">
        <p className="text-white/50">Link not found or invalid.</p>
      </GlassCard>
    </div>
  );

  if (data.is_expired) return (
    <div className="min-h-screen bg-glow flex items-center justify-center p-4">
      <GlassCard className="max-w-md w-full text-center space-y-3">
        <div className="text-4xl text-white/20">⧖</div>
        <h1 className="text-white font-light">Link Expired</h1>
        <p className="text-white/40 text-sm">This scheduling link has expired. Please contact your recruiter at <span className="text-white/60">{data.recruiter_email}</span> for a new link.</p>
      </GlassCard>
    </div>
  );

  if (data.already_submitted) return (
    <div className="min-h-screen bg-glow flex items-center justify-center p-4">
      <GlassCard className="max-w-md w-full text-center space-y-3">
        <div className="text-4xl text-white/80">✓</div>
        <h1 className="text-white font-light">Already submitted</h1>
        <p className="text-white/40 text-sm">You've already selected your availability. Check your email for confirmation details.</p>
      </GlassCard>
    </div>
  );

  return (
    <div className="min-h-screen bg-glow flex items-center justify-center p-4 py-12">
      <div className="max-w-lg w-full space-y-4 animate-fade-in">
        {/* Header Card */}
        <GlassCard className="!p-6 space-y-3">
          <div>
            <p className="text-white/40 text-xs uppercase tracking-wider">Interview Invitation</p>
            <h1 className="text-white text-xl font-light mt-1">Hi {data.candidate_name},</h1>
          </div>
          <div className="glass-flat !rounded-xl !p-4 space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-white/35">Position</span>
              <span className="text-white/70">{data.job_title}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/35">Round</span>
              <span className="text-white/70 capitalize">{data.round_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/35">Duration</span>
              <span className="text-white/70">{data.duration_minutes} minutes</span>
            </div>
          </div>
          <p className="text-white/40 text-sm">Please select up to 3 preferred time slots below. We'll confirm the best one.</p>
        </GlassCard>

        {/* Timezone selector */}
        <div className="flex items-center gap-3 px-1">
          <span className="text-white/30 text-xs shrink-0">Your timezone:</span>
          <select className="glass-input !py-2 !text-xs flex-1" value={tz} onChange={(e) => setTz(e.target.value)}>
            {TIMEZONES.map((t) => <option key={t} value={t} style={{ background: "#111" }}>{t}</option>)}
          </select>
        </div>

        {/* Slots */}
        <GlassCard className="!p-5 space-y-2">
          <div className="flex justify-between items-center mb-3">
            <p className="text-white/40 text-xs uppercase tracking-wider">Available Slots</p>
            <p className="text-white/25 text-xs">{selected.length}/3 selected</p>
          </div>
          {data.slots.length === 0 ? (
            <p className="text-white/30 text-sm text-center py-6">No slots available. Contact your recruiter.</p>
          ) : (
            data.slots.map((slot: any) => {
              const isSelected = selected.includes(slot.id);
              return (
                <div
                  key={slot.id}
                  onClick={() => toggle(slot.id)}
                  className={clsx(
                    "p-4 rounded-xl border cursor-pointer transition-all",
                    isSelected ? "border-white/35 bg-white/10" : "border-white/08 hover:border-white/20",
                    !isSelected && selected.length >= 3 && "opacity-40 cursor-not-allowed"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/80 text-sm font-medium">{formatInTz(slot.start_time)}</p>
                      {slot.ai_reasoning && (
                        <p className="text-white/25 text-xs mt-0.5">{slot.ai_reasoning}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-3">
                      {slot.ai_score !== null && (
                        <span className="text-white/20 text-xs font-mono hidden sm:block">{scoreBar(slot.ai_score)}</span>
                      )}
                      <div className={clsx("w-4 h-4 rounded border flex items-center justify-center text-xs shrink-0 transition-all", isSelected ? "bg-white border-white text-black" : "border-white/20")}>
                        {isSelected && "✓"}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </GlassCard>

        <button
          className="btn-primary w-full justify-center py-3 text-base"
          onClick={handleSubmit}
          disabled={submitting || selected.length === 0}
        >
          {submitting ? <LoadingSpinner size="sm" /> : `Confirm ${selected.length} slot${selected.length !== 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}