from manim import *


class LogoReveal(Scene):
    """Shapes fly in, lock together into a mark, and the brand name appears."""

    def construct(self):
        self.camera.background_color = "#101216"
        colors = [BLUE_C, TEAL_C, GREEN_C, YELLOW_C]
        tiles = VGroup(*[
            Square(side_length=0.9, fill_opacity=1, stroke_width=0, fill_color=c).rotate(PI / 4) for c in colors
        ])
        targets = [UP * 0.65, RIGHT * 0.65, DOWN * 0.65, LEFT * 0.65]
        starts = [UP * 4 + LEFT * 5, RIGHT * 7 + UP * 2, DOWN * 4 + RIGHT * 4, LEFT * 7 + DOWN * 2]
        for t, s in zip(tiles, starts):
            t.move_to(s).rotate(PI)

        self.play(
            LaggedStart(*[t.animate.move_to(p).rotate(-PI) for t, p in zip(tiles, targets)], lag_ratio=0.15),
            run_time=1.8,
        )
        mark = tiles.copy()
        self.play(Rotate(tiles, angle=PI / 2), run_time=0.8)
        self.play(tiles.animate.scale(0.6).shift(LEFT * 3))
        name = Text("Northwind", font_size=80, weight=BOLD).next_to(tiles, RIGHT, buff=0.6)
        tagline = Text("studio", font_size=34, color=GREY_B).next_to(name, DOWN, aligned_edge=LEFT, buff=0.15)
        self.play(Write(name), run_time=1.2)
        self.play(FadeIn(tagline, shift=UP * 0.2))
        self.wait(1.2)
        del mark
