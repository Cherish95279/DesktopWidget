# DesktopWidget Theme Development Guide

This document is intended for theme designers and developers. It explains how to create an importable theme archive from scratch.

---

## 1. Canvas Specifications

| Item                                    | Value                     |
| --------------------------------------- | ------------------------- |
| Canvas size (W × H)                     | **400 × 297 pixels**      |
| Clock center coordinates                | **(201, 144)**            |
| Fixed window size                       | 400 × 297 (not resizable) |
| Hand rotation pivot (image coordinates) | **(199, 143)**            |

> All 5 images **must** have a pixel size of **400 × 297**, matching the canvas.

> Images are drawn onto the canvas aligned to the top-left corner (0,0), without scaling.

---

## 2. Theme File List

A theme consists of the following images:

| File name         |  Required  | Description                                                      |
| ----------------- | :--------: | ---------------------------------------------------------------- |
| `bg.png`          | ✅ Required | Background layer, drawn first; affected by opacity/tint          |
| `face.png`        | ✅ Required | Clock face layer, drawn above the background and below the hands |
| `Hour_Hand.png`   |  Optional  | Hour hand; falls back to the default theme hand if missing       |
| `Minute_Hand.png` |  Optional  | Minute hand; falls back to the default theme hand if missing     |
| `Second_Hand.png` |  Optional  | Second hand; falls back to the default theme hand if missing     |

> `bg.png` and `face.png` **must both be present** for the theme to be considered valid. Otherwise, the import validation will fail.

---

## 3. Layer Drawing Order

Layers are drawn from bottom to top in the following order:

1. **`bg.png`** — Background layer

   * Controlled by the "Opacity" slider (20%–100%)
   * Controlled by "Tint Intensity": the user-selected background color is overlaid using the `SourceAtop` blend mode
   * A semi-transparent or tintable base color is recommended; pure white/black may affect the tinting effect

2. **`face.png`** — Clock face layer

   * Not affected by opacity/tint settings; drawn as-is
   * Suitable for clock markings, numbers, decorative borders, and clock center decorations

3. **`Hour_Hand.png`** — Hour hand (rotated when drawn)

4. **`Minute_Hand.png`** — Minute hand (rotated when drawn)

5. **`Second_Hand.png`** — Second hand (rotated when drawn)

6. **Text information** — 8 display items are drawn by the program on the topmost layer (see Section 5)

---

## 4. Hand Drawing Specifications (Important)

### 4.1 Hand Image Size

Each hand image must also be **400 × 297 pixels**. The remaining area of the canvas must remain **transparent** (RGBA, alpha=0).

### 4.2 Hand Orientation: Must Point to 12 O'Clock

In the source image's **unrotated state (0°)**, the hand must point straight upward (12 o'clock).

