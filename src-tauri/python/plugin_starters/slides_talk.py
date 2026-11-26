"""A presentation with manim-slides: each self.next_slide() is a pause you click past.

Render it here to check the slides, then present with `manim-slides present Presentation`
(or export to HTML / PowerPoint with `manim-slides convert`).
"""
from manim import *
from manim_slides import Slide


class Presentation(Slide):
    def construct(self):
        title = Text("My talk", font_size=60)
        subtitle = Text("Press space to go on", font_size=28, color=GREY_B).next_to(title, DOWN)
        self.play(Write(title), FadeIn(subtitle, shift=UP * 0.2))
        self.next_slide()

        self.play(FadeOut(subtitle), title.animate.to_edge(UP))
        points = VGroup(*[Text(t, font_size=34) for t in ["One idea per slide", "Animate the change", "Pause to explain"]])
        points.arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        for p in points:
            self.play(FadeIn(p, shift=RIGHT * 0.3))
            self.next_slide()

        self.play(FadeOut(points), title.animate.move_to(ORIGIN).set_color(YELLOW))
        self.wait()
