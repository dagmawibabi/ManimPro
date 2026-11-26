export const DISPLAY_FPS = 30;

/** HH:MM:SS:FF timecode, the way editors show it. */
export function timecode(seconds: number, fps = DISPLAY_FPS): string {
  const s = Math.max(0, seconds);
  const totalFrames = Math.round(s * fps);
  const f = totalFrames % fps;
  const total = Math.floor(totalFrames / fps);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(Math.floor(total / 3600))}:${pad(Math.floor(total / 60) % 60)}:${pad(total % 60)}:${pad(f)}`;
}

/** Short form for rulers and clip labels: 0:05, 1:30. */
export function shortTime(seconds: number): string {
  const s = Math.max(0, seconds);
  const m = Math.floor(s / 60);
  const rest = s - m * 60;
  const sec = Number.isInteger(rest) ? String(rest) : rest.toFixed(1);
  return `${m}:${sec.padStart(rest < 10 ? (Number.isInteger(rest) ? 2 : 4) : 0, "0")}`;
}

export function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}
