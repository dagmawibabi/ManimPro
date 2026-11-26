<script lang="ts">
  // A small Manim-style scene: axes appear, a curve is drawn, Riemann rectangles
  // fill in under it, then the integral is written. It plays once on load.
  const W = 720;
  const H = 460;
  const O = { x: 70, y: 390 }; // origin
  const SX = 92; // px per unit
  const SY = 78;
  const f = (x: number) => 1.15 + 0.85 * Math.sin(1.05 * x - 0.4) + 0.32 * x;
  const px = (x: number) => O.x + x * SX;
  const py = (y: number) => O.y - y * SY;

  const curve = Array.from({ length: 121 }, (_, i) => {
    const x = (i / 120) * 6.6;
    return `${i ? "L" : "M"}${px(x).toFixed(1)},${py(f(x)).toFixed(1)}`;
  }).join(" ");

  const a = 1;
  const b = 5;
  const n = 16;
  const dx = (b - a) / n;
  const rects = Array.from({ length: n }, (_, i) => {
    const x = a + i * dx;
    const h = f(x + dx / 2);
    return { x: px(x), y: py(h), w: dx * SX, h: h * SY, i };
  });

  const area = `M${px(a)},${py(0)} ` +
    Array.from({ length: 61 }, (_, i) => {
      const x = a + ((b - a) * i) / 60;
      return `L${px(x).toFixed(1)},${py(f(x)).toFixed(1)}`;
    }).join(" ") + ` L${px(b)},${py(0)} Z`;

  const xticks = [1, 2, 3, 4, 5, 6];
  const yticks = [1, 2, 3, 4];
</script>

