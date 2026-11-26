"""A ManimGL scene (3Blue1Brown's version of Manim).

`from manimlib import *` tells ManimPro to render this file with ManimGL. Its API differs a
little from Manim Community: ShowCreation instead of Create, InteractiveScene for live tinkering.
"""
from manimlib import *


class GLIntro(Scene):
    def construct(self):
        plane = NumberPlane()
        graph = FunctionGraph(lambda x: 0.5 * x**2 - 2, x_range=(-3, 3, 0.05), color=YELLOW)
        label = Text("Rendered with ManimGL").to_edge(UP)
        self.play(ShowCreation(plane, lag_ratio=0.1), Write(label))
        self.play(ShowCreation(graph))
        dot = Dot(color=RED).move_to(graph.get_start())
        self.play(FadeIn(dot))
        self.play(MoveAlongPath(dot, graph), run_time=2)
        self.wait()
