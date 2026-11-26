<script lang="ts">
  import { onMount } from "svelte";
  import type * as Monaco from "monaco-editor";
  import { studio } from "#lib/studio.svelte.ts";
  import { MANIM_COMPLETIONS } from "#lib/manim-symbols.ts";
  import { settings, ACCENTS } from "#lib/settings.svelte.ts";

  /** Editor options that come from Settings. */
  function editorOptions() {
    const s = settings.value;
    return {
      fontFamily: s.fontFamily,
      fontLigatures: s.ligatures,
      fontSize: s.fontSize,
      lineHeight: Math.round(s.fontSize * s.lineHeight),
      tabSize: s.tabSize,
      wordWrap: (s.wordWrap ? "on" : "off") as "on" | "off",
      minimap: { enabled: s.minimap },
      lineNumbers: (s.lineNumbers ? "on" : "off") as "on" | "off",
      stickyScroll: { enabled: s.stickyScroll },
    };
  }

  /** The editor theme; cursor, selection and class names follow the accent color. */
  function defineTheme(m: typeof Monaco) {
    const accent = (ACCENTS[settings.value.accent] ?? ACCENTS.blue).color;
    m.editor.defineTheme("manimpro", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "5f636d", fontStyle: "italic" },
        { token: "keyword", foreground: "c792ea" },
        { token: "string", foreground: "a5d6a7" },
        { token: "number", foreground: "f8c37a" },
        { token: "type.identifier", foreground: accent.slice(1) },
      ],
      colors: {
        "editor.background": "#161618",
        "editor.foreground": "#e4e5e9",
        "editorLineNumber.foreground": "#4a4d56",
        "editorLineNumber.activeForeground": "#9599a3",
        "editor.lineHighlightBackground": "#1d1d20",
        "editor.lineHighlightBorder": "#00000000",
        "editor.selectionBackground": accent + "33",
        "editorCursor.foreground": accent,
        "editorIndentGuide.background1": "#2a2c33",
        "editorWidget.background": "#1d1d20",
        "editorWidget.border": "#323236",
        "editorSuggestWidget.selectedBackground": "#262629",
        "scrollbarSlider.background": "#2a2c3388",
      },
    });
  }

  const bumpFont = (d: number) =>
    settings.set("fontSize", d === 0 ? 13.5 : Math.min(28, Math.max(9, settings.value.fontSize + d)));

  let host: HTMLDivElement;
  let monaco: typeof Monaco | undefined = $state();
  let editor: Monaco.editor.IStandaloneCodeEditor | undefined = $state();
  let applying = false;

  onMount(() => {
    let disposed = false;
    const disposables: Monaco.IDisposable[] = [];
    (async () => {
      const [m, { default: EditorWorker }] = await Promise.all([
        import("monaco-editor"),
        import("monaco-editor/editor/editor.worker?worker"),
      ]);
      if (disposed) return;
      (self as any).MonacoEnvironment = { getWorker: () => new EditorWorker() };

      defineTheme(m);

      disposables.push(
        m.languages.registerCompletionItemProvider("python", {
          provideCompletionItems(model, position) {
            if (!settings.value.manimCompletions) return { suggestions: [] };
            const word = model.getWordUntilPosition(position);
            const range = {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: word.startColumn,
              endColumn: word.endColumn,
            };
            return {
              suggestions: MANIM_COMPLETIONS.map(([label, kind, detail, insert]) => ({
                label,
                kind: m.languages.CompletionItemKind[kind],
                detail,
                insertText: insert ?? label,
                insertTextRules: insert ? m.languages.CompletionItemInsertTextRule.InsertAsSnippet : undefined,
                range,
              })),
            };
          },
        }),
      );

      const ed = m.editor.create(host, {
        value: studio.code,
        language: "python",
        theme: "manimpro",
        automaticLayout: true,
        ...editorOptions(),
        scrollBeyondLastLine: false,
        padding: { top: 12 },
        renderLineHighlight: "line",
        smoothScrolling: true,
        insertSpaces: true,
        guides: { indentation: true },
        overviewRulerLanes: 0,
        hideCursorInOverviewRuler: true,
        scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
      });
      ed.onDidChangeModelContent(() => {
        if (!applying) studio.codeChanged(ed.getValue());
      });
      ed.onDidChangeCursorPosition((e) => (studio.cursorLine = e.position.lineNumber));
      ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.KeyS, async () => {
        await studio.save();
        if (studio.autoRender) studio.renderCurrent();
      });
      ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Enter, () => studio.renderCurrent());
      ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Equal, () => bumpFont(1));
      ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.NumpadAdd, () => bumpFont(1));
      ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Minus, () => bumpFont(-1));
      ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.NumpadSubtract, () => bumpFont(-1));
      ed.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Digit0, () => bumpFont(0));
      monaco = m;
      editor = ed;
    })();
    return () => {
      disposed = true;
      disposables.forEach((d) => d.dispose());
      editor?.dispose();
    };
  });

  // Accent changes recolor the editor too.
  $effect(() => {
    settings.value.accent;
    if (monaco) {
      defineTheme(monaco);
      monaco.editor.setTheme("manimpro");
    }
  });

  // Settings change live.
  $effect(() => {
    const opts = editorOptions();
    editor?.updateOptions(opts);
  });

  // Load files opened from outside the editor.
  $effect(() => {
    studio.docVersion;
    if (!editor) return;
    const text = studio.code;
    if (editor.getValue() === text) return;
    applying = true;
    editor.setValue(text);
    applying = false;
    editor.setScrollTop(0);
  });

  // Error squiggles from syntax checks and render failures.
  $effect(() => {
    if (!monaco || !editor) return;
    const model = editor.getModel();
    if (!model) return;
    const marks: Monaco.editor.IMarkerData[] = [];
    const push = (line: number, message: string) =>
      marks.push({
        severity: monaco!.MarkerSeverity.Error,
        message,
        startLineNumber: line,
        endLineNumber: line,
        startColumn: model.getLineFirstNonWhitespaceColumn(line) || 1,
        endColumn: model.getLineMaxColumn(line),
      });
    if (studio.syntaxError) push(studio.syntaxError.line, studio.syntaxError.message);
    const err = studio.error;
    if (err?.line && err.file === studio.activeFile && err.line <= model.getLineCount()) push(err.line, err.message);
    monaco.editor.setModelMarkers(model, "manim", marks);
  });

  $effect(() => {
    const r = studio.reveal;
    if (!r || !editor) return;
    editor.revealLineInCenter(r.line);
    editor.setPosition({ lineNumber: r.line, column: 1 });
    editor.focus();
  });
