"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { getBookingByToken, cancelBooking } from "@/lib/api";
import { formatDateTime, roundLabel } from "@/lib/utils";
import toast from "react-hot-toast";

export default function ConfirmPage() {
  const { token } = useParams<{ token: string }>();
  const [booking, setBooking] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    getBookingByToken(token)
      .then(setBooking)
      .catch(() => toast.error("Booking not found"))
      .finally(() => setLoading(false));
  }, [token]);

  const handleReschedule = async () => {
    if (!confirm("Request a reschedule? You'll receive a new link to pick a time.")) return;
    setCancelling(true);
    try {
      await cancelBooking(booking.id);
      toast.success("Reschedule requested. Your recruiter will send a new link.");
      setBooking({ ...booking, status: "cancelled" });
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setCancelling(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-glow flex items-center justify-center">
      <LoadingSpinner size="lg" />
    </div>
  );

  if (!booking) return (
    <div className="min-h-screen bg-glow flex items-center justify-center p-4">
      <GlassCard className="max-w-md w-full text-center">
        <p className="text-white/50">Booking not found.</p>
      </GlassCard>
    </div>
  );

  const isCancelled = booking.status === "cancelled" || booking.status === "rescheduled";

  return (
    <div className="min-h-screen bg-glow flex items-center justify-center p-4 py-12">
      <div className="max-w-md w-full space-y-4 animate-fade-in">
        <GlassCard className="!p-8 text-center space-y-5">
          <div className="text-6xl font-light text-white/80">
            {isCancelled ? "○" : "✓"}
          </div>
          <div>
            <h1 className="text-white text-xl font-light">
              {isCancelled ? "Interview Cancelled" : "Interview Confirmed"}
            </h1>
            <p className="text-white/40 text-sm mt-1">
              {isCancelled ? "Your recruiter will send a new scheduling link." : "A calendar invite has been sent to your email."}
            </p>
          </div>

          {!isCancelled && (
            <div className="glass-flat !rounded-xl !p-5 text-left space-y-2.5 text-sm">
              {[
                ["Position", booking.job_title],
                ["Round", roundLabel(booking.round_type || "")],
                ["Date & Time", booking.slot_start ? formatDateTime(booking.slot_start) : "—"],
                ["Format", "Google Meet (Video Call)"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <span className="text-white/35 shrink-0">{k}</span>
                  <span className="text-white/70 text-right">{v}</span>
                </div>
              ))}
              {booking.meet_link && (
                <div className="pt-2 border-t border-white/[0.07]">
                  <a
                    href={booking.meet_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary w-full justify-center text-sm"
                  >
                    Join Meeting →
                  </a>
                </div>
              )}
            </div>
          )}

          {!isCancelled && (
            <p className="text-white/25 text-xs">
              You'll receive reminders 24 hours and 1 hour before the interview.
            </p>
          )}
        </GlassCard>

        {!isCancelled && (
          <div className="text-center">
            <button
              onClick={handleReschedule}
              disabled={cancelling}
              className="text-white/25 text-xs hover:text-white/50 transition-colors underline underline-offset-2"
            >
              {cancelling ? "Processing..." : "Need to reschedule?"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
