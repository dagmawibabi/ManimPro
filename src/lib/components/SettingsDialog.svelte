<script lang="ts">
  import { onMount } from "svelte";
  import { open as openDialog } from "@tauri-apps/plugin-dialog";
  import { settings, ACCENTS, FONT_FAMILIES, type Accent, type Settings } from "#lib/settings.svelte.ts";
  import { assistant, PROVIDERS } from "#lib/assistant.svelte.ts";
  import { models } from "#lib/models.svelte.ts";
  import { studio, EXPORT_PRESETS } from "#lib/studio.svelte.ts";
  import { api, type Provider } from "#lib/api.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import Icon from "./Icon.svelte";
  import Picker from "./Picker.svelte";
  import { openUrl } from "@tauri-apps/plugin-opener";

  let dialog: HTMLDialogElement;
  const v = $derived(settings.value);

  const SECTIONS = [
    { id: "interface", label: "Interface", icon: "home" },
    { id: "editor", label: "Code editor", icon: "file" },
    { id: "accounts", label: "Accounts", icon: "user" },
    { id: "assistant", label: "Assistant", icon: "sparkle" },
    { id: "rendering", label: "Rendering", icon: "bolt" },
    { id: "export", label: "Export", icon: "export" },
    { id: "timeline", label: "Timeline", icon: "film" },
    { id: "shortcuts", label: "Shortcuts", icon: "terminal" },
    { id: "resources", label: "Resources", icon: "book" },
    { id: "about", label: "About", icon: "info" },
  ];

  const REPO = "https://github.com/dagmawibabi/ManimPro";
  const SITE = "https://manim.dagmawi.dev";

  const RESOURCES: { title: string; links: { label: string; sub: string; url: string }[] }[] = [
    {
      title: "Manim",
      links: [
        { label: "Manim Community", sub: "Website, news and getting started", url: "https://www.manim.community/" },
        { label: "Documentation", sub: "Reference, tutorials and example gallery", url: "https://docs.manim.community/" },
        { label: "Manim Community on GitHub", sub: "Source code, issues and releases (the version ManimPro uses)", url: "https://github.com/ManimCommunity/manim" },
        { label: "3b1b/manim on GitHub", sub: "Grant Sanderson's original version, ManimGL", url: "https://github.com/3b1b/manim" },
      ],
    },
    {
      title: "3Blue1Brown",
      links: [
        { label: "3Blue1Brown on YouTube", sub: "The videos Manim was made for", url: "https://www.youtube.com/@3blue1brown" },
        { label: "Video source code", sub: "The scenes behind 3Blue1Brown's videos", url: "https://github.com/3b1b/videos" },
        { label: "3blue1brown.com", sub: "Lessons, written versions and more", url: "https://www.3blue1brown.com/" },
      ],
    },
    {
      title: "ManimPro",
      links: [
        { label: "ManimPro on GitHub", sub: "Open source: code, issues and releases", url: REPO },
        { label: "manim.dagmawi.dev", sub: "The ManimPro website", url: SITE },
      ],
    },
  ];

  const BUILT_WITH: [string, string][] = [
    ["Manim Community Edition", "the animation engine (MIT)"],
    ["Python 3.12", "embedded, with Manim, PyAV and Pillow"],
    ["FFmpeg", "encoding and export, via imageio-ffmpeg"],
    ["TinyTeX", "a bundled LaTeX for MathTex and Tex"],
    ["Tauri 2", "the desktop shell, written in Rust"],
    ["SvelteKit and Svelte 5", "the interface"],
    ["Monaco", "the code editor (from VS Code)"],
    ["marked, KaTeX and DOMPurify", "Markdown and math in the assistant chat"],
    ["Geist", "the heading typeface"],
    ["models.dev", "model names, limits and prices for the pickers"],
    ["Claude Code, Codex and OpenCode", "assistants, through their own command-line tools"],
    ["ElevenLabs", "voiceovers (optional, with your own key)"],
  ];

  // API keys: the UI only ever sees "••••1234".
  const KEYED = [
    ...PROVIDERS.filter((p) => p.key).map((p) => ({ id: p.id as string, name: p.name, note: "Assistant, through OpenCode" })),
    { id: "elevenlabs", name: "ElevenLabs", note: "Voiceovers and narration" },
  ];
  const SIGN_IN = PROVIDERS.filter((p) => !p.key);
  let voiceQuota = $state<string | null>(null);
  let keyHints = $state<Record<string, string | null>>({});
  let keyDrafts = $state<Record<string, string>>({});
  let keyErrors = $state<Record<string, string | null>>({});

  onMount(() => {
    dialog.showModal();
    for (const p of KEYED) api.apiKeyHint(p.id).then((h) => (keyHints[p.id] = h));
    for (const p of SIGN_IN) if (!assistant.status[p.id]) assistant.refresh(p.id);
    loadQuota();
    models.load();
    // API-key providers run through OpenCode: make sure its status is known.
    if (!assistant.status.opencode) assistant.refresh("opencode");
  });

  function close() {
    dialog.close();
    settings.open = false;
  }

  async function loadQuota() {
    try {
      const u = await api.voiceAccount();
      voiceQuota = u ? `${u.used.toLocaleString()} of ${u.limit.toLocaleString()} characters used this period (${u.tier})` : null;
    } catch (e) {
      voiceQuota = String(e);
    }
  }

  async function saveKey(id: string) {
    keyErrors[id] = null;
    try {
      await api.setApiKey(id, keyDrafts[id] ?? "");
      keyDrafts[id] = "";
      keyHints[id] = await api.apiKeyHint(id);
      if (id === "elevenlabs") loadQuota();
      else assistant.refresh(id as Provider);
    } catch (e) {
      keyErrors[id] = String(e);
    }
  }

  async function removeKey(id: string) {
    await api.clearApiKey(id);
    keyHints[id] = null;
    if (id === "elevenlabs") voiceQuota = null;
    else assistant.refresh(id as Provider);
  }

  async function chooseFolder() {
    const dir = await openDialog({ directory: true, title: "Default export folder" });
    if (typeof dir === "string") settings.set("exportFolder", dir);
  }

  function set<K extends keyof Settings>(k: K, value: Settings[K]) {
    settings.set(k, value);
  }

  const SHORTCUTS = [
    ["Ctrl + Enter", "Render the scene under the cursor"],
    ["Ctrl + S", "Save (and render, if Render on save is on)"],
    ["Ctrl + = / Ctrl + −", "Code font size bigger / smaller"],
    ["Ctrl + 0", "Reset code font size"],
    ["F11", "Full screen for the focused panel"],
    ["Esc", "Leave full screen"],
    ["Space", "Play / pause"],
    ["S", "Split clip at playhead"],
    ["Delete", "Delete selected clip"],
    ["← / →", "Step one frame (Shift: one second)"],
    ["Ctrl + scroll", "Zoom the timeline"],
    ["Ctrl + E", "Export"],
    ["Ctrl + ,", "Open settings"],
  ];
