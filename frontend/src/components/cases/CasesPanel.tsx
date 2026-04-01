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

type CasesPanelProps = {
  allowCreate: boolean;
  autoRefresh?: boolean;
  onSelectCase: (caseId: string | null) => void;
};

export default function CasesPanel({ allowCreate, autoRefresh = false, onSelectCase }: CasesPanelProps) {
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
      const createdCase = await createCase({
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
      updateSelection(createdCase.case_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-outline-variant/10 bg-surface-container-lowest shadow-sm">
      <div className="flex items-center justify-between border-b border-outline-variant/10 bg-white px-8 py-6">
        <div className="flex items-center gap-4">
          <h3 className="font-headline text-lg font-extrabold text-on-surface">Active Cases Lifecycle</h3>
          <div className="rounded bg-surface-container px-2.5 py-1 text-[10px] font-bold text-outline">
            {cases.length} TOTAL
          </div>
        </div>
        <button
          type="button"
          className="flex items-center gap-2 text-xs font-bold text-primary transition-transform hover:translate-x-1"
          onClick={() => void refreshCases()}
        >
          VIEW ARCHIVE
          <span className="material-symbols-outlined text-base">arrow_forward</span>
        </button>
      </div>

      <div className="px-8 pb-4 pt-4">
        {loading && <p className="text-sm text-on-surface-variant">Loading cases...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {message && <p className="text-sm text-primary-alt">{message}</p>}
      </div>

      <ul className="divide-y divide-outline-variant/10">
        {cases.map((item) => {
          const lawyersForCase = item.assigned_lawyers.map((lawyerId) => lawyerNameById.get(lawyerId) ?? lawyerId);

          return (
            <li key={item.case_id}>
              <button
                type="button"
                className={
                  item.case_id === selectedCaseId
                    ? "grid w-full grid-cols-1 items-center gap-4 bg-surface-container-low px-8 py-6 text-left transition-colors lg:grid-cols-12 lg:gap-6"
                    : "grid w-full grid-cols-1 items-center gap-4 px-8 py-6 text-left transition-colors hover:bg-surface-container-low lg:grid-cols-12 lg:gap-6"
                }
                onClick={() => updateSelection(item.case_id)}
              >
                <div className="lg:col-span-4">
                  <p className="mb-1 text-[10px] font-black tracking-widest text-primary">#{item.case_id.slice(0, 8).toUpperCase()}</p>
                  <h4 className="font-headline text-base font-bold text-on-surface">{item.name}</h4>
                  <div className="mt-2 flex gap-1">
                    <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[9px] font-bold text-primary">CIVIL</span>
                    {item.status === "active" ? (
                      <span className="rounded bg-secondary/15 px-1.5 py-0.5 text-[9px] font-bold text-secondary">H-PRIORITY</span>
                    ) : null}
                  </div>
                </div>

                <div className="lg:col-span-3">
                  <p className="mb-3 text-[9px] font-black uppercase tracking-widest text-outline">Assigned Lawyers</p>
                  {lawyersForCase.length > 0 ? (
                    <div className="flex -space-x-2">
                      {lawyersForCase.slice(0, 3).map((lawyerName, index) => (
                        <span
                          key={`${item.case_id}-${lawyerName}`}
                          className={
                            index === 0
                              ? "flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-primary text-[10px] font-bold text-white shadow-sm"
                              : "flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-secondary text-[10px] font-bold text-white shadow-sm"
                          }
                          title={lawyerName}
                        >
                          {lawyerName
                            .split(" ")
                            .map((part) => part[0])
                            .join("")
                            .slice(0, 2)
                            .toUpperCase()}
                        </span>
                      ))}
                      {lawyersForCase.length > 3 ? (
                        <span className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-surface-container text-[10px] font-bold text-outline">
                          +{lawyersForCase.length - 3}
                        </span>
                      ) : null}
                    </div>
                  ) : (
                    <p className="text-xs text-on-surface-variant">None assigned</p>
                  )}
                </div>

                <div className="lg:col-span-3">
                  <p className="mb-3 text-[9px] font-black uppercase tracking-widest text-outline">Status Progression</p>
                  <div className="flex items-center gap-2.5">
                    <span className={item.status === "active" ? "relative h-3 w-3 rounded-full bg-primary" : "h-3 w-3 rounded-full bg-outline-variant"}>
                      {item.status === "active" ? <span className="absolute inset-0 animate-ping rounded-full bg-primary/30" /> : null}
                    </span>
                    <span className="text-xs font-bold text-on-surface">
                      {item.status === "active" ? "Discovery Ingestion" : "Awaiting Intake"}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end lg:col-span-2">
                  <span className="material-symbols-outlined rounded-xl p-2.5 text-outline shadow-sm transition-colors hover:bg-white hover:text-primary">
                    more_horiz
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {allowCreate && (
        <details className="m-4 rounded-xl bg-surface-container-low p-3">
          <summary className="cursor-pointer text-xs font-bold uppercase tracking-[0.08em] text-primary">Create case</summary>
          <div className="mt-3 grid gap-3">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Case name"
              className="rounded-lg border border-outline-variant/50 bg-white px-3 py-2 text-sm"
            />
            <input
              value={clientName}
              onChange={(event) => setClientName(event.target.value)}
              placeholder="Client name"
              className="rounded-lg border border-outline-variant/50 bg-white px-3 py-2 text-sm"
            />

            <div className="grid gap-2">
              <p className="text-xs font-semibold text-on-surface-variant">Assign lawyers</p>
              <div className="flex flex-wrap gap-2">
                {selectedLawyerIds.map((lawyerId) => {
                  const lawyer = lawyerById.get(lawyerId);
                  const label = lawyer?.full_name ?? lawyerId;
                  const locked = lawyerId === primaryLawyerId;
                  return (
                    <span key={lawyerId} className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-2 py-1 text-xs text-primary">
                      {label}
                      <button
                        type="button"
                        onClick={() => toggleLawyer(lawyerId)}
                        disabled={locked}
                        aria-label={`Remove ${label}`}
                        className="rounded-full bg-white px-1.5 py-0.5 text-[10px] text-primary disabled:opacity-40"
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
                className="rounded-lg border border-outline-variant/50 bg-white px-3 py-2 text-sm"
              />

              {pickerOpen && (
                <ul className="max-h-56 space-y-1 overflow-y-auto rounded-lg bg-surface-container p-2">
                  {filteredLawyers.length === 0 ? (
                    <li className="px-2 py-1 text-xs text-on-surface-variant">No matching lawyers</li>
                  ) : (
                    filteredLawyers.map((lawyer) => (
                      <li key={lawyer.user_id}>
                        <button
                          type="button"
                          className="flex w-full items-center justify-between rounded-md bg-white px-3 py-2 text-left"
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => addLawyer(lawyer.user_id)}
                        >
                          <span className="grid">
                            <strong className="text-sm text-on-surface">{lawyer.full_name}</strong>
                            <small className="text-xs text-on-surface-variant">{lawyer.email}</small>
                          </span>
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              )}
            </div>

            <button
              type="button"
              onClick={() => void submitCreate()}
              disabled={creating}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {creating ? "Creating..." : "Create case"}
            </button>
          </div>
        </details>
      )}
    </section>
  );
}
