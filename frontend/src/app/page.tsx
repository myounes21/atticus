"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { login, register, resetDemoData } from "@/lib/api";
import { getStoredUser, getToken, type Role, saveSession } from "@/lib/auth";

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
  const [role, setRole] = useState<Role>("lawyer");
  const [loginBusy, setLoginBusy] = useState(false);
  const [registerBusy, setRegisterBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState<"lawyer" | "admin" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const selfRegisterEnabled = useMemo(
    () => process.env.NEXT_PUBLIC_ENABLE_SELF_REGISTER !== "false",
    [],
  );
  const demoAuthEnabled = useMemo(
    () => process.env.NEXT_PUBLIC_DEMO_AUTH !== "false",
    [],
  );

  const busy = loginBusy || registerBusy || demoBusy !== null;

  useEffect(() => {
    if (demoAuthEnabled) {
      void ensureFreshDemoData().catch(() => {});
    }
  }, [demoAuthEnabled]);

  useEffect(() => {
    const user = getStoredUser();
    const token = getToken();
    if (user && token) {
      router.replace(targetPathForRole(user.role));
    }
  }, [router]);

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
    if (!validateCredentials()) {
      return;
    }
    setLoginBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await login(email.trim(), password || "demo");
      saveSession(result);
      setMessage(`Welcome back, ${result.user.email}`);
      router.replace(targetPathForRole(result.user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoginBusy(false);
    }
  }

  async function doRegister() {
    if (!validateCredentials()) {
      return;
    }
    setRegisterBusy(true);
    setError("");
    setMessage("");
    try {
      const user = await register(email.trim(), password || "demo", role);
      setMessage(`Registered ${user.email}. You can now log in.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setRegisterBusy(false);
    }
  }

  async function ensureFreshDemoData(): Promise<void> {
    if (demoPreparedForSession) {
      return;
    }
    const now = Date.now();
    if (now < demoResetCooldownAt.current) {
      return;
    }
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
    setError("");
    setMessage("");
    try {
      await ensureFreshDemoData();
      const result = await login(demoEmail, demoPassword);
      saveSession(result);
      router.replace(targetPathForRole(result.user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start demo");
    } finally {
      setDemoBusy(null);
    }
  }

  return (
    <main className="welcome-shell">
      <div className="welcome-bg" aria-hidden="true">
        <div className="welcome-glow welcome-glow-left" />
        <div className="welcome-glow welcome-glow-right" />
      </div>

      <header className="welcome-branding">
        <h1>Legal Atelier</h1>
        <p>Precision in Practice</p>
      </header>

      <section className="welcome-demo-pill" aria-label="Environment badge">
        <span className="material-symbols-outlined">biotech</span>
        Demo Environment
      </section>

      <section className="welcome-card glass-panel">
        <div className="welcome-card-main">
          <div className="welcome-anchor">
            <span className="material-symbols-outlined">timer</span>
          </div>
          <h2>Understand the product in 60 seconds</h2>
          <p>
            Experience case-scoped legal Q&amp;A. Our engine ingests your active litigation files to provide
            instant, sourced answers to complex procedural and factual inquiries.
          </p>
          {demoAuthEnabled && (
            <p className="welcome-demo-note">
              This is a simulated environment for portfolio demonstration. Authentication checks are relaxed.
            </p>
          )}

          <div className="welcome-cta-row">
            <button type="button" className="signature-gradient" onClick={() => void startGuidedDemo("lawyer")} disabled={busy}>
              <span className="material-symbols-outlined">person</span>
              {demoBusy === "lawyer" ? "Opening Lawyer Demo" : "Start Lawyer Demo"}
            </button>
            <button
              type="button"
              className="outline-cta"
              onClick={() => void startGuidedDemo("admin")}
              disabled={busy}
            >
              <span className="material-symbols-outlined">admin_panel_settings</span>
              {demoBusy === "admin" ? "Opening Admin Demo" : "Start Admin Demo"}
            </button>
          </div>

          <p className="welcome-trial-note">
            <span className="material-symbols-outlined">verified_user</span>
            No account required for trial
          </p>
        </div>

        <div className="welcome-detail-strip">
          <article>
            <span className="material-symbols-outlined">psychology</span>
            <div>
              <h3>Neural Synthesis</h3>
              <p>Logic applied to your case specifics.</p>
            </div>
          </article>
          <article>
            <span className="material-symbols-outlined">history_edu</span>
            <div>
              <h3>Source Integrity</h3>
              <p>Every answer cited to your discovery.</p>
            </div>
          </article>
        </div>
      </section>

      <footer className="welcome-footer-copy">
        <p>Trusted by elite firms for complex multi-district litigation research.</p>
        <div className="welcome-logo-placeholders" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </footer>

      <section className="manual-auth card">
        <details>
          <summary>Manual sign in and account tools</summary>
          <div className="stack">
            {!selfRegisterEnabled && (
              <p className="muted">
                Demo accounts: <strong>demo.admin@atticus.local</strong> and <strong>demo.lawyer@atticus.local</strong>.
                Password: <strong>DemoPass!123</strong>.
              </p>
            )}
            <form className="stack" onSubmit={(event) => void doLogin(event)}>
              <label className="field">
                <span>Email</span>
                <input
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@firm.com"
                  autoComplete="email"
                />
              </label>

              <label className="field">
                <span>Password</span>
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={demoAuthEnabled ? "Optional in demo mode" : "Required"}
                  type="password"
                  autoComplete="current-password"
                />
              </label>

              <button type="submit" disabled={busy}>
                {loginBusy ? "Signing in..." : "Manual sign in"}
              </button>
            </form>

            {selfRegisterEnabled && (
              <div className="stack register-area">
                <p className="muted">Need a user for local testing?</p>
                <div className="row">
                  <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
                    <option value="admin">Admin</option>
                    <option value="lawyer">Lawyer</option>
                  </select>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => void doRegister()}
                    disabled={busy}
                  >
                    {registerBusy ? "Creating..." : "Create account"}
                  </button>
                </div>
              </div>
            )}

            {error && <p className="error-text">{error}</p>}
            {message && <p className="ok-text">{message}</p>}
          </div>
        </details>
      </section>

      <nav className="welcome-fixed-nav" aria-label="Policy links">
        <div>
          <a href="#">Privacy Protocol</a>
          <a href="#">Data Residency</a>
        </div>
        <p>© 2024 Legal Atelier. Precision Workspace.</p>
      </nav>
    </main>
  );
}
