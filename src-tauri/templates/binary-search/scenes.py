"""Binary search: halve the search range until the target is found.

An original ManimPro template. Change VALUES and TARGET to try other inputs.
"""
from manim import *

VALUES = [2, 5, 8, 12, 16, 23, 31, 34, 37, 41, 48, 53, 60, 67, 75]
TARGET = 37


def make_boxes():
    boxes = VGroup()
    for v in VALUES:
        sq = RoundedRectangle(width=0.72, height=0.72, corner_radius=0.1, stroke_color=GREY_B, stroke_width=2)
        num = Text(str(v), font_size=24)
        boxes.add(VGroup(sq, num))
    boxes.arrange(RIGHT, buff=0.12)
    indexes = VGroup(*[Text(str(i), font_size=16, color=GREY_C).next_to(b, DOWN, buff=0.12) for i, b in enumerate(boxes)])
    return boxes, indexes


def pointer(box, label, color, up=False):
    arrow = Arrow(ORIGIN, DOWN * 0.6 if not up else UP * 0.6, buff=0, color=color, stroke_width=5, max_tip_length_to_length_ratio=0.35)
    tag = Text(label, font_size=22, color=color, weight=BOLD)
    if up:
        arrow.next_to(box, DOWN, buff=0.45)
        tag.next_to(arrow, DOWN, buff=0.05)
    else:
        arrow.next_to(box, UP, buff=0.1)
        tag.next_to(arrow, UP, buff=0.05)
    return VGroup(arrow, tag)


class Intro(Scene):
    """Scene 1: the task."""

    def construct(self):
        title = Text("Binary search", font_size=52, weight=BOLD)
        sub = Text(f"Find {TARGET} in a sorted list without checking every number", font_size=28, color=GREY_B)
        sub.next_to(title, DOWN, buff=0.4)
        self.play(Write(title))
        self.play(FadeIn(sub, shift=UP * 0.2))
        self.wait(1.5)


class Search(Scene):
    """Scene 2: low, middle and high pointers close in on the target."""

    def construct(self):
        boxes, indexes = make_boxes()
        title = Text(f"Looking for {TARGET}", font_size=34).to_edge(UP)
        self.play(Write(title), LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in boxes], lag_ratio=0.05), FadeIn(indexes))

        lo, hi, step = 0, len(VALUES) - 1, 0
        L = pointer(boxes[lo], "L", BLUE_C, up=True)
        R = pointer(boxes[hi], "R", ORANGE, up=True)
        self.play(FadeIn(L), FadeIn(R))
        caption = Text(" ", font_size=26).to_edge(DOWN, buff=0.8)
        found = False
        while lo <= hi:
            step += 1
            mid = (lo + hi) // 2
            M = pointer(boxes[mid], "M", YELLOW)
            new_caption = Text(f"Step {step}:  mid = ({lo} + {hi}) // 2 = {mid}", font_size=26).to_edge(DOWN, buff=0.8)
            self.play(FadeIn(M), Transform(caption, new_caption), boxes[mid][0].animate.set_stroke(YELLOW, 4))
            v = VALUES[mid]
            if v == TARGET:
                verdict = Text(f"{v} = {TARGET}: found it at index {mid}", font_size=26, color=GREEN_C).to_edge(DOWN, buff=0.8)
                self.play(Transform(caption, verdict), boxes[mid][0].animate.set_fill(GREEN_D, 0.7).set_stroke(GREEN_C, 5))
                self.play(Circumscribe(boxes[mid], color=GREEN_C))
                found = True
                break
            if v < TARGET:
                verdict = Text(f"{v} < {TARGET}: drop the left half", font_size=26, color=GREY_A).to_edge(DOWN, buff=0.8)
                dropped = VGroup(*boxes[lo:mid + 1])
                lo = mid + 1
            else:
                verdict = Text(f"{v} > {TARGET}: drop the right half", font_size=26, color=GREY_A).to_edge(DOWN, buff=0.8)
                dropped = VGroup(*boxes[mid:hi + 1])
                hi = mid - 1
            self.play(Transform(caption, verdict))
            self.play(dropped.animate.set_opacity(0.2), FadeOut(M))
            moves = []
            if lo <= hi:
                moves = [L.animate.become(pointer(boxes[lo], "L", BLUE_C, up=True)),
                         R.animate.become(pointer(boxes[hi], "R", ORANGE, up=True))]
            if moves:
                self.play(*moves)
        if not found:
            self.play(Transform(caption, Text(f"{TARGET} is not in the list", font_size=26, color=RED_C).to_edge(DOWN, buff=0.8)))
        self.wait(1)
        summary = Text(f"{step} steps instead of up to {len(VALUES)}: each step halves the range", font_size=26, color=GREY_B)
        summary.next_to(title, DOWN, buff=0.3)
        self.play(FadeIn(summary, shift=DOWN * 0.2))
        self.wait(2)