</script>

<section class="editor">
  <div class="host" bind:this={host}></div>
  {#if !editor || studio.loadingFile || (studio.dir && !studio.activeFile && studio.files.length)}
    <!-- Placeholder lines while Monaco starts or a file loads. -->
    <div class="skeleton" aria-busy="true" aria-label="Loading code">
      {#each [38, 0, 0, 52, 66, 44, 72, 58, 0, 61, 47, 69, 35, 0, 56, 74, 41, 63] as w, i (i)}
        <div class="line">
          <span class="ln"></span>
          {#if w}<span class="bar" style:width="{w}%" style:margin-left="{i > 3 && i % 5 !== 0 ? 28 : 0}px"></span>{/if}
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .editor {
    display: flex;
    flex-direction: column;
    min-width: 0;
    height: 100%;
    background: var(--panel);
  }
  .editor {
    position: relative;
  }
  .host {
    flex: 1;
    min-height: 0;
  }
  .skeleton {
    position: absolute;
    inset: 0;
    z-index: 2;
    display: grid;
    align-content: start;
    gap: 9px;
    padding: 16px 18px;
    background: var(--panel);
  }
  .line {
    display: flex;
    align-items: center;
    gap: 22px;
    height: 12px;
  }
  .ln {
    flex: none;
    width: 18px;
    height: 8px;
    border-radius: 4px;
    background: var(--raised);
    opacity: 0.5;
  }
  .bar {
    height: 10px;
    border-radius: 5px;
    background: linear-gradient(90deg, var(--raised) 0%, var(--line-strong) 50%, var(--raised) 100%);
    background-size: 200% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
  }
  @keyframes shimmer {
    to {
      background-position: -200% 0;
    }
  }
</style>
