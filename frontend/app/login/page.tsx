"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import GlassCard from "@/components/ui/GlassCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { login } from "@/lib/api";
import { setToken, setStoredUser } from "@/lib/auth";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      toast.error("Email and password are required");
      return;
    }
    setSubmitting(true);
    try {
      const res = await login(email.trim(), password);
      setToken(res.access_token);
      setStoredUser(res.user);
      toast.success(`Welcome, ${res.user.name}`);
      router.push("/");
    } catch (err: any) {
      toast.error(err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-glow p-6">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="text-white font-semibold text-sm tracking-widest uppercase opacity-80">
            Interview Scheduler
          </div>
          <div className="text-white/30 text-xs mt-1">Sign in to continue</div>
        </div>
        <GlassCard className="animate-fade-in">
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Email</label>
              <input
                className="glass-input"
                type="email"
                autoComplete="username"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="text-white/40 text-xs uppercase tracking-wider block mb-1.5">Password</label>
              <input
                className="glass-input"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button className="btn-primary w-full justify-center" type="submit" disabled={submitting}>
              {submitting ? <LoadingSpinner size="sm" /> : "Sign In"}
            </button>
          </form>
        </GlassCard>
      </div>
    </div>
  );
}
