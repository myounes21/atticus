"use client";

import { useEffect, useState } from "react";
import ChatPanel from "@/components/chat/ChatPanel";
import { listCases, type CaseItem } from "@/lib/api";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function LawyerPage() {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [showCasesPanel, setShowCasesPanel] = useState(false);
  const { loading, user, logout } = useAuthGuard({ allowedRoles: ["lawyer"] });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await listCases();
        if (!cancelled) {
          setCases(rows);
          setSelectedCaseId((prev) => prev ?? rows[0]?.case_id ?? null);
        }
      } catch {
        // Ignore; we fall back to empty selection.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <section className="rounded-xl border border-outline-variant/30 bg-white px-6 py-4 shadow-sm">
          <p className="text-sm text-on-surface-variant">Loading lawyer workspace...</p>
        </section>
      </main>
    );
  }

  return (
    <main className="flex h-screen overflow-hidden bg-surface font-body text-on-surface antialiased">
      <aside className="z-50 flex w-20 flex-col items-center border-r border-outline-variant/50 bg-white py-8">
        <div className="mb-10">
          <div className="signature-gradient flex h-10 w-10 items-center justify-center rounded-xl text-white shadow-lg">
            <span className="material-symbols-outlined text-2xl" style={{ fontVariationSettings: '"FILL" 1' }}>
              gavel
            </span>
          </div>
        </div>

        <nav className="flex flex-1 flex-col space-y-8" aria-label="Primary">
          <button
            type="button"
            className={
              showCasesPanel
                ? "group relative flex items-center justify-center rounded-xl bg-primary/5 p-3 text-primary transition-colors"
                : "group relative flex items-center justify-center p-3 text-outline transition-colors hover:text-primary"
            }
            aria-label="Cases"
            onClick={() => setShowCasesPanel((prev) => !prev)}
          >
            <span className="material-symbols-outlined text-2xl">folder_open</span>
            <span className="absolute left-16 whitespace-nowrap rounded bg-on-surface px-2 py-1 text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100">
              Cases
            </span>
          </button>
          <button type="button" className="group relative flex items-center justify-center rounded-xl bg-primary/5 p-3 text-primary transition-colors" aria-current="page" aria-label="Assistant">
            <span className="material-symbols-outlined text-2xl" style={{ fontVariationSettings: '"FILL" 1' }}>
              chat_bubble
            </span>
            <span className="absolute left-16 whitespace-nowrap rounded bg-on-surface px-2 py-1 text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100">
              Assistant
            </span>
          </button>
          <button type="button" className="group relative flex items-center justify-center p-3 text-outline transition-colors hover:text-primary" aria-label="Documents">
            <span className="material-symbols-outlined text-2xl">description</span>
            <span className="absolute left-16 whitespace-nowrap rounded bg-on-surface px-2 py-1 text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100">
              Documents
            </span>
          </button>
        </nav>

        <div className="mt-auto flex flex-col space-y-6">
          <button type="button" className="group relative flex items-center justify-center p-3 text-outline transition-colors hover:text-primary" aria-label="Settings">
            <span className="material-symbols-outlined text-2xl">settings</span>
          </button>
          <button
            type="button"
            className="flex h-10 w-10 items-center justify-center rounded-full border border-outline-variant/40 text-outline transition-all duration-300 hover:border-primary/20 hover:bg-primary/5 hover:text-primary"
            onClick={logout}
            title={user?.email ? `Logout (${user.email})` : "Logout"}
          >
            <span className="material-symbols-outlined text-xl">person</span>
          </button>
        </div>
      </aside>

      <aside
        className={
          showCasesPanel
            ? "w-80 border-r border-outline-variant/40 bg-white/90 p-4 transition-all duration-300"
            : "w-0 overflow-hidden p-0 transition-all duration-300"
        }
      >
        {showCasesPanel && (
          <div className="flex h-full min-h-0 flex-col">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-headline text-sm font-bold tracking-wide text-on-surface">Cases</h2>
              <span className="rounded-full bg-surface-container px-2.5 py-1 text-[10px] font-bold text-outline">
                {cases.length}
              </span>
            </div>

            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
              {cases.length === 0 ? (
                <p className="text-xs text-on-surface-variant">No cases available.</p>
              ) : (
                cases.map((item) => (
                  <button
                    key={item.case_id}
                    type="button"
                    onClick={() => {
                      setSelectedCaseId(item.case_id);
                      setShowCasesPanel(false);
                    }}
                    className={
                      item.case_id === selectedCaseId
                        ? "w-full rounded-xl border border-primary/30 bg-primary/5 px-3 py-2 text-left"
                        : "w-full rounded-xl border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 text-left hover:border-primary/30"
                    }
                  >
                    <p className="truncate text-sm font-semibold text-on-surface">{item.name}</p>
                    <p className="mt-1 text-[11px] text-on-surface-variant">#{item.case_id.slice(0, 8).toUpperCase()}</p>
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </aside>

      <section className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex h-20 items-center justify-between border-b border-outline-variant/30 bg-surface/80 px-10 backdrop-blur-md">
          <div className="flex items-center gap-8">
            <div>
              <h1 className="text-sm font-semibold text-on-surface-variant">ATTICUS</h1>
            </div>
            <div className="h-6 w-px bg-outline-variant/50" />
            <div className="flex items-center gap-3 rounded-full border border-outline-variant/40 bg-surface-container-low/50 px-3 py-1.5">
              <span className="h-2 w-2 animate-pulse rounded-full bg-primary-alt" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-primary-alt">Demo Mode</span>
            </div>
            <div className="flex items-center gap-3 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-primary">Finch Demo Matter</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="group relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg text-outline">search</span>
              <input
                className="w-48 rounded-full border border-outline-variant/40 bg-surface-container-low/30 py-2 pl-10 pr-4 text-sm shadow-sm transition-all hover:border-outline-variant/80 focus:w-64 focus:border-primary/40 focus:bg-white focus:ring-1 focus:ring-primary/20"
                placeholder="Search insights..."
              />
            </label>
            <button
              type="button"
              className="flex h-10 w-10 items-center justify-center rounded-full border border-outline-variant/40 text-outline transition-all duration-300 hover:border-primary/20 hover:bg-primary/5 hover:text-primary"
              aria-label="Notifications"
            >
              <span className="material-symbols-outlined">notifications</span>
            </button>
          </div>
        </header>

        <main className="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface">
          <ChatPanel caseId={selectedCaseId} variant="lawyer-atelier" />
        </main>
      </section>
    </main>
  );
}
