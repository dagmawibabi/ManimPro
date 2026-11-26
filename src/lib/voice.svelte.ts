/** ElevenLabs voiceovers: voice list, defaults and generation. */
import { api, joinPath, type Voice } from "./api";
import { studio } from "./studio.svelte";

const store = typeof localStorage !== "undefined" ? localStorage : null;

export const VOICE_MODELS = [
  { value: "eleven_multilingual_v2", label: "Multilingual v2", sub: "Most stable for long narration · 29 languages" },
  { value: "eleven_flash_v2_5", label: "Flash v2.5", sub: "Fast and half the cost · 32 languages" },
  { value: "eleven_v3", label: "Eleven v3", sub: "Most expressive · 70+ languages" },
];

/** How a voiceover was made, so it can be opened again and regenerated. */
export type VoiceMeta = { text: string; voiceId: string; modelId: string; speed?: number; stability?: number };

class VoiceStore {
  /** Per project: relative audio path → how it was generated (.manimpro/voiceovers.json). */
  meta = $state<Record<string, VoiceMeta>>({});
  #metaDir: string | null = null;
  voices = $state<Voice[]>([]);
  loading = $state(false);
  error = $state<string | null>(null);
  voiceId = $state(store?.getItem("mp.voice") ?? "");
  modelId = $state(store?.getItem("mp.voiceModel") ?? VOICE_MODELS[0].value);
  generating = $state(false);

  current = $derived(this.voices.find((v) => v.id === this.voiceId) ?? this.voices[0]);

  async load(force = false) {
    if ((this.voices.length && !force) || this.loading) return;
    this.loading = true;
    this.error = null;
    try {
      this.voices = await api.voiceList();
      if (!this.voices.some((v) => v.id === this.voiceId) && this.voices[0]) this.setVoice(this.voices[0].id);
    } catch (e) {
      this.error = String(e);
    } finally {
      this.loading = false;
    }
  }

  setVoice(id: string) {
    this.voiceId = id;
    store?.setItem("mp.voice", id);
  }

  setModel(id: string) {
    this.modelId = id;
    store?.setItem("mp.voiceModel", id);
  }

  private rel(path: string) {
    return studio.dir && path.toLowerCase().startsWith(studio.dir.toLowerCase())
      ? path.slice(studio.dir.length + 1).replaceAll("\\", "/")
      : path;
  }

  async loadMeta() {
    if (!studio.dir || this.#metaDir === studio.dir) return;
    this.#metaDir = studio.dir;
    try {
      this.meta = JSON.parse(await api.readText(joinPath(studio.dir, ".manimpro\\voiceovers.json")));
    } catch {
      this.meta = {};
    }
  }

  /** The settings a generated file was made with, if ManimPro made it. */
  async metaFor(path: string): Promise<VoiceMeta | undefined> {
    await this.loadMeta();
    return this.meta[this.rel(path)];
  }

  private async saveMeta(path: string, m: VoiceMeta) {
    await this.loadMeta();
    this.meta[this.rel(path)] = m;
    if (studio.dir) await api.writeText(joinPath(studio.dir, ".manimpro\\voiceovers.json"), JSON.stringify(this.meta, null, 1));
  }

  /** Finds a voice by id or (part of) its name. */
  find(query?: string | null): Voice | undefined {
    if (!query) return this.current;
    const q = query.toLowerCase();
    return this.voices.find((v) => v.id === query) ?? this.voices.find((v) => v.name.toLowerCase().includes(q));
  }

  /** Generates speech into assets/audio; optionally places it on the audio track. */
  async generate(text: string, opts: { voice?: string; name?: string; speed?: number; stability?: number; place?: boolean; at?: number } = {}) {
    if (!studio.dir) throw new Error("Open a project first.");
    await this.load();
    const voice = this.find(opts.voice);
    if (!voice) throw new Error(this.error ?? "No ElevenLabs voices are available for this account.");
    this.generating = true;
    try {
      const path = await api.voiceGenerate({
        projectDir: studio.dir,
        text,
        voiceId: voice.id,
        modelId: this.modelId,
        name: opts.name ?? null,
        speed: opts.speed ?? null,
        stability: opts.stability ?? null,
      });
      if (!studio.audioFiles.includes(path)) studio.audioFiles = [...studio.audioFiles, path].sort();
      await this.saveMeta(path, { text, voiceId: voice.id, modelId: this.modelId, speed: opts.speed, stability: opts.stability });
      const clip = opts.place ? await studio.placeAudio(path, opts.at) : null;
      return { path, voice: voice.name, clip };
    } finally {
      this.generating = false;
    }
  }
}

export const voice = new VoiceStore();

// Let assistants list voices and make voiceovers through ManimPro's bridge.
studio.voiceTools = {
  async list() {
    await voice.load();
    if (voice.error) throw new Error(voice.error);
    return voice.voices.map((v) => ({ id: v.id, name: v.name, category: v.category, labels: v.labels }));
  },
  async generate(args) {
    const audioEnd = studio.audio.reduce((m, a) => Math.max(m, a.start + a.out - a.in), 0);
    const r = await voice.generate(String(args.text ?? ""), {
      voice: args.voice ?? null,
      name: args.name ?? undefined,
      place: args.add_to_timeline !== false,
      at: typeof args.start === "number" ? args.start : audioEnd,
    });
    return {
      file: r.path.split(/[\\/]/).pop(),
      voice: r.voice,
      start: r.clip?.start ?? null,
      duration: r.clip ? r.clip.out - r.clip.in : null,
    };
  },
};
