/** Small bits of UI state shared between routes and panels. */
class Ui {
  /** Left sidebar: the project's files and scenes, or saved assistant chats. */
  sideTab = $state<"project" | "chats">("project");
  /** Main panel: the code editor, or the assistant conversation. */
  mainTab = $state<"code" | "assistant">("code");
  latexOpen = $state(false);
  voiceOpen = $state(false);
  /** When set, the voice dialog edits this generated voiceover (and the clip that uses it). */
  voiceEdit = $state<{ path: string; clipId?: string } | null>(null);
}

export const ui = new Ui();
