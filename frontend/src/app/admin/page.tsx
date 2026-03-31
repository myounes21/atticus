"use client";

import { useState } from "react";
import Image from "next/image";
import CasesPanel from "@/components/cases/CasesPanel";
import DocumentsPanel from "@/components/documents/DocumentsPanel";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function AdminPage() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const { loading, user, logout } = useAuthGuard({ allowedRoles: ["admin"] });

  if (loading) {
    return (
      <main className="portal-loading-shell">
        <section className="card">
          <p className="muted">Loading admin workspace...</p>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-brand">
          <div className="admin-brand-icon">
            <span className="material-symbols-outlined ms-fill">gavel</span>
          </div>
          <div>
            <h1>Atticus</h1>
            <p>Admin Portal</p>
          </div>
        </div>

        <nav className="admin-nav-list">
          <button type="button" className="admin-nav-item active">
            <span className="material-symbols-outlined ms-fill">dashboard</span>
            Dashboard
          </button>
          <button type="button" className="admin-nav-item">
            <span className="material-symbols-outlined">work</span>
            Cases
          </button>
          <button type="button" className="admin-nav-item">
            <span className="material-symbols-outlined">description</span>
            Documents
          </button>
          <button type="button" className="admin-nav-item">
            <span className="material-symbols-outlined">group</span>
            Clients
          </button>
          <button type="button" className="admin-nav-item">
            <span className="material-symbols-outlined">analytics</span>
            Analytics
          </button>
        </nav>

        <div className="admin-sidebar-foot">
          <button type="button" className="signature-gradient admin-initiate-btn">
            <span className="material-symbols-outlined">add</span>
            Initiate Case
          </button>
          <button type="button" className="admin-nav-item compact">
            <span className="material-symbols-outlined">help</span>
            Help Center
          </button>
          <button type="button" className="admin-nav-item compact" onClick={logout}>
            <span className="material-symbols-outlined">logout</span>
            Logout
          </button>
        </div>
      </aside>

      <section className="admin-main">
        <header className="admin-topbar glass-effect">
          <div>
            <h2>The Informed Architect</h2>
            <p>Firm Administration &amp; Operations</p>
          </div>
          <div className="admin-topbar-actions">
            <label className="admin-search">
              <span className="material-symbols-outlined">search</span>
              <input placeholder="Search cases, docs, or lawyers..." />
            </label>
            <div className="admin-topbar-divider">
              <button type="button" className="admin-icon-btn" aria-label="Notifications">
                <span className="material-symbols-outlined">notifications</span>
                <span className="admin-notification-dot" aria-hidden="true" />
              </button>
              <button type="button" className="admin-icon-btn" aria-label="Settings">
                <span className="material-symbols-outlined">settings</span>
              </button>
            </div>
            <div className="admin-profile">
              <div className="admin-user">
                <p>Admin</p>
                <small>{user?.email ?? "Mr. Finch"}</small>
              </div>
              <Image
                className="admin-avatar"
                alt="Admin profile"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBAAAlvlgfi6TBj_xxCe0mQuuD1ldiVQMVB_fAOR955O8fXQqT53wiu55B29oLpkhzwnpEwAowLfOQ7hXsecqxHJziq6FTdqgKcYZnchVyXvpwdhBjcuvDvrliXnbVU7g-LeOM56gWADEMhSofQhq8AovRip3mN7mZBbk3X-kyl8KBR61GgEqHuc6pNtB5CEkIU-kbNvh-bJGHlzwh5K3msb417Zho2fKkIvLBeTX710ziXCZ5byN1CEEWRytwQ_QBV3qxO4wZw9j4"
                width={40}
                height={40}
                unoptimized={false}
              />
            </div>
          </div>
        </header>

        <section className="admin-canvas">
          <div className="admin-summary-grid">
            <article className="admin-overview-card">
              <h3>Administrative Overview</h3>
              <p>
                Infrastructure operational. Your workspace leverages a production-minded stack of <strong>FastAPI</strong>,{" "}
                <strong>Next.js</strong>, and <strong>Celery</strong>. Document ingestion and hybrid vector search are
                currently active across all assigned matters.
              </p>
              <div className="admin-overview-chips">
                <span className="admin-chip">
                  <span className="admin-chip-dot" aria-hidden="true" />
                  Engine: Qdrant + ES
                </span>
                <span className="admin-chip">
                  <span className="material-symbols-outlined">security</span>
                  RBAC Hardened
                </span>
              </div>
            </article>

            <article className="admin-pulse-card signature-gradient">
              <div className="admin-pulse-head">
                <h3>Live Firm Pulse</h3>
                <span>Operational</span>
              </div>
              <div className="admin-pulse-metrics">
                <div>
                  <p>Aggregate Win Rate</p>
                  <div className="admin-pulse-value">
                    <strong>94.2%</strong>
                    <span className="admin-pulse-delta">+2.1%</span>
                  </div>
                </div>
                <div>
                  <p>Case Velocity</p>
                  <div className="admin-pulse-value">
                    <strong>+12.4%</strong>
                    <span className="material-symbols-outlined admin-pulse-trend">trending_up</span>
                  </div>
                </div>
              </div>
              <div className="admin-throughput">
                <div>
                  <span>Ingestion Pipeline Throughput</span>
                  <span>89%</span>
                </div>
                <div className="admin-throughput-bar" aria-label="Ingestion throughput">
                  <div className="admin-throughput-fill" style={{ width: "89%" }} />
                </div>
              </div>
            </article>
          </div>

          <section className="admin-operations-grid">
            <DocumentsPanel caseId={selectedCaseId} allowUpload autoRefresh variant="ingestion" />
            <CasesPanel
              allowCreate
              showAssignedSummary
              autoRefresh
              variant="admin-lifecycle"
              onSelectCase={(caseId) => setSelectedCaseId(caseId)}
            />
          </section>
        </section>
      </section>

      <button type="button" className="admin-fab" aria-label="Open AI Operational Assistant">
        <span className="material-symbols-outlined">chat_bubble</span>
      </button>
    </main>
  );
}
