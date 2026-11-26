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
      { title: "Code editor that knows Python", body: "The editor from VS Code with real Python help: completions for everything in scope, docs on hover, argument hints, Ctrl+click to jump to a definition, and warnings for typos and undefined names." },
      { title: "Projects and files", body: "Scene files in folders, plus any data or pictures your scenes read: CSV, JSON, images. Add them with a button or drag them in from File Explorer." },
      { title: "16 templates, and your own", body: "Calculus, linear algebra, Fourier series, Bayes, neural networks, sorting, search and more, each a finished 25–40 second video. Save any project as a template to start the next one from it." },
      { title: "Open any folder", body: "Point ManimPro at an existing Manim project, or right-click a folder in File Explorer. Relative paths and your manim.cfg work as they do on the command line." },
      { title: "Plugins, ready to go", body: "manim-slides for presentations, ManimML for neural networks, manim-chemistry for atoms and molecules. Install one in a click and add a starter scene that shows how it works." },
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
      { title: "It can do the whole edit", body: "Captions, transitions, clip speed, music, your photos and videos, the frame shape, even the export. It checks Manim's own docs instead of guessing, and asks before installing anything." },
      { title: "Research and your files", body: "Assistants can search the web and read files elsewhere on your PC, like notes or a dataset, then copy what a scene needs into the project. Both can be switched off." },
      { title: "Undo a request", body: "Every request saves a checkpoint first. If you don't like what changed, put the files and timeline back with one click." },
      { title: "Use it from other apps", body: "Claude Desktop, Claude Code, Cursor and other MCP apps can render scenes and edit the timeline of the project open in ManimPro, once you allow it in Settings." },
      { title: "Attachments and history", body: "Attach sketches, screenshots or data. Chats are saved with the project, with formatted answers, math, and highlighted code you can copy." },
    ],
  },
  {
    name: "Preview",
    lead: "See every scene beside its code, at the speed you need.",
    features: [
      { title: "Live preview", body: "Render the scene under your cursor with Ctrl + Enter, or every time you save. The engine stays loaded, so previews start in about a second." },
      { title: "Fast mode and quick look", body: "A 360p, 12 fps preview for quick checks, and a button that renders only the last frame." },
      { title: "Any frame shape", body: "16:9, vertical 9:16 for Shorts and Reels, square, 4:5, 4:3 and 21:9. Previews match, and scenes laid out for 16:9 can fit without being cut off." },
      { title: "ManimGL too", body: "Install 3Blue1Brown's own version of Manim in a click. Files written for it, including ones from the 3b1b/videos repository, render with it; everything else keeps using Manim Community." },
      { title: "LaTeX included", body: "MathTex and Tex work out of the box. No separate TeX install." },
    ],
  },
  {
    name: "Narrate",
    lead: "Narration that stays in step with the picture.",
    features: [
      { title: "Speak inside the scene", body: "Wrap animations in self.voiceover(\"...\") and the line is spoken, placed in the video, and the scene waits until it's finished. Bookmarks start an animation on an exact word." },
      { title: "Voiceovers on the timeline", body: "Or generate narration with ElevenLabs on the audio track, pick a voice by ear, and regenerate a line in place when the script changes." },
      { title: "Captions", body: "Made from your narration with its real timing, or typed by hand, edited on their own track, and exported as subtitles or burned into the picture." },
    ],
  },
  {
    name: "Edit",
    lead: "A timeline for scenes, your own footage, narration and music.",
    features: [
      { title: "Timeline", body: "Drag scenes in, trim, split at the playhead, duplicate, snap to edges and close gaps. Clips show frames from the render. Undo and redo everything." },
      { title: "Your photos and videos", body: "Put your own pictures and clips between scenes. Photos last as long as you like; videos keep their sound." },
      { title: "Speed", body: "Play any clip at half speed up to double speed, in the preview and the export." },
      { title: "Transitions", body: "Fade through black or crossfade between clips, in the preview and in the export." },
      { title: "Music library", body: "Eight original tracks made for ManimPro, free for any video including commercial ones (CC0). Or import your own audio." },
    ],
  },
  {
    name: "Export",
    lead: "Every scene is rendered again at full quality, then put together.",
    features: [
      { title: "Formats", body: "MP4 for anywhere, WebM for the web, ProRes MOV for editing apps, GIF, or a folder of PNG frames." },
      { title: "Transparent video", body: "Export with no background, as ProRes 4444 or VP9 WebM, to lay animations over other footage." },
      { title: "720p to 4K", body: "Pick the resolution, the frame shape and the file size you want. Export the whole timeline or a single scene." },
      { title: "Share the project", body: "Export a whole project as a .zip, with its code, assets and timeline, and import one someone sent you." },
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
  "Choose where projects are saved, outside OneDrive if you like",
  "Files, scenes and the chat are locked while an assistant works on them",
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
  { name: "Jedi and Pyflakes", role: "Python help in the code editor", license: "MIT", url: "https://github.com/davidhalter/jedi" },
  { name: "Cairo and Pango", role: "Drawing shapes and text", license: "LGPL / MPL", url: "https://www.cairographics.org/" },
];

/** What the app itself is built with. */
export const BUILT_WITH: Dep[] = [
  { name: "Tauri 2", role: "The desktop shell, in Rust", license: "MIT / Apache-2.0", url: "https://tauri.app/" },
  { name: "SvelteKit and Svelte 5", role: "The interface", license: "MIT", url: "https://svelte.dev/" },
  { name: "Monaco", role: "The code editor", license: "MIT", url: "https://microsoft.github.io/monaco-editor/" },
  { name: "KaTeX", role: "Math in chat answers", license: "MIT", url: "https://katex.org/" },
  { name: "highlight.js", role: "Highlighted code in chat answers", license: "BSD-3-Clause", url: "https://highlightjs.org/" },
  { name: "marked and DOMPurify", role: "Formatted chat answers", license: "MIT / Apache-2.0", url: "https://marked.js.org/" },
  { name: "Geist", role: "Interface type", license: "OFL-1.1", url: "https://vercel.com/font" },
];

/** Optional services you connect yourself. */
export const SERVICES: Dep[] = [
  { name: "Claude Code", role: "Assistant, with your Anthropic account", license: "Sign in", url: "https://www.anthropic.com/claude-code" },
  { name: "Codex", role: "Assistant, with your ChatGPT account", license: "Sign in", url: "https://openai.com/codex/" },
  { name: "OpenCode", role: "Assistant, with many model providers", license: "Sign in", url: "https://opencode.ai/" },
  { name: "OpenRouter and Vercel AI Gateway", role: "Models by API key, through OpenCode", license: "API key", url: "https://openrouter.ai/" },
  { name: "ElevenLabs", role: "Voiceovers and in-scene narration", license: "API key", url: "https://elevenlabs.io/" },
  { name: "ManimGL", role: "3Blue1Brown's Manim, installed on request", license: "MIT", url: "https://github.com/3b1b/manim" },
  { name: "Manim plugins", role: "manim-slides, ManimML, manim-chemistry", license: "Install in Settings", url: "https://plugins.manim.community/" },
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
  { q: "Can I run 3Blue1Brown's code?", a: "Yes, with ManimGL (one click to install). Files from the 3b1b/videos repository render once ManimPro fetches that repository's shared code, which it offers to do. Scenes with Pi creatures can't, because their artwork isn't public." },
  { q: "Can I use ManimPro from Claude Desktop or Cursor?", a: "Yes. Turn on \"Let other apps use ManimPro\" in Settings > Assistant and paste the configuration it shows into the other app. ManimPro needs to be open while they work." },
  { q: "Can I use the videos commercially?", a: "Yes. What you make is yours, and the built-in music is CC0. Check the terms of any voices or assets you bring in." },
  { q: "Is it affiliated with 3Blue1Brown or the Manim Community?", a: "No. ManimPro is an independent app built on Manim Community Edition, which is MIT-licensed." },
];
