/** Captions built from the voiceovers on the timeline. */
import { studio, sceneKey, type Caption } from "./studio.svelte";
import { voice } from "./voice.svelte";

const MAX_LINE = 42;
const uid = () => Math.random().toString(36).slice(2, 10);

/** Splits narration into caption-sized pieces (at most two lines of ~42 characters). */
export function splitText(text: string): string[] {
  const sentences = text.replace(/\s+/g, " ").trim().split(/(?<=[.!?…])\s+/);
  const out: string[] = [];
  for (const s of sentences) {
    if (s.length <= MAX_LINE * 2) {
      out.push(s);
      continue;
    }
    // Long sentence: break at commas or semicolons, then at words.
    let cur = "";
    for (const word of s.split(" ")) {
      const next = cur ? `${cur} ${word}` : word;
      const breakHere = cur.length > MAX_LINE && /[,;:—–]$/.test(cur);
      if (next.length > MAX_LINE * 2 || breakHere) {
        out.push(cur);
        cur = word;
      } else cur = next;
    }
    if (cur) out.push(cur);
  }
  return out.filter(Boolean).map(wrap);
}

/** Two balanced lines when a caption is longer than one line. */
function wrap(s: string) {
  if (s.length <= MAX_LINE) return s;
  const mid = s.length / 2;
  let best = -1;
  for (let i = 0; i < s.length; i++) if (s[i] === " " && (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))) best = i;
  return best < 0 ? s : `${s.slice(0, best)}\n${s.slice(best + 1)}`;
}

/**
 * One caption per sentence of every generated voiceover on the timeline, timed by how much
 * of the narration's text comes before it (speech runs at a fairly even pace). Captions you
 * wrote yourself are kept; ones generated earlier are replaced.
 */
export async function captionsFromVoiceovers(): Promise<number> {
  await voice.loadMeta();
  const made: Caption[] = [];
  for (const a of studio.audio) {
    const meta = await voice.metaFor(a.path);
    if (!meta?.text?.trim()) continue;
    const full = a.duration || a.out - a.in;
    const pieces = splitText(meta.text);
    const total = pieces.reduce((n, p) => n + p.length, 0) || 1;
    let acc = 0;
    for (const p of pieces) {
      const s0 = (full * acc) / total;
      acc += p.length;
      const s1 = (full * acc) / total;
      const st = Math.max(s0, a.in);
      const en = Math.min(s1, a.out);
      if (en - st < 0.3) continue;
      made.push({ id: `v-${uid()}`, start: a.start + st - a.in, end: a.start + en - a.in, text: p });
    }
  }
  // Narration spoken inside scenes (self.voiceover): exact timing, mapped through trims and speed.
  for (const clip of studio.clips) {
    const r = studio.renders[sceneKey(clip.file, clip.scene)];
    const sp = clip.speed ?? 1;
    for (const line of r?.narration ?? []) {
      const pieces = splitText(line.text);
      const total = pieces.reduce((n, p) => n + p.length, 0) || 1;
      let acc = 0;
      for (const p of pieces) {
        const s0 = line.start + ((line.end - line.start) * acc) / total;
        acc += p.length;
        const s1 = line.start + ((line.end - line.start) * acc) / total;
        const st = Math.max(s0, clip.in);
        const en = Math.min(s1, clip.out);
        if (en - st < 0.3) continue;
        made.push({ id: `v-${uid()}`, start: clip.start + (st - clip.in) / sp, end: clip.start + (en - clip.in) / sp, text: p });
      }
    }
  }
  const own = studio.captions.filter((c) => !c.id.startsWith("v-"));
  studio.setCaptions([...own, ...made]);
  return made.length;
}
