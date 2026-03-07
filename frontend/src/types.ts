import { StartSessionResponse } from "./api";

export interface SessionConfig {
  name: string;
  role: string;
  topics: string[];
  difficulty: "easy" | "medium" | "hard";
  mode: "buddy" | "strict";
  videoSource?: "camera" | "screen" | "none";
}

export type LiveSessionConfig = SessionConfig & StartSessionResponse;

export interface QuestionResult {
  q: string;
  score: number;
  emotion: string;
  fillers: number;
  feedback: string;
}

export interface SessionReport {
  overallScore: number;
  confidenceAvg: number;
  duration: string;
  questionsAnswered: number;
  breakdown: QuestionResult[];
  strengths: string[];
  weaknesses: string[];
  emotionTimeline: number[];
}
