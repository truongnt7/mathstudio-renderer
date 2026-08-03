"""HELLO_V1 — Hello Math Studio text animation smoke test."""

from manim import *  # noqa: F401, F403


class HelloScene(Scene):
    """Renders 'Hello Math Studio' with a write animation."""

    def construct(self) -> None:
        title = Text("Hello Math Studio", font_size=52, weight=BOLD)
        subtitle = Text("Manim Renderer Runtime · M2-B3.1", font_size=24, color=GRAY)
        subtitle.next_to(title, DOWN, buff=0.4)

        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.8)
        self.wait(1.5)
        self.play(FadeOut(title), FadeOut(subtitle), run_time=0.8)
