"""Add up more dice and the distribution turns into a bell curve.

An original ManimPro template inspired by the topic of 3Blue1Brown's
"But what is the Central Limit Theorem?". Exact probabilities, no randomness.
"""
from manim import *

FACES = np.ones(6) / 6


def sum_distribution(n):
    """Exact probabilities for the sum of n fair dice: index k is the sum n + k."""
    d = np.array([1.0])
    for _ in range(n):
        d = np.convolve(d, FACES)
    return d


def bars(axes, n, width_scale=1.0, color=BLUE_C):
    d = sum_distribution(n)
    group = VGroup()
    # Plot the *mean* of the dice so every n shares the same 1..6 axis.
    for k, p in enumerate(d):
        mean = (n + k) / n
        h = p * n  # density on the mean scale
        bar = Rectangle(
            width=axes.x_axis.unit_size * width_scale / n * 0.92,
            height=max(h * axes.y_axis.unit_size, 0.001),
            stroke_width=0, fill_color=color, fill_opacity=0.85,
        )
        bar.move_to(axes.c2p(mean, 0), aligned_edge=DOWN)
        group.add(bar)
    return group


class OneDie(Scene):
    """Scene 1: one die is flat."""

    def construct(self):
        axes = Axes(x_range=[0.5, 6.5, 1], y_range=[0, 0.25, 0.05], x_length=10, y_length=4.6, tips=False,
                    axis_config={"color": GREY_C}).shift(DOWN * 0.6)
        faces = VGroup(*[Text(str(i), font_size=24, color=GREY_B).next_to(axes.c2p(i, 0), DOWN) for i in range(1, 7)])
        title = Text("Roll one die: every face is equally likely", font_size=34).to_edge(UP)
        sixth = Text("each face: 1 in 6", font_size=26, color=GREY_B).next_to(title, DOWN, buff=0.3)
        self.play(Write(title), Create(axes), FadeIn(faces))
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars(axes, 1)], lag_ratio=0.1))
        self.play(FadeIn(sixth))
        self.wait(1.5)


class AddingDice(Scene):
    """Scene 2: the average of more dice piles up in the middle."""

    def construct(self):
        axes = Axes(x_range=[0.5, 6.5, 1], y_range=[0, 1.6, 0.4], x_length=10, y_length=4.6, tips=False,
                    axis_config={"color": GREY_C}).shift(DOWN * 0.6)
        faces = VGroup(*[Text(str(i), font_size=24, color=GREY_B).next_to(axes.c2p(i, 0), DOWN) for i in range(1, 7)])
        title = Text("Average of several dice", font_size=34).to_edge(UP)
        self.add(axes, faces)
        self.play(Write(title))

        current = bars(axes, 1)
        label = Text("1 die", font_size=30, color=YELLOW).next_to(title, DOWN)
        self.play(FadeIn(current), FadeIn(label))
        for n in [2, 3, 5, 10, 20]:
            new = bars(axes, n, color=interpolate_color(ManimColor(BLUE_C), ManimColor(TEAL_C), min(n / 20, 1)))
            new_label = Text(f"{n} dice", font_size=30, color=YELLOW).next_to(title, DOWN)
            self.play(Transform(current, new), Transform(label, new_label), run_time=1.5)
            self.wait(0.6)

        n = 20
        mu, sigma = 3.5, np.sqrt(35 / 12) / np.sqrt(n)
        bell = axes.plot(lambda x: np.exp(-((x - mu) ** 2) / (2 * sigma**2)) / (sigma * np.sqrt(2 * PI)),
                         x_range=[0.6, 6.4], color=YELLOW, stroke_width=4)
        note = Text("It approaches a bell curve, whatever the starting shape", font_size=26, color=GREY_B)
        note.next_to(label, DOWN, buff=0.25)
        self.play(Create(bell), run_time=2)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(2)
