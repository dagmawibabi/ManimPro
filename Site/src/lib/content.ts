/** Everything the page says, in one place. */

export const REPO = "https://github.com/dagmawibabi/ManimPro";
export const RELEASES = `${REPO}/releases`;
export const DOWNLOAD = `${RELEASES}/latest`;

export type Feature = { title: string; body: string };
export type Stage = { name: string; lead: string; features: Feature[] };

/** The whole app, in the order you use it. */
export const STAGES: Stage[] = [
  {
    name: "Write",
    lead: "A real code editor for Manim, and a project that holds everything a video needs.",
    features: [
      { title: "Code editor that knows Manim", body: "The editor from VS Code, with suggestions for Manim classes, animations and colors, snippets, and errors underlined on the line that caused them." },
      { title: "Projects and files", body: "Scene files in folders, plus any data or pictures your scenes read: CSV, JSON, images. Add them with a button or drag them in from File Explorer." },
      { title: "16 templates", body: "Calculus, linear algebra, Fourier series, Bayes, neural networks, sorting, search and more. Each is a finished 25–40 second video you can take apart." },
      { title: "Open any folder", body: "Point ManimPro at an existing Manim project, or right-click a folder in File Explorer. Relative paths and your manim.cfg work as they do on the command line." },
      { title: "Python packages", body: "Need networkx or scipy for a scene? Add it from PyPI in Settings. ManimPro keeps its own Manim and NumPy versions safe." },
    ],
  },
  {
    name: "Ask",
    lead: "Describe the video. An assistant plans it, writes the scenes, renders them and checks the result.",
    features: [
      { title: "Bring your own assistant", body: "Claude Code, Codex or OpenCode, each signed in through its own app. Or use an OpenRouter or Vercel AI Gateway key. Model details come from models.dev." },
      { title: "It plans, then builds", body: "Longer videos are split into scenes with a storyboard you can see, written one idea at a time and laid out on the timeline in order." },
      { title: "It looks at its own work", body: "After rendering, the assistant views frames from the preview to catch overlaps and text that runs off the edge, then fixes them." },
      { title: "Undo a request", body: "Every request saves a checkpoint first. If you don't like what changed, put the files and timeline back with one click." },
      { title: "Attachments and history", body: "Attach sketches, screenshots or data. Chats are saved with the project, with formatted answers and math." },
    ],
  },
  {
    name: "Preview",
    lead: "See every scene beside its code, at the speed you need.",
    features: [
      { title: "Live preview", body: "Render the scene under your cursor with Ctrl + Enter, or every time you save. The engine stays loaded, so previews start in about a second." },
      { title: "Fast mode and quick look", body: "A 360p, 12 fps preview for quick checks, and a button that renders only the last frame." },
      { title: "Any frame shape", body: "16:9, vertical 9:16 for Shorts and Reels, square, 4:5, 4:3 and 21:9. Previews match, and scenes laid out for 16:9 can fit without being cut off." },
      { title: "LaTeX included", body: "MathTex and Tex work out of the box. No separate TeX install." },
    ],
  },
  {
    name: "Edit",
    lead: "A timeline for scenes, narration and music.",
    features: [
      { title: "Timeline", body: "Drag scenes in, trim, split at the playhead, duplicate, snap to edges and close gaps. Clips show frames from the render. Undo and redo everything." },
      { title: "Transitions", body: "Fade through black or crossfade between scenes, in the preview and in the export." },
      { title: "Voiceovers", body: "Generate narration with ElevenLabs, pick a voice by ear, and regenerate a line in place when the script changes." },
      { title: "Music library", body: "Eight original tracks made for ManimPro, free for any video including commercial ones (CC0). Or import your own audio." },
      { title: "Captions", body: "Made from your narration or typed by hand, edited on their own track, exported as subtitles or burned into the picture." },
    ],
  },
  {
    name: "Export",
    lead: "Every scene is rendered again at full quality, then put together.",
    features: [
      { title: "Formats", body: "MP4 for anywhere, WebM for the web, ProRes MOV for editing apps, GIF, or a folder of PNG frames." },
      { title: "720p to 4K", body: "Pick the resolution, the frame shape and the file size you want. Export the whole timeline or a single scene." },
    ],
  },
];

/** Smaller things that make the app pleasant to live in. */
export const DETAILS: string[] = [
  "A home page to start from a prompt, a template or a recent project",
  "Project previews that play when you rest the pointer on them",
  "Switch projects from the title bar",
  "Layouts: preview in the middle, panels left or right, full-height panels",
  "Accent colors, interface size and editor fonts",
  "Full screen for the preview or the code",
  "Keyboard shortcuts for rendering, playback and the timeline",
  "API keys kept in Windows Credential Manager, never in your projects",
];

export type Dep = { name: string; role: string; license: string; url: string };

