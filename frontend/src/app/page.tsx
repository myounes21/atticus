"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";
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

  const busy = loginBusy || registerBusy;

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

  return (
    <main className="landing-shell">
      <section className="landing-grid">
        <section className="card landing-intro">
          <span className="intro-pill">Atticus Legal Workspace</span>
          <h1>Simple case operations, clear answers, less tool friction.</h1>
          <p>
            Organize cases, manage document ingestion, and ask grounded questions with source-backed
            responses.
          </p>
          <ul>
            <li>Admins can create cases and upload files.</li>
            <li>Lawyers can run case-scoped Q&amp;A.</li>
            <li>Session-based access keeps each portal focused.</li>
          </ul>
        </section>

        <section className="card auth-card">
          <h2>Sign in</h2>
          <p className="muted">Enter your account details to open your portal.</p>
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
              {loginBusy ? "Signing in..." : "Sign in"}
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
