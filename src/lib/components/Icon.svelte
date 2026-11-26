<script lang="ts" module>
  // Small hand-tuned 16px icon set (stroke icons, 1.5px) so the app ships no icon font.
  const paths: Record<string, string> = {
    play: "M5 3.5v9l7.5-4.5z",
    pause: "M5 3.5v9M11 3.5v9",
    stop: "M4 4h8v8H4z",
    render: "M3 8a5 5 0 1 0 1.5-3.6M3 3v3h3",
    plus: "M8 3v10M3 8h10",
    folder: "M2 4.5h4l1.5 1.5H14v6.5H2z",
    file: "M4 2h5l3 3v9H4zM9 2v3h3",
    scissors: "M5.5 5.5 13 13M5.5 10.5 13 3M4 6.5a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2zM4 12.7a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2z",
    trash: "M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.7 8.5h5.6l.7-8.5",
    export: "M8 10V2.5M5 5.5l3-3 3 3M3 9.5v4h10v-4",
    zoomIn: "M7 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM13.5 13.5 10 10M5 7h4M7 5v4",
    zoomOut: "M7 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM13.5 13.5 10 10M5 7h4",
    toStart: "M4 3.5v9M12 3.5v9L6 8z",
    stepBack: "M11 3.5v9L5 8zM4.5 3.5v9",
    stepFwd: "M5 3.5v9L11 8zM11.5 3.5v9",
    bolt: "M9 1.5 3.5 9H8l-1 5.5L12.5 7H8z",
    terminal: "M2.5 3h11v10h-11zM5 6.5l2 1.5-2 1.5M8.5 10H11",
    close: "M4 4l8 8M12 4l-8 8",
    alert: "M8 2 14 13H2zM8 6.5v3M8 11.2v.1",
    check: "M3.5 8.5 6.5 11.5 12.5 5",
    film: "M2.5 3h11v10h-11zM5 3v10M11 3v10M2.5 6h2.5M2.5 10h2.5M11 6h2.5M11 10h2.5",
    reveal: "M2 4.5h4l1.5 1.5H14v6.5H2zM8 8v3M6.5 9.5 8 8l1.5 1.5",
    send: "M8 13V3.5M4 7l4-4 4 4",
    sparkle: "M8 1.5 9.4 6.6 14.5 8 9.4 9.4 8 14.5 6.6 9.4 1.5 8 6.6 6.6z",
    home: "M2.5 7.5 8 3l5.5 4.5V13h-3.5V9.5h-4V13H2.5z",
    music: "M6 12V3.5l7-1.5v8.5M6 12a1.75 1.75 0 1 1-3.5 0A1.75 1.75 0 0 1 6 12zM13 10.5a1.75 1.75 0 1 1-3.5 0 1.75 1.75 0 0 1 3.5 0z",
    volume: "M2.5 6h2.5L8.5 3v10L5 10H2.5zM11 5.5a3.5 3.5 0 0 1 0 5M12.8 3.8a6 6 0 0 1 0 8.4",
    mute: "M2.5 6h2.5L8.5 3v10L5 10H2.5zM11 6l3.5 4M14.5 6 11 10",
    refresh: "M13 8a5 5 0 1 1-1.5-3.6M13 3v3h-3",
    search: "M7 2.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9zM14 14l-3.5-3.5",
    sigma: "M12 3H4l4.5 5L4 13h8",
    more: "M3.5 8h.01M8 8h.01M12.5 8h.01",
    copy: "M5.5 5.5h7v7h-7zM3.5 10.5v-7h7",
    trimStart: "M5 3v10M8 8h5.5M10.5 5.5 8 8l2.5 2.5",
    trimEnd: "M11 3v10M8 8H2.5M5.5 5.5 8 8l-2.5 2.5",
    grid: "M2.5 2.5h4.5V7H2.5zM9 2.5h4.5V7H9zM2.5 9h4.5v4.5H2.5zM9 9h4.5v4.5H9z",
    list: "M5.5 4h8M5.5 8h8M5.5 12h8M2.5 4h.01M2.5 8h.01M2.5 12h.01",
    mic: "M8 1.8a2 2 0 0 0-2 2v4a2 2 0 0 0 4 0v-4a2 2 0 0 0-2-2zM4 7.5a4 4 0 0 0 8 0M8 11.5v2.7M5.8 14.2h4.4",
    folderPlus: "M2 4.5h4l1.5 1.5H14v6.5H2zM8 7.8v3.4M6.3 9.5h3.4",
    filePlus: "M4 2h5l3 3v9H4zM9 2v3h3M8 7.5v4M6 9.5h4",
    pencil: "M10.5 2.8l2.7 2.7-7.4 7.4H3.1v-2.7z",
    chevron: "M6 4l4 4-4 4",
    paperclip: "M13 7.2 7.6 12.6a3.2 3.2 0 0 1-4.5-4.5L8.9 2.3a2.1 2.1 0 0 1 3 3L6.2 11a1.1 1.1 0 0 1-1.6-1.6l5-5",
    image: "M2.5 3h11v10h-11zM2.5 11l3.5-3.5 3 3 2-2 2.5 2.5M10 6.2a.01.01 0 1 0 0 .02",
    pauseFill: "M4.5 3h2.5v10H4.5zM9 3h2.5v10H9z",
    user: "M8 8.2a2.9 2.9 0 1 0 0-5.8 2.9 2.9 0 0 0 0 5.8zM2.8 13.8c.6-2.5 2.7-3.9 5.2-3.9s4.6 1.4 5.2 3.9",
    info: "M8 1.8a6.2 6.2 0 1 0 0 12.4A6.2 6.2 0 0 0 8 1.8zM8 7.2v4M8 4.9v.1",
    expand: "M2.5 6V2.5H6M10 2.5h3.5V6M13.5 10v3.5H10M6 13.5H2.5V10",
    undo: "M5.5 4 2.5 7l3 3M2.5 7h6.5a4 4 0 0 1 0 8H7",
    redo: "M10.5 4l3 3-3 3M13.5 7H7a4 4 0 0 0 0 8h2",
    captions: "M2 3.5h12v9H2zM4.5 9.5h3M9 9.5h2.5M4.5 7h7",
    link: "M9.5 2.5h4v4M13.5 2.5 7.5 8.5M11.5 9.5v4h-9v-9h4",
    book: "M2.5 3h4.2a1.8 1.8 0 0 1 1.3.6 1.8 1.8 0 0 1 1.3-.6h4.2v9.5H9.3a1.3 1.3 0 0 0-1.3 1.3 1.3 1.3 0 0 0-1.3-1.3H2.5zM8 3.6v10.2",
    shrink: "M6 2.5V6H2.5M13.5 6H10V2.5M10 13.5V10h3.5M2.5 10H6v3.5",
    settings: "M6.9 1.6h2.2l.4 1.7c.4.15.8.35 1.15.6l1.65-.55 1.1 1.9-1.3 1.15c.05.4.05.8 0 1.2l1.3 1.15-1.1 1.9-1.65-.55c-.35.25-.75.45-1.15.6l-.4 1.7H6.9l-.4-1.7c-.4-.15-.8-.35-1.15-.6l-1.65.55-1.1-1.9 1.3-1.15a4.6 4.6 0 0 1 0-1.2L2.6 5.25l1.1-1.9 1.65.55c.35-.25.75-.45 1.15-.6zM8 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z",
  };
  const filled = new Set(["play", "stop", "toStart", "stepBack", "stepFwd", "bolt", "sparkle", "pauseFill"]);
</script>

<script lang="ts">
  let { name, size = 16 }: { name: keyof typeof paths | string; size?: number } = $props();
  const isFilled = $derived(filled.has(name));
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 16 16"
  fill={isFilled ? "currentColor" : "none"}
  stroke="currentColor"
  stroke-width={isFilled ? 0.6 : 1.5}
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"><path d={paths[name]} /></svg>
