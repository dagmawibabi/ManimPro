from manim import *

VALUES = [5, 2, 8, 1, 6, 3, 7, 4]


class BubbleSort(Scene):
    """Bars swap places until they are sorted."""

    def construct(self):
        title = Text("Bubble sort", font_size=40).to_edge(UP)
        width = 0.8
        bars = []
        for i, v in enumerate(VALUES):
            bar = Rectangle(width=width, height=v * 0.55, fill_opacity=0.9, stroke_width=0, fill_color=BLUE_C)
            bar.move_to([(i - (len(VALUES) - 1) / 2) * 1.1, -2.5 + bar.height / 2, 0])
            bars.append(bar)
        self.play(FadeIn(title), LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.08))

        values = VALUES[:]
        n = len(values)
        for end in range(n - 1, 0, -1):
            for i in range(end):
                a, b = bars[i], bars[i + 1]
                self.play(a.animate.set_fill(YELLOW), b.animate.set_fill(YELLOW), run_time=0.15)
                if values[i] > values[i + 1]:
                    ax, bx = a.get_x(), b.get_x()
                    self.play(a.animate.set_x(bx), b.animate.set_x(ax), run_time=0.3)
                    bars[i], bars[i + 1] = b, a
                    values[i], values[i + 1] = values[i + 1], values[i]
                self.play(bars[i].animate.set_fill(BLUE_C), bars[i + 1].animate.set_fill(BLUE_C), run_time=0.1)
            self.play(bars[end].animate.set_fill(GREEN_C), run_time=0.15)
        self.play(bars[0].animate.set_fill(GREEN_C))
        self.wait()
