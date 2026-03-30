"use client";

import type { ReactNode } from "react";

type WorkspaceShellProps = {
  title: string;
  subtitle: string;
  userEmail?: string | null;
  onLogout: () => void;
  children: ReactNode;
};

export default function WorkspaceShell({
  title,
  subtitle,
  userEmail,
  onLogout,
  children,
}: WorkspaceShellProps) {
  return (
    <main className="workspace-shell">
      <section className="card workspace-head">
        <div>
          <p className="eyebrow">Signed in workspace</p>
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

      <section className="workspace-content">{children}</section>
    </main>
  );
}
