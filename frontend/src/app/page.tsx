"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { login, register, resetDemoData } from "@/lib/api";
import { getStoredUser, getToken, type Role, saveSession } from "@/lib/auth";

function targetPathForRole(role: Role): string {
  return role === "admin" ? "/admin" : "/lawyer";
}

export default function HomePage() {
  const router = useRouter();
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

  async function startGuidedDemo(roleTarget: "lawyer" | "admin") {
    const demoEmail = roleTarget === "lawyer" ? "demo.lawyer@atticus.local" : "demo.admin@atticus.local";
    const demoPassword = "DemoPass!123";

    setEmail(demoEmail);
    setPassword(demoPassword);
    setDemoBusy(roleTarget);
    setError("");
    setMessage("");
    try {
      const result = await login(demoEmail, demoPassword);
      saveSession(result);
      router.replace(targetPathForRole(result.user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start demo");
    } finally {
      setDemoBusy(null);
    }
  }

  async function startFreshDemo() {
    const demoPassword = "DemoPass!123";
    setDemoBusy("lawyer");
    setError("");
    setMessage("");
    try {
      const adminSession = await login("demo.admin@atticus.local", demoPassword);
      await resetDemoData(adminSession.access_token);
      const targetSession = await login("demo.lawyer@atticus.local", demoPassword);
      saveSession(targetSession);
      router.replace(targetPathForRole(targetSession.user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start fresh demo");
    } finally {
      setDemoBusy(null);
    }
  }

  return (
    <main className="landing-shell">
      <section className="landing-grid">
        <section className="card landing-intro">
          <span className="intro-pill">Atticus Legal Workspace</span>
          <h1>Understand the product in 60 seconds.</h1>
          <p>
            This demo shows case-scoped legal Q&amp;A with source-backed responses. Start with Lawyer mode for
            the clearest walkthrough.
          </p>
          <div className="demo-quick-actions">
            <button type="button" onClick={() => void startGuidedDemo("lawyer")} disabled={busy}>
              {demoBusy === "lawyer" ? "Starting demo..." : "Start 60-second demo"}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => void startGuidedDemo("admin")}
              disabled={busy}
            >
              {demoBusy === "admin" ? "Opening admin..." : "Open admin view"}
            </button>
            <button type="button" className="secondary" onClick={() => void startFreshDemo()} disabled={busy}>
              {demoBusy !== null ? "Resetting demo..." : "Start fresh demo (resets data)"}
            </button>
          </div>
          <ol className="demo-steps">
            <li>Open a seeded case.</li>
            <li>Click a suggested prompt.</li>
            <li>Review answer and source references.</li>
          </ol>
        </section>

        <section className="card auth-card">
          <h2>Sign in</h2>
          <p className="muted">Use the quick demo buttons, or sign in manually below.</p>
          {!selfRegisterEnabled && (
            <p className="muted">
              Demo accounts: <strong>demo.admin@atticus.local</strong> and <strong>demo.lawyer@atticus.local</strong>.
              Password: <strong>DemoPass!123</strong>.
            </p>
          )}
          {demoAuthEnabled && (
            <p className="ok-text">Demo authentication is enabled. Password checks are relaxed.</p>
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
        </section>
      </section>
    </main>
  );
}
