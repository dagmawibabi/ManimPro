"""Building a square wave out of sine waves.

An original ManimPro template inspired by the topic of 3Blue1Brown's
"But what is a Fourier series?". No LaTeX needed.
"""
from manim import *


def partial_sum(x, terms):
    """First `terms` odd harmonics of a square wave of height 1."""
    return sum(4 / (PI * n) * np.sin(n * x) for n in range(1, 2 * terms, 2))


class AddingSines(Scene):
    """Scene 1: more terms, closer to a square wave."""

    def construct(self):
        axes = Axes(x_range=[-0.2, 4 * PI, PI], y_range=[-1.6, 1.6, 1], x_length=11.5, y_length=4.5, tips=False,
                    axis_config={"color": GREY_C, "stroke_width": 2}).shift(DOWN * 0.4)
        # The target square wave: flat runs at +1 / -1 joined by vertical jumps.
        target = VGroup()
        for i, a in enumerate(np.arange(0, 4 * PI - 0.01, PI)):
            y = 1 if i % 2 == 0 else -1
            target.add(DashedLine(axes.c2p(a, y), axes.c2p(a + PI, y), color=GREY_B, dash_length=0.1))
            if i:
                target.add(DashedLine(axes.c2p(a, -y), axes.c2p(a, y), color=GREY_B, dash_length=0.1))
        title = Text("Adding sine waves", font_size=38).to_edge(UP)

        def wave(terms):
            return axes.plot(lambda x: partial_sum(x, terms), x_range=[0, 4 * PI], color=BLUE_C, stroke_width=4,
                             use_smoothing=False)

        def label(terms):
            harmonics = " + ".join(f"sin({n}x)/{n}" if n > 1 else "sin(x)" for n in range(1, min(2 * terms, 8), 2))
            more = " + …" if terms > 4 else ""
            return VGroup(
                Text(f"{terms} {'term' if terms == 1 else 'terms'}", font_size=30, color=YELLOW),
                Text(harmonics + more, font_size=22, color=GREY_A),
            ).arrange(DOWN, buff=0.15).next_to(title, DOWN, buff=0.3)

        self.play(Write(title), Create(axes))
        self.play(Create(target), run_time=1.5)
        current = wave(1)
        info = label(1)
        self.play(Create(current), FadeIn(info), run_time=1.5)
        self.wait(0.5)
        for terms in [2, 3, 5, 10, 30]:
            self.play(Transform(current, wave(terms)), Transform(info, label(terms)), run_time=1.5)
            self.wait(0.7)
        note = Text("Notice the overshoot at the jumps: it never goes away (Gibbs phenomenon)",
                    font_size=24, color=GREY_B).to_edge(DOWN)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(2)


class RotatingCircles(Scene):
    """Scene 2: each term is a circle; stacked circles draw the wave."""

    def construct(self):
        terms = 5
        radii = [4 / (PI * n) for n in range(1, 2 * terms, 2)]
        freqs = list(range(1, 2 * terms, 2))
        scale = 1.1
        center = LEFT * 4.3
        wave_start = -1.2
        t = ValueTracker(0)

        def joints():
            p, pts = center.copy(), [center.copy()]
            for r, k in zip(radii, freqs):
                a = k * t.get_value()
                p = p + scale * r * np.array([np.cos(a), np.sin(a), 0])
                pts.append(p)
            return pts

        def circles():
            pts = joints()
            g = VGroup(*[
                Circle(radius=scale * r, stroke_width=1.5, stroke_color=GREY_C).move_to(c)
                for r, c in zip(radii, pts[:-1])
            ])
            g.add(VMobject(stroke_color=WHITE, stroke_width=2).set_points_as_corners(pts))
            return g

        def wave():
            history = np.linspace(max(0, t.get_value() - 4.5 * PI / 1), t.get_value(), 300)
            pts = []
            for s in history:
                y = center[1] + scale * sum(r * np.sin(k * s) for r, k in zip(radii, freqs))
                pts.append([wave_start + (t.get_value() - s) * 0.42, y, 0])
            return VMobject(stroke_color=BLUE_C, stroke_width=4).set_points_as_corners(pts) if len(pts) > 1 else VMobject()

        tip = always_redraw(lambda: Dot(joints()[-1], radius=0.06, color=YELLOW))
        link = always_redraw(lambda: DashedLine(joints()[-1], [wave_start, joints()[-1][1], 0], color=YELLOW, stroke_width=2))
        title = Text("Five spinning circles, five sine waves", font_size=34).to_edge(UP)
        self.add(always_redraw(circles), always_redraw(wave), link, tip)
        self.play(Write(title))
        self.play(t.animate.set_value(4 * PI), run_time=12, rate_func=linear)
        self.wait()