<svg viewBox="0 0 {W} {H}" role="img" aria-label="An animation: a curve is drawn on axes and the area under it fills in, labelled with its integral.">
  <!-- Background plane, like Manim's NumberPlane -->
  <g class="plane">
    {#each Array(9) as _, i (i)}<line x1={px(i - 0.5)} y1="10" x2={px(i - 0.5)} y2={H - 10} />{/each}
    {#each Array(7) as _, i (i)}<line x1="10" y1={py(i - 0.5)} x2={W - 10} y2={py(i - 0.5)} />{/each}
  </g>

  <g class="axes">
    <line class="draw" style="--len: 640; --d: 0s" x1={O.x - 20} y1={O.y} x2={W - 30} y2={O.y} />
    <line class="draw" style="--len: 390; --d: 0.1s" x1={O.x} y1={O.y + 20} x2={O.x} y2="30" />
    <path class="tip" style="--d: 0.7s" d="M{W - 30},{O.y} l-11,-5 v10 z" />
    <path class="tip" style="--d: 0.7s" d="M{O.x},30 l-5,11 h10 z" />
    {#each xticks as t (t)}
      <line class="tick" style="--d: {0.5 + t * 0.04}s" x1={px(t)} y1={O.y - 6} x2={px(t)} y2={O.y + 6} />
      {#if t !== a && t !== b}<text class="num" style="--d: {0.6 + t * 0.04}s" x={px(t)} y={O.y + 30}>{t}</text>{/if}
    {/each}
    {#each yticks as t (t)}
      <line class="tick" style="--d: {0.5 + t * 0.04}s" x1={O.x - 6} y1={py(t)} x2={O.x + 6} y2={py(t)} />
    {/each}
    <text class="var" style="--d: 0.8s" x={W - 26} y={O.y - 14}>x</text>
    <text class="var" style="--d: 0.8s" x={O.x + 14} y="44">y</text>
  </g>

  <g class="rects">
    {#each rects as r (r.i)}
      <rect style="--d: {2.5 + r.i * 0.06}s" x={r.x} y={r.y} width={r.w} height={r.h} />
    {/each}
  </g>
  <path class="area" d={area} />

  <path class="curve draw" style="--len: 900; --d: 0.9s" d={curve} />

  <g class="bounds">
    <line class="draw" style="--len: {f(a) * SY}; --d: 2.2s" x1={px(a)} y1={O.y} x2={px(a)} y2={py(f(a))} />
    <line class="draw" style="--len: {f(b) * SY}; --d: 2.2s" x1={px(b)} y1={O.y} x2={px(b)} y2={py(f(b))} />
    <text class="num" style="--d: 2.3s" x={px(a)} y={O.y + 30}>a</text>
    <text class="num" style="--d: 2.3s" x={px(b)} y={O.y + 30}>b</text>
  </g>

  <g class="label">
    <text class="int" x={px(2.55)} y={py(4.3)}>∫</text>
    <text class="lim" x={px(2.55) + 26} y={py(4.3) - 34}>b</text>
    <text class="lim" x={px(2.55) + 17} y={py(4.3) + 10}>a</text>
    <text x={px(2.55) + 44} y={py(4.3) - 8}><tspan class="it">f</tspan>(<tspan class="it">x</tspan>)<tspan class="it" dx="8">dx</tspan></text>
  </g>
  <circle class="dot" r="5.5" cx={px(b)} cy={py(f(b))} />
</svg>

<style>
  svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }
  line,
  path {
    vector-effect: non-scaling-stroke;
  }
  .plane line {
    stroke: #fff;
    stroke-opacity: 0.07;
    stroke-width: 1;
  }
  .axes line {
    stroke: #fff;
    stroke-width: 2;
  }
  .tip {
    fill: #fff;
  }
  .num,
  .var {
    fill: #fff;
    font-family: "KaTeX_Main", serif;
    font-size: 20px;
    text-anchor: middle;
  }
  .var {
    font-family: "KaTeX_Math", "KaTeX_Main", serif;
    font-style: italic;
    font-size: 22px;
  }
  .curve {
    fill: none;
    stroke: #fff;
    stroke-width: 3.5;
    stroke-linecap: round;
  }
  .bounds line {
    stroke: #fff;
    stroke-width: 1.5;
    stroke-dasharray: 5 6;
  }
  .rects rect {
    fill: #fff;
    fill-opacity: 0.16;
    stroke: #fff;
    stroke-opacity: 0.55;
    stroke-width: 1;
  }
  .area {
    fill: #fff;
    fill-opacity: 0.2;
  }
  .label text {
    fill: #fff;
    font-family: "KaTeX_Main", serif;
    font-size: 30px;
  }
  .label .int {
    font-size: 46px;
  }
  .label .lim {
    font-size: 17px;
    font-family: "KaTeX_Math", serif;
    font-style: italic;
  }
  .label .it {
    font-family: "KaTeX_Math", serif;
    font-style: italic;
  }
  .dot {
    fill: #fff;
  }

  /* ---- the one orchestrated sequence ---- */
  @media (prefers-reduced-motion: no-preference) {
    .draw {
      stroke-dasharray: var(--len) var(--len);
      stroke-dashoffset: var(--len);
      animation: draw 1.3s cubic-bezier(0.6, 0, 0.3, 1) var(--d) forwards;
    }
    .bounds .draw {
      stroke-dasharray: 5 6;
      stroke-dashoffset: 0;
      animation: none;
      opacity: 0;
      animation: fade 0.5s ease var(--d) forwards;
    }
    .tip,
    .tick,
    .num,
    .var {
      opacity: 0;
      animation: fade 0.5s ease var(--d) forwards;
    }
    .rects rect {
      opacity: 0;
      transform-box: fill-box;
      transform-origin: bottom;
      transform: scaleY(0);
      animation:
        grow 0.55s cubic-bezier(0.3, 0, 0.2, 1) var(--d) forwards,
        merge 0.9s ease 4.3s forwards;
    }
    .area {
      opacity: 0;
      animation: fade 0.9s ease 4.3s forwards;
    }
    .label {
      opacity: 0;
      animation: write 1s ease 4.6s forwards;
    }
    .dot {
      opacity: 0;
      animation: fade 0.4s ease 2.1s forwards;
    }
  }
  @keyframes draw {
    to {
      stroke-dashoffset: 0;
    }
  }
  @keyframes fade {
    to {
      opacity: 1;
    }
  }
  @keyframes grow {
    to {
      opacity: 1;
      transform: scaleY(1);
    }
  }
  @keyframes merge {
    to {
      opacity: 0;
    }
  }
  @keyframes write {
    from {
      opacity: 0;
      filter: blur(6px);
    }
    to {
      opacity: 1;
      filter: blur(0);
    }
  }
</style>