</script>

{#snippet toggle(key: keyof Settings, label: string, hint?: string)}
  <label class="row">
    <span class="text"><span class="label">{label}</span>{#if hint}<span class="hint">{hint}</span>{/if}</span>
    <input type="checkbox" class="switch" checked={!!v[key]} onchange={(e) => set(key, e.currentTarget.checked as never)} />
  </label>
{/snippet}

{#snippet segmented(key: keyof Settings, label: string, options: { value: string | number; label: string }[], hint?: string)}
  <div class="row">
    <span class="text"><span class="label">{label}</span>{#if hint}<span class="hint">{hint}</span>{/if}</span>
    <div class="seg" role="radiogroup" aria-label={label}>
      {#each options as o (o.value)}
        <button role="radio" aria-checked={v[key] === o.value} class:on={v[key] === o.value} onclick={() => set(key, o.value as never)}>{o.label}</button>
      {/each}
    </div>
  </div>
{/snippet}

<dialog bind:this={dialog} oncancel={(e) => { e.preventDefault(); close(); }}>
  <nav>
    <h2>Settings</h2>
    {#each SECTIONS as s (s.id)}
      <button class:active={settings.section === s.id} onclick={() => (settings.section = s.id)}>
        <Icon name={s.icon} size={14} /> {s.label}
      </button>
    {/each}
  </nav>

  <section class="content">
    <header>
      <h3>{SECTIONS.find((s) => s.id === settings.section)?.label}</h3>
      <button class="icon-btn" aria-label="Close settings" onclick={close}><Icon name="close" /></button>
    </header>

    <div class="scroll">
      {#if settings.section === "interface"}
        <div class="group">
          <h4>Appearance</h4>
          {@render segmented("uiScale", "Interface size", [90, 100, 110, 125].map((n) => ({ value: n, label: `${n}%` })))}
          {@render segmented(
            "sidebarSide",
            "Project and chats panel",
            [{ value: "left", label: "Left" }, { value: "right", label: "Right" }],
            "Right swaps it with the code panel.",
          )}
          {@render segmented(
            "editorLayout",
            "Editor layout",
            [{ value: "code-center", label: "Code in the middle" }, { value: "preview-center", label: "Preview in the middle" }],
            "Preview in the middle puts Code and Assistant on the right.",
          )}
          {@render segmented(
            "fullHeight",
            "Full-height panel",
            [{ value: "none", label: "None" }, { value: "project", label: "Project" }, { value: "code", label: "Code" }],
            "Runs that panel down to the bottom of the window; the timeline sits under the preview instead.",
          )}
          <div class="row">
            <span class="text"><span class="label">Accent color</span><span class="hint">Used for the playhead, selection and main buttons.</span></span>
            <div class="swatches" role="radiogroup" aria-label="Accent color">
              {#each Object.entries(ACCENTS) as [id, a] (id)}
                <button
                  role="radio"
                  aria-checked={v.accent === id}
                  aria-label={a.label}
                  title={a.label}
                  class="swatch"
                  class:on={v.accent === id}
                  style:--c={a.color}
                  onclick={() => set("accent", id as Accent)}
                ></button>
              {/each}
            </div>
          </div>
          {@render toggle("reduceMotion", "Reduce motion", "Turns off interface animations. Your videos are not affected.")}
          {@render toggle("showStatusBar", "Show status bar", "Render engine status, LaTeX and the render log.")}
        </div>
        <div class="group">
          <h4>Behavior</h4>
          {@render toggle("openLastProject", "Open the last project on launch", "Skip the home page and continue where you left off.")}
          {@render toggle("confirmDelete", "Ask before deleting clips")}
        </div>
      {:else if settings.section === "editor"}
        <div class="group">
          <h4>Text</h4>
          <div class="row">
            <span class="text"><span class="label">Font size</span><span class="hint">Also Ctrl + = and Ctrl + − in the editor.</span></span>
            <div class="stepper">
              <button class="icon-btn" aria-label="Smaller" onclick={() => set("fontSize", Math.max(9, v.fontSize - 0.5))}><Icon name="zoomOut" size={14} /></button>
              <span>{v.fontSize}px</span>
              <button class="icon-btn" aria-label="Bigger" onclick={() => set("fontSize", Math.min(28, v.fontSize + 0.5))}><Icon name="zoomIn" size={14} /></button>
            </div>
          </div>
          <div class="row">
            <span class="text"><span class="label">Font</span></span>
            <div class="field"><Picker label="Font" variant="field" width={280} items={FONT_FAMILIES} value={v.fontFamily} onChange={(x) => set("fontFamily", x)} /></div>
          </div>
          {@render segmented("lineHeight", "Line spacing", [{ value: 1.4, label: "Compact" }, { value: 1.55, label: "Normal" }, { value: 1.75, label: "Relaxed" }])}
          {@render toggle("ligatures", "Font ligatures", "Joins symbols like -> and != when the font supports it.")}
        </div>
        <div class="group">
          <h4>Layout</h4>
          {@render segmented("tabSize", "Tab size", [{ value: 2, label: "2" }, { value: 4, label: "4" }])}
          {@render toggle("wordWrap", "Wrap long lines")}
          {@render toggle("lineNumbers", "Line numbers")}
          {@render toggle("minimap", "Minimap", "A zoomed-out view of the file on the right.")}
          {@render toggle("stickyScroll", "Sticky scroll", "Keeps the current class and method at the top while scrolling.")}
        </div>
        <div class="group">
          <h4>Help while typing</h4>
          {@render toggle("manimCompletions", "Manim suggestions", "Suggests Manim classes, animations, colors and snippets.")}
        </div>
      {:else if settings.section === "accounts"}
        <div class="group">
          <h4>Assistants you sign in to</h4>
          <p class="note">Each one signs in through its own window. ManimPro never sees your password or tokens.</p>
          {#each SIGN_IN as p (p.id)}
            {@const st = assistant.status[p.id]}
            <div class="row">
              <span class="text">
                <span class="label">{p.name}</span>
                <span class="hint">
                  {#if !st}Checking…{:else if !st.installed}Not installed. {st.install_hint}{:else if st.signed_in}Signed in{st.account ? ` as ${st.account}` : ""}{st.version ? ` · ${st.version}` : ""}{:else}Not signed in{/if}
                </span>
              </span>
              <div class="actions">
                {#if st?.installed && !st.signed_in}
                  <button class="btn primary" onclick={() => { assistant.setProvider(p.id); assistant.login(); }}>Sign in</button>
                {/if}
                <button class="btn ghost" onclick={() => assistant.refresh(p.id)}><Icon name="refresh" size={13} /> Check</button>
              </div>
            </div>
          {/each}
        </div>
        <div class="group">
          <h4>API keys</h4>
          <p class="note">Stored in Windows Credential Manager, never in your projects, and only shown as the last four characters.</p>
          {#each KEYED as p (p.id)}
            <div class="key">
              <div class="key-head">
                <span class="label">{p.name}</span>
                <span class="hint">{p.note}</span>
                {#if keyHints[p.id]}<span class="saved"><Icon name="check" size={12} /> Saved {keyHints[p.id]}</span>{/if}
              </div>
              <div class="key-row">
                <input
                  type="password"
                  placeholder={keyHints[p.id] ? "Paste a new key to replace it" : "Paste your API key"}
                  autocomplete="off"
                  value={keyDrafts[p.id] ?? ""}
                  oninput={(e) => (keyDrafts[p.id] = e.currentTarget.value)}
                />
                <button class="btn primary" disabled={!keyDrafts[p.id]?.trim()} onclick={() => saveKey(p.id)}>Save</button>
                {#if keyHints[p.id]}<button class="btn ghost" onclick={() => removeKey(p.id)}>Remove</button>{/if}
              </div>
              {#if p.id === "elevenlabs" && keyHints.elevenlabs && voiceQuota}<span class="hint">{voiceQuota}</span>{/if}
              {#if p.id !== "elevenlabs" && !assistant.status.opencode?.installed}<span class="hint">Needs OpenCode: npm i -g opencode-ai</span>{/if}
              {#if keyErrors[p.id]}<span class="error">{keyErrors[p.id]}</span>{/if}
            </div>
          {/each}
        </div>
      {:else if settings.section === "assistant"}
        <div class="group">
          <h4>How the assistant works</h4>
          {@render toggle("multiSceneByDefault", "Split longer videos into scenes", "Plans a storyboard, writes one Scene per idea and arranges them on the timeline.")}
          {@render toggle("autoRenderAfterAssistant", "Render after each reply", "Shows the result even when the assistant didn't render it itself.")}
          {@render toggle("showToolDetails", "Show tool details", "Tool output under each step. Errors always show.")}
          <div class="row col">
            <span class="text"><span class="label">Standing instructions</span><span class="hint">Added to every request, e.g. "Use a dark navy background and the Inter font."</span></span>
            <textarea rows="3" value={v.extraInstructions} oninput={(e) => set("extraInstructions", e.currentTarget.value)} placeholder="Optional"></textarea>
          </div>
        </div>
        <div class="group">
          <h4>Model details</h4>
          <div class="row">
            <span class="text">
              <span class="label">models.dev catalog</span>
              <span class="hint">{models.catalog ? `${Object.keys(models.catalog).length} providers loaded. Refreshed daily.` : models.error ?? "Loading…"}</span>
            </span>
            <button class="btn" disabled={models.loading} onclick={() => models.load(true)}><Icon name="refresh" size={13} /> Refresh</button>
          </div>
        </div>
      {:else if settings.section === "rendering"}
        <div class="group">
          <h4>Previews</h4>
          {@render segmented("previewQuality", "Preview quality", [{ value: "preview", label: "480p" }, { value: "draft", label: "720p" }, { value: "high", label: "1080p" }], "Lower is faster. Exports always re-render at full quality.")}
          {@render toggle("renderOnSave", "Render on save", "Ctrl + S renders the scene under the cursor.")}
          {@render toggle("disableCache", "Always render from scratch", "Skips Manim's animation cache. Slower; use it if a preview looks stale.")}
        </div>
        <div class="group">
          <h4>Look</h4>
          <div class="row">
            <span class="text"><span class="label">Default background</span><span class="hint">Scenes that set their own background keep it.</span></span>
            <div class="swatches">
              {#each ["#000000", "#0f1115", "#1c1f26", "#ffffff"] as c (c)}
                <button class="swatch square" class:on={v.backgroundColor === c} style:--c={c} aria-label="Background {c}" onclick={() => set("backgroundColor", c)}></button>
              {/each}
              <input type="color" aria-label="Custom background" value={v.backgroundColor} onchange={(e) => set("backgroundColor", e.currentTarget.value)} />
            </div>
          </div>
        </div>
        <div class="group">
          <h4>Engine</h4>
          <div class="row">
            <span class="text"><span class="label">Manim {studio.worker.manim ?? ""}</span><span class="hint">Bundled with ManimPro: Python, Manim and FFmpeg.</span></span>
            <button class="btn" onclick={() => studio.cancel()}><Icon name="refresh" size={13} /> Restart engine</button>
          </div>
          <div class="row">
            <span class="text"><span class="label">LaTeX</span><span class="hint">{studio.worker.latex ? "Installed. MathTex and Tex work." : "Not installed. Needed for MathTex and Tex."}</span></span>
            <button class="btn" onclick={() => { close(); ui.latexOpen = true; }}>{studio.worker.latex ? "Details" : "Install"}</button>
          </div>
        </div>
      {:else if settings.section === "export"}
        <div class="group">
          <h4>Defaults</h4>
          {@render segmented("exportPreset", "Resolution", EXPORT_PRESETS.map((p) => ({ value: p.id, label: p.label.split(" · ")[0] })))}
          {@render segmented("exportQuality", "Quality", [{ value: "small", label: "Smaller file" }, { value: "balanced", label: "Balanced" }, { value: "high", label: "Best" }], "Best keeps fine lines crisp at the cost of file size.")}
          <div class="row">
            <span class="text"><span class="label">Save exports to</span><span class="hint">{v.exportFolder || "The project folder"}</span></span>
            <div class="actions">
              {#if v.exportFolder}<button class="btn ghost" onclick={() => set("exportFolder", "")}>Use project folder</button>{/if}
              <button class="btn" onclick={chooseFolder}><Icon name="folder" size={13} /> Choose</button>
            </div>
          </div>
        </div>
      {:else if settings.section === "timeline"}
        <div class="group">
          <h4>Editing</h4>
          {@render toggle("snapping", "Snap to clip edges and the playhead")}
          <div class="row">
            <span class="text"><span class="label">Default zoom</span><span class="hint">{v.defaultZoom}px per second</span></span>
            <input type="range" min="12" max="160" step="4" value={v.defaultZoom} oninput={(e) => set("defaultZoom", +e.currentTarget.value)} aria-label="Default zoom" />
          </div>
        </div>
      {:else if settings.section === "shortcuts"}
        <div class="group">
          {#each SHORTCUTS as [keys, what] (keys)}
            <div class="row"><span class="label">{what}</span><kbd>{keys}</kbd></div>
          {/each}
        </div>
      {:else if settings.section === "resources"}
        {#each RESOURCES as group (group.title)}
          <div class="group">
            <h4>{group.title}</h4>
            {#each group.links as l (l.url)}
              <button class="link-row" onclick={() => openUrl(l.url)} title={l.url}>
                <span class="text"><span class="label">{l.label}</span><span class="hint">{l.sub}</span></span>
                <Icon name="link" size={14} />
              </button>
            {/each}
          </div>
        {/each}
      {:else}
        <div class="group about">
          <img src="/logo.svg" alt="" width="48" height="48" />
          <div class="about-text">
            <h4>ManimPro <span class="version">0.1.0</span></h4>
            <p class="note">
              A desktop studio for making and editing Manim videos: write scenes or ask an assistant to, preview them,
              arrange them on a timeline with voiceovers and music, and export. Everything it needs (Python, Manim,
              FFmpeg and LaTeX) comes with the app.
            </p>
            <p class="note">
              ManimPro is <strong>open source</strong>. The code, issues and releases are on GitHub, and contributions are welcome.
            </p>
            <div class="about-links">
              <button class="btn" onclick={() => openUrl(REPO)}><Icon name="link" size={13} /> github.com/dagmawibabi/ManimPro</button>
              <button class="btn" onclick={() => openUrl(SITE)}><Icon name="link" size={13} /> manim.dagmawi.dev</button>
            </div>
          </div>
        </div>

        <div class="group">
          <h4>Built with</h4>
          {#each BUILT_WITH as [name, what] (name)}
            <div class="row compact"><span class="label">{name}</span><span class="hint right">{what}</span></div>
          {/each}
        </div>

        <div class="group">
          <h4>This install</h4>
          <div class="row compact"><span class="label">Render engine</span><span class="hint right">{studio.worker.status === "ready" ? "Ready" : studio.worker.status}</span></div>
          <div class="row compact"><span class="label">Manim</span><span class="hint right">{studio.worker.manim ?? "Not loaded yet"}</span></div>
        </div>

        <div class="group">
          <h4>Credits</h4>
          <p class="note credits">
            Manim was created by Grant Sanderson (3Blue1Brown) and is maintained by the Manim Community developers.
            Several templates are original scenes inspired by topics from 3Blue1Brown's videos. ManimPro is not
            affiliated with 3Blue1Brown or the Manim Community.
          </p>
        </div>
      {/if}
    </div>

    <footer>
      <button class="btn ghost" onclick={() => settings.reset()}>Reset everything</button>
      <span class="spacer"></span>
      <span class="saved-note">Changes save automatically</span>
      <button class="btn primary" onclick={close}>Done</button>
    </footer>
  </section>
</dialog>

<style>
  dialog {
    width: min(860px, 92vw);
    height: min(620px, 86vh);
    padding: 0;
    border: 1px solid var(--line-strong);
    border-radius: 22px;
    background: var(--panel);
    color: var(--text);
    box-shadow: 0 30px 80px rgb(0 0 0 / 0.6);
    overflow: hidden;
  }
  dialog[open] {
    display: grid;
    grid-template-columns: 210px 1fr;
  }
  dialog::backdrop {
    background: rgb(5 5 6 / 0.6);
    backdrop-filter: blur(3px);
  }
  nav {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 18px 10px;
    background: var(--bg);
    border-right: 1px solid var(--line);
  }
  nav h2 {
    margin: 0 10px 14px;
    font-family: var(--font-display);
    font-size: 17px;
    font-weight: 600;
  }
  nav button {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 34px;
    padding: 0 12px;
    border-radius: 10px;
    color: var(--muted);
    text-align: left;
  }
  nav button:hover {
    color: var(--text);
    background: var(--panel);
  }
  nav button.active {
    color: var(--text);
    background: var(--raised);
  }
  .content {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 14px 6px 26px;
  }
  h3 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 600;
  }
  .scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 6px 26px 20px;
  }
  .group {
    margin-top: 14px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--panel-2);
    padding: 4px 16px;
  }
  .group h4 {
    margin: 12px 0 2px;
    font-size: 11.5px;
    font-weight: 600;
    color: var(--faint);
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    min-height: 54px;
    padding: 10px 0;
    border-top: 1px solid var(--line);
  }
  .group h4 + .row,
  .group > .row:first-child {
    border-top: 0;
  }
  .row.col {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .text {
    display: grid;
    gap: 2px;
    min-width: 0;
  }
  .label {
    font-weight: 500;
  }
  .hint,
  .note {
    font-size: 12px;
    color: var(--faint);
    line-height: 1.45;
  }
  .note {
    margin: 4px 0 10px;
  }
  .switch {
    appearance: none;
    flex: none;
    width: 36px;
    height: 20px;
    padding: 0;
    border: 0;
    border-radius: 999px;
    background: var(--raised);
    position: relative;
    cursor: pointer;
    transition: background 0.15s;
  }
  .switch::after {
    content: "";
    position: absolute;
    top: 3px;
    left: 3px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--muted);
    transition: transform 0.15s, background 0.15s;
  }
  .switch:checked {
    background: var(--accent-soft);
  }
  .switch:checked::after {
    transform: translateX(16px);
    background: var(--accent);
  }
  .seg {
    display: flex;
    flex: none;
    gap: 2px;
    padding: 3px;
    border-radius: 11px;
    background: var(--bg);
  }
  .seg button {
    height: 28px;
    padding: 0 12px;
    border-radius: 8px;
    color: var(--muted);
    font-size: 12.5px;
    white-space: nowrap;
  }
  .seg button.on {
    background: var(--raised);
    color: var(--text);
  }
  .swatches {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .swatch {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: var(--c);
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.12);
  }
  .swatch.square {
    border-radius: 7px;
  }
  .swatch.on {
    box-shadow: 0 0 0 2px var(--panel-2), 0 0 0 4px var(--text);
  }
  input[type="color"] {
    width: 30px;
    height: 24px;
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .stepper {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: var(--mono);
    font-size: 12px;
  }
  .stepper span {
    min-width: 48px;
    text-align: center;
  }
  .field {
    width: 240px;
    display: flex;
  }
  textarea {
    width: 100%;
    resize: vertical;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--panel);
    color: var(--text);
    font: inherit;
    line-height: 1.5;
    user-select: text;
  }
  .key {
    display: grid;
    gap: 6px;
    padding: 12px 0;
    border-top: 1px solid var(--line);
  }
  .key-head {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .saved {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--ok);
  }
  .key-row {
    display: flex;
    gap: 6px;
  }
  .key-row input {
    flex: 1;
    height: 32px;
    border-radius: 10px;
    user-select: text;
  }
  .error {
    color: #f3c7c3;
    font-size: 12px;
  }
  .actions {
    display: flex;
    gap: 6px;
  }
  input[type="range"] {
    width: 180px;
    padding: 0;
    border: 0;
    background: none;
    accent-color: var(--accent);
  }
  .about {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    padding: 18px;
  }
  .about h4 {
    margin: 0 0 4px;
    font-size: 15px;
    color: var(--text);
  }
  .about-text {
    display: grid;
    gap: 8px;
  }
  .about-text .note {
    margin: 0;
  }
  .version {
    margin-left: 6px;
    font-size: 12px;
    font-weight: 500;
    color: var(--faint);
  }
  .about-links {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }
  .row.compact {
    min-height: 40px;
    padding: 8px 0;
  }
  .link-row + .link-row {
    border-top: 1px solid var(--line);
    border-radius: 0;
  }
  .hint.right {
    text-align: right;
  }
  .credits {
    margin: 0;
    padding: 4px 0 8px;
  }
  .link-row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 10px 8px;
    margin: 0 -8px;
    width: calc(100% + 16px);
    border-radius: 10px;
    text-align: left;
    color: var(--muted);
  }
  .link-row:hover {
    background: var(--raised);
    color: var(--text);
  }
  .link-row .text {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
  }
  footer {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 20px 16px 26px;
    border-top: 1px solid var(--line);
  }
  .spacer {
    flex: 1;
  }
  .saved-note {
    font-size: 12px;
    color: var(--faint);
  }
  kbd {
    flex: none;
  }
</style>
