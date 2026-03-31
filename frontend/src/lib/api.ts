import { clearSession, getToken, type AuthUser, type LoginResult } from "./auth";

const API_BASE = "/api";

export type CaseItem = {
  case_id: string;
  name: string;
  client_name: string | null;
  status: "active" | "closed";
  assigned_lawyers: string[];
};

export type LawyerOption = {
  user_id: string;
  full_name: string;
  email: string;
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

type ChatStreamDone = {
  conversation_id?: string;
  message_id?: string;
};

type AskChatStreamHandlers = {
  onToken?: (token: string, fullText: string) => void;
  onCitation?: (citation: ChatCitation) => void;
  onDone?: (meta: ChatStreamDone) => void;
};

function formatApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") {
    return fallback;
  }

  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown; loc?: unknown } | undefined;
    const msg = typeof first?.msg === "string" ? first.msg : "Validation error";
    const loc = Array.isArray(first?.loc) ? first.loc.join(".") : "request";
    return `${msg} (${loc})`;
  }

  return fallback;
}

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
    throw new Error("Cannot reach API server. Check backend service.");
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
      const data = (await response.json()) as unknown;
      message = formatApiError(data, message);
    } catch {}
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

export async function listLawyers(): Promise<LawyerOption[]> {
  const data = await request<{ lawyers: LawyerOption[] }>("/cases/lawyers");
  return data.lawyers;
}

export async function createCase(payload: {
  name: string;
  client_name?: string;
  assigned_lawyers?: string[];
}): Promise<CaseItem> {
  return request<CaseItem>("/cases", {
    method: "POST",
    body: JSON.stringify({ ...payload, assigned_lawyers: payload.assigned_lawyers ?? [] }),
  });
}

export async function resetDemoData(adminToken: string): Promise<void> {
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${adminToken}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/cases/demo/reset`, {
      method: "POST",
      headers,
    });
  } catch {
    throw new Error("Cannot reach API server. Check backend service.");
  }

  if (!response.ok) {
    let message = `Demo reset failed (${response.status})`;
    try {
      const data = (await response.json()) as unknown;
      message = formatApiError(data, message);
    } catch {}
    throw new Error(message);
  }
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
    throw new Error("Cannot reach API server. Check backend service.");
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
      const data = (await response.json()) as unknown;
      message = formatApiError(data, message);
    } catch {}
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

export async function askChatStream(
  payload: {
    query: string;
    case_id: string;
    conversation_id?: string;
  },
  handlers: AskChatStreamHandlers = {},
): Promise<ChatResult> {
  const token = typeof window !== "undefined" ? getToken() : null;
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  headers.set("Accept", "text/event-stream");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      body: JSON.stringify(payload),
      headers,
    });
  } catch {
    throw new Error("Cannot reach API server. Check backend service.");
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data.detail) {
        message = data.detail;
      }
    } catch {}
    throw new Error(message);
  }

  if (!response.body) {
    throw new Error("Streaming is not available in this environment.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";
  let conversationId = payload.conversation_id ?? "";
  let messageId = "";
  const citations: ChatCitation[] = [];

  function handleEvent(rawEvent: string) {
    const dataLines = rawEvent
      .split("\n")
      .map((line) => line.trimEnd())
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim());

    if (dataLines.length === 0) {
      return;
    }

    let event: { type?: string; content?: unknown };
    try {
      event = JSON.parse(dataLines.join("\n")) as { type?: string; content?: unknown };
    } catch {
      return;
    }

    if (event.type === "token") {
      const tokenText = typeof event.content === "string" ? event.content : "";
      answer += tokenText;
      handlers.onToken?.(tokenText, answer);
      return;
    }

    if (event.type === "citation") {
      const citation = (event.content ?? {}) as ChatCitation;
      if (citation.chunk_id && !citations.some((item) => item.chunk_id === citation.chunk_id)) {
        citations.push(citation);
        handlers.onCitation?.(citation);
      }
      return;
    }

    if (event.type === "done") {
      const doneMeta = (event.content ?? {}) as ChatStreamDone;
      if (doneMeta.conversation_id) {
        conversationId = doneMeta.conversation_id;
      }
      if (doneMeta.message_id) {
        messageId = doneMeta.message_id;
      }
      handlers.onDone?.(doneMeta);
      return;
    }

    if (event.type === "error") {
      const errorMessage =
        typeof event.content === "string" ? event.content : "Streaming request failed";
      throw new Error(errorMessage);
    }
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    while (true) {
      const splitIndex = buffer.indexOf("\n\n");
      if (splitIndex < 0) {
        break;
      }

      const rawEvent = buffer.slice(0, splitIndex);
      buffer = buffer.slice(splitIndex + 2);

      handleEvent(rawEvent);
    }
  }

  const trailing = buffer.trim();
  if (trailing) {
    handleEvent(trailing);
  }

  if (!conversationId || !messageId) {
    throw new Error("Streaming ended unexpectedly. Please retry.");
  }

  return {
    answer,
    conversation_id: conversationId,
    message_id: messageId,
    chunks_used: citations,
  };
}
