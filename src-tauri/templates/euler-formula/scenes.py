"""e to the i theta walks around a circle; at theta = pi it lands on -1.

An original ManimPro template inspired by the topic of 3Blue1Brown's
"e to the pi i, a nontechnical explanation". No LaTeX needed.
"""
from manim import *


def plane():
    p = ComplexPlane(x_range=[-2.5, 2.5], y_range=[-2.2, 2.2], x_length=8, y_length=7,
                     background_line_style={"stroke_color": BLUE_E, "stroke_opacity": 0.6})
    labels = VGroup(
        Text("1", font_size=24).next_to(p.n2p(1), DR, buff=0.08),
        Text("−1", font_size=24).next_to(p.n2p(-1), DL, buff=0.08),
        Text("i", font_size=26, slant=ITALIC).next_to(p.n2p(1j), UR, buff=0.08),
        Text("−i", font_size=24).next_to(p.n2p(-1j), DR, buff=0.08),
    )
    return p, labels


class Multiplying(Scene):
    """Scene 1: multiplying by i turns a point a quarter turn."""

    def construct(self):
        p, labels = plane()
        title = Text("Multiplying by i is a quarter turn", font_size=34).to_edge(UP).add_background_rectangle()
        self.play(Create(p), FadeIn(labels), run_time=1.5)
        self.play(FadeIn(title))
        z = 1.5 + 0.5j
        dot = Dot(p.n2p(z), color=YELLOW)
        arrow = Arrow(p.n2p(0), p.n2p(z), buff=0, color=YELLOW)
        self.play(GrowArrow(arrow), FadeIn(dot))
        for _ in range(4):
            z *= 1j
            self.play(
                Rotate(VGroup(arrow, dot), angle=PI / 2, about_point=p.n2p(0)),
                run_time=1,
            )
            self.wait(0.25)
        self.wait()


class AroundTheCircle(Scene):
    """Scene 2: e^(iθ) moves along the unit circle at speed 1."""

    def construct(self):
        p, labels = plane()
        self.add(p, labels)
        circle = Circle(radius=p.n2p(1)[0] - p.n2p(0)[0], color=GREY_B).move_to(p.n2p(0))
        theta = ValueTracker(0.0001)

        def point():
            return p.n2p(np.exp(1j * theta.get_value()))

        vector = always_redraw(lambda: Arrow(p.n2p(0), point(), buff=0, color=YELLOW, stroke_width=5))
        dot = always_redraw(lambda: Dot(point(), color=YELLOW))
        arc = always_redraw(lambda: Arc(radius=circle.radius, start_angle=0, angle=theta.get_value(),
                                        arc_center=p.n2p(0), color=TEAL_C, stroke_width=7))
        readout = always_redraw(lambda: MarkupText(
            f"e<sup>iθ</sup>   with θ = {theta.get_value():.2f}", font_size=30,
        ).to_corner(UL).add_background_rectangle())
        note = Text("θ is the distance walked along the circle", font_size=26, color=TEAL_B).to_corner(DL).add_background_rectangle()

        self.play(Create(circle))
        self.add(arc, vector, dot, readout)
        self.play(FadeIn(note))
        self.play(theta.animate.set_value(PI / 2), run_time=2.5, rate_func=smooth)
        self.wait(0.4)
        self.play(theta.animate.set_value(PI), run_time=2.5, rate_func=smooth)
        self.wait(0.4)

        result = MarkupText("e<sup>iπ</sup> = −1", font_size=56, color=YELLOW).to_edge(RIGHT, buff=0.8)
        result.add_background_rectangle(buff=0.25)
        self.play(Flash(dot.get_center(), color=YELLOW, flash_radius=0.4), FadeIn(result, scale=0.8))
        self.wait(0.8)
        final = MarkupText("e<sup>iπ</sup> + 1 = 0", font_size=48).next_to(result, DOWN, buff=0.5)
        final.add_background_rectangle(buff=0.2)
        self.play(Write(final))
        self.wait(2)
