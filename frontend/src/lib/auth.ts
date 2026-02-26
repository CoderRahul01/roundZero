const NEON_AUTH_URL = (process.env.REACT_APP_NEON_AUTH_URL || "").trim();

export interface NeonSdkError {
  message?: string;
}

export interface NeonSdkUser {
  id?: string;
  email?: string | null;
  name?: string | null;
  [key: string]: unknown;
}

export interface NeonSdkSession {
  token?: string;
  expiresAt?: string | Date;
  expires_at?: string | Date;
  user?: NeonSdkUser;
  [key: string]: unknown;
}

export interface NeonSdkSessionResponse {
  data?: {
    user?: NeonSdkUser | null;
    session?: NeonSdkSession | null;
  } | null;
  error?: NeonSdkError | null;
}

export interface NeonSdkActionResponse {
  data?: unknown;
  error?: NeonSdkError | null;
}

export interface NeonAuthClient {
  getSession: () => Promise<NeonSdkSessionResponse>;
  signIn: {
    email: (payload: { email: string; password: string }) => Promise<NeonSdkActionResponse>;
  };
  signUp: {
    email: (payload: { email: string; password: string; name: string }) => Promise<NeonSdkActionResponse>;
  };
  signOut: () => Promise<NeonSdkActionResponse>;
}

let neonAuthClientPromise: Promise<NeonAuthClient | null> | null = null;

export function getNeonAuthUrl(): string {
  return NEON_AUTH_URL;
}

export async function getNeonAuthClient(): Promise<NeonAuthClient | null> {
  if (!NEON_AUTH_URL) {
    return null;
  }

  if (!neonAuthClientPromise) {
    neonAuthClientPromise = (async () => {
      try {
        const sdk = await import("@neondatabase/neon-js/auth");
        return sdk.createAuthClient(NEON_AUTH_URL) as unknown as NeonAuthClient;
      } catch (error) {
        console.error("Failed to initialize Neon Auth client:", error);
        return null;
      }
    })();
  }

  return neonAuthClientPromise;
}
