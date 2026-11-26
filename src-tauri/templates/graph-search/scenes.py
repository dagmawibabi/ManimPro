"""Breadth-first vs depth-first search on the same graph, with the queue and stack shown.

An original ManimPro template. Edit NODES and EDGES to search your own graph.
"""
from manim import *

# Node name -> position.
NODES = {
    "A": (-4.6, 0.6), "B": (-2.8, 2.0), "C": (-2.8, -0.8), "D": (-1.0, 2.6), "E": (-1.0, 0.9),
    "F": (-1.0, -1.0), "G": (-1.0, -2.6), "H": (0.8, 1.8), "I": (0.8, -0.2), "J": (0.8, -2.0),
}
EDGES = [("A", "B"), ("A", "C"), ("B", "D"), ("B", "E"), ("C", "F"), ("C", "G"),
         ("D", "H"), ("E", "H"), ("E", "I"), ("F", "I"), ("G", "J"), ("F", "J")]
START = "A"
SHIFT = LEFT * 0.6


def neighbours(n):
    out = [b for a, b in EDGES if a == n] + [a for a, b in EDGES if b == n]
    return sorted(out)


def build_graph():
    dots = {n: VGroup(Circle(radius=0.3, color=GREY_B, fill_color=BLACK, fill_opacity=1, stroke_width=3),
                      Text(n, font_size=24)).move_to([x, y, 0]).shift(SHIFT) for n, (x, y) in NODES.items()}
    lines = {(a, b): Line(dots[a].get_center(), dots[b].get_center(), color=GREY_D, stroke_width=3, buff=0.3) for a, b in EDGES}
    return dots, lines


def edge(lines, a, b):
    return lines.get((a, b)) or lines.get((b, a))


def slot_row(title, color):
    head = Text(title, font_size=24, color=color, weight=BOLD)
    frame = RoundedRectangle(width=4.6, height=0.8, corner_radius=0.15, stroke_color=color)
    group = VGroup(head, frame).arrange(DOWN, buff=0.15, aligned_edge=LEFT).to_corner(UR, buff=0.5).shift(DOWN * 0.8)
    return group


def items_in(frame, names, color):
    boxes = VGroup(*[VGroup(Square(0.55, color=color, fill_opacity=0.25), Text(n, font_size=22)) for n in names])
    if names:
        boxes.arrange(RIGHT, buff=0.08).move_to(frame).align_to(frame, LEFT).shift(RIGHT * 0.15)
    return boxes


def run(scene, kind, color):
    dots, lines = build_graph()
    scene.play(LaggedStart(*[Create(l) for l in lines.values()], lag_ratio=0.05),
               LaggedStart(*[GrowFromCenter(d) for d in dots.values()], lag_ratio=0.05), run_time=1.5)
    box = slot_row("Queue (first in, first out)" if kind == "bfs" else "Stack (last in, first out)", color)
    order_label = Text("Visit order:", font_size=24, color=GREY_B).next_to(box, DOWN, buff=0.6, aligned_edge=LEFT)
    scene.play(FadeIn(box), FadeIn(order_label))

    frontier = [START]
    seen = {START}
    order = VGroup()
    shown = items_in(box[1], frontier, color)
    scene.play(FadeIn(shown), dots[START][0].animate.set_stroke(color, 4))
    while frontier:
        n = frontier.pop(0) if kind == "bfs" else frontier.pop()
        tag = Text(n, font_size=26, color=color)
        if len(order):
            tag.next_to(order, RIGHT, buff=0.22)
        else:
            tag.next_to(order_label, DOWN, buff=0.2, aligned_edge=LEFT)
        order.add(tag)
        scene.play(dots[n][0].animate.set_fill(color, 0.85), FadeIn(tag, shift=DOWN * 0.15), run_time=0.45)
        new = [m for m in neighbours(n) if m not in seen]
        if kind == "dfs":
            new = list(reversed(new))
        anims = []
        for m in new:
            seen.add(m)
            frontier.append(m)
            anims += [edge(lines, n, m).animate.set_stroke(color, 5), dots[m][0].animate.set_stroke(color, 4)]
        nxt = items_in(box[1], frontier, color)
        scene.play(*anims, Transform(shown, nxt), run_time=0.55)
    return dots, order


class BreadthFirst(Scene):
    """Scene 1: a queue makes the search spread out in rings around the start."""

    def construct(self):
        title = Text("Breadth-first search", font_size=40, weight=BOLD).to_edge(UP, buff=0.3).shift(LEFT * 3)
        self.play(Write(title))
        run(self, "bfs", BLUE_C)
        note = Text("Nearest nodes first: ring by ring", font_size=26, color=BLUE_B).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(1.5)


class DepthFirst(Scene):
    """Scene 2: swap the queue for a stack and the search dives down one path first."""

    def construct(self):
        title = Text("Depth-first search", font_size=40, weight=BOLD).to_edge(UP, buff=0.3).shift(LEFT * 3)
        self.play(Write(title))
        run(self, "dfs", ORANGE)
        note = Text("One path as deep as it goes, then back up", font_size=26, color=ORANGE).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(note, shift=UP * 0.2))
        self.wait(1.5)
