import { useEffect, useState } from "react";
import { getAccessToken, refreshSession, signOut } from "../auth";

export function useAuthGuard() {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const t = await getAccessToken();
      if (!mounted) return;
      setToken(t);
      setReady(true);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handle401 = async () => {
    const t = await refreshSession();
    setToken(t);
    if (!t) {
      await signOut();
    }
    return t;
  };

  return { ready, token, handle401, signOut };
}
