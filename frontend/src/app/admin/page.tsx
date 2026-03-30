"use client";

import { useState } from "react";
import CasesPanel from "@/components/cases/CasesPanel";
import DocumentsPanel from "@/components/documents/DocumentsPanel";
import WorkspaceShell from "@/components/layout/WorkspaceShell";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function AdminPage() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const { loading, user, logout } = useAuthGuard({ allowedRoles: ["admin"] });

  if (loading) {
    return (
      <main className="workspace-shell">
        <section className="card">
          <p className="muted">Loading admin workspace...</p>
        </section>
      </main>
    );
  }

  return (
    <WorkspaceShell
      title="Admin Portal"
      subtitle="Manage cases, upload files, and monitor ingestion status."
      userEmail={user?.email}
      onLogout={logout}
    >
      <CasesPanel allowCreate onSelectCase={(caseId) => setSelectedCaseId(caseId)} />
      <DocumentsPanel caseId={selectedCaseId} allowUpload />
    </WorkspaceShell>
  );
}
