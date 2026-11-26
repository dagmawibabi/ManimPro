from manim import *


class MyScene(Scene):
    def construct(self):
        title = Text("Your video starts here")
        self.play(Write(title))
        self.wait()
