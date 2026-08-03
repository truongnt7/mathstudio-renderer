"""VIETNAMESE_TEXT_V1 — Unicode / Pango Vietnamese text rendering.

Renders: Đạo hàm là hệ số góc của tiếp tuyến
(Translation: The derivative is the slope of the tangent line)

Uses an explicit open-source Vietnamese-capable font (Noto Sans).
Falls back gracefully if the font is not registered.
"""

from manim import *  # noqa: F401, F403

# Primary font with full Vietnamese Unicode support
_PRIMARY_FONT = "Noto Sans"
# Fallback chain for environments without Noto Sans
_FALLBACK_FONTS = ["Liberation Sans", "DejaVu Sans", "sans-serif"]


def _resolve_font() -> str:
    try:
        import manimpango  # type: ignore[import-untyped]

        available = [f.lower() for f in manimpango.list_fonts()]
        for font in [_PRIMARY_FONT, *_FALLBACK_FONTS]:
            if font.lower() in available:
                return font
    except Exception:  # noqa: BLE001,S110
        pass
    return _PRIMARY_FONT  # Let Manim/Pango fall back naturally


class VietnameseTextScene(Scene):
    """Vietnamese calculus definition with write/transform animations."""

    def construct(self) -> None:
        font = _resolve_font()

        # Main Vietnamese text
        main_text = Text(
            "Đạo hàm là hệ số góc của tiếp tuyến",
            font=font,
            font_size=36,
        )

        # English subtitle
        sub_text = Text(
            "The derivative is the slope of the tangent line",
            font=font,
            font_size=22,
            color=GRAY_B,
        )
        sub_text.next_to(main_text, DOWN, buff=0.5)

        label = Text("Vietnamese Text Smoke Test", font_size=20, color=GRAY)
        label.to_edge(UP)

        self.play(Write(label), run_time=0.5)
        self.play(Write(main_text), run_time=2.0)
        self.play(FadeIn(sub_text, shift=UP * 0.1), run_time=0.8)
        self.wait(2.0)
        self.play(FadeOut(main_text), FadeOut(sub_text), FadeOut(label), run_time=0.8)
