"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { getPanelists, createInterview } from "@/lib/api";
import { TIMEZONES, ROUND_TYPES, DURATIONS } from "@/lib/utils";
import toast from "react-hot-toast";
import clsx from "clsx";

const STEPS = ["Candidate", "Interview Details", "Panelists", "Review"];

export default function NewRequestPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [panelists, setPanelists] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    candidate: { name: "", email: "", phone: "", timezone: "Asia/Kolkata" },
    job_title: "",
    round_type: "technical",
    duration_minutes: 60,
    buffer_minutes: 15,
    window_start: "",
    window_end: "",
    notes: "",
    required_panelist_ids: [] as string[],
  });

  useEffect(() => {
    getPanelists().then(setPanelists).catch(() => toast.error("Could not load panelists"));
  }, []);

  const setField = (path: string, value: any) => {
    setForm((prev) => {
      const parts = path.split(".");
      if (parts.length === 1) return { ...prev, [path]: value };
      return { ...prev, [parts[0]]: { ...(prev as any)[parts[0]], [parts[1]]: value } };
    });
  };

  const togglePanelist = (id: string) => {
    setForm((prev) => ({
      ...prev,
      required_panelist_ids: prev.required_panelist_ids.includes(id)
        ? prev.required_panelist_ids.filter((p) => p !== id)
        : [...prev.required_panelist_ids, id],
    }));
  };

  const validateStep = () => {
    if (step === 0) {
      if (!form.candidate.name.trim()) { toast.error("Candidate name is required"); return false; }
      if (!form.candidate.email.trim()) { toast.error("Candidate email is required"); return false; }
    }
    if (step === 1) {
      if (!form.job_title.trim()) { toast.error("Job title is required"); return false; }
      if (!form.window_start || !form.window_end) { toast.error("Interview window dates are required"); return false; }
      if (new Date(form.window_end) <= new Date(form.window_start)) { toast.error("Window end must be after window start"); return false; }
    }
    if (step === 2) {
      if (form.required_panelist_ids.length === 0) { toast.error("Select at least one panelist"); return false; }
    }
    return true;
  };

  const next = () => { if (validateStep()) setStep((s) => Math.min(s + 1, 3)); };
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const submit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        window_start: new Date(form.window_start).toISOString(),
        window_end: new Date(form.window_end).toISOString(),
      };
      const result = await createInterview(payload);
      toast.success("Interview request created! Candidate email sent.");
      router.push(`/requests/${result.id}`);
    } catch (err: any) {
      toast.error(err.message || "Failed to create request");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-glow">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 max-w-2xl mx-auto w-full">
          {/* Step Indicators */}
          <div className="flex items-center gap-2 mb-8">
            {STEPS.map((label, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className={clsx(
                  "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-all",
                  i < step ? "step-done text-black" : i === step ? "step-active text-white" : "step-todo text-white/30"
                )}>
                  {i < step ? "✓" : i + 1}
                </div>
                <span className={clsx("text-xs", i === step ? "text-white/70" : "text-white/25")}>{label}</span>
                {i < STEPS.length - 1 && <div className="w-6 h-px bg-white/10 mx-1" />}
              </div>
            ))}
          </div>

          <GlassCard className="animate-fade-in">
            {/* Step 0: Candidate */}
            {step === 0 && (
              <div className="space-y-4">
                <h2 className="text-white font-medium mb-5">Candidate Information</h2>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Full Name *</label>
                  <input className="glass-input" placeholder="Jane Smith" value={form.candidate.name} onChange={(e) => setField("candidate.name", e.target.value)} />
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Email *</label>
                  <input className="glass-input" type="email" placeholder="jane@example.com" value={form.candidate.email} onChange={(e) => setField("candidate.email", e.target.value)} />
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Phone (optional)</label>
                  <input className="glass-input" placeholder="+1 555 000 0000" value={form.candidate.phone} onChange={(e) => setField("candidate.phone", e.target.value)} />
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Candidate Timezone</label>
                  <select className="glass-input" value={form.candidate.timezone} onChange={(e) => setField("candidate.timezone", e.target.value)}>
                    {TIMEZONES.map((tz) => <option key={tz} value={tz} style={{ background: "#111" }}>{tz}</option>)}
                  </select>
                </div>
              </div>
            )}

            {/* Step 1: Interview Details */}
            {step === 1 && (
              <div className="space-y-4">
                <h2 className="text-white font-medium mb-5">Interview Details</h2>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Job Title *</label>
                  <input className="glass-input" placeholder="Senior Software Engineer" value={form.job_title} onChange={(e) => setField("job_title", e.target.value)} />
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-3">Round Type *</label>
                  <div className="grid grid-cols-2 gap-2">
                    {ROUND_TYPES.map((rt) => (
                      <button
                        key={rt.value}
                        type="button"
                        onClick={() => setField("round_type", rt.value)}
                        className={clsx(
                          "py-2.5 px-4 rounded-xl text-sm border transition-all",
                          form.round_type === rt.value
                            ? "bg-white text-black border-white font-medium"
                            : "bg-white/05 text-white/50 border-white/10 hover:border-white/25"
                        )}
                      >
                        {rt.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Duration</label>
                    <select className="glass-input" value={form.duration_minutes} onChange={(e) => setField("duration_minutes", Number(e.target.value))}>
                      {DURATIONS.map((d) => <option key={d.value} value={d.value} style={{ background: "#111" }}>{d.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Buffer Time</label>
                    <select className="glass-input" value={form.buffer_minutes} onChange={(e) => setField("buffer_minutes", Number(e.target.value))}>
                      {[0, 15, 30].map((b) => <option key={b} value={b} style={{ background: "#111" }}>{b === 0 ? "No buffer" : `${b} min buffer`}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Window Start *</label>
                    <input className="glass-input" type="datetime-local" value={form.window_start} onChange={(e) => setField("window_start", e.target.value)} />
                  </div>
                  <div>
                    <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Window End *</label>
                    <input className="glass-input" type="datetime-local" value={form.window_end} onChange={(e) => setField("window_end", e.target.value)} />
                  </div>
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Notes (optional)</label>
                  <textarea className="glass-input min-h-[80px] resize-none" placeholder="Any additional context..." value={form.notes} onChange={(e) => setField("notes", e.target.value)} />
                </div>
              </div>
            )}

            {/* Step 2: Panelists */}
            {step === 2 && (
              <div className="space-y-4">
                <h2 className="text-white font-medium mb-2">Select Panelists</h2>
                <p className="text-white/40 text-xs mb-5">
                  {form.required_panelist_ids.length} selected — the system will check their Google Calendars
                </p>
                {panelists.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-white/40 text-sm">No panelists found.</p>
                    <a href="/panelists/new" className="text-white/50 text-xs underline mt-2 block">Add panelists first →</a>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {panelists.map((p) => {
                      const selected = form.required_panelist_ids.includes(p.id);
                      return (
                        <div
                          key={p.id}
                          onClick={() => togglePanelist(p.id)}
                          className={clsx(
                            "flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all",
                            selected ? "border-white/30 bg-white/08" : "border-white/08 hover:border-white/18"
                          )}
                        >
                          <div className={clsx("w-4 h-4 rounded border flex items-center justify-center text-xs transition-all", selected ? "bg-white border-white text-black" : "border-white/20")}>
                            {selected && "✓"}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-white/80 text-sm font-medium truncate">{p.name}</p>
                            <p className="text-white/35 text-xs truncate">{p.role || p.email}</p>
                          </div>
                          <div className={clsx("w-2 h-2 rounded-full", p.calendar_connected ? "bg-white" : "bg-white/15")} title={p.calendar_connected ? "Calendar connected" : "No calendar"} />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Review */}
            {step === 3 && (
              <div className="space-y-4">
                <h2 className="text-white font-medium mb-5">Review & Submit</h2>
                <div className="space-y-3 text-sm">
                  {[
                    ["Candidate", `${form.candidate.name} — ${form.candidate.email}`],
                    ["Timezone", form.candidate.timezone],
                    ["Job Title", form.job_title],
                    ["Round", form.round_type.toUpperCase()],
                    ["Duration", `${form.duration_minutes} min + ${form.buffer_minutes} min buffer`],
                    ["Window", `${form.window_start} → ${form.window_end}`],
                    ["Panelists", `${form.required_panelist_ids.length} selected`],
                  ].map(([k, v]) => (
                    <div key={k} className="flex gap-4 py-2 border-b border-white/[0.06]">
                      <span className="text-white/35 w-24 shrink-0 text-xs uppercase tracking-wider">{k}</span>
                      <span className="text-white/70 flex-1">{v}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 p-3 glass-flat text-white/50 text-xs">
                  Submitting will check all panelist calendars, find available slots using AI ranking, and send an invitation email to the candidate.
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8 pt-5 border-t border-white/[0.07]">
              <button className="btn-ghost" onClick={back} disabled={step === 0}>← Back</button>
              {step < 3 ? (
                <button className="btn-primary" onClick={next}>Continue →</button>
              ) : (
                <button className="btn-primary min-w-[140px] justify-center" onClick={submit} disabled={submitting}>
                  {submitting ? <LoadingSpinner size="sm" /> : "Create & Send Invite"}
                </button>
              )}
            </div>
          </GlassCard>
        </main>
      </div>
    </div>
  );
}
