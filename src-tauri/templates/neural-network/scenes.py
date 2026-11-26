"""How a neural network makes a guess: structure, one neuron, then a full forward pass.

An original ManimPro template. Change LAYERS, LABELS or SEED to explore other networks.
"""
from manim import *
import numpy as np

LAYERS = [6, 5, 5, 3]
LABELS = ["cat", "dog", "bird"]
SEED = 4
LAYER_NAMES = ["input", "hidden", "hidden", "output"]


def build_network():
    layers = VGroup()
    for i, n in enumerate(LAYERS):
        col = VGroup(*[Circle(radius=0.26, stroke_color=BLUE_B, stroke_width=2, fill_color=BLUE_E, fill_opacity=0.2) for _ in range(n)])
        col.arrange(DOWN, buff=0.32).move_to([(i - (len(LAYERS) - 1) / 2) * 2.7 - 0.8, -0.2, 0])
        layers.add(col)
    links = VGroup()
    for a, b in zip(layers[:-1], layers[1:]):
        for x in a:
            for y in b:
                links.add(Line(x.get_right(), y.get_left(), stroke_width=1, color=GREY_D))
    names = VGroup(*[Text(t, font_size=20, color=GREY_B).next_to(layers[i], DOWN, buff=0.3) for i, t in enumerate(LAYER_NAMES)])
    outs = VGroup(*[Text(l, font_size=22).next_to(c, RIGHT, buff=0.3) for l, c in zip(LABELS, layers[-1])])
    return layers, links, names, outs


def activations():
    rng = np.random.default_rng(SEED)
    acts = [rng.uniform(0.05, 1.0, LAYERS[0])]
    for n_in, n_out in zip(LAYERS[:-1], LAYERS[1:]):
        w = rng.normal(0, 1.2, (n_out, n_in))
        acts.append(1 / (1 + np.exp(-(w @ acts[-1] - 0.4))))
    out = np.exp(acts[-1] * 4)
    acts[-1] = out / out.sum()
    return acts


class Structure(Scene):
    """Scene 1: layers of neurons, every one connected to the next layer."""

    def construct(self):
        title = Text("How a neural network makes a guess", font_size=40, weight=BOLD).to_edge(UP)
        self.play(Write(title))
        layers, links, names, outs = build_network()
        self.play(LaggedStart(*[LaggedStart(*[GrowFromCenter(c) for c in col], lag_ratio=0.08) for col in layers], lag_ratio=0.25))
        self.play(FadeIn(names, shift=UP * 0.1))
        self.play(Create(links), run_time=2)
        self.play(FadeIn(outs, shift=LEFT * 0.2))
        n_weights = sum(a * b for a, b in zip(LAYERS[:-1], LAYERS[1:]))
        note = Text(f"{n_weights} connections, each with its own weight", font_size=26, color=YELLOW_B).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.play(LaggedStart(*[l.animate(rate_func=there_and_back).set_stroke(YELLOW, 2.5) for l in links], lag_ratio=0.01), run_time=2)
        self.wait(1.5)


