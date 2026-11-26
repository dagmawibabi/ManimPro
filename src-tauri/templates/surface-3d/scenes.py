"""Functions of two variables: a surface, then slices through it.

An original ManimPro template. Change f to plot your own surface.
"""
from manim import *
import numpy as np


def f(x, y):
    return 0.9 * np.sin(x) * np.cos(y) + 0.15 * x


def axes3d():
    return ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-2, 2, 1], x_length=6, y_length=6, z_length=3.2)


def surface(axes):
    s = Surface(lambda u, v: axes.c2p(u, v, f(u, v)), u_range=[-3, 3], v_range=[-3, 3], resolution=(28, 28))
    s.set_style(fill_opacity=0.85, stroke_width=0.4, stroke_color=BLUE_E)
    s.set_fill_by_value(axes=axes, colorscale=[(BLUE_E, -1.4), (BLUE_C, 0), (YELLOW, 1.4)], axis=2)
    return s


class Surface3D(ThreeDScene):
    """Scene 1: z = f(x, y) rises out of the plane while the camera orbits."""

    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES, zoom=0.9)
        title = Text("A function of two variables", font_size=38, weight=BOLD).to_edge(UP)
        formula = Text("z = 0.9·sin(x)·cos(y) + 0.15·x", font_size=26, color=GREY_B).next_to(title, DOWN, buff=0.2)
        self.add_fixed_in_frame_mobjects(title, formula)
        self.play(Write(title), FadeIn(formula))
        axes = axes3d()
        flat = Surface(lambda u, v: axes.c2p(u, v, 0), u_range=[-3, 3], v_range=[-3, 3], resolution=(28, 28))
        flat.set_style(fill_color=BLUE_E, fill_opacity=0.4, stroke_width=0.4, stroke_color=BLUE_D)
        self.play(Create(axes), FadeIn(flat))
        surf = surface(axes)
        self.play(Transform(flat, surf), run_time=2.5)
        self.begin_ambient_camera_rotation(rate=0.35)
        self.wait(5)
        self.stop_ambient_camera_rotation()
        note = Text("Every point (x, y) on the floor gets a height", font_size=26, color=YELLOW_B).to_edge(DOWN, buff=0.4)
        self.add_fixed_in_frame_mobjects(note)
        self.play(FadeIn(note))
        self.wait(1.5)


class Slices(ThreeDScene):
    """Scene 2: hold y fixed and the surface becomes an ordinary curve."""

    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-80 * DEGREES, zoom=0.9)
        axes = axes3d()
        surf = surface(axes).set_fill(opacity=0.35)
        title = Text("Slicing the surface", font_size=38, weight=BOLD).to_edge(UP)
        self.add_fixed_in_frame_mobjects(title)
        self.add(axes, surf)
        self.play(Write(title))

        y = ValueTracker(-2.5)
        plane = always_redraw(lambda: Surface(
            lambda u, w: axes.c2p(u, y.get_value(), w), u_range=[-3, 3], v_range=[-2, 2], resolution=(2, 2),
        ).set_style(fill_color=GREY_B, fill_opacity=0.18, stroke_width=0))
        curve = always_redraw(lambda: ParametricFunction(
            lambda t: axes.c2p(t, y.get_value(), f(t, y.get_value())), t_range=[-3, 3], color=YELLOW, stroke_width=6,
        ))
        label = Text("y = −2.5", font_size=28, color=YELLOW).to_corner(UR, buff=0.6)
        self.add_fixed_in_frame_mobjects(label)
        label.add_updater(lambda m: m.become(Text(f"y = {y.get_value():+.1f}", font_size=28, color=YELLOW).to_corner(UR, buff=0.6)))
        self.play(FadeIn(plane), Create(curve))
        self.play(y.animate.set_value(2.5), run_time=6, rate_func=there_and_back_with_pause)
        label.clear_updaters()
        note = Text("Each slice is a 1D graph: that's what a partial derivative looks at", font_size=24, color=GREY_A)
        note.to_edge(DOWN, buff=0.4)
        self.add_fixed_in_frame_mobjects(note)
        self.play(FadeIn(note))
        self.move_camera(theta=-60 * DEGREES, run_time=2)
        self.wait(1)
