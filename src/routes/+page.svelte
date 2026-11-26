<script lang="ts">
  import { onMount } from "svelte";
  import { open } from "@tauri-apps/plugin-dialog";
  import { api, mediaUrl, type PendingAttachment, type ProjectSummary } from "#lib/api.ts";
  import { studio } from "#lib/studio.svelte.ts";
  import { assistant } from "#lib/assistant.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import { enterProject, type EnterOptions } from "#lib/navigation.ts";
  import templates from "#lib/templates.json";
  import PromptBox from "#lib/components/PromptBox.svelte";
  import Icon from "#lib/components/Icon.svelte";
  import LatexDialog from "#lib/components/LatexDialog.svelte";
  import WindowControls from "#lib/components/WindowControls.svelte";
  import { settings } from "#lib/settings.svelte.ts";

  type Template = (typeof templates)[number];

  let recent = $state<ProjectSummary[]>([]);
  let all = $state<ProjectSummary[]>([]);
  let root = $state("");
  let query = $state("");
  let category = $state("All");
  let busy = $state<string | null>(null);
  let failure = $state<string | null>(null);
  let box: PromptBox | undefined = $state();

  const categories = ["All", ...new Set(templates.map((t) => t.category))];
  const shown = $derived(templates.filter((t) => category === "All" || t.category === category));
  const filtered = $derived(
    all.filter((p) => !query.trim() || p.name.toLowerCase().includes(query.trim().toLowerCase())),
  );

  const ideas = [
    "A 30-second explainer of how compound interest grows",
    "Animate the steps of binary search on a sorted list",
    "Show how a Fourier series builds a square wave",
    "An intro title for my channel, 'Small Big Ideas'",
  ];

  onMount(() => {
    studio.init();
    assistant.init();
    load();
  });

  async function load() {
    try {
      const r = await api.listProjects();
      recent = r.recent.slice(0, 6);
      all = r.all;
      root = r.root;
    } catch (e) {
      failure = String(e);
    }
  }

  function nameFrom(prompt: string) {
    const words = prompt.replace(/[^\p{L}\p{N}\s'-]/gu, " ").split(/\s+/).filter(Boolean).slice(0, 6);
    const name = words.join(" ");
    return name ? name[0].toUpperCase() + name.slice(1) : "Untitled";
  }

  const enter = (dir: string, opts: EnterOptions = {}) => enterProject(dir, opts);

  async function startFromPrompt(prompt: string, files: PendingAttachment[] = []) {
    busy = "prompt";
    failure = null;
    try {
      const dir = await api.createProject(nameFrom(prompt || files[0]?.name || "Untitled"), "blank");
      await enter(dir, { prompt, files });
    } catch (e) {
      failure = String(e);
    } finally {
      busy = null;
    }
  }

  async function useTemplate(t: Template) {
    busy = t.id;
    failure = null;
    try {
      const dir = await api.createProject(t.title, t.id);
      await enter(dir, { render: true });
    } catch (e) {
      failure = String(e);
    } finally {
      busy = null;
    }
  }

  async function openFolder() {
    const dir = await open({ directory: true, title: "Open a project folder", defaultPath: root || undefined });
    if (typeof dir === "string") await enter(dir);
  }

  function ago(ms: number) {
    const s = (Date.now() - ms) / 1000;
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)} min ago`;
    if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
    if (s < 86400 * 7) return `${Math.floor(s / 86400)} d ago`;
    return new Date(ms).toLocaleDateString();
  }

  function seconds(d: number | null | undefined) {
    if (!d) return "";
    return d >= 60 ? `${Math.floor(d / 60)}:${String(Math.round(d % 60)).padStart(2, "0")}` : `${Math.round(d)}s`;
  }
</script>

<div class="home">
  <header class="top" data-tauri-drag-region>
    <div class="brand" data-tauri-drag-region><img src="/logo.svg" alt="" width="22" height="22" /> ManimPro</div>
    <div class="top-actions" data-tauri-drag-region>
      <button class="icon-btn" title="Settings (Ctrl + ,)" aria-label="Settings" onclick={() => settings.show()}>
        <Icon name="settings" size={16} />
      </button>
      {#if studio.worker.status === "ready" && !studio.worker.latex}
        <button class="btn" onclick={() => (ui.latexOpen = true)}><Icon name="sigma" size={13} /> Install LaTeX</button>
      {/if}
      <button class="btn" onclick={openFolder}><Icon name="folder" size={14} /> Open folder</button>
      <WindowControls />
    </div>
  </header>

  <!-- Only this area scrolls; the top bar stays put. -->
  <div class="scroll">
  <main>
    <section class="hero">
      <h1>What do you want to make?</h1>
      <p class="lede">Describe a video and your assistant writes the Manim scenes, renders them and puts them on the timeline.</p>
      <div class="prompt">
        <PromptBox
          bind:this={box}
          large
          placeholder="e.g. Show how the area of a circle comes from unrolling it into a triangle"
          disabled={busy !== null || !assistant.current?.signed_in}
          onSubmit={startFromPrompt}
        />
        {#if assistant.current && (!assistant.current.installed || !assistant.current.signed_in)}
          <p class="hint">
            {#if !assistant.current.installed}
              {assistant.current.install_hint}
            {:else}
              Sign in to your assistant first.
              <button class="link" onclick={() => assistant.login()}>Sign in</button>
              <button class="link" onclick={() => assistant.refresh()}>Check again</button>
            {/if}
          </p>
        {/if}
        <div class="ideas">
          {#each ideas as idea (idea)}
            <button class="idea" onclick={() => box?.fill(idea)}>{idea}</button>
          {/each}
        </div>
      </div>
      <button class="browse" onclick={() => document.getElementById("templates")?.scrollIntoView({ behavior: "smooth" })}>
        Or start from one of {templates.length - 1} templates
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5 6 7.5 9 4.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
      {#if failure}<p class="failure">{failure}</p>{/if}
    </section>

    {#if recent.length}
      <section>
        <div class="section-head"><h2>Recent</h2></div>
        <div class="projects recent">
          {#each recent as p (p.dir)}
            <button class="project" onclick={() => enter(p.dir)}>
              <div class="thumb">
                {#if p.thumbnail}<img src={mediaUrl(p.thumbnail, p.modified)} alt="" />{:else}<Icon name="film" size={22} />{/if}
              </div>
              <div class="meta">
                <span class="name">{p.name}</span>
                <span class="sub">{ago(p.modified)} · {p.scenes} {p.scenes === 1 ? "scene" : "scenes"}</span>
              </div>
            </button>
          {/each}
        </div>
      </section>
    {/if}

    <section id="templates">
      <div class="section-head">
        <h2>Start from a template</h2>
        <div class="filters" role="tablist" aria-label="Template categories">
          {#each categories as c (c)}
            <button role="tab" aria-selected={category === c} class:active={category === c} onclick={() => (category = c)}>{c}</button>
          {/each}
        </div>
      </div>
      <div class="templates">
        {#each shown as t (t.id)}
          <button class="template" disabled={busy !== null} onclick={() => useTemplate(t)}>
            <div class="thumb">
              {#if t.thumbnail}
                <img src={t.thumbnail} alt="" loading="lazy" />
              {:else if t.id === "blank"}
                <Icon name="plus" size={26} />
              {:else}
                <span class="formula">{t.latex ? "a² + b² = c²" : t.title}</span>
              {/if}
              {#if t.duration}<span class="dur">{seconds(t.duration)}</span>{/if}
              {#if busy === t.id}<span class="busy"><span class="spin"></span></span>{/if}
            </div>
            <div class="meta">
              <span class="name">{t.title}{#if t.latex}<span class="badge" title="Needs LaTeX">LaTeX</span>{/if}</span>
              <span class="sub">{t.description}</span>
              <span class="facts">{t.category}{t.scenes.length > 1 ? ` · ${t.scenes.length} scenes` : ""}</span>
            </div>
          </button>
        {/each}
      </div>
    </section>

    <section>
      <div class="section-head">
        <h2>All projects</h2>
        <label class="search">
          <Icon name="search" size={13} />
          <input placeholder="Search projects" bind:value={query} aria-label="Search projects" />
        </label>
      </div>
      {#if filtered.length}
        <div class="projects">
          {#each filtered as p (p.dir)}
            <button class="project" onclick={() => enter(p.dir)}>
              <div class="thumb">
                {#if p.thumbnail}<img src={mediaUrl(p.thumbnail, p.modified)} alt="" loading="lazy" />{:else}<Icon name="film" size={22} />{/if}
              </div>
              <div class="meta">
                <span class="name">{p.name}</span>
                <span class="sub">{ago(p.modified)} · {p.clips} {p.clips === 1 ? "clip" : "clips"}</span>
              </div>
            </button>
          {/each}
        </div>
      {:else}
        <p class="empty">{query ? "No projects match that search." : "Projects you create appear here."}</p>
      {/if}
      {#if root}<p class="root">Saved in {root}</p>{/if}
    </section>
  </main>
  </div>
</div>

{#if ui.latexOpen}
  <LatexDialog onClose={() => (ui.latexOpen = false)} />
{/if}

<style>
  .home {
    position: relative;
    isolation: isolate;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    user-select: none;
    background:
      radial-gradient(1100px 600px at 50% -120px, color-mix(in srgb, var(--accent) 18%, transparent), transparent 70%),
      radial-gradient(700px 420px at 88% 8%, rgb(255 255 255 / 0.035), transparent 70%),
      var(--bg);
  }
  /* Faint graph paper (minor and major lines), fading out toward the edges. */
  .home::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -1;
    pointer-events: none;
    background-image:
      linear-gradient(rgb(255 255 255 / 0.07) 1px, transparent 1px),
      linear-gradient(90deg, rgb(255 255 255 / 0.07) 1px, transparent 1px),
      linear-gradient(rgb(255 255 255 / 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgb(255 255 255 / 0.03) 1px, transparent 1px);
    background-size:
      96px 96px,
      96px 96px,
      24px 24px,
      24px 24px;
    background-position: center -1px;
    mask-image: radial-gradient(ellipse 70% 60% at 50% 32%, #000 0%, rgb(0 0 0 / 0.5) 45%, transparent 80%);
  }
  .scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }
  .top {
    position: relative;
    flex: none;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 52px;
    padding: 0 0 0 20px;
    background: rgb(12 12 14 / 0.6);
    backdrop-filter: blur(14px);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 15px;
  }
  .top-actions {
    display: flex;
    align-items: center;
    align-self: stretch;
    gap: 8px;
  }
  main {
    max-width: 1180px;
    margin: 0 auto;
    padding: 0 28px 60px;
  }
  /* The composer sits in the middle of the first screen; the gallery follows below. */
  .hero {
    position: relative;
    isolation: isolate;
    min-height: calc(100vh - 52px - 110px);
    max-width: 780px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: stretch;
    text-align: center;
    padding: 40px 0 24px;
  }
  /* A faint glow of the accent color behind the composer. */
  .hero::before {
    content: "";
    position: absolute;
    left: 50%;
    top: 50%;
    width: 900px;
    height: 520px;
    transform: translate(-50%, -46%);
    background: radial-gradient(closest-side, var(--accent-soft), transparent 72%);
    opacity: 0.35;
    pointer-events: none;
    z-index: -1;
  }
  .prompt :global(.box) {
    box-shadow: 0 24px 70px rgb(0 0 0 / 0.45);
  }
  .browse {
    align-self: center;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 34px;
    padding: 6px 12px;
    border-radius: 999px;
    color: var(--faint);
    font-size: 12.5px;
  }
  .browse:hover {
    color: var(--text);
    background: var(--panel);
  }
  .facts {
    font-size: 11.5px;
    color: var(--muted);
  }
  h1 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 36px;
    font-weight: 600;
    letter-spacing: -0.035em;
    line-height: 1.15;
  }
  .lede {
    margin: 12px auto 26px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.55;
    max-width: 54ch;
  }
  .prompt {
    display: grid;
    gap: 14px;
    text-align: left;
  }
  .hint {
    margin: 0;
    color: var(--muted);
    font-size: 12.5px;
    text-align: center;
  }
  .link {
    color: var(--accent);
    font-weight: 500;
    margin-left: 6px;
  }
  .ideas {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 6px;
  }
  .idea {
    padding: 7px 13px;
    border-radius: 999px;
    border: 1px solid var(--line-strong);
    color: var(--muted);
    font-size: 12.5px;
  }
  .idea:hover {
    border-color: var(--line-strong);
    color: var(--text);
  }
  .failure {
    color: #f3c7c3;
    font-family: var(--mono);
    font-size: 12px;
  }

  section {
    margin-top: 34px;
  }
  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 600;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    padding: 3px;
    border-radius: 12px;
    background: var(--panel);
  }
  .filters button {
    padding: 5px 11px;
    border-radius: var(--r-sm);
    font-size: 12px;
    color: var(--muted);
  }
  .filters button.active {
    background: var(--raised);
    color: var(--text);
  }

  .templates {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(232px, 1fr));
    gap: 18px 16px;
  }
  .projects {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
  }
  .template,
  .project {
    display: flex;
    flex-direction: column;
    gap: 9px;
    text-align: left;
    border-radius: var(--r-lg);
  }
  .template:disabled {
    cursor: progress;
  }
  /* The outline is an inset ring drawn above the image (::after), not a border on the
     clipped box, so rounded corners stay smooth on hover and at any interface zoom. */
  .thumb {
    position: relative;
    aspect-ratio: 16 / 9;
    border-radius: 14px;
    overflow: hidden;
    isolation: isolate;
    background: #0d0e11;
    display: grid;
    place-items: center;
    color: var(--faint);
  }
  .thumb::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 2;
    border-radius: inherit;
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.07);
    pointer-events: none;
    transition: box-shadow 0.18s ease;
  }
  .template:hover .thumb::after,
  .project:hover .thumb::after,
  .template:focus-visible .thumb::after,
  .project:focus-visible .thumb::after {
    box-shadow: inset 0 0 0 2px var(--accent);
  }
  .template:focus-visible,
  .project:focus-visible {
    outline: none;
  }
  .thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    border-radius: inherit;
    transition: transform 0.35s ease;
  }
  .template:hover .thumb img,
  .project:hover .thumb img {
    transform: scale(1.025);
  }
  .formula {
    font-family: "Cambria Math", Cambria, serif;
    font-size: 22px;
    color: var(--muted);
    font-style: italic;
  }
  .dur {
    position: absolute;
    right: 6px;
    bottom: 6px;
    padding: 2px 7px;
    border-radius: 7px;
    background: rgb(0 0 0 / 0.65);
    color: var(--text);
    font-size: 11px;
    font-family: var(--mono);
  }
  .busy {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.5);
  }
  .spin {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--accent-soft);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .meta {
    display: grid;
    gap: 3px;
    padding: 0 2px;
  }
  .name {
    display: flex;
    align-items: center;
    gap: 7px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sub {
    color: var(--faint);
    font-size: 12px;
    line-height: 1.45;
  }
  .badge {
    padding: 0 6px;
    border-radius: 6px;
    border: 1px solid var(--line-strong);
    color: var(--muted);
    font-size: 10.5px;
    font-weight: 500;
  }
  .search {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 0 10px;
    border-radius: 10px;
    border: 1px solid var(--line);
    background: var(--panel);
    color: var(--faint);
  }
  .search input {
    border: 0;
    background: none;
    padding: 5px 0;
    width: 200px;
    outline: none;
  }
  .search:focus-within {
    border-color: var(--accent);
  }
  .empty,
  .root {
    color: var(--faint);
    font-size: 12.5px;
  }
  .root {
    margin-top: 14px;
  }
</style>
