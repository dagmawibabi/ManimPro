"""Area under a curve, from rectangles to the integral.

An original ManimPro template inspired by the topic of 3Blue1Brown's
"Essence of Calculus" series. No LaTeX needed: formulas use Pango markup.
"""
from manim import *

CURVE = BLUE_C
AREA = TEAL_D


def f(x):
    return 0.12 * x**2 + 0.25 * x + 0.6


def make_axes():
    axes = Axes(x_range=[0, 6, 1], y_range=[0, 6, 1], x_length=8, y_length=5, tips=False,
                axis_config={"color": GREY_B, "stroke_width": 2})
    axes.to_edge(DOWN, buff=0.6)
    labels = VGroup(
        Text("x", font_size=24, color=GREY_B).next_to(axes.x_axis, RIGHT, buff=0.15),
        Text("f(x)", font_size=24, color=GREY_B).next_to(axes.y_axis, UP, buff=0.15),
    )
    return axes, labels


class Question(Scene):
    """Scene 1: what is the area under this curve?"""

    def construct(self):
        axes, labels = make_axes()
        graph = axes.plot(f, x_range=[0, 5.5], color=CURVE, stroke_width=4)
        area = axes.get_area(graph, x_range=(1, 5), color=AREA, opacity=0.45)
        title = Text("How big is this area?", font_size=40).to_edge(UP)
        bounds = VGroup(
            DashedLine(axes.c2p(1, 0), axes.c2p(1, f(1)), color=GREY_B),
            DashedLine(axes.c2p(5, 0), axes.c2p(5, f(5)), color=GREY_B),
        )
        ab = VGroup(
            Text("a", font_size=26).next_to(axes.c2p(1, 0), DOWN),
            Text("b", font_size=26).next_to(axes.c2p(5, 0), DOWN),
        )
        self.play(Create(axes), FadeIn(labels), run_time=1.5)
        self.play(Create(graph), run_time=1.5)
        self.play(Create(bounds), FadeIn(ab))
        self.play(FadeIn(area), Write(title))
        self.wait(1.5)


class RiemannSums(Scene):
    """Scene 2: thinner rectangles get closer to the true area."""

    def construct(self):
        axes, labels = make_axes()
        graph = axes.plot(f, x_range=[0, 5.5], color=CURVE, stroke_width=4)
        self.add(axes, labels, graph)

        def rects(n):
            return axes.get_riemann_rectangles(
                graph, x_range=[1, 5], dx=4 / n, input_sample_type="left",
                stroke_width=1 if n < 40 else 0, stroke_color=BLACK, fill_opacity=0.75,
                color=(BLUE_D, GREEN_C),
            )

        def estimate(n):
            dx = 4 / n
            return sum(f(1 + i * dx) * dx for i in range(n))

        exact = (0.04 * 125 + 0.125 * 25 + 0.6 * 5) - (0.04 + 0.125 + 0.6)
        title = Text("Approximate it with rectangles", font_size=36).to_edge(UP)
        self.play(Write(title))

        current = rects(4)
        info = self.caption(4, estimate(4))
        self.play(Create(current, lag_ratio=0.1), FadeIn(info))
        for n in [8, 16, 32, 96]:
            new = rects(n)
            new_info = self.caption(n, estimate(n))
            self.play(Transform(current, new), Transform(info, new_info), run_time=1.4)
            self.wait(0.6)
        exact_text = Text(f"exact area = {exact:.3f}", font_size=28, color=YELLOW).next_to(info, DOWN, aligned_edge=LEFT, buff=0.25)
        self.play(FadeIn(exact_text, shift=UP * 0.2))
        self.wait(1.5)

    def caption(self, n, value):
        return VGroup(
            Text(f"{n} rectangles", font_size=28),
            Text(f"area ≈ {value:.3f}", font_size=28, color=GREY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_corner(UR, buff=0.6).shift(DOWN * 0.9 + LEFT * 0.6)


class AreaGrows(Scene):
    """Scene 3: the area function A(x) grows at the rate f(x)."""

    def construct(self):
        axes, labels = make_axes()
        axes.scale(0.8).to_edge(LEFT, buff=0.6).to_edge(DOWN, buff=0.8)
        labels = VGroup(
            Text("f(x)", font_size=22, color=CURVE).next_to(axes.y_axis, UP, buff=0.1),
        )
        graph = axes.plot(f, x_range=[0, 5.5], color=CURVE, stroke_width=4)

        right = Axes(x_range=[0, 6, 1], y_range=[0, 16, 4], x_length=5, y_length=4, tips=False,
                     axis_config={"color": GREY_B, "stroke_width": 2}).to_edge(RIGHT, buff=0.6).to_edge(DOWN, buff=0.8)
        right_label = Text("A(x) = area so far", font_size=22, color=YELLOW).next_to(right.y_axis, UP, buff=0.1)

        x = ValueTracker(0.01)

        def area_to(t):
            return 0.04 * t**3 + 0.125 * t**2 + 0.6 * t

        shaded = always_redraw(lambda: axes.get_area(graph, x_range=(0, x.get_value()), color=AREA, opacity=0.5))
        edge = always_redraw(lambda: Line(axes.c2p(x.get_value(), 0), axes.c2p(x.get_value(), f(x.get_value())), color=YELLOW, stroke_width=4))
        dot = always_redraw(lambda: Dot(right.c2p(x.get_value(), area_to(x.get_value())), color=YELLOW))
        trace = TracedPath(dot.get_center, stroke_color=YELLOW, stroke_width=4)
        note = MarkupText("Area grows fastest where the curve is <span fgcolor='#58C4DD'>tallest</span>",
                          font_size=28).to_edge(UP)

        self.play(Create(axes), Create(right), FadeIn(labels), FadeIn(right_label))
        self.play(Create(graph))
        self.add(shaded, edge, trace, dot)
        self.play(FadeIn(note))
        self.play(x.animate.set_value(5.5), run_time=6, rate_func=linear)
        self.wait(0.5)

        rule = MarkupText("dA/dx = f(x)", font_size=38, color=YELLOW)
        box = SurroundingRectangle(rule, color=YELLOW, buff=0.25, corner_radius=0.15)
        group = VGroup(rule, box).next_to(note, DOWN, buff=0.45).add_background_rectangle(opacity=0.85, buff=0.2)
        self.play(FadeIn(group, scale=0.9))
        self.wait(2)
