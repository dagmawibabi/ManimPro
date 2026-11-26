from manim import *


class Pendulum(Scene):
    """A damped pendulum, simulated step by step, leaves a fading trail."""

    def construct(self):
        pivot = UP * 2.5
        length = 3.5
        state = {"theta": 1.1, "omega": 0.0}

        rod = Line(pivot, pivot + DOWN * length, color=GREY_B)
        bob = Circle(radius=0.25, color=ORANGE, fill_opacity=1)
        ceiling = Line(pivot + LEFT * 1.5, pivot + RIGHT * 1.5, color=GREY_C)

        def place():
            p = pivot + length * np.array([np.sin(state["theta"]), -np.cos(state["theta"]), 0])
            rod.put_start_and_end_on(pivot, p)
            bob.move_to(p)

        def step(mob, dt):
            g, damping = 9.8, 0.25
            alpha = -(g / length) * np.sin(state["theta"]) - damping * state["omega"]
            state["omega"] += alpha * dt
            state["theta"] += state["omega"] * dt
            place()

        place()
        trail = TracedPath(bob.get_center, stroke_color=ORANGE, stroke_width=3, dissipating_time=1.2)
        self.add(ceiling, trail, rod, bob)
        rod.add_updater(step)
        self.wait(8)
        rod.remove_updater(step)
