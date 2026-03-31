"use client";

import { useState } from "react";
import CasesPanel from "@/components/cases/CasesPanel";
import ChatPanel from "@/components/chat/ChatPanel";
import DocumentsPanel from "@/components/documents/DocumentsPanel";
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
      subtitle="Ask focused case questions and verify every answer with sources."
      greeting="Hey, welcome back, Mr Finch."
      demoGuide={[
        "Select a case from the list.",
        "Watch documents become ready after admin uploads.",
        "Start with a source-specific suggested question.",
        "Review streamed answer structure and source references.",
      ]}
      userEmail={user?.email}
      onLogout={logout}
    >
      <div className="stack">
        <CasesPanel allowCreate={false} autoRefresh onSelectCase={(caseId) => setSelectedCaseId(caseId)} />
        <DocumentsPanel caseId={selectedCaseId} allowUpload={false} autoRefresh />
      </div>
      <ChatPanel caseId={selectedCaseId} />
    </WorkspaceShell>
  );
}
