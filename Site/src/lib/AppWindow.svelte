<script lang="ts">
  // A drawing of the ManimPro editor, playing a real template render in the preview.
  const code = [
    [["k", "from"], ["t", " manim "], ["k", "import"], ["t", " *"]],
    [],
    [["k", "class"], ["c", " RiemannSums"], ["t", "(Scene):"]],
    [["t", "    "], ["k", "def"], ["f", " construct"], ["t", "(self):"]],
    [["t", "        axes = "], ["c", "Axes"], ["t", "(x_range=[0, 6], y_range=[0, 4])"]],
    [["t", "        graph = axes."], ["f", "plot"], ["t", "("], ["k", "lambda"], ["t", " x: 0.3 * x**2 + 1)"]],
    [["t", "        self."], ["f", "play"], ["t", "("], ["c", "Create"], ["t", "(axes), "], ["c", "Create"], ["t", "(graph))"]],
    [],
    [["t", "        "], ["k", "for"], ["t", " n "], ["k", "in"], ["t", " [4, 8, 16, 32]:"]],
    [["t", "            rects = axes."], ["f", "get_riemann_rectangles"], ["t", "("]],
    [["t", "                graph, x_range=[1, 5], dx=4 / n)"]],
    [["t", "            self."], ["f", "play"], ["t", "("], ["c", "Transform"], ["t", "(area, rects))"]],
    [],
    [["t", "        self."], ["f", "play"], ["t", "("], ["c", "Write"], ["t", "(label))"]],
  ];
  const files = ["intro.py", "riemann.py", "outro.py"];
  const scenes = ["Question", "RiemannSums", "AreaGrows"];
</script>

