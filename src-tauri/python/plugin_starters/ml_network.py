"""A neural network with ManimML: layers drawn for you, with a forward-pass animation."""
from manim import *
from manim_ml.neural_network import FeedForwardLayer, NeuralNetwork


class Network(Scene):
    def construct(self):
        network = NeuralNetwork(
            [FeedForwardLayer(3), FeedForwardLayer(5), FeedForwardLayer(5), FeedForwardLayer(2)],
            layer_spacing=0.6,
        )
        network.scale(1.4)  # ManimML's scale() doesn't return the network, so it gets its own line
        title = Text("A forward pass", font_size=36).to_edge(UP)
        self.play(Write(title), FadeIn(network))
        self.play(network.make_forward_pass_animation(), run_time=3)
        self.wait()
