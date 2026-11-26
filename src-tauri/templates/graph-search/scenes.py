from manim import *

EDGES = [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7), (5, 8), (6, 8), (7, 9), (8, 10), (9, 10)]


class BreadthFirst(Scene):
    """Breadth-first search spreads out from a start node, layer by layer."""

    def construct(self):
        vertices = sorted({v for e in EDGES for v in e})
        graph = Graph(
            vertices, EDGES, layout="kamada_kawai", layout_scale=3.2,
            vertex_config={"radius": 0.22, "color": GREY_B}, edge_config={"stroke_color": GREY_D},
        )
        title = Text("Breadth-first search", font_size=36).to_edge(UP)
        self.play(Create(graph), FadeIn(title), run_time=2)

        adjacency = {v: [] for v in vertices}
        for a, b in EDGES:
            adjacency[a].append(b)
            adjacency[b].append(a)
        seen, frontier = {1}, [1]
        colors = [YELLOW, ORANGE, RED_C, PINK, PURPLE_B, BLUE_C]
        self.play(graph.vertices[1].animate.set_color(colors[0]).scale(1.3))
        depth = 0
        while frontier:
            depth += 1
            nxt, anims = [], []
            for v in frontier:
                for w in adjacency[v]:
                    if w not in seen:
                        seen.add(w)
                        nxt.append(w)
                        edge = graph.edges.get((v, w)) or graph.edges.get((w, v))
                        anims += [edge.animate.set_color(colors[depth % len(colors)]).set_stroke(width=6),
                                  graph.vertices[w].animate.set_color(colors[depth % len(colors)])]
            if anims:
                self.play(*anims, run_time=0.8)
            frontier = nxt
        self.wait()
