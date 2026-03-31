"use client";

import { useEffect, useState } from "react";
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
  variant = "default",
}: {
  caseId: string | null;
  allowUpload: boolean;
  autoRefresh?: boolean;
  variant?: "default" | "compact" | "ingestion";
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

  if (variant === "ingestion") {
    return (
      <section className="admin-ingestion-shell">
        <div className="admin-ingestion-head">
          <h3>Ingestion Oversight</h3>
          <span className="material-symbols-outlined">cloud_sync</span>
        </div>

        {allowUpload && caseId && (
          <label className="admin-upload-drop" aria-label="Vault deposit">
            <input
              type="file"
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                setPendingFile(file);
              }}
            />
            <div className="admin-upload-icon">
              <span className="material-symbols-outlined">upload_file</span>
            </div>
            <div>
              <p>Vault Deposit</p>
              <small>Automatic OCR and vector indexing</small>
            </div>
          </label>
        )}

        {allowUpload && caseId && pendingFile && (
          <div className="admin-upload-inline">
            <span className="muted">{pendingFile.name}</span>
            <button type="button" onClick={() => void submitUpload()} disabled={uploading}>
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </div>
        )}

        {!caseId && <p className="muted">Select a case to view jobs.</p>}
        {loading && <p className="muted">Loading jobs...</p>}
        {error && <p className="error-text">{error}</p>}
        {message && <p className="ok-text">{message}</p>}

        <div className="admin-jobs-caption">Live Jobs</div>
        <ul className="list-reset admin-jobs-list">
          {docs.slice(0, 4).map((item) => {
            const normalized = item.status.toLowerCase();
            const active = normalized.includes("processing") || normalized.includes("index") || normalized.includes("queued");
            const done = normalized.includes("complete") || normalized.includes("done") || normalized.includes("ready");
            return (
              <li key={item.file_id} className="admin-job-row">
                <div className="admin-job-icon">
                  <span className="material-symbols-outlined">description</span>
                </div>
                <div className="admin-job-meta">
                  <p>{item.name}</p>
                  <small className={done ? "ok-text" : active ? "admin-job-active" : "muted"}>{item.status}</small>
                </div>
                {active && !done ? <span className="admin-job-spinner" aria-hidden="true" /> : null}
                {done ? <span className="material-symbols-outlined admin-job-done">check_circle</span> : null}
              </li>
            );
          })}
          {!loading && caseId && docs.length === 0 && <li className="muted">No documents uploaded yet.</li>}
        </ul>
      </section>
    );
  }

  return (
    <section className={variant === "compact" ? "card compact-card" : "card"}>
      <div className="section-head">
        <h2>Documents</h2>
        <span className="pill subtle">{docs.length} files</span>
      </div>
      {!caseId && <p className="muted">Select a case to view documents.</p>}
      {loading && <p className="muted">Loading documents...</p>}
      {error && <p className="error-text">{error}</p>}
      {message && <p className="ok-text">{message}</p>}
      {!loading && caseId && docs.length === 0 && <p className="muted">No documents uploaded for this case.</p>}

      <ul className="list-reset stack-sm">
        {docs.map((item) => (
          <li key={item.file_id} className="list-row">
            <span>
              <strong>{item.name}</strong>
              {item.is_latest ? <small className="muted">Latest version</small> : null}
            </span>
            <span className="status-tag">
              v{item.version} {item.status}
            </span>
          </li>
        ))}
      </ul>

      {allowUpload && caseId && (
        <div className="row upload-row upload-card">
          <input
            type="file"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setPendingFile(file);
            }}
          />
          <span className="muted">{pendingFile ? pendingFile.name : "No file selected"}</span>
          <button type="button" onClick={() => void submitUpload()} disabled={!pendingFile || uploading}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      )}
    </section>
  );
}
