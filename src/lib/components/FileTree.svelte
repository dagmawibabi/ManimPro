<script lang="ts" module>
  export type TreeNode = { name: string; path: string; kind: "folder" | "file"; children: TreeNode[] };
</script>

<script lang="ts">
  import { ask } from "@tauri-apps/plugin-dialog";
  import { studio } from "#lib/studio.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import Icon from "./Icon.svelte";
  import PythonIcon from "./PythonIcon.svelte";
  import ContextMenu, { type MenuItem } from "./ContextMenu.svelte";

  const store = typeof localStorage !== "undefined" ? localStorage : null;
  let collapsed = $state<Record<string, boolean>>(JSON.parse(store?.getItem("mp.collapsed") ?? "{}"));
  let menu = $state<{ x: number; y: number; items: MenuItem[] } | null>(null);
  /** Inline name entry: creating a file/folder inside `parent`, or renaming `path`. */
  let editing = $state<{ mode: "file" | "folder" | "rename"; parent: string; path?: string; value: string } | null>(null);
  let dropTarget = $state<string | null>(null);
  let error = $state<string | null>(null);

  const tree = $derived.by(() => {
    const root: TreeNode = { name: "", path: studio.dir ?? "", kind: "folder", children: [] };
    if (!studio.dir) return root;
    const index = new Map<string, TreeNode>([[studio.dir.toLowerCase(), root]]);
    const parentOf = (p: string) => p.slice(0, p.lastIndexOf("\\"));
    const ensure = (dir: string): TreeNode => {
      const key = dir.toLowerCase();
      const found = index.get(key);
      if (found) return found;
      const node: TreeNode = { name: dir.slice(dir.lastIndexOf("\\") + 1), path: dir, kind: "folder", children: [] };
      index.set(key, node);
      ensure(parentOf(dir)).children.push(node);
      return node;
    };
    for (const f of studio.folders) ensure(f);
    for (const f of studio.files) {
      ensure(parentOf(f)).children.push({ name: f.slice(f.lastIndexOf("\\") + 1), path: f, kind: "file", children: [] });
    }
    const sort = (n: TreeNode) => {
      n.children.sort((a, b) => (a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === "folder" ? -1 : 1));
      n.children.forEach(sort);
    };
    sort(root);
    return root;
  });

  function toggle(path: string) {
    collapsed[path] = !collapsed[path];
    store?.setItem("mp.collapsed", JSON.stringify(collapsed));
  }

  export function startNew(mode: "file" | "folder", parent: string = studio.dir!) {
    collapsed[parent] = false;
    editing = { mode, parent, value: "" };
  }

  async function commit() {
    const e = editing;
    editing = null;
    if (!e || !e.value.trim()) return;
    error = null;
    try {
      if (e.mode === "file") await studio.newFile(e.value.trim(), e.parent);
      else if (e.mode === "folder") await studio.newFolder(e.parent, e.value.trim());
      else if (e.path) await studio.renamePath(e.path, e.value.trim());
    } catch (err) {
      error = String(err);
    }
  }

  async function remove(node: TreeNode) {
    const what = node.kind === "folder" ? `the folder “${node.name}” and everything in it` : `“${node.name}”`;
    if (!(await ask(`Move ${what} to the Recycle Bin?`, { title: "Delete", kind: "warning" }))) return;
    try {
      await studio.trashPath(node.path);
    } catch (err) {
      error = String(err);
    }
  }

  function nodeMenu(e: MouseEvent, node: TreeNode | null) {
    e.preventDefault();
    e.stopPropagation();
    const folder = node?.kind === "folder" ? node.path : node ? node.path.slice(0, node.path.lastIndexOf("\\")) : studio.dir!;
    const items: MenuItem[] = [
      { label: "New scene file", icon: "filePlus", action: () => startNew("file", folder) },
      { label: "New folder", icon: "folderPlus", action: () => startNew("folder", folder) },
    ];
    if (node) {
      items.push(
        "separator",
        {
          label: "Rename",
          icon: "pencil",
          action: () => (editing = { mode: "rename", parent: folder, path: node.path, value: node.kind === "file" ? node.name.replace(/\.py$/i, "") : node.name }),
        },
        { label: "Move to project root", icon: "folder", disabled: folder.toLowerCase() === studio.dir?.toLowerCase(), action: () => studio.movePath(node.path, studio.dir!) },
        "separator",
        { label: "Delete", icon: "trash", danger: true, action: () => remove(node) },
      );
    }
    menu = { x: e.clientX, y: e.clientY, items };
  }

  // Drag files and folders onto folders to move them.
  function dragStart(e: DragEvent, node: TreeNode) {
    e.dataTransfer?.setData("application/x-mp-path", node.path);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
  }
  function dragOver(e: DragEvent, folder: string) {
    if (!e.dataTransfer?.types.includes("application/x-mp-path")) return;
    e.preventDefault();
    e.stopPropagation();
    dropTarget = folder;
  }
  async function drop(e: DragEvent, folder: string) {
    const path = e.dataTransfer?.getData("application/x-mp-path");
    dropTarget = null;
    if (!path) return;
    e.preventDefault();
    e.stopPropagation();
    try {
      await studio.movePath(path, folder);
    } catch (err) {
      error = String(err);
    }
  }

  function focusInput(el: HTMLInputElement) {
    el.focus();
    el.select();
  }
