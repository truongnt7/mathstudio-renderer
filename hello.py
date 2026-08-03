from manim import *

class Hello(Scene):
    def construct(self):
        text = Text("Hello Math Studio")
        self.play(Write(text))
        self.wait(2)
