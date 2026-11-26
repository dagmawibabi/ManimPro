<script lang="ts">
  import { onMount } from "svelte";
  import { assistant, PROVIDERS } from "#lib/assistant.svelte.ts";
  import { models } from "#lib/models.svelte.ts";
  import { open } from "@tauri-apps/plugin-dialog";
  import { convertFileSrc } from "@tauri-apps/api/core";
  import type { PendingAttachment, Provider } from "#lib/api.ts";
  import Icon from "./Icon.svelte";
  import Picker from "./Picker.svelte";

  let {
    placeholder = "Describe what to make or change…",
    large = false,
    disabled = false,
    onSubmit,
  }: {
    placeholder?: string;
    large?: boolean;
    disabled?: boolean;
    onSubmit: (text: string, attachments: PendingAttachment[]) => void;
  } = $props();

  let text = $state("");
  let attachments = $state<PendingAttachment[]>([]);
  let dragging = $state(false);
  const IMAGE = /\.(png|jpe?g|gif|webp)$/i;

  async function pick() {
    const files = await open({
      multiple: true,
      title: "Attach files",
      filters: [
        { name: "Images and files", extensions: ["png", "jpg", "jpeg", "gif", "webp", "py", "txt", "md", "json", "csv", "pdf", "svg"] },
        { name: "All files", extensions: ["*"] },
      ],
    });
    for (const f of !files ? [] : Array.isArray(files) ? files : [files]) {
      const name = f.split(/[\\/]/).pop() ?? f;
      const image = IMAGE.test(name);
      attachments.push({ name, source: f, image, preview: image ? convertFileSrc(f) : undefined });
    }
  }

  function readFile(file: File) {
    if (file.size > 25 * 1024 * 1024) return;
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result);
      const image = file.type.startsWith("image/");
      const ext = image ? `.${file.type.split("/")[1] || "png"}` : "";
      const name = file.name && file.name !== "image.png" ? file.name : `pasted-${Date.now()}${ext}`;
      attachments.push({ name, data: url.slice(url.indexOf(",") + 1), image, preview: image ? url : undefined });
    };
    reader.readAsDataURL(file);
  }

  function onPaste(e: ClipboardEvent) {
    const files = [...(e.clipboardData?.files ?? [])];
    if (!files.length) return;
    e.preventDefault();
    files.forEach(readFile);
  }

  function onDrop(e: DragEvent) {
    dragging = false;
    const files = [...(e.dataTransfer?.files ?? [])];
    if (!files.length) return;
    e.preventDefault();
    files.forEach(readFile);
  }
  let box: HTMLTextAreaElement;

  onMount(() => {
    models.load();
  });

  const providerItems = PROVIDERS.map((p) => ({ value: p.id, label: p.name, sub: p.plan, group: p.key ? "API key" : "Your subscription" }));
  const modelItems = $derived(models.items(assistant.provider, assistant.modelLists[assistant.provider] ?? []));
  const st = $derived(assistant.current);
  const tone = $derived(!st ? "wait" : !st.installed ? "bad" : !st.signed_in ? "warn" : "ok");
  const label = $derived(
    !st ? "Checking…" : !st.installed ? "Not installed" : !st.signed_in ? "Not signed in" : (st.account ?? "Ready"),
  );

  function submit() {
    const t = text.trim();
    if ((!t && !attachments.length) || disabled || assistant.busy) return;
    onSubmit(t, $state.snapshot(attachments));
    attachments = [];
    text = "";
    box.style.height = "";
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function grow() {
    box.style.height = "auto";
    box.style.height = Math.min(box.scrollHeight, large ? 260 : 180) + "px";
  }

  export function fill(value: string) {
    text = value;
    queueMicrotask(() => {
      grow();
      box.focus();
    });
  }
</script>

<div
  class="box"
  class:large
  class:dragging
  role="group"
  aria-label="Composer"
  ondragover={(e) => {
    if (e.dataTransfer?.types.includes("Files")) {
      e.preventDefault();
      dragging = true;
    }
  }}
  ondragleave={() => (dragging = false)}
  ondrop={onDrop}
>
  {#if attachments.length}
    <div class="attachments">
      {#each attachments as a, i (i)}
        <span class="chip" title={a.name}>
          {#if a.preview}<img src={a.preview} alt="" />{:else}<Icon name="file" size={13} />{/if}
          <span class="chip-name">{a.name}</span>
          <button class="chip-x" aria-label="Remove {a.name}" onclick={() => attachments.splice(i, 1)}><Icon name="close" size={10} /></button>
        </span>
      {/each}
    </div>
  {/if}
  <textarea
    onpaste={onPaste}
    bind:this={box}
    bind:value={text}
    rows={large ? 3 : 2}
    {placeholder}
    aria-label="Prompt"
    oninput={grow}
    onkeydown={onKey}
  ></textarea>
  <div class="row">
    <button class="attach" title="Attach files or images (or paste / drop them)" aria-label="Attach files" onclick={pick}>
      <Icon name="paperclip" size={15} />
    </button>
    <div class="pick"><Picker label="Assistant" items={providerItems} value={assistant.provider} width={290} onChange={(v) => assistant.setProvider(v as Provider)} /></div>
    <div class="pick model">
      <Picker
        label="Model"
        items={modelItems}
        value={assistant.model}
        placeholder="Choose a model"
        width={400}
        searchable={modelItems.length > 8}
        onChange={(v) => assistant.setModel(v)}
      />
    </div>
    <span class="state {tone}" title={label}>
      <span class="dot"></span>
      {#if st && st.installed && !st.signed_in}
        <button class="signin" onclick={() => assistant.login()}>Sign in</button>
      {:else if st && !st.installed}
        <span class="label">Not installed</span>
      {/if}
    </span>
    {#if assistant.busy}
      <button class="send stop" aria-label="Stop" title="Stop" onclick={() => assistant.stop()}><Icon name="stop" size={11} /></button>
    {:else}
      <button class="send" aria-label="Send" title="Send (Enter)" disabled={(!text.trim() && !attachments.length) || disabled} onclick={submit}>
        <Icon name="send" size={15} />
      </button>
    {/if}
  </div>
</div>

<style>
  .box {
    container-type: inline-size;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 10px 10px 14px;
    border: 1px solid var(--line-strong);
    border-radius: 18px;
    background: var(--panel-2);
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .box:focus-within {
    border-color: color-mix(in srgb, var(--accent) 35%, var(--line-strong));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 9%, transparent);
  }
  .box.dragging {
    border-color: var(--accent);
    background: var(--accent-soft);
  }
  .attachments {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    max-width: 220px;
    height: 34px;
    padding: 0 6px 0 4px;
    border-radius: 10px;
    background: var(--panel);
    border: 1px solid var(--line);
    color: var(--muted);
    font-size: 12px;
  }
  .chip img {
    width: 26px;
    height: 26px;
    border-radius: 7px;
    object-fit: cover;
  }
  .chip :global(svg) {
    margin-left: 4px;
  }
  .chip-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .chip-x {
    display: grid;
    place-items: center;
    width: 18px;
    height: 18px;
    border-radius: 6px;
    color: var(--faint);
  }
  .chip-x:hover {
    background: var(--raised);
    color: var(--text);
  }
  .attach {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 10px;
    color: var(--muted);
  }
  .attach:hover {
    background: var(--raised);
    color: var(--text);
  }
  .large {
    border-radius: 22px;
    padding: 16px 12px 12px 18px;
  }
  textarea {
    width: 100%;
    resize: none;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--text);
    font: inherit;
    line-height: 1.5;
    user-select: text;
  }
  textarea::placeholder {
    color: var(--faint);
  }
  .large textarea {
    font-size: 15px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }
  .pick {
    flex: 0 1 auto;
    min-width: 0;
    max-width: 170px;
    display: flex;
  }
  .model {
    max-width: 220px;
  }
  .state {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    margin-left: 4px;
    font-size: 11.5px;
    color: var(--faint);
  }
  .label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .signin {
    color: var(--accent);
    font-size: 12px;
    font-weight: 500;
  }
  .signin:hover {
    text-decoration: underline;
  }
  .dot {
    flex: none;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--faint);
  }
  .ok .dot {
    background: var(--ok);
  }
  .warn .dot {
    background: #e0b04a;
  }
  .bad .dot {
    background: var(--danger);
  }
  .send {
    flex: none;
    margin-left: auto;
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--text);
    color: var(--bg);
    transition: background 0.12s, opacity 0.12s;
  }
  .send:disabled {
    background: var(--raised);
    color: var(--faint);
    cursor: default;
  }
  @container (max-width: 430px) {
    .label {
      display: none;
    }
    .pick {
      max-width: 130px;
    }
  }
</style>
