from manim import *

# Needs LaTeX (MathTex). Install it from ManimPro's status bar if renders ask for it.


class SolveEquation(Scene):
    """Solve a linear equation step by step; matching terms glide into place."""

    def construct(self):
        steps = [
            MathTex("3x", "+", "5", "=", "20"),
            MathTex("3x", "=", "20", "-", "5"),
            MathTex("3x", "=", "15"),
            MathTex("x", "=", r"\frac{15}{3}"),
            MathTex("x", "=", "5"),
        ]
        notes = ["Start", "Move 5 across", "Simplify", "Divide by 3", "Solved"]
        for s in steps:
            s.scale(1.6)
        current = steps[0]
        note = Text(notes[0], font_size=30, color=GREY_B).to_edge(DOWN)
        self.play(Write(current), FadeIn(note))
        for nxt, text in zip(steps[1:], notes[1:]):
            new_note = Text(text, font_size=30, color=GREY_B).to_edge(DOWN)
            self.play(TransformMatchingTex(current, nxt), FadeTransform(note, new_note), run_time=1.3)
            current, note = nxt, new_note
            self.wait(0.4)
        self.play(Circumscribe(current, color=YELLOW))
        self.wait()
