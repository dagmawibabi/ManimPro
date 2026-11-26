<script lang="ts">
  import type { Plan } from "#lib/assistant.svelte.ts";
  import { studio, sceneKey } from "#lib/studio.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import Icon from "./Icon.svelte";

  let { plan }: { plan: Plan } = $props();

  const total = $derived(plan.scenes.reduce((s, x) => s + (x.seconds ?? 0), 0));
  const files = $derived(new Set(plan.scenes.map((s) => s.file)).size);

  function fmt(sec: number) {
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return m ? `${m}:${String(s).padStart(2, "0")}` : `${s}s`;
  }

  /** Per scene: written yet (found in the project) and rendered yet. */
  function state(file: string, scene: string) {
    const f = studio.resolveFile(file);
    if (!f || !studio.scenes[f]?.some((s) => s.name === scene)) return "planned";
    return studio.renders[sceneKey(f, scene)] ? "rendered" : "written";
  }

  async function openScene(file: string, scene: string) {
    const f = studio.resolveFile(file);
    if (!f) return;
    await studio.openFile(f);
    ui.mainTab = "code";
    const s = studio.scenes[f]?.find((x) => x.name === scene);
    if (s) studio.goToLine(s.line);
  }
</script>

<article class="plan">
  <header>
    <span class="tile"><Icon name="film" size={15} /></span>
    <div class="title">
      <h4>{plan.title}</h4>
      <span class="meta">
        {plan.scenes.length} scenes{total ? ` · about ${fmt(total)}` : ""} · {files} {files === 1 ? "file" : "files"}
      </span>
    </div>
  </header>
  <ol>
    {#each plan.scenes as sc, i (i)}
      {@const st = state(sc.file, sc.scene)}
      <li class={st}>
        <button onclick={() => openScene(sc.file, sc.scene)} disabled={st === "planned"} title={st === "planned" ? "Not written yet" : "Open the code"}>
          <span class="num">{#if st === "rendered"}<Icon name="check" size={11} />{:else}{i + 1}{/if}</span>
          <span class="body">
            <span class="top">
              <span class="name">{sc.scene}</span>
              <span class="chip">{sc.file}</span>
              {#if sc.seconds}<span class="chip">~{fmt(sc.seconds)}</span>{/if}
            </span>
            <span class="sum">{sc.summary}</span>
          </span>
        </button>
      </li>
    {/each}
  </ol>
</article>

<style>
  .plan {
    border-radius: 16px;
    background: var(--panel-2);
    border: 1px solid var(--line);
    overflow: hidden;
  }
  header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px 10px;
  }
  .tile {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 11px;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .title {
    display: grid;
    gap: 2px;
    min-width: 0;
  }
  h4 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 14.5px;
    font-weight: 600;
  }
  .meta {
    font-size: 11.5px;
    color: var(--faint);
  }
  ol {
    list-style: none;
    margin: 0;
    padding: 4px 8px 10px;
    position: relative;
  }
  li {
    position: relative;
  }
  /* The connecting line between scene numbers. */
  li:not(:last-child)::before {
    content: "";
    position: absolute;
    left: 21px;
    top: 34px;
    bottom: -6px;
    width: 1px;
    background: var(--line-strong);
  }
  li button {
    display: flex;
    gap: 12px;
    width: 100%;
    padding: 8px;
    border-radius: 12px;
    text-align: left;
  }
  li button:not(:disabled):hover {
    background: var(--raised);
  }
  li button:disabled {
    cursor: default;
  }
  .num {
    position: relative;
    z-index: 1;
    flex: none;
    display: grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--panel);
    border: 1px solid var(--line-strong);
    color: var(--muted);
    font-size: 11.5px;
    font-weight: 600;
  }
  .written .num {
    border-color: var(--accent);
    color: var(--accent);
  }
  .rendered .num {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-ink);
  }
  .body {
    display: grid;
    gap: 3px;
    min-width: 0;
    padding-top: 2px;
  }
  .top {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .name {
    font-weight: 600;
  }
  .planned .name {
    color: var(--muted);
  }
  .chip {
    padding: 1px 7px;
    border-radius: 6px;
    background: var(--bg);
    color: var(--faint);
    font-size: 11px;
    font-family: var(--mono);
  }
  .sum {
    color: var(--muted);
    font-size: 12.5px;
    line-height: 1.5;
  }
</style>
