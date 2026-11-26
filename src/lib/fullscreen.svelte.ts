import { getCurrentWindow } from "@tauri-apps/api/window";

export type FullscreenTarget = "viewer" | "code";

/** One panel at a time can fill the screen; the window goes full screen with it. */
class Fullscreen {
  target = $state<FullscreenTarget | null>(null);

  async toggle(t: FullscreenTarget) {
    const next = this.target === t ? null : t;
    this.target = next;
    try {
      await getCurrentWindow().setFullscreen(next !== null);
    } catch {
      /* the panel still fills the window */
    }
  }

  exit() {
    if (this.target) this.toggle(this.target);
  }
}

export const fullscreen = new Fullscreen();
