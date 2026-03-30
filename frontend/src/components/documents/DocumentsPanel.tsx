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
}: {
  caseId: string | null;
  allowUpload: boolean;
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

  return (
    <section className="card">
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
