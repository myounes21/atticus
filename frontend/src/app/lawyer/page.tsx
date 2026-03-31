"use client";

import { useState } from "react";
import CasesPanel from "@/components/cases/CasesPanel";
import ChatPanel from "@/components/chat/ChatPanel";
import DocumentsPanel from "@/components/documents/DocumentsPanel";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function LawyerPage() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const { loading, user, logout } = useAuthGuard({ allowedRoles: ["lawyer"] });

  if (loading) {
    return (
      <main className="portal-loading-shell">
        <section className="card">
          <p className="muted">Loading lawyer workspace...</p>
        </section>
      </main>
    );
  }

  return (
    <main className="lawyer-portal">
      <aside className="lawyer-slim-sidebar">
        <div className="lawyer-logo-mark">
          <span className="material-symbols-outlined">gavel</span>
        </div>
        <nav>
          <button type="button" className="lawyer-icon-btn">
            <span className="material-symbols-outlined">folder_open</span>
          </button>
          <button type="button" className="lawyer-icon-btn active">
            <span className="material-symbols-outlined">chat_bubble</span>
          </button>
          <button type="button" className="lawyer-icon-btn">
            <span className="material-symbols-outlined">description</span>
          </button>
        </nav>
        <div className="lawyer-sidebar-foot">
          <button type="button" className="lawyer-icon-btn">
            <span className="material-symbols-outlined">settings</span>
          </button>
          <button
            type="button"
            className="lawyer-account-chip"
            onClick={logout}
            title={user?.email ? `Logout (${user.email})` : "Logout"}
          >
            <span className="material-symbols-outlined">person</span>
          </button>
        </div>
      </aside>

      <section className="lawyer-main-shell">
        <header className="lawyer-topbar">
          <div className="lawyer-topbar-left">
            <div>
              <p className="lawyer-brand">ATTICUS</p>
            </div>
            <div className="lawyer-divider" />
            <span className="lawyer-pill pulse">Demo Mode</span>
            <span className="lawyer-pill case">{selectedCaseId ? "Matter Selected" : "Finch Demo Matter"}</span>
          </div>

          <div className="lawyer-topbar-right">
            <label className="lawyer-search">
              <span className="material-symbols-outlined">search</span>
              <input placeholder="Search insights..." />
            </label>
            <button type="button" className="lawyer-ring-btn">
              <span className="material-symbols-outlined">notifications</span>
            </button>
          </div>
        </header>

        <section className="lawyer-content-grid">
          <aside className="lawyer-left-column">
            <CasesPanel allowCreate={false} autoRefresh variant="compact" onSelectCase={(caseId) => setSelectedCaseId(caseId)} />
            <DocumentsPanel caseId={selectedCaseId} allowUpload={false} autoRefresh variant="compact" />
          </aside>
          <section className="lawyer-chat-column">
            <ChatPanel caseId={selectedCaseId} variant="lawyer-atelier" />
            <div className="lawyer-footer-badges" aria-hidden="true">
              <div>
                <span className="material-symbols-outlined">verified_user</span>
                Privileged and Confidential
              </div>
              <div>
                <span className="material-symbols-outlined">memory</span>
                Atelier Legal v4.2
              </div>
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}
