"""Gradient descent: step downhill along the slope, and what the learning rate does.

An original ManimPro template. Change LOSS, START or the learning rates to experiment.
"""
from manim import *


def LOSS(x):
    return 0.12 * (x - 1) ** 2 * (0.25 * (x + 2) ** 2 + 1) / 2 + 0.4


def SLOPE(x, h=1e-4):
    return (LOSS(x + h) - LOSS(x - h)) / (2 * h)


START = -3.2


def make_axes():
    axes = Axes(x_range=[-4, 4, 1], y_range=[0, 5, 1], x_length=10, y_length=5, tips=False,
                axis_config={"color": GREY_B}).shift(DOWN * 0.6)
    curve = axes.plot(LOSS, x_range=[-4, 4], color=BLUE_C, stroke_width=5)
    xl = Text("weight", font_size=22, color=GREY_B).next_to(axes.x_axis, DOWN, buff=0.15).align_to(axes.x_axis, RIGHT)
    yl = Text("loss", font_size=22, color=GREY_B).next_to(axes.y_axis, UP, buff=0.1)
    return axes, curve, VGroup(xl, yl)


def descend(scene, axes, rate, steps, color, run_time=0.45):
    x = START
    ball = Dot(axes.c2p(x, LOSS(x)), color=color, radius=0.13)
    trail = VGroup()
    scene.play(FadeIn(ball, scale=2))
    for _ in range(steps):
        g = SLOPE(x)
        tangent = Line(axes.c2p(x - 0.7, LOSS(x) - 0.7 * g), axes.c2p(x + 0.7, LOSS(x) + 0.7 * g), color=YELLOW, stroke_width=3)
        scene.play(Create(tangent), run_time=run_time * 0.5)
        nx = max(-4, min(4, x - rate * g))
        step_line = DashedLine(axes.c2p(x, LOSS(x)), axes.c2p(nx, LOSS(nx)), color=color, stroke_width=3.5)
        trail.add(step_line)
        scene.play(ball.animate.move_to(axes.c2p(nx, LOSS(nx))), Create(step_line), FadeOut(tangent), run_time=run_time)
        x = nx
    return ball, trail, x


class Downhill(Scene):
    """Scene 1: follow the negative slope, one step at a time."""

    def construct(self):
        title = Text("Gradient descent", font_size=42, weight=BOLD).to_edge(UP)
        rule = Text("new weight = weight − learning rate × slope", font_size=26, color=GREY_B).next_to(title, DOWN, buff=0.2)
        self.play(Write(title), FadeIn(rule))
        axes, curve, labels = make_axes()
        self.play(Create(axes), Create(curve), FadeIn(labels), run_time=1.5)
        ball, trail, x = descend(self, axes, 1.1, 9, GREEN_C)
        note = Text(f"Settled at the bottom: loss {LOSS(x):.2f}", font_size=26, color=GREEN_C).to_edge(DOWN, buff=0.25)
        self.play(FadeIn(note, shift=UP * 0.2), Flash(ball, color=GREEN_C))
        self.wait(1.5)


class LearningRate(Scene):
    """Scene 2: too small crawls, too big bounces; a good rate gets there quickly."""

    def construct(self):
        title = Text("Choosing the learning rate", font_size=40, weight=BOLD).to_edge(UP)
        self.play(Write(title))
        axes, curve, labels = make_axes()
        self.play(Create(axes), Create(curve), FadeIn(labels))
        runs = [(0.25, 8, RED_C, "too small: crawls"), (2.6, 8, ORANGE, "too big: overshoots"), (1.1, 8, GREEN_C, "about right")]
        legend = VGroup()
        for rate, n, color, words in runs:
            tag = Text(f"rate {rate}: {words}", font_size=24, color=color)
            tag.next_to(legend, DOWN, buff=0.12, aligned_edge=LEFT) if len(legend) else tag.next_to(title, DOWN, buff=0.35).shift(LEFT * 1.2)
            legend.add(tag)
            self.play(FadeIn(tag, shift=LEFT * 0.2), run_time=0.5)
            ball, trail, _ = descend(self, axes, rate, n, color, run_time=0.28)
            self.play(ball.animate.set_opacity(0.5), trail.animate.set_opacity(0.4), run_time=0.3)
        self.wait(1.5)
