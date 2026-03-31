"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createCase, listCases, listLawyers, type LawyerOption } from "@/lib/api";

type CaseItem = {
  case_id: string;
  name: string;
  client_name: string | null;
  status: "active" | "closed";
  assigned_lawyers: string[];
};

export default function CasesPanel({
  allowCreate,
  autoRefresh = false,
  showAssignedSummary = false,
  onSelectCase,
}: {
  allowCreate: boolean;
  autoRefresh?: boolean;
  showAssignedSummary?: boolean;
  onSelectCase: (caseId: string | null) => void;
}) {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [name, setName] = useState("");
  const [clientName, setClientName] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const selectedCaseIdRef = useRef<string | null>(null);
  const [lawyers, setLawyers] = useState<LawyerOption[]>([]);
  const [selectedLawyerIds, setSelectedLawyerIds] = useState<string[]>([]);
  const [lawyerSearch, setLawyerSearch] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const primaryLawyerId = lawyers.find((item) => item.full_name.toLowerCase() === "mr lawyer")?.user_id ?? null;
  const lawyerNameById = useMemo(() => {
    return new Map(lawyers.map((lawyer) => [lawyer.user_id, lawyer.full_name]));
  }, [lawyers]);
  const lawyerById = useMemo(() => {
    return new Map(lawyers.map((lawyer) => [lawyer.user_id, lawyer]));
  }, [lawyers]);
  const filteredLawyers = useMemo(() => {
    const query = lawyerSearch.trim().toLowerCase();
    return lawyers
      .filter((lawyer) => {
        if (selectedLawyerIds.includes(lawyer.user_id)) {
          return false;
        }
        if (!query) {
          return true;
        }
        return lawyer.full_name.toLowerCase().includes(query) || lawyer.email.toLowerCase().includes(query);
      })
      .slice(0, 10);
  }, [lawyerSearch, lawyers, selectedLawyerIds]);

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

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshCases();
    }, 4500);
    return () => {
      window.clearInterval(timer);
    };
  }, [autoRefresh, refreshCases]);

  useEffect(() => {
    if (!allowCreate) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const rows = await listLawyers();
        if (cancelled) {
          return;
        }
        setLawyers(rows);
        setSelectedLawyerIds((prev) => {
          if (prev.length > 0) {
            return prev;
          }
          const defaultLawyer = rows.find((item) => item.full_name.toLowerCase() === "mr lawyer");
          return defaultLawyer ? [defaultLawyer.user_id] : [];
        });
      } catch {
        if (!cancelled) {
          setLawyers([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [allowCreate]);

  function toggleLawyer(userId: string) {
    if (primaryLawyerId && userId === primaryLawyerId && selectedLawyerIds.includes(userId)) {
      return;
    }
    setSelectedLawyerIds((prev) =>
      prev.includes(userId) ? prev.filter((item) => item !== userId) : [...prev, userId],
    );
  }

  function addLawyer(userId: string) {
    if (selectedLawyerIds.includes(userId)) {
      return;
    }
    setSelectedLawyerIds((prev) => [...prev, userId]);
    setLawyerSearch("");
  }

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
        assigned_lawyers: selectedLawyerIds,
      });
      setName("");
      setClientName("");
      setLawyerSearch("");
      setSelectedLawyerIds((prev) => {
        if (prev.length === 0) {
          const defaultLawyer = lawyers.find((item) => item.full_name.toLowerCase() === "mr lawyer");
          return defaultLawyer ? [defaultLawyer.user_id] : [];
        }
        return prev;
      });
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
      {!loading && cases.length === 0 && (
        <p className="muted">No cases found yet. Seed demo data or create your first case.</p>
      )}
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
                {showAssignedSummary && item.assigned_lawyers.length > 0 ? (
                  <small className="muted">
                    Assigned: {item.assigned_lawyers.map((lawyerId) => lawyerNameById.get(lawyerId) ?? lawyerId).join(", ")}
                  </small>
                ) : null}
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
            <div className="stack-sm">
              <p className="muted">Assign lawyers</p>
              <div className="assignee-picker">
                <div className="assignee-chip-row">
                  {selectedLawyerIds.map((lawyerId) => {
                    const lawyer = lawyerById.get(lawyerId);
                    const label = lawyer?.full_name ?? lawyerId;
                    const locked = lawyerId === primaryLawyerId;
                    return (
                      <span key={lawyerId} className="assignee-chip">
                        {label}
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => toggleLawyer(lawyerId)}
                          disabled={locked}
                          aria-label={`Remove ${label}`}
                        >
                          x
                        </button>
                      </span>
                    );
                  })}
                </div>

                <input
                  value={lawyerSearch}
                  onFocus={() => setPickerOpen(true)}
                  onBlur={() => {
                    window.setTimeout(() => setPickerOpen(false), 100);
                  }}
                  onChange={(event) => {
                    setLawyerSearch(event.target.value);
                    setPickerOpen(true);
                  }}
                  placeholder="Search lawyers by name or email"
                />

                {pickerOpen && (
                  <ul className="assignee-results list-reset">
                    {filteredLawyers.length === 0 ? (
                      <li className="muted">No matching lawyers</li>
                    ) : (
                      filteredLawyers.map((lawyer) => (
                        <li key={lawyer.user_id}>
                          <button
                            type="button"
                            className="assignee-result-btn"
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => addLawyer(lawyer.user_id)}
                          >
                            <span>
                              <strong>{lawyer.full_name}</strong>
                              <small className="muted">{lawyer.email}</small>
                            </span>
                          </button>
                        </li>
                      ))
                    )}
                  </ul>
                )}
                {pickerOpen && filteredLawyers.length > 0 && (
                  <small className="muted">Showing {filteredLawyers.length} matching lawyers</small>
                )}
              </div>
              <small className="muted">Mr Lawyer stays assigned in demo mode.</small>
            </div>
            <button type="button" onClick={() => void submitCreate()} disabled={creating}>
              {creating ? "Creating..." : "Create case"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
