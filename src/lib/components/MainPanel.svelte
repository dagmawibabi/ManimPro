<script lang="ts">
  import { studio } from "#lib/studio.svelte.ts";
  import { assistant } from "#lib/assistant.svelte.ts";
  import { basename } from "#lib/api.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import { settings } from "#lib/settings.svelte.ts";
  import { fullscreen } from "#lib/fullscreen.svelte.ts";
  import CodeEditor from "./CodeEditor.svelte";
  import AssistantPanel from "./AssistantPanel.svelte";
  import Icon from "./Icon.svelte";
  import PythonIcon from "./PythonIcon.svelte";
</script>

<section class="main" class:fs={fullscreen.target === "code"}>
  <header>
    <div class="tabs" role="tablist" aria-label="Main panel">
      <button role="tab" aria-selected={ui.mainTab === "code"} class:active={ui.mainTab === "code"} onclick={() => (ui.mainTab = "code")}>
        <PythonIcon size={14} />
        {studio.activeFile ? basename(studio.activeFile) : "Code"}
        {#if studio.dirty}<span class="dirty" title="Unsaved changes"></span>{/if}
      </button>
      <button role="tab" aria-selected={ui.mainTab === "assistant"} class:active={ui.mainTab === "assistant"} onclick={() => (ui.mainTab = "assistant")}>
        <Icon name="sparkle" size={13} />
        Assistant
        {#if assistant.busy}<span class="busy" title="Working"></span>{/if}
      </button>
    </div>
    <div class="aside">
      {#if ui.mainTab === "code"}
        <span class="info">
          <button class="icon-btn" aria-label="Editor shortcuts" aria-describedby="editor-tips"><Icon name="info" size={14} /></button>
          <span class="tip" role="tooltip" id="editor-tips">
            <span><kbd>Ctrl</kbd> <kbd>Enter</kbd> Render the scene under the cursor</span>
            <span><kbd>Ctrl</kbd> <kbd>S</kbd> Save{settings.value.renderOnSave ? " and render" : ""}</span>
            <span><kbd>Ctrl</kbd> <kbd>=</kbd> / <kbd>−</kbd> Text size</span>
            <span><kbd>F11</kbd> Full screen</span>
          </span>
        </span>
        <div class="font" role="group" aria-label="Code font size">
          <button class="icon-btn" title="Smaller text (Ctrl + −)" aria-label="Smaller code text" onclick={() => settings.set("fontSize", Math.max(9, settings.value.fontSize - 1))}>
            <span class="a small">A</span>
          </button>
          <span class="size">{settings.value.fontSize}</span>
          <button class="icon-btn" title="Bigger text (Ctrl + =)" aria-label="Bigger code text" onclick={() => settings.set("fontSize", Math.min(28, settings.value.fontSize + 1))}>
            <span class="a">A</span>
          </button>
        </div>
      {:else}
        <button class="icon-btn" title="New chat" aria-label="New chat" disabled={assistant.busy} onclick={() => assistant.newChat()}>
          <Icon name="plus" size={14} />
        </button>
      {/if}
      <button
        class="icon-btn"
        title={fullscreen.target === "code" ? "Exit full screen (Esc)" : "Full screen (F11)"}
        aria-label={fullscreen.target === "code" ? "Exit full screen" : "Full screen"}
        onclick={() => fullscreen.toggle("code")}
      >
        <Icon name={fullscreen.target === "code" ? "shrink" : "expand"} size={14} />
      </button>
    </div>
  </header>
  <div class="body">
    <!-- Both stay mounted: switching tabs never loses editor state or a running chat. -->
    <div class="pane" class:hidden={ui.mainTab !== "code"}><CodeEditor /></div>
    <div class="pane" class:hidden={ui.mainTab !== "assistant"}><AssistantPanel /></div>
  </div>
</section>

<style>
  .main.fs {
    position: fixed;
    inset: 0;
    z-index: 60;
  }
  .font {
    display: flex;
    align-items: center;
    gap: 4px;
    padding-left: 8px;
    border-left: 1px solid var(--line);
  }
  .font .icon-btn {
    width: 26px;
    height: 26px;
  }
  .a {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 14px;
  }
  .a.small {
    font-size: 11px;
  }
  .size {
    min-width: 30px;
    text-align: center;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--faint);
  }
  .main {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    background: var(--panel);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    height: 44px;
    padding: 0 8px;
    border-bottom: 1px solid var(--line);
  }
  .tabs {
    display: flex;
    gap: 2px;
    padding: 3px;
    border-radius: 11px;
    background: var(--bg);
  }
  .tabs button {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 28px;
    padding: 0 12px;
    border-radius: var(--r-sm);
    color: var(--muted);
    font-weight: 500;
    white-space: nowrap;
  }
  .tabs button:hover {
    color: var(--text);
  }
  .tabs button.active {
    background: var(--raised);
    color: var(--text);
  }
  .dirty {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--muted);
  }
  .busy {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.2s ease-in-out infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.3;
    }
  }
  .aside {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }
  .info {
    position: relative;
    display: flex;
  }
  .tip {
    position: absolute;
    top: calc(100% + 8px);
    right: -6px;
    z-index: 20;
    display: grid;
    gap: 8px;
    width: max-content;
    padding: 12px 14px;
    border-radius: 14px;
    background: #1b1b1e;
    border: 1px solid var(--line-strong);
    box-shadow: 0 16px 40px rgb(0 0 0 / 0.5);
    color: var(--muted);
    font-size: 12.5px;
    white-space: nowrap;
    opacity: 0;
    transform: translateY(-4px);
    pointer-events: none;
    transition: opacity 0.12s, transform 0.12s;
  }
  .tip kbd {
    margin-right: 2px;
  }
  .info:hover .tip,
  .info:focus-within .tip {
    opacity: 1;
    transform: none;
  }
  .body {
    position: relative;
    flex: 1;
    min-height: 0;
  }
  .pane {
    position: absolute;
    inset: 0;
  }
  .pane.hidden {
    visibility: hidden;
    pointer-events: none;
  }

</style>
