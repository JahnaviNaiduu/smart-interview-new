"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { getPanelists, createPanelist, deletePanelist, getCalendarAuthUrl } from "@/lib/api";
import toast from "react-hot-toast";
import clsx from "clsx";

export default function PanelistsPage() {
  const [panelists, setPanelists] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "", skills: "" });

  const load = () => {
    getPanelists()
      .then(setPanelists)
      .catch(() => toast.error("Failed to load panelists"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim() || !form.email.trim()) { toast.error("Name and email are required"); return; }
    setSaving(true);
    try {
      await createPanelist({
        name: form.name,
        email: form.email,
        role: form.role || undefined,
        skills: form.skills ? form.skills.split(",").map((s) => s.trim()).filter(Boolean) : [],
      });
      toast.success("Panelist added");
      setForm({ name: "", email: "", role: "", skills: "" });
      setShowForm(false);
      load();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleConnectCalendar = async (id: string) => {
    try {
      const data = await getCalendarAuthUrl(id);
      window.open(data.auth_url, "_blank");
    } catch (err: any) {
      toast.error("Failed to get calendar auth URL");
    }
  };

  const handleDeactivate = async (id: string, name: string) => {
    if (!confirm(`Deactivate ${name}?`)) return;
    try {
      await deletePanelist(id);
      toast.success("Panelist deactivated");
      load();
    } catch {
      toast.error("Failed to deactivate");
    }
  };

  return (
    <div className="flex min-h-screen bg-glow">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-6 space-y-5">
          <div className="flex items-center justify-between">
            <p className="text-white/40 text-sm">{panelists.length} panelists</p>
            <button className="btn-primary text-xs px-4 py-2" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancel" : "+ Add Panelist"}
            </button>
          </div>

          {showForm && (
            <GlassCard className="animate-fade-in space-y-4">
              <h3 className="text-white font-medium mb-4">New Panelist</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Name *</label>
                  <input className="glass-input" placeholder="Alex Johnson" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Email *</label>
                  <input className="glass-input" type="email" placeholder="alex@company.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Role</label>
                  <input className="glass-input" placeholder="Engineering Manager" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
                </div>
                <div>
                  <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Skills (comma separated)</label>
                  <input className="glass-input" placeholder="Python, System Design" value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <button className="btn-primary min-w-[100px] justify-center" onClick={handleCreate} disabled={saving}>
                  {saving ? <LoadingSpinner size="sm" /> : "Add Panelist"}
                </button>
              </div>
            </GlassCard>
          )}

          <GlassCard className="!p-0 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-48"><LoadingSpinner /></div>
            ) : panelists.length === 0 ? (
              <EmptyState icon="◉" title="No panelists yet" description="Add panelists to start scheduling interviews" />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.07]">
                    {["Name", "Email", "Role", "Skills", "Calendar", ""].map((h) => (
                      <th key={h} className="text-left px-5 py-3 text-white/30 text-xs font-medium uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {panelists.map((p) => (
                    <tr key={p.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-3.5 text-white/80 font-medium">{p.name}</td>
                      <td className="px-5 py-3.5 text-white/50 text-xs">{p.email}</td>
                      <td className="px-5 py-3.5 text-white/40 text-xs">{p.role || "—"}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex flex-wrap gap-1">
                          {(p.skills || []).slice(0, 3).map((s: string) => (
                            <span key={s} className="text-white/40 text-xs border border-white/10 px-2 py-0.5 rounded-full">{s}</span>
                          ))}
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        {p.calendar_connected ? (
                          <span className="text-xs text-white/50 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-white inline-block" /> Connected
                          </span>
                        ) : (
                          <button onClick={() => handleConnectCalendar(p.id)} className="text-xs text-white/40 hover:text-white underline underline-offset-2 transition-colors">
                            Connect →
                          </button>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        <button onClick={() => handleDeactivate(p.id, p.name)} className="text-white/20 hover:text-white/50 text-xs transition-colors">
                          Remove
                        </button>
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
