from __future__ import annotations

import numpy as np

from app.models import ReliefStyle

DIGIT_PATTERNS: dict[str, list[str]] = {
    "0": [
        " ### ",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        " ### ",
    ],
    "1": [
        "  #  ",
        " ##  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        " ### ",
    ],
    "2": [
        " ### ",
        "#   #",
        "    #",
        "  ## ",
        " #   ",
        "#    ",
        "#####",
    ],
    "3": [
        " ### ",
        "#   #",
        "    #",
        "  ## ",
        "    #",
        "#   #",
        " ### ",
    ],
    "4": [
        "   # ",
        "  ## ",
        " # # ",
        "#  # ",
        "#####",
        "   # ",
        "   # ",
    ],
    "5": [
        "#####",
        "#    ",
        "#### ",
        "    #",
        "    #",
        "#   #",
        " ### ",
    ],
    "6": [
        " ### ",
        "#    ",
        "#    ",
        "#### ",
        "#   #",
        "#   #",
        " ### ",
    ],
    "7": [
        "#####",
        "    #",
        "   # ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
    ],
    "8": [
        " ### ",
        "#   #",
        "#   #",
        " ### ",
        "#   #",
        "#   #",
        " ### ",
    ],
    "9": [
        " ### ",
        "#   #",
        "#   #",
        " ####",
        "    #",
        "    #",
        " ### ",
    ],
}


def get_number_pixels(
    number: int,
    center_x: float,
    center_y: float,
    char_height_mm: float,
) -> list[tuple[float, float, float, float]]:
    """Return list of (x, y, width, height) rectangles for active pixels of a number."""
    text = str(number)
    char_width_mm = char_height_mm * 5 / 7

    total_width = len(text) * char_width_mm + (len(text) - 1) * char_width_mm * 0.3
    start_x = center_x - total_width / 2

    pixels: list[tuple[float, float, float, float]] = []
    cursor_x = start_x

    for ch in text:
        pattern = DIGIT_PATTERNS.get(ch)
        if pattern is None:
            cursor_x += char_width_mm * 1.3
            continue

        rows = len(pattern)
        cols = max(len(row) for row in pattern)
        pixel_h = char_height_mm / rows
        pixel_w = char_width_mm / cols

        for r, row in enumerate(pattern):
            for c, pixel in enumerate(row):
                if pixel == "#":
                    px = cursor_x + c * pixel_w
                    py = center_y + char_height_mm / 2 - r * pixel_h - pixel_h
                    pixels.append((px, py, pixel_w, pixel_h))

        cursor_x += char_width_mm * 1.3

    return pixels


def generate_number_relief_faces(
    number: int,
    center_x: float,
    center_y: float,
    char_height_mm: float,
    base_z: float,
    relief_height: float,
    style: ReliefStyle,
) -> np.ndarray:
    text = str(number)
    char_width_mm = char_height_mm * 5 / 7

    total_width = len(text) * char_width_mm + (len(text) - 1) * char_width_mm * 0.3
    start_x = center_x - total_width / 2

    faces: list = []
    cursor_x = start_x

    for ch in text:
        pattern = DIGIT_PATTERNS.get(ch)
        if pattern is None:
            cursor_x += char_width_mm * 1.3
            continue

        rows = len(pattern)
        cols = max(len(row) for row in pattern)
        pixel_h = char_height_mm / rows
        pixel_w = char_width_mm / cols

        if style == ReliefStyle.EMBOSSED:
            z_bot = base_z
            z_top = base_z + relief_height
        else:
            z_bot = base_z - relief_height
            z_top = base_z

        for r, row in enumerate(pattern):
            for c, pixel in enumerate(row):
                if pixel == "#":
                    px = cursor_x + c * pixel_w
                    py = center_y + char_height_mm / 2 - r * pixel_h - pixel_h

                    _add_pixel_box(faces, px, py, pixel_w, pixel_h, z_bot, z_top)

        cursor_x += char_width_mm * 1.3

    return np.array(faces, dtype=np.float64) if faces else np.empty((0, 3, 3), dtype=np.float64)


def _add_pixel_box(
    faces: list,
    x: float,
    y: float,
    w: float,
    h: float,
    z_bottom: float,
    z_top: float,
) -> None:
    x0, x1 = x, x + w
    y0, y1 = y, y + h

    faces.append([[x0, y0, z_top], [x1, y0, z_top], [x1, y1, z_top]])
    faces.append([[x0, y0, z_top], [x1, y1, z_top], [x0, y1, z_top]])

    faces.append([[x0, y0, z_bottom], [x1, y1, z_bottom], [x1, y0, z_bottom]])
    faces.append([[x0, y0, z_bottom], [x0, y1, z_bottom], [x1, y1, z_bottom]])

    faces.append([[x0, y0, z_bottom], [x1, y0, z_bottom], [x1, y0, z_top]])
    faces.append([[x0, y0, z_bottom], [x1, y0, z_top], [x0, y0, z_top]])

    faces.append([[x0, y1, z_bottom], [x1, y1, z_top], [x1, y1, z_bottom]])
    faces.append([[x0, y1, z_bottom], [x0, y1, z_top], [x1, y1, z_top]])

    faces.append([[x0, y0, z_bottom], [x0, y0, z_top], [x0, y1, z_top]])
    faces.append([[x0, y0, z_bottom], [x0, y1, z_top], [x0, y1, z_bottom]])

    faces.append([[x1, y0, z_bottom], [x1, y1, z_top], [x1, y0, z_top]])
    faces.append([[x1, y0, z_bottom], [x1, y1, z_bottom], [x1, y1, z_top]])
