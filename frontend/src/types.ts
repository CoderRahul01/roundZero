import { StartSessionResponse } from "./api";

export interface SessionConfig {
  name: string;
  role: string;
  topics: string[];
  difficulty: "easy" | "medium" | "hard";
  mode: "buddy" | "strict";
  videoSource?: "camera" | "screen" | "none";
  externalStream?: MediaStream | null;
}

export type LiveSessionConfig = SessionConfig & StartSessionResponse;

export interface QuestionResult {
  q: string;
  score: number;
  fillers: number;
  feedback: string;
  whatWasRight?: string;
  whatWasWrong?: string;
  correctnessPercent?: number;
  topic?: string;
}

export interface SessionReport {
  overallScore: number;
  confidenceAvg: number;
  totalFillers: number;
  questionsAnswered: number;
  summary: string;
  breakdown: QuestionResult[];
  strengths: string[];
  weaknesses: string[];
  scoreTrend?: "improving" | "declining" | "stable";
  scoreTrendNote?: string;
  topicsCovered?: string[];
  scoresByQuestion?: number[];
}
