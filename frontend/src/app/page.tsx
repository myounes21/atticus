"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { login, resetDemoData } from "@/lib/api";
import { type Role, saveSession } from "@/lib/auth";

function targetPathForRole(role: Role): string {
  return role === "admin" ? "/admin" : "/lawyer";
}

let demoPreparedForSession = false;

export default function HomePage() {
  const router = useRouter();
  const demoResetInFlight = useRef<Promise<void> | null>(null);
  const demoResetCooldownAt = useRef<number>(0);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState<"lawyer" | "admin" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const demoAuthEnabled = useMemo(() => process.env.NEXT_PUBLIC_DEMO_AUTH !== "false", []);

  const busy = loginBusy || demoBusy !== null;

  useEffect(() => {
    if (demoAuthEnabled) {
      void ensureFreshDemoData().catch(() => {});
    }
  }, [demoAuthEnabled]);

  function validateCredentials(): boolean {
    if (!email.trim()) {
      setError("Email is required.");
      return false;
    }
    if (!demoAuthEnabled && !password.trim()) {
      setError("Password is required.");
      return false;
    }
    return true;
  }

  async function doLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validateCredentials()) return;
    setLoginBusy(true); setError(""); setMessage("");
    try {
      const result = await login(email.trim(), password || "demo");
      saveSession(result);
      setMessage(`Welcome back, ${result.user.email}`);
      router.push(targetPathForRole(result.user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoginBusy(false);
    }
  }

  async function ensureFreshDemoData(): Promise<void> {
    if (demoPreparedForSession) return;
    const now = Date.now();
    if (now < demoResetCooldownAt.current) return;
    if (demoResetInFlight.current) {
      await demoResetInFlight.current;
      return;
    }

    demoResetInFlight.current = (async () => {
      const demoPassword = "DemoPass!123";
      const adminSession = await login("demo.admin@atticus.local", demoPassword);
      await resetDemoData(adminSession.access_token);
      demoPreparedForSession = true;
      demoResetCooldownAt.current = Date.now() + 5 * 60 * 1000;
    })();

    try {
      await demoResetInFlight.current;
    } finally {
      demoResetInFlight.current = null;
    }
  }

  async function startGuidedDemo(roleTarget: "lawyer" | "admin") {
    const demoEmail = roleTarget === "lawyer" ? "demo.lawyer@atticus.local" : "demo.admin@atticus.local";
    const demoPassword = "DemoPass!123";

    setEmail(demoEmail);
    setPassword(demoPassword);
    setDemoBusy(roleTarget);
    setError(""); setMessage("");
    try {
      await ensureFreshDemoData();
      const result = await login(demoEmail, demoPassword);
      saveSession(result);
      router.push(targetPathForRole(result.user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start demo");
    } finally {
      setDemoBusy(null);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 overflow-hidden relative">
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px]"></div>
        <div className="absolute -bottom-[10%] -right-[10%] w-[50%] h-[50%] rounded-full bg-tertiary/5 blur-[150px]"></div>
      </div>

      <header className="mb-16 text-center">
        <h1 className="font-display text-3xl font-extrabold text-primary tracking-tight">Legal Assistant</h1>
        <p className="text-on-surface-variant font-label text-sm mt-2 tracking-widest uppercase">Precision in Practice</p>
      </header>

      <main className="w-full max-w-2xl">
        <div className="flex justify-center mb-8">
          <span className="inline-flex items-center px-4 py-1.5 rounded-full text-xs font-bold tracking-widest uppercase bg-primary/10 text-primary border border-primary/20 shadow-sm">
            <span className="material-symbols-outlined text-sm mr-2">biotech</span>
            Demo Environment
          </span>
        </div>

        <section className="glass-panel rounded-xl shadow-[0_32px_64px_-12px_rgba(0,95,90,0.08)] overflow-hidden border border-outline-variant/20">
          <div className="p-10 md:p-14 text-center">
            <div className="mb-8 inline-flex items-center justify-center w-16 h-16 rounded-full bg-surface-container-high text-primary">
              <span className="material-symbols-outlined text-3xl">timer</span>
            </div>
            
            <h2 className="font-display text-4xl md:text-5xl font-bold text-on-surface tracking-tight leading-tight mb-6">
              Understand the product in 60 seconds
            </h2>
            
            <p className="text-on-surface-variant text-lg leading-relaxed mb-10 max-w-lg mx-auto">
              Experience case-scoped legal Q&amp;A. Our engine ingests your active litigation files to provide instant, sourced answers to complex procedural and factual inquiries.
            </p>
            
            {demoAuthEnabled && (
              <p className="text-xs text-on-surface-variant/70 italic mb-10 -mt-6">
                This is a simulated environment for portfolio demonstration. Authentication checks are relaxed.
              </p>
            )}

            <div className="flex flex-col items-center gap-8">
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 w-full">
                <button 
                  onClick={() => startGuidedDemo("lawyer")}
                  disabled={busy}
                  className="signature-gradient text-white font-headline font-semibold py-4 px-8 rounded-xl shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-3 w-full sm:w-auto min-w-[200px]"
                >
                  <span className="material-symbols-outlined">person</span>
                  <span>{demoBusy === "lawyer" ? "Opening..." : "Start Lawyer Demo"}</span>
                </button>
                <button 
                  onClick={() => startGuidedDemo("admin")}
                  disabled={busy}
                  className="border-2 border-primary text-primary font-headline font-semibold py-4 px-8 rounded-xl hover:bg-primary/5 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-3 w-full sm:w-auto min-w-[200px]"
                >
                  <span className="material-symbols-outlined">admin_panel_settings</span>
                  <span>{demoBusy === "admin" ? "Opening..." : "Start Admin Demo"}</span>
                </button>
              </div>
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-sm">verified_user</span>
                <span className="font-label text-xs text-on-surface-variant font-medium">No account required for trial</span>
              </div>
            </div>
          </div>

          <div className="bg-surface-container flex flex-col md:flex-row divide-y md:divide-y-0 md:divide-x divide-outline-variant/30">
            <div className="flex-1 p-6 flex items-start gap-4">
              <span className="material-symbols-outlined text-primary">psychology</span>
              <div>
                <p className="font-headline font-bold text-sm text-on-surface">Neural Synthesis</p>
                <p className="text-xs text-on-surface-variant">Logic applied to your case specifics.</p>
              </div>
            </div>
            <div className="flex-1 p-6 flex items-start gap-4">
              <span className="material-symbols-outlined text-primary">history_edu</span>
              <div>
                <p className="font-headline font-bold text-sm text-on-surface">Source Integrity</p>
                <p className="text-xs text-on-surface-variant">Every answer cited to your discovery.</p>
              </div>
            </div>
          </div>
        </section>

        <footer className="mt-12 text-center">
          <p className="text-on-surface-variant font-label text-sm">
            Trusted by elite firms for complex multi-district litigation research.
          </p>
          <div className="mt-6 flex justify-center gap-8 opacity-40 grayscale contrast-125">
            <div className="h-6 w-24 bg-on-surface-variant/20 rounded-sm"></div>
            <div className="h-6 w-24 bg-on-surface-variant/20 rounded-sm"></div>
            <div className="h-6 w-24 bg-on-surface-variant/20 rounded-sm"></div>
          </div>
        </footer>

        <div className="mt-12 flex justify-center">
          <details className="text-center group">
            <summary className="cursor-pointer text-xs text-outline hover:text-primary transition-colors font-medium">
              Advanced: Manual Authentication
            </summary>
            <div className="mt-6 p-6 glass-panel rounded-xl text-left">
               <form className="flex flex-col gap-4" onSubmit={doLogin}>
                  <label className="flex flex-col gap-1 text-sm font-semibold text-on-surface-variant">
                    Email
                    <input 
                      className="border border-outline-variant/40 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary/40 outline-none transition-all"
                      value={email} onChange={e => setEmail(e.target.value)} placeholder="you@firm.com" 
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-sm font-semibold text-on-surface-variant">
                    Password
                    <input 
                      type="password"
                      className="border border-outline-variant/40 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary/40 outline-none transition-all"
                      value={password} onChange={e => setPassword(e.target.value)} 
                    />
                  </label>
                  <button type="submit" disabled={busy} className="signature-gradient text-white py-2 rounded-lg font-bold mt-2">
                    {loginBusy ? "Signing in..." : "Sign In"}
                  </button>
                  {error && <p className="text-red-600 text-sm">{error}</p>}
                  {message && <p className="text-primary text-sm">{message}</p>}
               </form>
            </div>
          </details>
        </div>
      </main>

      <nav className="fixed bottom-8 w-full px-6 flex justify-between items-center text-on-surface-variant font-label text-xs">
        <div className="flex gap-6">
          <a href="#" className="hover:text-primary transition-colors">Privacy Protocol</a>
          <a href="#" className="hover:text-primary transition-colors">Data Residency</a>
        </div>
        <div className="text-right">
          <span>© 2026 Legal Assistant. Precision Workspace.</span>
        </div>
      </nav>
    </div>
  );
}
