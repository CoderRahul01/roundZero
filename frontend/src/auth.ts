import { getNeonAuthClient, getNeonAuthUrl } from "./lib/auth";

const ALLOW_LEGACY_DEV_AUTH = import.meta.env.VITE_ALLOW_LEGACY_DEV_AUTH === "true";

const LEGACY_USER_STORAGE_KEY = "roundzero_legacy_user_id";
const LEGACY_JWT_SECRET = import.meta.env.VITE_JWT_SECRET || "roundzero-super-secret-key";

type JsonObject = Record<string, unknown>;

export interface AuthUser {
  id: string;
  email: string | null;
  name: string | null;
}

export interface AuthActionResult {
  ok: boolean;
  user: AuthUser | null;
  error?: string;
}

interface SessionState {
  user: AuthUser | null;
  token: string | null;
  expiresAt: string | null;
}

let cachedSession: SessionState | null = null;
let cachedLegacyToken: string | null = null;
let legacyUserId: string | null = null;

function generateUserId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `legacy_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

function asObject(value: unknown): JsonObject | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as JsonObject;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

function asIsoDate(value: unknown): string | null {
  if (value instanceof Date) {
    return value.toISOString();
  }

  const asText = asString(value);
  if (!asText) {
    return null;
  }

  const parsed = new Date(asText);
  if (Number.isNaN(parsed.getTime())) {
    return asText;
  }

  return parsed.toISOString();
}

function parseSdkError(result: unknown, fallback: string): string {
  const root = asObject(result);
  if (!root) return fallback;

  const nested = asObject(root.error);
  return asString(nested?.message) ?? asString(root.message) ?? fallback;
}

function normalizeNeonSession(resultData: unknown): SessionState | null {
  const root = asObject(resultData);
  if (!root) {
    return null;
  }

  const sessionNode = asObject(root.session);
  const userNode = asObject(root.user) ?? asObject(sessionNode?.user);

  if (!sessionNode || !userNode) {
    return null;
  }

  const userId = asString(userNode.id) ?? asString(userNode.userId) ?? asString(userNode.sub);
  if (!userId) {
    return null;
  }

  return {
    user: {
      id: userId,
      email: asString(userNode.email),
      name: asString(userNode.name),
    },
    token: asString(sessionNode.token),
    expiresAt: asIsoDate(sessionNode.expiresAt) ?? asIsoDate(sessionNode.expires_at),
  };
}

async function fetchCurrentSession(): Promise<SessionState | null> {
  const client = await getNeonAuthClient();
  if (!client) {
    cachedSession = null;
    return null;
  }

  // Check if current cached session is expired
  if (cachedSession?.expiresAt) {
    const expires = new Date(cachedSession.expiresAt).getTime();
    const now = Date.now() + 30000; // 30s buffer
    if (now > expires) {
      console.log("🔐 Proactively clearing expired session cache");
      cachedSession = null;
    }
  }

  try {
    const result: any = await client.getSession();
    if (result?.error) {
      cachedSession = null;
      return null;
    }

    const sessionData = result?.data !== undefined ? result.data : result;
    const session = normalizeNeonSession(sessionData);
    cachedSession = session;
    return session;
  } catch (error) {
    console.error("Failed to fetch Neon Auth session:", error);
    cachedSession = null;
    return null;
  }
}

function getLegacyUserId(): string | null {
  if (legacyUserId) return legacyUserId;
  if (typeof window === "undefined") return null;

  legacyUserId = window.localStorage.getItem(LEGACY_USER_STORAGE_KEY);
  if (!legacyUserId) {
    legacyUserId = generateUserId();
    window.localStorage.setItem(LEGACY_USER_STORAGE_KEY, legacyUserId);
  }
  return legacyUserId;
}

function getLegacyUser(): AuthUser | null {
  const userId = getLegacyUserId();
  if (!userId) return null;

  return {
    id: userId,
    email: `${userId}@legacy.local`,
    name: "Legacy Dev User",
  };
}

async function getLegacyToken(): Promise<string | null> {
  if (cachedLegacyToken) return cachedLegacyToken;
  const user = getLegacyUser();
  if (!user) return null;

  try {
    if (typeof TextEncoder === "undefined") {
      return null;
    }

    const secretBytes = new TextEncoder().encode(LEGACY_JWT_SECRET);
    const jose = await import("jose");
    cachedLegacyToken = await new jose.SignJWT({
      sub: user.id,
      email: user.email,
      aud: "authenticated",
      role: "authenticated",
    })
      .setProtectedHeader({ alg: "HS256" })
      .setIssuedAt()
      .setExpirationTime("24h")
      .sign(secretBytes);

    return cachedLegacyToken;
  } catch (error) {
    console.error("Failed to generate legacy dev token:", error);
    return null;
  }
}

function clearLegacyAuth(): void {
  cachedLegacyToken = null;
  legacyUserId = null;

  if (typeof window !== "undefined") {
    window.localStorage.removeItem(LEGACY_USER_STORAGE_KEY);
  }
}

function fallbackAuthResult(): AuthActionResult {
  if (!isLegacyDevAuthEnabled()) {
    return { ok: false, user: null, error: "Neon Auth is not configured." };
  }

  const user = getLegacyUser();
  return {
    ok: Boolean(user),
    user,
    error: user ? undefined : "Unable to create local development auth user.",
  };
}

function displayNameFromEmail(email: string): string {
  const prefix = email.split("@")[0]?.trim();
  return prefix && prefix.length > 0 ? prefix : "User";
}

export function isNeonAuthConfigured(): boolean {
  return Boolean(getNeonAuthUrl());
}

export function isLegacyDevAuthEnabled(): boolean {
  return ALLOW_LEGACY_DEV_AUTH;
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  if (isNeonAuthConfigured()) {
    const session = await fetchCurrentSession();
    return session?.user ?? null;
  }

  if (isLegacyDevAuthEnabled()) {
    return getLegacyUser();
  }

  return null;
}

export async function getAccessToken(): Promise<string | null> {
  if (isNeonAuthConfigured()) {
    const session = await fetchCurrentSession();
    return session?.token ?? null;
  }

  if (isLegacyDevAuthEnabled()) {
    return getLegacyToken();
  }

  return null;
}

export async function refreshSession(): Promise<string | null> {
  cachedSession = null;
  return getAccessToken();
}

export async function signInWithEmail(email: string, password: string): Promise<AuthActionResult> {
  if (!isNeonAuthConfigured()) {
    return fallbackAuthResult();
  }

  const client = await getNeonAuthClient();
  if (!client) {
    return { ok: false, user: null, error: "Failed to initialize Neon Auth client." };
  }

  try {
    const result: any = await client.signIn.email({ email, password });
    if (result?.error) {
      return {
        ok: false,
        user: null,
        error: parseSdkError(result, "Sign-in failed."),
      };
    }

    const session = await fetchCurrentSession();
    if (!session?.user) {
      return { ok: false, user: null, error: "Signed in, but no active session was returned." };
    }

    return { ok: true, user: session.user };
  } catch (error) {
    return {
      ok: false,
      user: null,
      error: error instanceof Error ? error.message : "Sign-in failed.",
    };
  }
}

export async function signUpWithEmail(email: string, password: string): Promise<AuthActionResult> {
  if (!isNeonAuthConfigured()) {
    return fallbackAuthResult();
  }

  const client = await getNeonAuthClient();
  if (!client) {
    return { ok: false, user: null, error: "Failed to initialize Neon Auth client." };
  }

  try {
    const result: any = await client.signUp.email({
      email,
      password,
      name: displayNameFromEmail(email),
    });

    if (result?.error) {
      return {
        ok: false,
        user: null,
        error: parseSdkError(result, "Sign-up failed."),
      };
    }

    const session = await fetchCurrentSession();
    if (!session?.user) {
      return {
        ok: false,
        user: null,
        error: "Account created. Complete verification if enabled, then sign in.",
      };
    }

    return { ok: true, user: session.user };
  } catch (error) {
    return {
      ok: false,
      user: null,
      error: error instanceof Error ? error.message : "Sign-up failed.",
    };
  }
}

export async function signOut(): Promise<void> {
  if (isNeonAuthConfigured()) {
    const client = await getNeonAuthClient();
    if (client) {
      try {
        await client.signOut();
      } catch (error) {
        console.error("Sign-out failed:", error);
      }
    }
    cachedSession = null;
  }

  clearLegacyAuth();
}
