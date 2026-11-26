"""Polynomials that hug sin(x) more and more closely.

An original ManimPro template inspired by the topic of 3Blue1Brown's
"Taylor series" (Essence of Calculus). No LaTeX needed.
"""
from math import factorial

from manim import *

SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def taylor_sin(x, degree):
    return sum((-1) ** k * x ** (2 * k + 1) / factorial(2 * k + 1) for k in range(degree // 2 + 1))


def formula(degree):
    parts = []
    for k in range(degree // 2 + 1):
        n = 2 * k + 1
        term = "x" if n == 1 else f"x{str(n).translate(SUP)}/{n}!"
        parts.append(("" if k == 0 else (" − " if k % 2 else " + ")) + term)
    return "sin(x) ≈ " + "".join(parts)


class Idea(Scene):
    """Scene 1: match the value, then the slope, then the curvature at x = 0."""

    def construct(self):
        lines = VGroup(
            Text("Idea: build a polynomial that copies sin(x) near 0", font_size=32),
            Text("match its value", font_size=28, color=BLUE_B),
            Text("then its slope", font_size=28, color=TEAL_B),
            Text("then how the slope changes, and so on", font_size=28, color=GREEN_B),
        ).arrange(DOWN, buff=0.45)
        self.play(Write(lines[0]), run_time=1.5)
        for line in lines[1:]:
            self.play(FadeIn(line, shift=RIGHT * 0.3))
            self.wait(0.4)
        self.wait(1.5)


class Approximations(Scene):
    """Scene 2: each extra term widens the region where the match is good."""

    def construct(self):
        axes = Axes(x_range=[-7, 7, 1], y_range=[-2.5, 2.5, 1], x_length=12.5, y_length=5, tips=False,
                    axis_config={"color": GREY_C, "stroke_width": 2}).shift(DOWN * 0.6)
        sine = axes.plot(np.sin, x_range=[-7, 7], color=WHITE, stroke_width=3)
        sine_label = Text("sin(x)", font_size=26).next_to(axes.c2p(7, np.sin(7)), UP + LEFT * 0.2)
        self.play(Create(axes), run_time=1.2)
        self.play(Create(sine), FadeIn(sine_label), run_time=1.5)

        colors = [BLUE_C, TEAL_C, GREEN_C, YELLOW_C, ORANGE, RED_C]
        degrees = [1, 3, 5, 7, 9, 11]

        def poly(d, c):
            # Draw only where the polynomial stays on the chart, so it leaves the frame cleanly.
            xs = np.linspace(0, 7, 701)
            inside = xs[np.abs(taylor_sin(xs, d)) <= 2.45]
            limit = inside[np.argmax(np.diff(inside) > 0.011)] if np.any(np.diff(inside) > 0.011) else inside[-1]
            return axes.plot(lambda x: taylor_sin(x, d), x_range=[-limit, limit], color=c, stroke_width=4)

        current = poly(1, colors[0])
        label = Text(formula(1), font_size=28, color=colors[0]).to_edge(UP)
        self.play(Create(current), Write(label))
        self.wait(0.6)
        for d, c in zip(degrees[1:], colors[1:]):
            new_label = Text(formula(d), font_size=26 if d < 9 else 22, color=c).to_edge(UP)
            self.play(Transform(current, poly(d, c)), Transform(label, new_label), run_time=1.4)
            self.wait(0.6)
        note = Text("More terms, a wider stretch where the copy is good", font_size=26, color=GREY_B).to_edge(DOWN)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(2)
