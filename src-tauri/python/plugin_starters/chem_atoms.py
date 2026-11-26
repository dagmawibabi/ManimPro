"""Atoms and elements with manim-chemistry."""
from manim import *
from manim_chemistry import BohrAtom, MElementObject


class Carbon(Scene):
    def construct(self):
        tile = MElementObject(atomic_number=6, atomic_mass=12.011, element_name="Carbon", element_symbol="C").scale(1.4)
        tile.to_edge(LEFT, buff=1.2)
        atom = BohrAtom(e=6, p=6, n=6).scale(0.8).to_edge(RIGHT, buff=1.2)
        self.play(FadeIn(tile, shift=RIGHT * 0.3))
        self.play(Create(atom), run_time=2)
        self.play(Rotate(atom, angle=PI, run_time=3))
        self.wait()
