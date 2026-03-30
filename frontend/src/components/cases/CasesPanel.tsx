"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createCase, listCases } from "@/lib/api";

type CaseItem = {
  case_id: string;
  name: string;
  client_name: string | null;
  status: "active" | "closed";
  assigned_lawyers: string[];
};

export default function CasesPanel({
  allowCreate,
  onSelectCase,
}: {
  allowCreate: boolean;
  onSelectCase: (caseId: string | null) => void;
}) {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [name, setName] = useState("");
  const [clientName, setClientName] = useState("");
  const [assigned, setAssigned] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const selectedCaseIdRef = useRef<string | null>(null);

  const updateSelection = useCallback(
    (nextCaseId: string | null) => {
      selectedCaseIdRef.current = nextCaseId;
      setSelectedCaseId(nextCaseId);
      onSelectCase(nextCaseId);
    },
    [onSelectCase],
  );

  const refreshCases = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const rows = await listCases();
      setCases(rows);
      if (rows.length === 0) {
        updateSelection(null);
        return;
      }

      const currentSelection = selectedCaseIdRef.current;
      const nextSelection =
        currentSelection && rows.some((item) => item.case_id === currentSelection)
          ? currentSelection
          : rows[0].case_id;
      updateSelection(nextSelection);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  }, [updateSelection]);

  useEffect(() => {
    void refreshCases();
  }, [refreshCases]);

  async function submitCreate() {
    setMessage("");
    if (!name.trim()) {
      setError("Case name is required.");
      return;
    }
    setCreating(true);
    setError("");
    try {
      await createCase({
        name: name.trim(),
        client_name: clientName.trim() || undefined,
        assigned_lawyers: assigned
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
      });
      setName("");
      setClientName("");
      setAssigned("");
      setMessage("Case created successfully.");
      await refreshCases();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="card">
      <div className="section-head">
        <h2>Cases</h2>
        <span className="pill subtle">{cases.length} total</span>
      </div>
      {loading && <p className="muted">Loading cases...</p>}
      {error && <p className="error-text">{error}</p>}
      {message && <p className="ok-text">{message}</p>}
      {!loading && cases.length === 0 && <p className="muted">No cases found yet.</p>}
      <ul className="list-reset stack-sm">
        {cases.map((item) => (
          <li key={item.case_id}>
            <button
              type="button"
              className={item.case_id === selectedCaseId ? "case-btn active" : "case-btn"}
              onClick={() => {
                updateSelection(item.case_id);
              }}
            >
              <span>
                <strong>{item.name}</strong>
                {item.client_name ? <small className="muted">{item.client_name}</small> : null}
              </span>
              <span className="status-tag">{item.status}</span>
            </button>
          </li>
        ))}
      </ul>

      {allowCreate && (
        <>
          <h3>Create Case</h3>
          <div className="stack create-case-grid">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Case name"
            />
            <input
              value={clientName}
              onChange={(event) => setClientName(event.target.value)}
              placeholder="Client name"
            />
            <input
              value={assigned}
              onChange={(event) => setAssigned(event.target.value)}
              placeholder="Assigned lawyer IDs (comma-separated)"
            />
            <button type="button" onClick={() => void submitCreate()} disabled={creating}>
              {creating ? "Creating..." : "Create case"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
