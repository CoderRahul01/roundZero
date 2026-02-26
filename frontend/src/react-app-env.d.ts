/// <reference types="react-scripts" />

// Optional Neon Auth SDK module. This silences TS when the package isn't installed.
declare module "@neondatabase/neon-js/auth" {
  export function createAuthClient(url: string): unknown;
}
