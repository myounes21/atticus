"use client";

import { useState } from "react";
import CasesPanel from "@/components/cases/CasesPanel";
import ChatPanel from "@/components/chat/ChatPanel";
import WorkspaceShell from "@/components/layout/WorkspaceShell";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function LawyerPage() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const { loading, user, logout } = useAuthGuard({ allowedRoles: ["lawyer"] });

  if (loading) {
    return (
      <main className="workspace-shell">
        <section className="card">
          <p className="muted">Loading lawyer workspace...</p>
        </section>
      </main>
    );
  }

  return (
    <WorkspaceShell
      title="Lawyer Portal"
      subtitle="Ask questions scoped to your assigned case documents."
      userEmail={user?.email}
      onLogout={logout}
    >
      <CasesPanel allowCreate={false} onSelectCase={(caseId) => setSelectedCaseId(caseId)} />
      <ChatPanel caseId={selectedCaseId} />
    </WorkspaceShell>
  );
}