class OneNeuron(Scene):
    """Scene 2: a neuron adds up weighted inputs, then squashes the total."""

    def construct(self):
        title = Text("Inside one neuron", font_size=38, weight=BOLD).to_edge(UP)
        self.play(Write(title))
        xs = [0.9, 0.2, 0.6]
        ws = [1.5, -2.0, 0.8]
        b = -0.3
        inputs = VGroup(*[Circle(radius=0.32, color=BLUE_B, fill_opacity=x) for x in xs]).arrange(DOWN, buff=0.7).shift(LEFT * 5)
        in_labels = VGroup(*[Text(f"{x:.1f}", font_size=22).move_to(c) for x, c in zip(xs, inputs)])
        neuron = Circle(radius=0.6, color=YELLOW, stroke_width=4).shift(LEFT * 1.2)
        arrows = VGroup(*[Arrow(c.get_right(), neuron.get_left(), buff=0.1, stroke_width=3 + 2 * abs(w), color=GREEN_C if w > 0 else RED_C)
                          for c, w in zip(inputs, ws)])
        w_labels = VGroup(*[Text(f"w = {w:+.1f}", font_size=20, color=a.get_color()).next_to(a.point_from_proportion(0.3), UP, buff=0.1)
                            for w, a in zip(ws, arrows)])
        self.play(LaggedStart(*[FadeIn(VGroup(c, l)) for c, l in zip(inputs, in_labels)], lag_ratio=0.2))
        self.play(GrowFromCenter(neuron), LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.2))
        self.play(FadeIn(w_labels))

        total = sum(x * w for x, w in zip(xs, ws)) + b
        terms = " + ".join(f"({w:+.1f})({x:.1f})" for x, w in zip(xs, ws))
        sum_text = Text(f"{terms} {b:+.1f} = {total:.2f}", font_size=24).to_edge(DOWN, buff=1.3)
        self.play(Write(sum_text), Indicate(neuron, color=YELLOW))

        axes = Axes(x_range=[-4, 4, 2], y_range=[0, 1, 0.5], x_length=4.2, y_length=2.4, tips=False,
                    axis_config={"color": GREY_B, "include_numbers": False}).shift(RIGHT * 3.6 + UP * 0.2)
        sigmoid = axes.plot(lambda t: 1 / (1 + np.exp(-t)), color=YELLOW)
        cap = Text("squash to 0…1", font_size=22, color=GREY_B).next_to(axes, UP, buff=0.2)
        self.play(Create(axes), Create(sigmoid), FadeIn(cap))
        out = 1 / (1 + np.exp(-total))
        dot = Dot(axes.c2p(total, out), color=GREEN_C, radius=0.09)
        guide = axes.get_vertical_line(axes.c2p(total, out), color=GREY_B)
        self.play(Create(guide), FadeIn(dot, scale=2))
        result = Text(f"output = {out:.2f}", font_size=28, color=GREEN_C).next_to(axes, DOWN, buff=0.3)
        self.play(Write(result), neuron.animate.set_fill(YELLOW, opacity=out))
        self.wait(2)


class ForwardPass(Scene):
    """Scene 3: activations light up layer by layer until the output picks a label."""

    def construct(self):
        layers, links, names, outs = build_network()
        self.add(layers, links, names, outs)
        acts = activations()
        title = Text("A forward pass", font_size=38, weight=BOLD).to_edge(UP)
        self.play(Write(title))
        self.play(*[c.animate.set_fill(WHITE, opacity=float(a)) for c, a in zip(layers[0], acts[0])], run_time=1)
        k = 0
        for li in range(1, len(LAYERS)):
            n = LAYERS[li - 1] * LAYERS[li]
            group = links[k:k + n]
            k += n
            flashes = [ShowPassingFlash(l.copy().set_stroke(YELLOW, 3), time_width=0.5) for l in group]
            self.play(*flashes, run_time=0.9)
            color = GREEN_C if li == len(LAYERS) - 1 else WHITE
            self.play(*[c.animate.set_fill(color, opacity=float(a)) for c, a in zip(layers[li], acts[li])], run_time=0.6)

        bars = VGroup()
        x0 = max(o.get_right()[0] for o in outs) + 0.25
        for p, label in zip(acts[-1], outs):
            bar = Rectangle(width=max(0.05, 1.4 * p), height=0.28, fill_color=GREEN_C, fill_opacity=0.8, stroke_width=0)
            bar.move_to([x0, label.get_y(), 0], aligned_edge=LEFT)
            pct = Text(f"{p:.0%}", font_size=20).next_to(bar, RIGHT, buff=0.12)
            bars.add(VGroup(bar, pct))
        self.play(LaggedStart(*[GrowFromEdge(b[0], LEFT) for b in bars], lag_ratio=0.2), FadeIn(VGroup(*[b[1] for b in bars])))
        best = int(np.argmax(acts[-1]))
        guess = Text(f"Best guess: {LABELS[best]}", font_size=32, color=GREEN_C).to_edge(DOWN, buff=0.3)
        self.play(Write(guess), Circumscribe(VGroup(layers[-1][best], outs[best]), color=GREEN_C))
        self.wait(2)