</script>

{#snippet nameInput(depth: number, kind: "file" | "folder")}
  <div class="row editing" style:padding-left="{10 + depth * 14}px">
    {#if kind === "folder"}<Icon name="folder" size={14} />{:else}<PythonIcon size={14} />{/if}
    <input
      use:focusInput
      bind:value={editing!.value}
      placeholder={kind === "folder" ? "folder name" : "file_name"}
      aria-label="Name"
      onkeydown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") editing = null;
      }}
      onblur={commit}
    />
    {#if kind === "file"}<span class="ext">.py</span>{/if}
  </div>
{/snippet}

{#snippet branch(node: TreeNode, depth: number)}
  {#each node.children as child (child.path)}
    {#if editing?.mode === "rename" && editing.path === child.path}
      {@render nameInput(depth, child.kind)}
    {:else if child.kind === "folder"}
      <div
        class="row folder"
        class:drop={dropTarget === child.path}
        role="treeitem"
        aria-expanded={!collapsed[child.path]}
        aria-selected="false"
        tabindex="0"
        style:padding-left="{10 + depth * 14}px"
        draggable="true"
        ondragstart={(e) => dragStart(e, child)}
        ondragover={(e) => dragOver(e, child.path)}
        ondragleave={() => (dropTarget = null)}
        ondrop={(e) => drop(e, child.path)}
        onclick={() => toggle(child.path)}
        onkeydown={(e) => (e.key === "Enter" || e.key === " ") && toggle(child.path)}
        oncontextmenu={(e) => nodeMenu(e, child)}
      >
        <span class="chev" class:open={!collapsed[child.path]}><Icon name="chevron" size={12} /></span>
        <Icon name="folder" size={14} />
        <span class="name">{child.name}</span>
      </div>
      {#if !collapsed[child.path]}
        {@render branch(child, depth + 1)}
        {#if editing && editing.mode !== "rename" && editing.parent === child.path}{@render nameInput(depth + 1, editing.mode)}{/if}
      {/if}
    {:else}
      {@const n = studio.scenes[child.path]?.length ?? 0}
      <button
        class="row file"
        class:active={child.path === studio.activeFile}
        role="treeitem"
        aria-selected={child.path === studio.activeFile}
        style:padding-left="{24 + depth * 14}px"
        draggable="true"
        ondragstart={(e) => dragStart(e, child)}
        onclick={() => {
          studio.openFile(child.path);
          ui.mainTab = "code";
        }}
        oncontextmenu={(e) => nodeMenu(e, child)}
      >
        <PythonIcon size={14} />
        <span class="name">{child.name}</span>
        {#if child.path === studio.activeFile && studio.dirty}<span class="dot" title="Unsaved changes"></span>{/if}
        {#if n}<span class="badge" title="{n} {n === 1 ? 'scene' : 'scenes'}">{n}</span>{/if}
      </button>
    {/if}
  {/each}
{/snippet}

{#if menu}<ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => (menu = null)} />{/if}

<div
  class="tree"
  class:drop={dropTarget === studio.dir}
  role="tree"
  aria-label="Project files"
  tabindex="-1"
  ondragover={(e) => dragOver(e, studio.dir!)}
  ondragleave={() => (dropTarget = null)}
  ondrop={(e) => drop(e, studio.dir!)}
  oncontextmenu={(e) => nodeMenu(e, null)}
>
  {@render branch(tree, 0)}
  {#if editing && editing.mode !== "rename" && editing.parent === studio.dir}{@render nameInput(0, editing.mode)}{/if}
  {#if !studio.files.length && !studio.folders.length && !editing}
    <p class="empty">No files yet. Right-click to add one.</p>
  {/if}
</div>
{#if error}<p class="error" role="alert">{error} <button class="link" onclick={() => (error = null)}>Dismiss</button></p>{/if}

<style>
  .tree {
    display: grid;
    gap: 1px;
    padding: 2px 0 6px;
    border-radius: 10px;
    min-height: 34px;
  }
  .tree.drop {
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  .row {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    height: 30px;
    padding-right: 10px;
    border-radius: 9px;
    color: var(--muted);
    text-align: left;
    cursor: pointer;
    outline: none;
  }
  .row:hover,
  .row:focus-visible {
    background: var(--panel-2);
    color: var(--text);
  }
  .row.active {
    background: var(--raised);
    color: var(--text);
  }
  .row.drop {
    background: var(--accent-soft);
    color: var(--text);
  }
  .chev {
    display: grid;
    transition: transform 0.12s;
  }
  .chev.open {
    transform: rotate(90deg);
  }
  .name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--muted);
  }
  .badge {
    min-width: 20px;
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--bg);
    color: var(--faint);
    font-size: 11px;
    text-align: center;
  }
  .editing {
    background: var(--panel-2);
    cursor: default;
  }
  .editing input {
    flex: 1;
    min-width: 0;
    padding: 0;
    border: 0;
    background: none;
    outline: none;
    user-select: text;
  }
  .ext {
    color: var(--faint);
  }
  .empty {
    margin: 6px 10px;
    color: var(--faint);
    font-size: 12px;
  }
  .error {
    margin: 4px 8px;
    color: #f3c7c3;
    font-size: 12px;
  }
  .link {
    color: var(--accent);
  }
</style>
