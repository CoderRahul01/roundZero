import { getAccessToken, refreshSession } from "./auth";

export type InterviewMode = "buddy" | "strict";
export type Difficulty = "easy" | "medium" | "hard";

// In dev (Vite devserver), use '' so proxy routes /profile and /session to localhost:8080.
// In production (Vercel), VITE_BACKEND_URL points to Cloud Run.
const API_BASE: string = import.meta.env.DEV
  ? ''  // relative — Vite proxy routes to localhost:8080
  : (() => {
      const url = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL;
      if (!url && !import.meta.env.DEV) {
        console.error("❌ MISSING VITE_BACKEND_URL! Falling back to localhost:8080 which will likely fail in production.");
      }
      return url || 'http://localhost:8080';
    })();

// WebSocket base — http → ws, https → wss (auto handles dev & prod)
export const WS_BASE: string = import.meta.env.DEV
  ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  : API_BASE.replace(/^http/, 'ws');


export interface StartSessionPayload {
  user_id?: string;
  name?: string;
  role: string;
  topics: string[];
  difficulty: Difficulty;
  mode: InterviewMode;
}

export interface StartSessionResponse {
  session_id: string;
  user_id: string;
  first_question: string;
  question_index: number;
  total_questions: number;
  memory_context: string;
  call_id: string;
  token: string | null;
  backend_token: string | null;
  stream_api_key: string | null;
}

export interface SubmitAnswerPayload {
  transcript: string;
  confidence?: number;
  emotion?: string;
}

export interface SubmitAnswerResponse {
  action: "CONTINUE" | "NEXT" | "HINT" | "ENCOURAGE";
  message: string;
  question: string | null;
  question_index: number;
  total_questions: number;
  is_finished: boolean;
  stats?: {
    fillers: number;
    confidence: number;
    emotion: string;
  };
}

export interface SessionReport {
  overallScore: number;
  confidenceAvg: number;
  totalFillers: number;
  questionsAnswered: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  breakdown: Array<{
    q: string;
    score: number;
    feedback: string;
    fillers: number;
  }>;
}

export interface UserProfileSchema {
  user_id: string;
  name: string | null;
  bio: string | null;
  resume_text: string | null;
  strengths: string[] | null;
  weaknesses: string[] | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Missing auth token. Sign in again to continue.");
  }
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) || {}),
  };
  headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, {
    headers,
    ...init,
  });

  if (response.status === 401 && !(init?.headers as Record<string, string> | undefined)?.["X-Retry"]) {
    console.warn(`🔐 401 Unauthorized for ${path}. Refreshing and retrying...`);
    await refreshSession();
    const retryInit = {
      ...init,
      headers: {
        ...headers,
        "X-Retry": "true"
      }
    };
    return request(path, retryInit);
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export function prepareSession(payload: StartSessionPayload) {
  return request<{ session_id: string; total_questions: number; questions: any[] }>("/session/prepare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startSession(payload: StartSessionPayload, sessionId?: string) {
  const url = sessionId ? `/session/start?session_id=${sessionId}` : "/session/start";
  return request<StartSessionResponse>(url, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitAnswer(sessionId: string, payload: SubmitAnswerPayload) {
  return request<SubmitAnswerResponse>(`/session/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function endSession(sessionId: string) {
  return request<{ session_id: string; status: string }>(`/session/${sessionId}/end`, {
    method: "POST",
  });
}

export function fetchReport(sessionId: string) {
  return request<SessionReport>(`/session/${sessionId}/report`);
}

export async function getEventSource(sessionId: string): Promise<EventSource> {
  const token = await getAccessToken();
  return new EventSource(`${API_BASE}/session/${sessionId}/events?token=${token}`);
}

export function fetchProfile() {
  return request<UserProfileSchema>("/profile/");
}

export function updateProfile(payload: Partial<UserProfileSchema>) {
  return request<UserProfileSchema>("/profile/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