* 0° = pointing up (12 o'clock)
* Clockwise rotation
* 90° = pointing right (3 o'clock)
* 180° = pointing down (6 o'clock)
* 270° = pointing left (9 o'clock)

> Design guideline: On the 400 × 297 canvas, draw the hand as a shape **extending upward from the center (199,143)**.

### 4.3 Hand Rotation Center (Pivot)

When drawing the hand, the program performs the following transformations:

```text
1. Translate to the canvas center (201, 144)

2. Rotate by the specified angle

3. Draw the hand image at (-199, -143)
```

This means that the **(199, 143) pixel point** inside the hand image will align with the canvas center (201, 144).

| Coordinate       | X   | Y   | Description                                               |
| ---------------- | --- | --- | --------------------------------------------------------- |
| Canvas center    | 201 | 144 | Clock rotation center                                     |
| Hand image pivot | 199 | 143 | Pixel in the hand image that should align with the center |

> Design guideline: The rotation axis of the hand (the tip of the tail or the center dot) should be placed at **(199, 143)** in the image.

> The hand body should extend upward from this point. Its length can be designed freely, but it should not exceed the canvas boundaries.

### 4.4 Rotation Angle Formula

| Hand        | Angle calculation                 | Step per unit                  |
| ----------- | --------------------------------- | ------------------------------ |
| Hour hand   | (hour % 12) × 30° + minute × 0.5° | 30° per hour, 0.5° per minute  |
| Minute hand | minute × 6° + second × 0.1°       | 6° per minute, 0.1° per second |
| Second hand | second × 6°                       | 6° per second                  |

---

## 5. Positions of the Eight Display Items

The program draws 8 text information slots on top of the images. Each slot is a rectangular area `(x, y, width, height)`.

Text is left-aligned and vertically centered. When designing a theme, **avoid these areas** or leave a background with sufficient contrast in these areas.

### 5.1 Slot Coordinate Table

| Slot   | X   | Y   | Width W | Height H | Default content                                |
| ------ | --- | --- | ------- | -------- | ---------------------------------------------- |
| slot_1 | 20  | 30  | 105     | 43       | Weather (city/weather/temperature, two lines)  |
| slot_2 | 20  | 86  | 85      | 43       | Network speed (↓ download/↑ upload, two lines) |
| slot_3 | 20  | 166 | 70      | 50       | Resolution                                     |
| slot_4 | 20  | 235 | 88      | 50       | Date (date/day of week, two lines)             |
| slot_5 | 280 | 30  | 94      | 43       | IP address                                     |
| slot_6 | 314 | 86  | 71      | 43       | GPU usage                                      |
| slot_7 | 324 | 166 | 60      | 50       | Memory (label/percentage, two lines)           |
| slot_8 | 273 | 238 | 97      | 43       | Total disk usage (label/percentage, two lines) |

> Users can customize the content displayed in each slot in Settings, but the **position of each slot remains fixed**.

> For multi-line content, the height H is divided equally into two lines, with each line having a height of H/2.

### 5.2 Slot Layout Diagram

```text
(0,0)──────────── 400 ────────────┐
│                                  │
│  slot_1             slot_5      │  ← Y=30
│  (20,30,105,43)    (280,30,94,43)│
│                                  │
│  slot_2             slot_6      │  ← Y=86
│  (20,86,85,43)     (314,86,71,43)│
│                                  │
│          ◷ Clock center          │
│             (201,144)            │
│                                  │
│  slot_3             slot_7      │  ← Y=166
│  (20,166,70,50)    (324,166,60,50)│
│                                  │
│  slot_4             slot_8      │  ← Y=235
│  (20,235,88,50)    (273,238,97,43)│
│                                  │
└──────────────────────────────────┘ 297
```

### 5.3 Available Content Types

A slot can be configured to display any one of the following content types (selected by the user in Settings):

| Content key | Description       | Format example                          |
| ----------- | ----------------- | --------------------------------------- |
| weather     | Weather           | ☀️ Clear 25°C (two lines: city/weather) |
| netspeed    | Network speed     | ↓12.3Mb/s / ↑4.5Mb/s (two lines)        |
| resolution  | Screen resolution | 1920×1080                               |
| date        | Date              | 2026/08/31 / Sunday (two lines)         |
| ip          | IP address        | 192.168.1.1                             |
| gpu         | GPU usage         | GPU45%                                  |
| memory      | Memory            | Memory / 65% (two lines)                |
| disk_total  | Total disk usage  | Disk / 70% (two lines)                  |
| cpu         | CPU usage         | CPU30%                                  |
| uptime      | Uptime            | 2h15m                                   |
| lunar       | Lunar calendar    | Eighth month, ninth day                 |
| term        | Solar term        | Chushu                                  |
| empty       | Empty             | (Not displayed)                         |

---

## 6. Fonts and Colors

Text information is drawn by the program. Theme designers do not need to include text in the images. The font settings read by the program are:

| Setting     | Default value   | Description       |
| ----------- | --------------- | ----------------- |
| font_family | Microsoft YaHei | User configurable |
| font_size   | 10              | User configurable |
| font_color  | #1c344d         | User configurable |

> Theme design recommendation: Use a relatively light or dark solid-color background in these text areas,

> to ensure sufficient contrast with the user-configurable font color.

---

## 7. Background Tinting Mechanism (Important)

`bg.png` is overlaid with a user-selected background color by the program, using the `SourceAtop` blend mode:

* User-selectable colors: Classic Dark #1c344d / Light Theme #f0f0f0 / Light Blue-Gray #a8c7dc / Custom
* Tint intensity slider: 0–255 (default 80), with higher alpha producing a stronger color
* `SourceAtop` mode: The color only covers **opaque** pixel areas of `bg.png`

> Design recommendations:

> * Transparent areas of `bg.png` remain transparent after tinting
> * Semi-transparent areas of `bg.png` blend with the color and can be used to create gradient effects
> * `face.png` is not affected by tinting and is suitable for fixed decorations that should not change color

---

## 8. Archive Creation Specifications

### 8.1 Directory Structure (Recommended: Folder Structure)

The archive contains a folder named after the theme. The folder contains 5 images:

```text
My Theme.zip

└── My Theme/
    ├── bg.png            ← Required, 400×297
    ├── face.png          ← Required, 400×297
    ├── Hour_Hand.png     ← Optional, 400×297, hand points to 12 o'clock
    ├── Minute_Hand.png   ← Optional, 400×297, hand points to 12 o'clock
    └── Second_Hand.png   ← Optional, 400×297, hand points to 12 o'clock
```

> The folder name is displayed as the theme name in the dropdown list and supports Chinese characters.

### 8.2 Directory Structure (Compatible: Flat Structure)

The assets are placed directly in the root of the archive, and the program uses the ZIP filename as the theme name:

```text
My Theme.zip

├── bg.png
├── face.png
├── Hour_Hand.png
├── Minute_Hand.png
└── Second_Hand.png
```

### 8.3 Format Requirements

* Compression format: **ZIP** (.zip)
* Image format: **PNG** (supports transparency; must use RGBA)
* Image size: Uniform **400 × 297 pixels**
* File names: Case-sensitive; use the English names listed above

### 8.4 Validation Rules

The program automatically validates the theme when importing:

| Check                      | Result                                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------------------------ |
| Contains bg.png + face.png | ✅ Validation passed; can be imported                                                                   |
| Missing bg.png or face.png | ❌ Missing bg.png, face.png (specifically lists which file is missing)                                  |
| Missing hand images        | ✅ Validation passed; missing optional assets are reported, and the default hands are used after import |
| No assets at all           | ❌ Archive is missing required assets                                                                   |

### 8.5 Naming Conflicts

If the imported theme name is the same as an existing theme, the program automatically appends `_2`, `_3`, and so on. Existing themes will not be overwritten.

---

## 9. Complete Creation Checklist

1. Create a 400 × 297 pixel canvas with an RGBA transparent background

2. Draw `bg.png`:

   * Background color/texture; will be tinted, while transparent areas remain transparent
   * Avoid the 8 text slot areas or leave a readable background color in those areas

3. Draw `face.png`:

   * Clock markings, numbers, border decorations, and clock center decorations
   * Not affected by tinting; displayed as-is

4. Draw the three hand images (`Hour_Hand.png` / `Minute_Hand.png` / `Second_Hand.png`):

   * 400 × 297 transparent canvas
   * Hand points straight upward (12 o'clock direction)
   * Rotation axis is placed at pixel (199, 143) in the image
   * Hand body extends upward from the axis

5. Export as PNG (preserve the transparency channel)

6. Package as ZIP (either folder structure or flat structure is supported)

7. Go to Settings → Themes, click "Import Theme", select the ZIP file, and import it after validation passes

---

## 10. Key Coordinates Quick Reference

```text
Canvas: 400 × 297

Clock center: (201, 144)

Hand pivot (inside image): (199, 143)

slot_1: x=20  y=30  w=105 h=43   ← Top left

slot_2: x=20  y=86  w=85  h=43

slot_3: x=20  y=166 w=70  h=50

slot_4: x=20  y=235 w=88  h=50   ← Bottom left

slot_5: x=280 y=30  w=94  h=43   ← Top right

slot_6: x=314 y=86  w=71  h=43

slot_7: x=324 y=166 w=60  h=50

slot_8: x=273 y=238 w=97  h=43   ← Bottom right
```
