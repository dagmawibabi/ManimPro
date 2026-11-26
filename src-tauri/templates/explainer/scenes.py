from manim import *

ACCENT = "#58C4DD"


class Hook(Scene):
    """Scene 1: a question that grabs attention."""

    def construct(self):
        q = Text("Why does a wheel\nroll so smoothly?", font_size=56, line_spacing=1.2)
        self.play(Write(q), run_time=2)
        self.wait()
        self.play(FadeOut(q, shift=UP * 0.4))


class KeyIdea(Scene):
    """Scene 2: show the idea visually."""

    def construct(self):
        ground = Line(LEFT * 6.5, RIGHT * 6.5, color=GREY_B).shift(DOWN * 2)
        start = ground.get_center() + UP + LEFT * 4.5
        rolled = ValueTracker(0)  # distance travelled; a unit wheel turns by the same angle

        def wheel():
            center = start + RIGHT * rolled.get_value()
            a = -rolled.get_value()
            rim = center + np.array([np.sin(a), -np.cos(a), 0])
            return VGroup(
                Circle(radius=1, color=ACCENT, fill_opacity=0.15).move_to(center),
                Line(center, rim, color=ACCENT),
                Dot(center, color=WHITE),
                Dot(rim, color=YELLOW),
            )

        rolling = always_redraw(wheel)
        trail = TracedPath(lambda: rolling[3].get_center(), stroke_color=YELLOW, stroke_width=3)
        hub_trail = TracedPath(lambda: rolling[2].get_center(), stroke_color=WHITE, stroke_width=2, stroke_opacity=0.6)
        label = Text("Its center stays at the same height", font_size=32).to_edge(UP)
        self.add(ground, trail, hub_trail, rolling)
        self.play(FadeIn(label))
        self.play(rolled.animate.set_value(2 * PI), run_time=4, rate_func=linear)
        self.wait()


class Outro(Scene):
    """Scene 3: wrap up with a takeaway."""

    def construct(self):
        takeaway = Text("Constant height = no bumps", font_size=48, color=ACCENT)
        thanks = Text("Thanks for watching", font_size=30, color=GREY_B).next_to(takeaway, DOWN, buff=0.5)
        self.play(FadeIn(takeaway, scale=0.9))
        self.play(FadeIn(thanks, shift=UP * 0.2))
        self.wait(1.5)