<div class="window" aria-label="The ManimPro editor" role="img">
  <div class="bar">
    <img src="/logo.svg" alt="" width="16" height="16" />
    <span class="title">Area under a curve</span>
    <span class="pill">Preview 480p</span>
    <span class="pill">Frame 16:9</span>
    <span class="spacer"></span>
    <span class="btn">Render</span>
    <span class="btn solid">Export</span>
  </div>
  <div class="body">
    <aside class="side">
      <div class="tabs"><span class="on">Project</span><span>Chats</span></div>
      <div class="label">Files</div>
      {#each files as f, i (f)}<div class="file" class:on={i === 1}>{f}</div>{/each}
      <div class="label">Scenes</div>
      <div class="thumbs">
        {#each scenes as s (s)}<div class="thumb"><span>{s}</span></div>{/each}
      </div>
    </aside>
    <section class="code">
      <div class="tabs"><span class="on">riemann.py</span><span>Assistant</span></div>
      <pre>{#each code as line, i (i)}<span class="ln">{i + 1}</span>{#each line as [k, t], j (j)}<span class={k}>{t}</span>{/each}
{/each}</pre>
    </section>
    <section class="view">
      <div class="tabs"><span class="on">Scene</span><span>Timeline</span></div>
      <div class="stage">
        <video src="/templates/calculus-area.mp4" poster="/templates/calculus-area.jpg" autoplay muted loop playsinline aria-hidden="true"></video>
      </div>
    </section>
  </div>
  <div class="timeline">
    <div class="track"><span class="tn">V1</span><span class="clip" style="--w: 26%">Question</span><span class="clip" style="--w: 38%">RiemannSums</span><span class="clip" style="--w: 30%">AreaGrows</span></div>
    <div class="track"><span class="tn">A1</span><span class="wave" style="--w: 64%"></span><span class="wave dim" style="--w: 30%"></span></div>
    <div class="track"><span class="tn">CC</span><span class="cc" style="--w: 20%"></span><span class="cc" style="--w: 24%"></span><span class="cc" style="--w: 18%"></span></div>
    <span class="head" aria-hidden="true"></span>
  </div>
</div>

<style>
  .window {
    border: 1px solid #262626;
    border-radius: 14px;
    background: #000;
    overflow: hidden;
    font-family: "Geist Variable", system-ui, sans-serif;
    font-size: 11px;
    color: #a3a3a3;
    box-shadow: 0 40px 120px -40px rgb(255 255 255 / 0.08);
  }
  .bar {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 38px;
    padding: 0 12px;
    border-bottom: 1px solid #1c1c1c;
  }
  .title {
    color: #fff;
    font-weight: 600;
  }
  .pill {
    padding: 3px 8px;
    border-radius: 7px;
    background: #141414;
  }
  .spacer {
    flex: 1;
  }
  .btn {
    padding: 4px 10px;
    border-radius: 7px;
    border: 1px solid #2a2a2a;
    color: #e5e5e5;
  }
  .btn.solid {
    background: #fff;
    border-color: #fff;
    color: #000;
    font-weight: 600;
  }
  .body {
    display: grid;
    grid-template-columns: 0.75fr 1.5fr 1.6fr;
    gap: 6px;
    padding: 6px;
    min-height: 300px;
  }
  .side,
  .code,
  .view {
    border: 1px solid #1c1c1c;
    border-radius: 10px;
    background: #070707;
    overflow: hidden;
    min-width: 0;
  }
  .tabs {
    display: flex;
    gap: 4px;
    padding: 6px;
    border-bottom: 1px solid #161616;
  }
  .tabs span {
    padding: 3px 8px;
    border-radius: 6px;
  }
  .tabs .on {
    background: #171717;
    color: #fff;
  }
  .label {
    padding: 10px 10px 4px;
    color: #6b6b6b;
  }
  .file {
    margin: 0 6px;
    padding: 4px 8px;
    border-radius: 6px;
  }
  .file.on {
    background: #171717;
    color: #fff;
  }
  .thumbs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    padding: 0 8px 8px;
  }
  .thumb {
    aspect-ratio: 16 / 9;
    font-size: 9px;
    overflow: hidden;
    border-radius: 6px;
    background: #111;
    border: 1px solid #1f1f1f;
    display: flex;
    align-items: flex-end;
    padding: 4px 6px;
  }
  pre {
    margin: 0;
    padding: 10px 12px;
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 10.5px;
    line-height: 1.75;
    white-space: pre;
    overflow: hidden;
    color: #bdbdbd;
  }
  .ln {
    display: inline-block;
    width: 22px;
    color: #3d3d3d;
  }
  .k {
    color: #fff;
    font-weight: 600;
  }
  .c {
    color: #fff;
  }
  .f {
    color: #d4d4d4;
    text-decoration: underline;
    text-decoration-color: #3a3a3a;
    text-underline-offset: 3px;
  }
  .stage {
    display: grid;
    place-items: center;
    padding: 12px;
    height: calc(100% - 34px);
  }
  video {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #000;
    border: 1px solid #1c1c1c;
    filter: grayscale(1) contrast(1.05);
  }
  .timeline {
    position: relative;
    display: grid;
    gap: 5px;
    margin: 0 6px 6px;
    padding: 8px;
    border: 1px solid #1c1c1c;
    border-radius: 10px;
    background: #070707;
  }
  .track {
    display: flex;
    gap: 4px;
    align-items: center;
    height: 22px;
  }
  .tn {
    width: 28px;
    color: #5a5a5a;
  }
  .clip,
  .wave,
  .cc {
    width: var(--w);
    height: 100%;
    border-radius: 5px;
  }
  .clip {
    display: flex;
    align-items: center;
    padding: 0 8px;
    background: #1d1d1d;
    border: 1px solid #333;
    color: #e5e5e5;
    overflow: hidden;
    white-space: nowrap;
  }
  .wave {
    background: repeating-linear-gradient(90deg, #3a3a3a 0 2px, transparent 2px 4px);
    mask: linear-gradient(transparent 20%, #000 20% 80%, transparent 80%);
  }
  .wave.dim {
    opacity: 0.5;
  }
  .cc {
    height: 60%;
    background: #262626;
  }
  .cc + .cc {
    margin-left: 4%;
  }
  .head {
    position: absolute;
    top: 4px;
    bottom: 4px;
    left: 38%;
    width: 1px;
    background: #fff;
  }
  @media (max-width: 860px) {
    .body {
      grid-template-columns: 1fr;
    }
    .side,
    .code {
      display: none;
    }
  }
</style>
