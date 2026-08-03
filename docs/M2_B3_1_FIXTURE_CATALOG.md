# M2-B3.1 Fixture Catalog

## HELLO_V1

**Purpose:** Basic text animation smoke test  
**Scene:** `HelloScene` in `scenes/hello_scene.py`  
**Fixture:** `fixtures/hello.json`  
**LaTeX required:** No  
**Font required:** System default (any)

**Content:** Renders "Hello Math Studio" with a write animation, followed by a subtitle fade-in.

**Expected output:**
- `render.mp4` — 854×480, H.264, 15fps, ~4s
- `poster.png` — First frame PNG

---

## MATHTEX_SMOKE_V1

**Purpose:** LaTeX math rendering via dvisvgm  
**Scene:** `MathTexSmokeScene` in `scenes/mathtex_scene.py`  
**Fixture:** `fixtures/mathtex.json`  
**LaTeX required:** YES (only works in Docker image)  
**Font required:** TeX math fonts (included in texlive)

**Content:** Renders `f(x) = x² - 3x + 2` with a highlight rectangle, then transforms to factored form `f(x) = (x-1)(x-2)` using `TransformMatchingTex`.

**Expected output:**
- `render.mp4` — 854×480, H.264, 15fps, ~5s

---

## VIETNAMESE_TEXT_V1

**Purpose:** Unicode / Pango Vietnamese text rendering  
**Scene:** `VietnameseTextScene` in `scenes/vietnamese_text_scene.py`  
**Fixture:** `fixtures/vietnamese_text.json`  
**LaTeX required:** No  
**Font required:** Noto Sans (or fallback)

**Content:** Renders "Đạo hàm là hệ số góc của tiếp tuyến" with an English subtitle.

**Expected output:**
- `render.mp4` — 854×480, H.264, 15fps, ~5s

---

## GEOMETRY_SMOKE_V1

**Purpose:** Shapes, labels, and transformation smoke test  
**Scene:** `GeometrySmokeScene` in `scenes/geometry_smoke_scene.py`  
**Fixture:** `fixtures/geometry_smoke.json`  
**LaTeX required:** No  
**Font required:** System default

**Content:** Renders a circle (C) and triangle (T) with an origin dot, then applies a deterministic scale + rotation transformation.

**Expected output:**
- `render.mp4` — 854×480, H.264, 15fps, ~6s
