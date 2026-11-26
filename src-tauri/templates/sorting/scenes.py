"""Bubble sort vs merge sort: the same list, and how many comparisons each one needs.

An original ManimPro template. Change VALUES to sort a different list.
"""
from manim import *

VALUES = [7, 3, 9, 1, 6, 2, 8, 4]
BAR_W = 0.7


def bars_for(values, color=BLUE_C):
    bars = VGroup()
    for v in values:
        rect = Rectangle(width=BAR_W, height=0.42 * v, fill_color=color, fill_opacity=0.85, stroke_width=0)
        num = Text(str(v), font_size=22).next_to(rect, DOWN, buff=0.12)
        bars.add(VGroup(rect, num))
    bars.arrange(RIGHT, buff=0.22, aligned_edge=DOWN)
    return bars


def counter(label, color):
    t = Text(f"{label}: 0", font_size=26, color=color)
    return t


class Title(Scene):
    """Scene 1: two ways to sort the same list."""

    def construct(self):
        title = Text("Two ways to sort", font_size=52, weight=BOLD)
        sub = Text("Bubble sort swaps neighbours. Merge sort splits, then merges.", font_size=28, color=GREY_B)
        sub.next_to(title, DOWN, buff=0.4)
        bars = bars_for(VALUES).scale(0.6).next_to(sub, DOWN, buff=0.6)
        self.play(Write(title))
        self.play(FadeIn(sub, shift=UP * 0.2))
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.1))
        self.wait(1.2)


class BubbleSort(Scene):
    """Scene 2: neighbours compare and swap; the biggest bubbles to the end each pass."""

    def construct(self):
        title = Text("Bubble sort", font_size=40, weight=BOLD).to_edge(UP)
        values = list(VALUES)
        bars = bars_for(values).move_to(DOWN * 0.4)
        count = counter("Comparisons", YELLOW).to_corner(UR)
        self.play(Write(title), FadeIn(bars), FadeIn(count))
        n, comps = len(values), 0
        for end in range(n - 1, 0, -1):
            for i in range(end):
                comps += 1
                a, b = bars[i], bars[i + 1]
                new_count = counter("Comparisons", YELLOW).to_corner(UR)
                new_count.become(Text(f"Comparisons: {comps}", font_size=26, color=YELLOW).to_corner(UR))
                self.play(a[0].animate.set_fill(YELLOW), b[0].animate.set_fill(YELLOW), Transform(count, new_count), run_time=0.14)
                if values[i] > values[i + 1]:
                    values[i], values[i + 1] = values[i + 1], values[i]
                    self.play(a.animate.move_to(b, aligned_edge=DOWN), b.animate.move_to(a, aligned_edge=DOWN), run_time=0.22)
                    bars.submobjects[i], bars.submobjects[i + 1] = b, a
                self.play(bars[i][0].animate.set_fill(BLUE_C), bars[i + 1][0].animate.set_fill(BLUE_C), run_time=0.06)
            self.play(bars[end][0].animate.set_fill(GREEN_C), run_time=0.12)
        self.play(bars[0][0].animate.set_fill(GREEN_C))
        note = Text(f"{comps} comparisons: about n²/2 for n = {n}", font_size=28, color=GREY_A).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(1.5)


class MergeSort(Scene):
    """Scene 3: split down to single items, then merge sorted halves back together."""

    def construct(self):
        title = Text("Merge sort", font_size=40, weight=BOLD).to_edge(UP)
        count = Text("Comparisons: 0", font_size=26, color=YELLOW).to_corner(UR)
        self.play(Write(title), FadeIn(count))

        def row(groups, y, color=BLUE_C):
            cells = VGroup()
            for g in groups:
                box = VGroup(*[VGroup(Square(0.55, color=color, fill_opacity=0.25), Text(str(v), font_size=22)) for v in g])
                box.arrange(RIGHT, buff=0.04)
                cells.add(box)
            cells.arrange(RIGHT, buff=0.45).move_to([0, y, 0])
            return cells

        levels = [[list(VALUES)]]
        while any(len(g) > 1 for g in levels[-1]):
            nxt = []
            for g in levels[-1]:
                if len(g) > 1:
                    m = len(g) // 2
                    nxt += [g[:m], g[m:]]
                else:
                    nxt.append(g)
            levels.append(nxt)
        ys = [2.0 - 1.05 * i for i in range(len(levels))]
        rows = [row(l, y) for l, y in zip(levels, ys)]
        self.play(FadeIn(rows[0]))
        split = Text("Split in half until each piece has one item", font_size=26, color=GREY_B).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(split))
        for a, b in zip(rows[:-1], rows[1:]):
            self.play(TransformFromCopy(a, b), run_time=0.8)
        self.wait(0.4)

        merge_note = Text("Merge pairs: compare the fronts, take the smaller", font_size=26, color=GREY_B).to_edge(DOWN, buff=0.35)
        self.play(Transform(split, merge_note))
        comps = 0
        groups = levels[-1]
        current = rows[-1]
        level = len(rows) - 1
        while len(groups) > 1:
            merged = []
            for i in range(0, len(groups), 2):
                if i + 1 == len(groups):
                    merged.append(groups[i])
                    continue
                a, b, out = list(groups[i]), list(groups[i + 1]), []
                while a and b:
                    comps += 1
                    out.append(a.pop(0) if a[0] <= b[0] else b.pop(0))
                merged.append(out + a + b)
            groups = merged
            level -= 1
            # Merged pieces rise to the row above, replacing the unsorted pieces there.
            nxt = row(groups, ys[level], GREEN_C)
            new_count = Text(f"Comparisons: {comps}", font_size=26, color=YELLOW).to_corner(UR)
            self.play(FadeOut(rows[level]), Transform(current, nxt), Transform(count, new_count), run_time=1.1)
            self.wait(0.3)
        self.play(current.animate.move_to(DOWN * 0.3).scale(1.3))
        note = Text(f"{comps} comparisons: about n·log₂n — far fewer on big lists", font_size=28, color=GREY_A).to_edge(DOWN, buff=0.35)
        self.play(Transform(split, note), Circumscribe(current, color=GREEN_C))
        self.wait(1.5)
