/**
 * ScreenShareService.ts
 * Isolated service for managing screen capture streams.
 */

export interface ScreenShareOptions {
  width?: number;
  height?: number;
  frameRate?: number;
}

class ScreenShareService {
  private currentStream: MediaStream | null = null;

  async startCapture(options: ScreenShareOptions = {}): Promise<MediaStream> {
    const { width = 1280, height = 720, frameRate = 2 } = options;

    if (this.currentStream) {
      this.stopCapture();
    }

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          width: { ideal: width },
          height: { ideal: height },
          frameRate: { ideal: frameRate },
        },
        audio: false,
      });

      this.currentStream = stream;

      // Handle user stopping the share via browser UI
      stream.getVideoTracks()[0].onended = () => {
        this.currentStream = null;
      };

      return stream;
    } catch (err) {
      console.error("Screen capture failed:", err);
      throw err;
    }
  }

  stopCapture() {
    if (this.currentStream) {
      this.currentStream.getTracks().forEach((track) => track.stop());
      this.currentStream = null;
    }
  }

  getStream(): MediaStream | null {
    return this.currentStream;
  }

  isActive(): boolean {
    return !!this.currentStream && this.currentStream.active;
  }
}

export const screenShareService = new ScreenShareService();
