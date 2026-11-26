"""Estimating π by throwing random darts at a square.

An original ManimPro template. Change SEED or DARTS for a different run.
"""
from manim import *
import numpy as np

SEED = 7
DARTS = 1200
SIDE = 5.0


def board():
    square = Square(SIDE, color=GREY_B, stroke_width=3)
    arc = Arc(radius=SIDE, start_angle=0, angle=PI / 2, color=YELLOW, stroke_width=4)
    arc.move_arc_center_to(square.get_corner(DL))
    return VGroup(square, arc)


class Idea(Scene):
    """Scene 1: the quarter circle covers π/4 of the square."""

    def construct(self):
        title = Text("Finding π with random darts", font_size=42, weight=BOLD).to_edge(UP)
        self.play(Write(title))
        b = board().shift(LEFT * 3 + DOWN * 0.4)
        self.play(Create(b[0]), run_time=1)
        sector = Sector(radius=SIDE, angle=PI / 2, color=YELLOW, fill_opacity=0.25, stroke_width=0).move_arc_center_to(b[0].get_corner(DL))
        self.play(Create(b[1]), FadeIn(sector))
        lines = VGroup(
            Text("square area = 1", font_size=28),
            Text("quarter circle area = π / 4", font_size=28, color=YELLOW),
            Text("so the share of darts that land", font_size=28, color=GREY_B),
            Text("inside the arc ≈ π / 4", font_size=28, color=GREY_B),
        ).arrange(DOWN, buff=0.3, aligned_edge=LEFT).next_to(b, RIGHT, buff=0.8)
        for l in lines:
            self.play(FadeIn(l, shift=LEFT * 0.2), run_time=0.7)
        result = Text("π ≈ 4 × (inside / total)", font_size=34, color=GREEN_C).next_to(lines, DOWN, buff=0.6, aligned_edge=LEFT)
        self.play(Write(result))
        self.play(Circumscribe(result, color=GREEN_C))
        self.wait(1.5)


class Throwing(Scene):
    """Scene 2: darts land, the estimate wobbles, then settles near 3.14."""

    def construct(self):
        rng = np.random.default_rng(SEED)
        pts = rng.random((DARTS, 2))
        b = board().shift(LEFT * 3.4 + DOWN * 0.2)
        origin = b[0].get_corner(DL)
        self.add(b)
        axes = Axes(x_range=[0, DARTS, DARTS // 4], y_range=[2.6, 3.8, 0.4], x_length=5, y_length=2.8, tips=False,
                    axis_config={"color": GREY_B, "include_numbers": False}).to_corner(DR, buff=0.6)
        est_label = Text("π ≈ —", font_size=40).next_to(axes, UP, buff=1.0).align_to(axes, LEFT)
        counts = Text("0 darts", font_size=24, color=GREY_B).next_to(est_label, DOWN, buff=0.2, aligned_edge=LEFT)
        self.play(FadeIn(est_label), FadeIn(counts))
        target = DashedLine(axes.c2p(0, PI), axes.c2p(DARTS, PI), color=YELLOW, stroke_width=2)
        tag = Text("π", font_size=24, color=YELLOW).next_to(target, RIGHT, buff=0.1)
        self.play(Create(axes), Create(target), FadeIn(tag))

        inside = 0
        history = []
        batches = [10, 20, 30, 40, 50, 100, 150, 200, 250, 350]
        done = 0
        for n in batches:
            n = min(n, DARTS - done)
            if n <= 0:
                break
            dots = VGroup()
            for x, y in pts[done:done + n]:
                hit = x * x + y * y <= 1
                inside += hit
                dots.add(Dot(origin + RIGHT * x * SIDE + UP * y * SIDE, radius=0.03, color=GREEN_C if hit else RED_C))
            done += n
            est = 4 * inside / done
            history.append((done, est))
            new_label = Text(f"π ≈ {est:.3f}", font_size=40).move_to(est_label, aligned_edge=LEFT)
            new_counts = Text(f"{done} darts, {inside} inside", font_size=24, color=GREY_B).move_to(counts, aligned_edge=LEFT)
            path = VMobject(color=GREEN_C, stroke_width=3).set_points_as_corners([axes.c2p(d, min(3.8, max(2.6, e))) for d, e in [(0, history[0][1])] + history])
            self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.6 / max(1, n)),
                      Transform(est_label, new_label), Transform(counts, new_counts),
                      Create(path) if len(history) == 1 else FadeIn(path), run_time=0.9)
        note = Text("More darts, closer to π: the error shrinks like 1/√n", font_size=26, color=GREY_A).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(1.5)
