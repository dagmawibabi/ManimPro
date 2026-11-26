"""The quadratic formula, derived by completing the square.

An original ManimPro template. Needs LaTeX (MathTex), which ships with ManimPro.
"""
from manim import *


def step(*parts):
    return MathTex(*parts).scale(1.25)


class Problem(Scene):
    """Scene 1: what we want to solve."""

    def construct(self):
        title = Text("Where the quadratic formula comes from", font_size=40, weight=BOLD).to_edge(UP)
        eq = MathTex("a", "x^2", "+", "b", "x", "+", "c", "=", "0").scale(1.6)
        goal = Text("Goal: get x on its own", font_size=28, color=GREY_B).next_to(eq, DOWN, buff=0.6)
        self.play(Write(title))
        self.play(Write(eq))
        self.play(FadeIn(goal, shift=UP * 0.2))
        self.play(Circumscribe(eq[1:5], color=YELLOW))
        self.wait(1.5)


class CompleteSquare(Scene):
    """Scene 2: divide by a, complete the square, take the root."""

    def construct(self):
        steps = [
            (step("a", "x^2", "+", "b", "x", "+", "c", "=", "0"), "Start"),
            (step("x^2", "+", r"\frac{b}{a}", "x", "+", r"\frac{c}{a}", "=", "0"), "Divide everything by a"),
            (step("x^2", "+", r"\frac{b}{a}", "x", "=", r"-\frac{c}{a}"), "Move the constant across"),
            (step("x^2", "+", r"\frac{b}{a}", "x", "+", r"\frac{b^2}{4a^2}", "=", r"\frac{b^2}{4a^2}", r"-\frac{c}{a}"),
             "Add (b/2a)² to both sides"),
            (step(r"\left(x + \frac{b}{2a}\right)^2", "=", r"\frac{b^2 - 4ac}{4a^2}"), "The left side is now a perfect square"),
            (step(r"x + \frac{b}{2a}", "=", r"\pm\frac{\sqrt{b^2 - 4ac}}{2a}"), "Take the square root"),
            (step("x", "=", r"\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}"), "Subtract b/2a"),
        ]
        current, text = steps[0]
        note = Text(text, font_size=28, color=GREY_B).to_edge(DOWN, buff=0.8)
        self.play(Write(current), FadeIn(note))
        for nxt, t in steps[1:]:
            new_note = Text(t, font_size=28, color=GREY_B).to_edge(DOWN, buff=0.8)
            self.play(TransformMatchingTex(current, nxt), FadeTransform(note, new_note), run_time=1.4)
            current, note = nxt, new_note
            self.wait(0.8)
        box = SurroundingRectangle(current, color=YELLOW, buff=0.25, corner_radius=0.1)
        self.play(Create(box))
        self.wait(1.5)


class Example(Scene):
    """Scene 3: plug in numbers and check against the graph."""

    def construct(self):
        title = Text("Try it: 2x² − 4x − 6 = 0", font_size=36, weight=BOLD).to_edge(UP)
        self.play(Write(title))
        calc = VGroup(
            MathTex(r"x = \frac{4 \pm \sqrt{16 + 48}}{4}"),
            MathTex(r"x = \frac{4 \pm 8}{4}"),
            MathTex(r"x = 3 \quad \text{or} \quad x = -1"),
        ).arrange(DOWN, buff=0.45, aligned_edge=LEFT).scale(1.05).to_edge(LEFT, buff=0.8)
        for m in calc:
            self.play(Write(m), run_time=1.1)
        axes = Axes(x_range=[-2, 4, 1], y_range=[-9, 6, 3], x_length=5.2, y_length=4.6, tips=False,
                    axis_config={"color": GREY_B}).to_edge(RIGHT, buff=0.6).shift(DOWN * 0.3)
        graph = axes.plot(lambda x: 2 * x * x - 4 * x - 6, x_range=[-1.6, 3.6], color=BLUE_C)
        self.play(Create(axes), Create(graph), run_time=1.5)
        roots = VGroup(*[Dot(axes.c2p(r, 0), color=YELLOW, radius=0.1) for r in (-1, 3)])
        self.play(LaggedStart(*[FadeIn(d, scale=2.5) for d in roots], lag_ratio=0.3))
        self.play(Indicate(calc[-1], color=YELLOW))
        self.wait(1.5)
