import { clearSession, getToken, type AuthUser, type LoginResult } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type CaseItem = {
  case_id: string;
  name: string;
  client_name: string | null;
  status: "active" | "closed";
  assigned_lawyers: string[];
};

export type DocumentItem = {
  file_id: string;
  case_id: string;
  name: string;
  version: number;
  is_latest: boolean;
  status: string;
};

export type ChatCitation = {
  chunk_id: string;
  document_name?: string;
  score?: number;
};

export type ChatResult = {
  answer: string;
  conversation_id: string;
  message_id: string;
  chunks_used: ChatCitation[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const redirectOnAuthError = init?.method !== "POST" || path !== "/auth/login";
  const token = typeof window !== "undefined" ? getToken() : null;
  const headers = new Headers(init?.headers ?? {});
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new Error("Cannot reach API server. Check backend and NEXT_PUBLIC_API_BASE_URL.");
  }
  if (!response.ok) {
    if (redirectOnAuthError && (response.status === 401 || response.status === 403)) {
      clearSession();
      if (typeof window !== "undefined") {
        window.location.href = "/";
      }
    }
    let message = `Request failed (${response.status})`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Ignore non-JSON error body.
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function register(email: string, password: string, role: string): Promise<AuthUser> {
  return request<AuthUser>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, role }),
  });
}

export async function login(email: string, password: string): Promise<LoginResult> {
  return request<LoginResult>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function me(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
}

export async function listCases(): Promise<CaseItem[]> {
  const data = await request<{ cases: CaseItem[] }>("/cases");
  return data.cases;
}

export async function createCase(payload: {
  name: string;
  client_name?: string;
  assigned_lawyers: string[];
}): Promise<CaseItem> {
  return request<CaseItem>("/cases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listDocuments(caseId: string): Promise<DocumentItem[]> {
  const data = await request<{ documents: DocumentItem[] }>(`/cases/${caseId}/documents`);
  return data.documents;
}

export async function uploadDocument(caseId: string, file: File): Promise<DocumentItem> {
  const token = typeof window !== "undefined" ? getToken() : null;
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const formData = new FormData();
  formData.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/cases/${caseId}/documents/upload`, {
      method: "POST",
      body: formData,
      headers,
    });
  } catch {
    throw new Error("Cannot reach API server. Check backend and NEXT_PUBLIC_API_BASE_URL.");
  }
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearSession();
      if (typeof window !== "undefined") {
        window.location.href = "/";
      }
    }
    let message = `Upload failed (${response.status})`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Ignore non-JSON error body.
    }
    throw new Error(message);
  }
  return (await response.json()) as DocumentItem;
}

export async function askChat(payload: {
  query: string;
  case_id: string;
  conversation_id?: string;
}): Promise<ChatResult> {
  return request<ChatResult>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
