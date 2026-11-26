from manim import *


class Intro(Scene):
    def construct(self):
        title = Text("Hello, Manim", weight=BOLD).scale(1.2)
        underline = Line(LEFT * 3, RIGHT * 3, color=BLUE).next_to(title, DOWN)
        self.play(Write(title), run_time=1.5)
        self.play(Create(underline))
        self.wait(0.5)
        self.play(FadeOut(title, shift=UP), FadeOut(underline, shift=UP))


class SquareToCircle(Scene):
    def construct(self):
        square = Square(side_length=3, color=BLUE, fill_opacity=0.4)
        circle = Circle(radius=1.6, color=RED, fill_opacity=0.4)
        self.play(Create(square))
        self.play(square.animate.rotate(PI / 4))
        self.play(Transform(square, circle))
        self.wait()


class Orbit(Scene):
    def construct(self):
        sun = Dot(radius=0.25, color=YELLOW)
        path = Circle(radius=2.5, color=GREY_B, stroke_opacity=0.5)
        planet = Dot(radius=0.12, color=TEAL).move_to(path.point_from_proportion(0))
        trail = TracedPath(planet.get_center, stroke_color=TEAL, stroke_width=3)
        self.add(path, sun, trail, planet)
        self.play(MoveAlongPath(planet, path), run_time=4, rate_func=linear)
        self.wait(0.5)