/** What ships inside the installer. */
export const BUNDLED: Dep[] = [
  { name: "Manim Community Edition 0.22", role: "The animation engine", license: "MIT", url: "https://www.manim.community/" },
  { name: "Python 3.12", role: "Runs Manim and your scenes", license: "PSF", url: "https://www.python.org/" },
  { name: "FFmpeg", role: "Encoding, mixing and export", license: "GPL-3.0", url: "https://ffmpeg.org/" },
  { name: "TinyTeX", role: "LaTeX for MathTex and Tex", license: "GPL-2.0 and TeX licences", url: "https://yihui.org/tinytex/" },
  { name: "NumPy, Pillow, PyAV", role: "Maths, images and video frames", license: "BSD and MIT-CMU", url: "https://numpy.org/" },
  { name: "Cairo and Pango", role: "Drawing shapes and text", license: "LGPL / MPL", url: "https://www.cairographics.org/" },
];

/** What the app itself is built with. */
export const BUILT_WITH: Dep[] = [
  { name: "Tauri 2", role: "The desktop shell, in Rust", license: "MIT / Apache-2.0", url: "https://tauri.app/" },
  { name: "SvelteKit and Svelte 5", role: "The interface", license: "MIT", url: "https://svelte.dev/" },
  { name: "Monaco", role: "The code editor", license: "MIT", url: "https://microsoft.github.io/monaco-editor/" },
  { name: "KaTeX", role: "Math in chat answers", license: "MIT", url: "https://katex.org/" },
  { name: "marked and DOMPurify", role: "Formatted chat answers", license: "MIT / Apache-2.0", url: "https://marked.js.org/" },
  { name: "Geist", role: "Interface type", license: "OFL-1.1", url: "https://vercel.com/font" },
];

/** Optional services you connect yourself. */
export const SERVICES: Dep[] = [
  { name: "Claude Code", role: "Assistant, with your Anthropic account", license: "Sign in", url: "https://www.anthropic.com/claude-code" },
  { name: "Codex", role: "Assistant, with your ChatGPT account", license: "Sign in", url: "https://openai.com/codex/" },
  { name: "OpenCode", role: "Assistant, with many model providers", license: "Sign in", url: "https://opencode.ai/" },
  { name: "OpenRouter and Vercel AI Gateway", role: "Models by API key, through OpenCode", license: "API key", url: "https://openrouter.ai/" },
  { name: "ElevenLabs", role: "Voiceovers", license: "API key", url: "https://elevenlabs.io/" },
];

export type Link = { label: string; note: string; url: string };
export const RESOURCES: { group: string; links: Link[] }[] = [
  {
    group: "Learn Manim",
    links: [
      { label: "Manim Community", note: "News, getting started and the community", url: "https://www.manim.community/" },
      { label: "Documentation", note: "Reference, tutorials and an example gallery", url: "https://docs.manim.community/" },
      { label: "ManimCommunity/manim", note: "Source code and releases of the engine ManimPro uses", url: "https://github.com/ManimCommunity/manim" },
      { label: "3b1b/manim", note: "Grant Sanderson's original version, ManimGL", url: "https://github.com/3b1b/manim" },
    ],
  },
  {
    group: "Get inspired",
    links: [
      { label: "3Blue1Brown on YouTube", note: "The videos Manim was made for", url: "https://www.youtube.com/@3blue1brown" },
      { label: "3b1b/videos", note: "The code behind 3Blue1Brown's videos", url: "https://github.com/3b1b/videos" },
      { label: "3blue1brown.com", note: "Lessons and written versions", url: "https://www.3blue1brown.com/" },
    ],
  },
  {
    group: "ManimPro",
    links: [
      { label: "Source code", note: "Read it, build it, contribute", url: REPO },
      { label: "Releases", note: "Installers and what changed", url: RELEASES },
      { label: "Report a problem", note: "Bugs and ideas on GitHub Issues", url: `${REPO}/issues` },
      { label: "Third-party notices", note: "Every component and its licence", url: `${REPO}/blob/main/THIRD-PARTY-NOTICES.md` },
    ],
  },
];

export const FAQ: { q: string; a: string }[] = [
  { q: "Do I need to install Python?", a: "No. Python, Manim, FFmpeg and LaTeX come inside the installer. Install ManimPro and start." },
  { q: "Is it free?", a: "Yes. ManimPro is free and open source. The AI assistants and ElevenLabs are optional and use your own accounts." },
  { q: "Which systems does it run on?", a: "Windows 10 and 11, 64-bit. The installer needs about 1 GB of disk space and doesn't need administrator rights." },
  { q: "Can I use my existing Manim code?", a: "Yes. Open the folder; your scenes, relative paths and manim.cfg work as they do with the manim command." },
  { q: "Can I use the videos commercially?", a: "Yes. What you make is yours, and the built-in music is CC0. Check the terms of any voices or assets you bring in." },
  { q: "Is it affiliated with 3Blue1Brown or the Manim Community?", a: "No. ManimPro is an independent app built on Manim Community Edition, which is MIT-licensed." },
];
