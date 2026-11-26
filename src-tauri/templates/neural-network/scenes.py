from manim import *

LAYERS = [3, 5, 5, 2]


class NeuralNetwork(Scene):
    """Signals pulse forward through a small neural network."""

    def construct(self):
        layers = VGroup()
        for i, n in enumerate(LAYERS):
            col = VGroup(*[Circle(radius=0.28, color=BLUE_B, fill_opacity=0.15) for _ in range(n)])
            col.arrange(DOWN, buff=0.45).move_to([(i - (len(LAYERS) - 1) / 2) * 3, 0, 0])
            layers.add(col)
        links = VGroup()
        for a, b in zip(layers[:-1], layers[1:]):
            for x in a:
                for y in b:
                    links.add(Line(x.get_right(), y.get_left(), stroke_width=1.2, color=GREY_D))
        names = VGroup(*[
            Text(t, font_size=22, color=GREY_B).next_to(layers[i], DOWN, buff=0.4)
            for i, t in enumerate(["input", "hidden", "hidden", "output"])
        ])

        self.play(LaggedStart(*[Create(c) for c in layers], lag_ratio=0.2), FadeIn(names))
        self.play(Create(links), run_time=1.5)
        for _ in range(2):
            for a, b in zip(layers[:-1], layers[1:]):
                pulses = [
                    ShowPassingFlash(Line(x.get_right(), y.get_left(), color=YELLOW, stroke_width=3), time_width=0.6)
                    for x in a for y in b
                ]
                self.play(*pulses, b.animate.set_fill(YELLOW, opacity=0.6), run_time=0.7)
                self.play(b.animate.set_fill(BLUE_B, opacity=0.15), run_time=0.2)
        self.play(Indicate(layers[-1][0], color=GREEN_C, scale_factor=1.4))
        self.wait()
