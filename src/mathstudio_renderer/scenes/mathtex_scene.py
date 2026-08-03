"""MATHTEX_SMOKE_V1 — LaTeX math expression rendering via dvisvgm.

This scene proves LaTeX + dvisvgm are functional inside the Docker image.
Expression: f(x) = x² - 3x + 2
"""

from manim import *  # noqa: F401, F403


class MathTexSmokeScene(Scene):
    """LaTeX quadratic expression with highlight transformation."""

    def construct(self) -> None:
        label = Text("MathTex Smoke Test", font_size=24, color=GRAY)
        label.to_edge(UP)

        expr = MathTex(r"f(x) = x^2 - 3x + 2", font_size=60)
        expr.move_to(ORIGIN)

        self.play(Write(label), run_time=0.6)
        self.play(Write(expr), run_time=1.5)
        self.wait(0.5)

        # Highlight the expression with a surrounding rectangle
        highlight = SurroundingRectangle(expr, color=YELLOW, buff=0.25, corner_radius=0.1)
        self.play(Create(highlight), run_time=0.8)
        self.wait(0.8)

        # Transform to factored form
        factored = MathTex(r"f(x) = (x - 1)(x - 2)", font_size=60)
        factored.move_to(ORIGIN)
        self.play(
            TransformMatchingTex(expr, factored),
            FadeOut(highlight),
            run_time=1.5,
        )
        self.wait(1.0)
        self.play(FadeOut(factored), FadeOut(label), run_time=0.6)
