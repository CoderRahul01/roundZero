import { getAccessToken } from "./auth";

export type InterviewMode = "buddy" | "strict";
export type Difficulty = "easy" | "medium" | "hard";

const API_BASE =
  process.env.REACT_APP_BACKEND_URL ||
  process.env.REACT_APP_API_BASE_URL ||
  "http://localhost:8000";

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
  overall_score: number;
  confidence_avg: number;
  duration_seconds: number;
  questions_answered: number;
  total_questions: number;
  strengths: string[];
  weaknesses: string[];
  emotion_timeline: number[];
  breakdown: Array<{
    question: string;
    score: number;
    emotion: string;
    fillers: number;
    feedback: string;
    user_answer: string;
  }>;
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

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export function startSession(payload: StartSessionPayload) {
  return request<StartSessionResponse>("/session/start", {
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
