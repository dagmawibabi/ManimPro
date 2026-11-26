from manim import *


class Ripple3D(ThreeDScene):
    """A rippling 3D surface with a slowly orbiting camera."""

    def construct(self):
        axes = ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[-1.5, 1.5], x_length=6, y_length=6, z_length=3)
        surface = Surface(
            lambda u, v: axes.c2p(u, v, 0.8 * np.cos(np.sqrt(u * u + v * v) * 2) * np.exp(-0.15 * (u * u + v * v))),
            u_range=[-3, 3], v_range=[-3, 3], resolution=(36, 36),
        )
        surface.set_style(fill_opacity=0.85, stroke_width=0.4, stroke_color=BLUE_E)
        surface.set_fill_by_checkerboard(BLUE_D, TEAL_D, opacity=0.85)

        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES, zoom=0.9)
        self.play(Create(axes))
        self.play(Create(surface), run_time=2.5)
        self.begin_ambient_camera_rotation(rate=0.25)
        self.wait(5)
        self.stop_ambient_camera_rotation()
