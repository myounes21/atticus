"use client";

import type { ReactNode } from "react";

type WorkspaceShellProps = {
  title: string;
  subtitle: string;
  demoGuide?: string[];
  greeting?: string;
  userEmail?: string | null;
  onLogout: () => void;
  children: ReactNode;
};

export default function WorkspaceShell({
  title,
  subtitle,
  demoGuide,
  greeting,
  userEmail,
  onLogout,
  children,
}: WorkspaceShellProps) {
  return (
    <main className="workspace-shell">
      <section className="card workspace-head">
        <div>
          <p className="eyebrow">Signed in workspace</p>
          {greeting ? <p className="welcome-line">{greeting}</p> : null}
          <h1>{title}</h1>
          <p className="muted">{subtitle}</p>
        </div>
        <div className="row">
          <span className="pill">{userEmail ?? "unknown user"}</span>
          <button type="button" className="secondary" onClick={onLogout}>
            Logout
          </button>
        </div>
      </section>

      {demoGuide && demoGuide.length > 0 && (
        <section className="card demo-guide-card">
          <div className="section-head">
            <h2>Demo guide</h2>
            <span className="pill subtle">Follow in order</span>
          </div>
          <ol className="demo-steps compact">
            {demoGuide.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      )}

      <section className="workspace-content">{children}</section>
    </main>
  );
}
