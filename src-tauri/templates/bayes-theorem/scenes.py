"""Bayes' theorem as areas: is Steve a librarian or a farmer?

An original ManimPro template inspired by the topic of 3Blue1Brown's
"Bayes theorem, the geometry of changing beliefs". No LaTeX needed.
"""
from manim import *

LIB = BLUE_C
FARM = GREEN_C
W, H = 10.5, 4.6
LIB_SHARE = 1 / 21  # 1 librarian for every 20 farmers
LIB_FIT, FARM_FIT = 0.4, 0.1  # share who fit the description


class TheQuestion(Scene):
    """Scene 1: the puzzle."""

    def construct(self):
        desc = Text(
            "Steve is shy and tidy.\nHe likes order and detail.",
            font_size=40, line_spacing=1.3,
        )
        q = MarkupText("Is Steve more likely a <span fgcolor='#58C4DD'>librarian</span> "
                       "or a <span fgcolor='#83C167'>farmer</span>?", font_size=34)
        q.next_to(desc, DOWN, buff=0.8)
        self.play(Write(desc), run_time=2)
        self.wait(0.6)
        self.play(FadeIn(q, shift=UP * 0.2))
        self.wait(1.2)
        hint = Text("Most people say librarian. Let's check with areas.", font_size=28, color=GREY_B).to_edge(DOWN)
        self.play(FadeIn(hint))
        self.wait(1.5)


class Population(Scene):
    """Scene 2: there are far more farmers than librarians."""

    def construct(self):
        frame = Rectangle(width=W, height=H, stroke_color=GREY_B).shift(DOWN * 0.3)
        lib_w = W * LIB_SHARE
        lib = Rectangle(width=lib_w, height=H, stroke_width=0, fill_color=LIB, fill_opacity=0.55)
        lib.align_to(frame, LEFT).align_to(frame, DOWN)
        farm = Rectangle(width=W - lib_w, height=H, stroke_width=0, fill_color=FARM, fill_opacity=0.45)
        farm.align_to(frame, RIGHT).align_to(frame, DOWN)
        title = Text("Start with everyone who could be Steve", font_size=34).to_edge(UP)
        lib_label = Text("librarians\n1 in 21", font_size=22, color=LIB, line_spacing=1.1).next_to(lib, DOWN, aligned_edge=LEFT)
        farm_label = Text("farmers: 20 in 21", font_size=26, color=FARM).next_to(farm, DOWN)

        self.play(Write(title), Create(frame))
        self.play(FadeIn(farm), FadeIn(lib), run_time=1.5)
        self.play(FadeIn(lib_label), FadeIn(farm_label))
        self.wait(2)


class Evidence(Scene):
    """Scene 3: shade the people who fit the description."""

    def construct(self):
        frame = Rectangle(width=W, height=H, stroke_color=GREY_B).shift(DOWN * 0.3)
        lib_w = W * LIB_SHARE
        lib = Rectangle(width=lib_w, height=H, stroke_width=0, fill_color=LIB, fill_opacity=0.2).align_to(frame, LEFT).align_to(frame, DOWN)
        farm = Rectangle(width=W - lib_w, height=H, stroke_width=0, fill_color=FARM, fill_opacity=0.15).align_to(frame, RIGHT).align_to(frame, DOWN)
        self.add(frame, lib, farm)

        lib_fit = Rectangle(width=lib_w, height=H * LIB_FIT, stroke_width=0, fill_color=LIB, fill_opacity=0.95)
        lib_fit.align_to(frame, LEFT).align_to(frame, DOWN)
        farm_fit = Rectangle(width=W - lib_w, height=H * FARM_FIT, stroke_width=0, fill_color=FARM, fill_opacity=0.95)
        farm_fit.align_to(frame, RIGHT).align_to(frame, DOWN)

        title = Text("Keep only people who fit the description", font_size=34).to_edge(UP, buff=0.4)
        notes = VGroup(
            MarkupText("<span fgcolor='#58C4DD'>40%</span> of librarians fit", font_size=26),
            MarkupText("<span fgcolor='#83C167'>10%</span> of farmers fit", font_size=26),
        ).arrange(RIGHT, buff=0.9).next_to(title, DOWN, buff=0.25)

        self.play(Write(title))
        self.play(GrowFromEdge(lib_fit, DOWN), FadeIn(notes[0]), run_time=1.2)
        self.play(GrowFromEdge(farm_fit, DOWN), FadeIn(notes[1]), run_time=1.2)
        self.wait(0.6)
        self.play(lib.animate.set_fill(opacity=0.05), farm.animate.set_fill(opacity=0.04))
        brace_l = Brace(lib_fit, LEFT, color=LIB)
        brace_f = Brace(farm_fit, UP, color=FARM)
        self.play(GrowFromCenter(brace_l), GrowFromCenter(brace_f))
        self.wait(2)


class Answer(Scene):
    """Scene 4: compare the shaded areas."""

    def construct(self):
        lib_area = LIB_SHARE * LIB_FIT
        farm_area = (1 - LIB_SHARE) * FARM_FIT
        p = lib_area / (lib_area + farm_area)

        lib_block = Rectangle(width=0.4 * 2, height=1, stroke_width=0, fill_color=LIB, fill_opacity=0.95)
        farm_block = Rectangle(width=2.0 * 2, height=1, stroke_width=0, fill_color=FARM, fill_opacity=0.95)
        blocks = VGroup(lib_block, farm_block).arrange(RIGHT, buff=0.1).shift(UP * 0.6)
        labels = VGroup(
            Text("4 librarians", font_size=24, color=LIB).next_to(lib_block, DOWN),
            Text("20 farmers", font_size=24, color=FARM).next_to(farm_block, DOWN),
        )
        title = Text("Out of every 210 people, those who fit:", font_size=32).to_edge(UP)
        result = MarkupText(
            f"P(librarian | description) = 4 / 24 ≈ <span fgcolor='#FFFF00'>{p:.0%}</span>",
            font_size=36,
        ).shift(DOWN * 1.6)
        moral = Text("The evidence matters less than how common each group is.", font_size=26, color=GREY_B).to_edge(DOWN)

        self.play(Write(title))
        self.play(FadeIn(blocks, lag_ratio=0.3), FadeIn(labels))
        self.wait(0.8)
        self.play(Write(result), run_time=1.5)
        self.play(Circumscribe(result, color=YELLOW))
        self.play(FadeIn(moral, shift=UP * 0.2))
        self.wait(2)
