"""GEOMETRY_SMOKE_V1 — Shapes, labels, and a deterministic transformation.

Renders:
  • A circle with label
  • A triangle with label
  • Point labels
  • One deterministic rotation + scale transformation
"""

from manim import *  # noqa: F401, F403


class GeometrySmokeScene(Scene):
    """Geometry shapes with deterministic transformation smoke test."""

    def construct(self) -> None:
        label = Text("Geometry Smoke Test", font_size=24, color=GRAY)
        label.to_edge(UP)

        # --- Shapes ---
        circle = Circle(radius=1.2, color=BLUE, fill_opacity=0.15)
        circle.shift(LEFT * 2.5)

        triangle = Triangle(color=GREEN, fill_opacity=0.15).scale(1.4)
        triangle.shift(RIGHT * 2.5)

        # --- Point labels ---
        lbl_c = Text("C", font_size=28, color=BLUE).next_to(circle.get_top(), UP, buff=0.1)
        lbl_t = Text("T", font_size=28, color=GREEN).next_to(triangle.get_top(), UP, buff=0.1)

        # --- Center dot ---
        center_dot = Dot(ORIGIN, color=YELLOW, radius=0.08)
        center_lbl = Text("O", font_size=22, color=YELLOW).next_to(center_dot, DOWN, buff=0.1)

        self.play(Write(label), run_time=0.5)
        self.play(
            Create(circle),
            Create(triangle),
            run_time=1.2,
        )
        self.play(
            Write(lbl_c),
            Write(lbl_t),
            GrowFromCenter(center_dot),
            Write(center_lbl),
            run_time=0.8,
        )
        self.wait(0.5)

        # --- Deterministic transformation ---
        # Circle scales down and moves to center; triangle rotates 60°
        self.play(
            circle.animate.scale(0.6).move_to(LEFT * 0.8),
            triangle.animate.rotate(PI / 3).scale(0.6).move_to(RIGHT * 0.8),
            lbl_c.animate.next_to(circle.get_top(), UP, buff=0.1).scale(0.8),
            lbl_t.animate.next_to(triangle.get_top(), UP, buff=0.1).scale(0.8),
            run_time=1.5,
        )
        self.wait(1.0)

        self.play(
            FadeOut(circle),
            FadeOut(triangle),
            FadeOut(lbl_c),
            FadeOut(lbl_t),
            FadeOut(center_dot),
            FadeOut(center_lbl),
            FadeOut(label),
            run_time=0.8,
        )
