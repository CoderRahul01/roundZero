import { createAuthClient } from "@neondatabase/auth";

export const getNeonAuthUrl = () => {
  return import.meta.env.VITE_NEON_AUTH_URL || "";
};

export const getNeonAuthClient = async () => {
  const url = getNeonAuthUrl();
  if (!url) {
    return null;
  }
  return createAuthClient(url);
};
