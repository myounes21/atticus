"use client";

import { useEffect, useMemo, useState } from "react";
import { listDocuments, uploadDocument } from "@/lib/api";

type DocumentItem = {
  file_id: string;
  name: string;
  version: number;
  status: string;
  is_latest: boolean;
};

export default function DocumentsPanel({
  caseId,
  allowUpload,
  autoRefresh = false,
}: {
  caseId: string | null;
  allowUpload: boolean;
  autoRefresh?: boolean;
}) {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function refreshDocuments(activeCaseId: string) {
    setLoading(true);
    setError("");
    try {
      const rows = await listDocuments(activeCaseId);
      setDocs(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!caseId) {
      setDocs([]);
      setPendingFile(null);
      setMessage("");
      setError("");
      return;
    }
    void refreshDocuments(caseId);
  }, [caseId]);

  useEffect(() => {
    if (!autoRefresh || !caseId) {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshDocuments(caseId);
    }, 4500);

    return () => {
      window.clearInterval(timer);
    };
  }, [autoRefresh, caseId]);

  async function submitUpload() {
    if (!caseId || !pendingFile) return;
    setError("");
    setMessage("");
    setUploading(true);
    try {
      await uploadDocument(caseId, pendingFile);
      setMessage(`Uploaded ${pendingFile.name}`);
      setPendingFile(null);
      await refreshDocuments(caseId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const jobs = useMemo(() => docs.slice(0, 4), [docs]);

  return (
    <section className="space-y-6 rounded-2xl border border-outline-variant/10 bg-surface-container-low/50 p-8">
      <div className="flex items-center justify-between">
        <h3 className="font-headline text-lg font-extrabold text-on-surface">Ingestion Oversight</h3>
        <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: '"FILL" 1' }}>
          cloud_sync
        </span>
      </div>

      {allowUpload && caseId && (
        <label
          className="group flex cursor-pointer flex-col items-center justify-center space-y-4 rounded-2xl border-2 border-dashed border-outline-variant/40 bg-surface-container-lowest p-10 text-center transition-all hover:border-primary/50 hover:bg-surface-container-low"
          aria-label="Vault deposit"
        >
          <input
            type="file"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setPendingFile(file);
            }}
          />
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform group-hover:scale-110">
            <span className="material-symbols-outlined text-3xl">upload_file</span>
          </div>
          <div>
            <p className="text-sm font-bold text-on-surface">Vault Deposit</p>
            <p className="text-[11px] font-medium text-outline">Automatic OCR &amp; vector indexing</p>
          </div>
        </label>
      )}

      {allowUpload && caseId && pendingFile && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-outline-variant/20 bg-surface-container-lowest px-4 py-3">
          <span className="truncate text-sm text-on-surface-variant">{pendingFile.name}</span>
          <button
            type="button"
            onClick={() => void submitUpload()}
            disabled={uploading}
            className="rounded-xl bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      )}

      {!caseId && <p className="text-sm text-on-surface-variant">Select a case to view jobs.</p>}
      {loading && <p className="text-sm text-on-surface-variant">Loading jobs...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {message && <p className="text-sm text-primary-alt">{message}</p>}

      <div className="text-[10px] font-black uppercase tracking-[0.15em] text-outline">Live Jobs</div>
      <ul className="space-y-3">
        {jobs.map((item) => {
          const normalized = item.status.toLowerCase();
          const active =
            normalized.includes("processing") || normalized.includes("index") || normalized.includes("queued");
          const done = normalized.includes("complete") || normalized.includes("done") || normalized.includes("ready");
          const ext = item.name.split(".").pop()?.toLowerCase();
          const iconMap: Record<string, string> = {
            pdf: "picture_as_pdf",
            doc: "description",
            docx: "description",
            txt: "article",
            eml: "mail",
            png: "image",
            jpg: "image",
            jpeg: "image",
          };
          const icon = iconMap[ext ?? ""] ?? "description";

          return (
            <li
              key={item.file_id}
              className="flex items-center justify-between gap-3 rounded-xl border border-outline-variant/5 bg-surface-container-lowest p-4 shadow-sm"
            >
              <div className="flex min-w-0 items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/5 text-primary">
                  <span className="material-symbols-outlined text-xl">{icon}</span>
                </div>
                <div className="min-w-0">
                  <p className="truncate text-xs font-bold text-on-surface">{item.name}</p>
                  <p
                    className={
                      done
                        ? "text-[10px] font-bold uppercase tracking-wider text-primary-alt"
                        : active
                          ? "text-[10px] font-bold uppercase tracking-wider text-primary"
                          : "text-[10px] font-bold uppercase tracking-wider text-outline"
                    }
                  >
                    {item.status}
                  </p>
                </div>
              </div>

              <div className="shrink-0">
                {active && !done ? (
                  <span className="block h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
                ) : null}
                {done ? (
                  <span className="material-symbols-outlined text-xl text-primary" style={{ fontVariationSettings: '"FILL" 1' }}>
                    check_circle
                  </span>
                ) : null}
              </div>
            </li>
          );
        })}

        {!loading && caseId && docs.length === 0 && <li className="text-sm text-on-surface-variant">No documents uploaded yet.</li>}
      </ul>
    </section>
  );
}
