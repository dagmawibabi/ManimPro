from manim import *

SOURCE = '''def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

print(fibonacci(10))  # 55'''


class CodeWalkthrough(Scene):
    """Show a code snippet and highlight it line by line."""

    def construct(self):
        code = Code(code_string=SOURCE, language="python", background="window", formatter_style="monokai")
        code.scale(0.9)
        title = Text("Walking through the code", font_size=32).to_edge(UP)
        self.play(FadeIn(title), FadeIn(code, shift=UP * 0.3))

        lines = code.code_lines
        notes = [
            "define a function",
            "start with 0 and 1",
            "repeat n times",
            "slide the pair forward",
            "return the answer",
        ]
        box = SurroundingRectangle(lines[0], color=YELLOW, buff=0.08)
        note = Text(notes[0], font_size=26, color=YELLOW).next_to(code, DOWN, buff=0.4)
        self.play(Create(box), FadeIn(note))
        for i in range(1, len(notes)):
            new_box = SurroundingRectangle(lines[i], color=YELLOW, buff=0.08)
            new_note = Text(notes[i], font_size=26, color=YELLOW).next_to(code, DOWN, buff=0.4)
            self.play(Transform(box, new_box), FadeTransform(note, new_note), run_time=0.8)
            note = new_note
            self.wait(0.4)
        self.wait()
