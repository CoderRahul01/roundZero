/**
 * useScreenShare.ts
 * React hook for managing screen sharing via ScreenShareService.
 */

import { useState, useCallback, useEffect } from "react";
import { screenShareService, ScreenShareOptions } from "./ScreenShareService";

export function useScreenShare() {
  const [stream, setStream] = useState<MediaStream | null>(screenShareService.getStream());
  const [isActive, setIsActive] = useState(screenShareService.isActive());

  const start = useCallback(async (options?: ScreenShareOptions) => {
    try {
      const s = await screenShareService.startCapture(options);
      setStream(s);
      setIsActive(true);
      return s;
    } catch (err) {
      setIsActive(false);
      throw err;
    }
  }, []);

  const stop = useCallback(() => {
    screenShareService.stopCapture();
    setStream(null);
    setIsActive(false);
  }, []);

  // Sync state if stream ends via browser UI
  useEffect(() => {
    if (!stream) return;

    const track = stream.getVideoTracks()[0];
    const onEnded = () => {
      setIsActive(false);
      setStream(null);
    };

    track.addEventListener("ended", onEnded);
    return () => track.removeEventListener("ended", onEnded);
  }, [stream]);

  return { stream, isActive, start, stop };
}
