"""Pythagorean theorem by rearrangement: the same four triangles, two arrangements.

An original ManimPro template. A classic proof, no LaTeX needed.
"""
from manim import *

A, B = 1.6, 2.6  # legs
S = A + B
TRI = dict(fill_color=BLUE_D, fill_opacity=0.85, stroke_color=WHITE, stroke_width=2)


def outer(center):
    return Square(side_length=S, stroke_color=GREY_B, stroke_width=3).move_to(center)


def tilted_arrangement(center):
    """Four triangles in the corners leave a tilted square of side c."""
    o = center + np.array([-S / 2, -S / 2, 0])
    p = lambda x, y: o + np.array([x, y, 0])
    tris = VGroup(
        Polygon(p(0, 0), p(B, 0), p(0, A), **TRI),
        Polygon(p(S, 0), p(S, B), p(B, 0), **TRI),
        Polygon(p(S, S), p(A, S), p(S, B), **TRI),
        Polygon(p(0, S), p(0, A), p(A, S), **TRI),
    )
    hole = Polygon(p(B, 0), p(S, B), p(A, S), p(0, A), fill_color=YELLOW_D, fill_opacity=0.35, stroke_width=0)
    return tris, hole


def split_arrangement(center):
    """The same triangles paired into two rectangles leave squares a² and b²."""
    o = center + np.array([-S / 2, -S / 2, 0])
    p = lambda x, y: o + np.array([x, y, 0])
    tris = VGroup(
        Polygon(p(A, 0), p(S, 0), p(A, A), **TRI),
        Polygon(p(S, A), p(A, A), p(S, 0), **TRI),
        Polygon(p(0, A), p(A, A), p(0, S), **TRI),
        Polygon(p(A, S), p(0, S), p(A, A), **TRI),
    )
    sq_a = Square(side_length=A, fill_color=GREEN_C, fill_opacity=0.45, stroke_width=0).move_to(p(A / 2, A / 2))
    sq_b = Square(side_length=B, fill_color=RED_C, fill_opacity=0.45, stroke_width=0).move_to(p(A + B / 2, A + B / 2))
    return tris, sq_a, sq_b


class Setup(Scene):
    """Scene 1: one right triangle with sides a, b and c."""

    def construct(self):
        tri = Polygon(ORIGIN, RIGHT * B, UP * A, **TRI).scale(1.4).move_to(ORIGIN)
        v = tri.get_vertices()
        labels = VGroup(
            Text("b", font_size=34).next_to(Line(v[0], v[1]), DOWN),
            Text("a", font_size=34).next_to(Line(v[0], v[2]), LEFT),
            Text("c", font_size=34, color=YELLOW).move_to(Line(v[1], v[2]).get_center() + np.array([0.35, 0.3, 0])),
        )
        corner = RightAngle(Line(v[0], v[1]), Line(v[0], v[2]), length=0.3, color=WHITE)
        claim = MarkupText("a² + b² = c²", font_size=48).to_edge(UP)
        self.play(DrawBorderThenFill(tri), run_time=1.5)
        self.play(Create(corner), FadeIn(labels, lag_ratio=0.3))
        self.play(Write(claim))
        self.wait(0.8)
        why = Text("Why? Let's move some triangles around.", font_size=28, color=GREY_B).to_edge(DOWN)
        self.play(FadeIn(why))
        self.wait(1.5)


class Rearrange(Scene):
    """Scene 2: same big square, same four triangles, different leftover area."""

    def construct(self):
        left_c, right_c = LEFT * 3.3 + DOWN * 0.3, RIGHT * 3.3 + DOWN * 0.3
        frame_l, frame_r = outer(left_c), outer(right_c)
        tris_l, hole = tilted_arrangement(left_c)
        tris_r, sq_a, sq_b = split_arrangement(right_c)

        title = Text("Same square, same four triangles", font_size=34).to_edge(UP)
        self.play(Write(title), Create(frame_l))
        self.play(LaggedStart(*[DrawBorderThenFill(t) for t in tris_l], lag_ratio=0.2), run_time=2)
        self.play(FadeIn(hole))
        c2 = MarkupText("c²", font_size=40).move_to(hole)
        self.play(Write(c2))
        self.wait(0.5)

        self.play(Create(frame_r))
        moving = tris_l.copy()
        self.play(*[Transform(m, t) for m, t in zip(moving, tris_r)], run_time=2.5)
        self.play(FadeIn(sq_a), FadeIn(sq_b))
        a2 = MarkupText("a²", font_size=34).move_to(sq_a)
        b2 = MarkupText("b²", font_size=40).move_to(sq_b)
        self.play(Write(a2), Write(b2))
        self.wait(0.8)

        conclusion = MarkupText("leftover area is equal:  <span fgcolor='#FFFF00'>a² + b² = c²</span>", font_size=32).to_edge(DOWN)
        self.play(FadeIn(conclusion, shift=UP * 0.2))
        self.play(Indicate(hole, color=YELLOW), Indicate(VGroup(sq_a, sq_b), color=YELLOW))
        self.wait(2)
