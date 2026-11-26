"""Linear transformations: where the basis vectors go, and how areas scale.

An original ManimPro template inspired by the topic of 3Blue1Brown's
"Essence of Linear Algebra". No LaTeX needed.
"""
from manim import *


def grid():
    plane = NumberPlane(
        x_range=[-9, 9], y_range=[-6, 6],
        background_line_style={"stroke_color": BLUE_D, "stroke_width": 2, "stroke_opacity": 0.7},
    )
    ghost = NumberPlane(
        x_range=[-9, 9], y_range=[-6, 6],
        background_line_style={"stroke_color": GREY_D, "stroke_opacity": 0.3},
        axis_config={"stroke_opacity": 0.3},
    )
    return plane, ghost


def basis():
    return Arrow(ORIGIN, RIGHT, buff=0, color=GREEN_C, stroke_width=6), Arrow(ORIGIN, UP, buff=0, color=RED_C, stroke_width=6)


def caption(text, sub=None):
    g = VGroup(Text(text, font_size=32))
    if sub:
        g.add(Text(sub, font_size=24, color=GREY_A))
    return g.arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_corner(UL).add_background_rectangle(opacity=0.85, buff=0.15)


class BasisVectors(Scene):
    """Scene 1: two arrows describe the whole grid."""

    def construct(self):
        plane, ghost = grid()
        i_hat, j_hat = basis()
        labels = VGroup(
            Text("î", font_size=34, color=GREEN_C).next_to(i_hat, DOWN, buff=0.1),
            Text("ĵ", font_size=34, color=RED_C).next_to(j_hat, LEFT, buff=0.1),
        )
        self.add(ghost)
        self.play(Create(plane), run_time=1.5)
        self.play(GrowArrow(i_hat), GrowArrow(j_hat), FadeIn(labels))
        c = caption("Every point is a mix of î and ĵ", "(3, 2) means 3 steps of î plus 2 of ĵ")
        self.play(FadeIn(c))
        path = VGroup(
            Arrow(ORIGIN, RIGHT * 3, buff=0, color=GREEN_C),
            Arrow(RIGHT * 3, RIGHT * 3 + UP * 2, buff=0, color=RED_C),
        )
        self.play(GrowArrow(path[0]))
        self.play(GrowArrow(path[1]))
        self.play(Flash(RIGHT * 3 + UP * 2, color=YELLOW))
        self.wait(1.5)


class Shear(Scene):
    """Scene 2: a shear keeps î, slides ĵ sideways."""

    def construct(self):
        self.transform_scene(
            [[1, 1], [0, 1]],
            "A shear: matrix [[1, 1], [0, 1]]",
            "î stays put, ĵ lands on (1, 1)",
        )

    def transform_scene(self, matrix, title, sub):
        plane, ghost = grid()
        i_hat, j_hat = basis()
        self.add(ghost, plane, i_hat, j_hat)
        self.play(FadeIn(caption(title, sub)))
        self.play(ApplyMatrix(matrix, plane), ApplyMatrix(matrix, i_hat), ApplyMatrix(matrix, j_hat), run_time=3)
        self.wait(1.5)


class Rotation(Shear):
    """Scene 3: a quarter turn."""

    def construct(self):
        self.transform_scene(
            [[0, -1], [1, 0]],
            "A 90° rotation: matrix [[0, −1], [1, 0]]",
            "î lands on (0, 1), ĵ lands on (−1, 0)",
        )


class Determinant(Scene):
    """Scene 4: the determinant is how much areas grow."""

    def construct(self):
        plane, ghost = grid()
        i_hat, j_hat = basis()
        square = Square(side_length=1, fill_color=YELLOW, fill_opacity=0.5, stroke_color=YELLOW).move_to([0.5, 0.5, 0])
        self.add(ghost, plane, square, i_hat, j_hat)
        c = caption("The unit square has area 1", "Watch what this matrix does to it")
        self.play(FadeIn(c))
        self.wait(0.6)
        matrix = [[2, 1], [0, 1]]
        self.play(*[ApplyMatrix(matrix, m) for m in (plane, square, i_hat, j_hat)], run_time=3)
        result = caption("Area is now 2", "determinant = 2 × 1 − 1 × 0 = 2")
        self.play(Transform(c, result))
        self.play(Indicate(square, color=YELLOW))
        self.wait(2)
