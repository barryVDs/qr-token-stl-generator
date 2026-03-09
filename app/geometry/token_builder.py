from __future__ import annotations

import logging
import math

import numpy as np

from app.models import NumberPosition, ReliefStyle, Shape, TokenConfig
from app.geometry.text_relief import get_number_pixels

logger = logging.getLogger(__name__)

CIRCLE_SEGMENTS = 128


def build_token_mesh(
    config: TokenConfig,
    qr_matrix: np.ndarray,
    nummer: int,
) -> np.ndarray:
    qr_rows, qr_cols = qr_matrix.shape

    # --- QR side length ---
    if config.shape == Shape.ROUND:
        qr_diagonal = config.size_mm - 2 * config.qr_margin_mm
        qr_side = qr_diagonal / math.sqrt(2)
    else:
        qr_side = config.size_mm - 2 * config.qr_margin_mm
        if config.border_enabled:
            qr_side -= 2 * config.border_mm

    qr_center_y = 0.0
    if config.show_number and config.number_position == NumberPosition.BOTTOM:
        qr_center_y += (config.number_size_mm + 1.0) / 2
        qr_side -= config.number_size_mm + 1.0
    elif config.show_number and config.number_position == NumberPosition.TOP:
        qr_center_y -= (config.number_size_mm + 1.0) / 2
        qr_side -= config.number_size_mm + 1.0

    module_size = qr_side / max(qr_rows, qr_cols)

    # QR boundaries in model space
    qr_width = qr_cols * module_size
    qr_height_model = qr_rows * module_size
    qr_left = -qr_width / 2
    qr_top = qr_center_y + qr_height_model / 2

    half = config.size_mm / 2
    faces: list = []

    # ── 1. Base shape: watertight cylinder or box ──
    if config.shape == Shape.ROUND:
        faces.extend(_closed_cylinder(0.0, 0.0, half, 0.0, config.thickness_mm, CIRCLE_SEGMENTS))
    else:
        cr = config.corner_radius_mm
        if cr > 0:
            outline = _rounded_rect_outline(config.size_mm, config.size_mm, cr)
        else:
            hw = half
            outline = [(hw, hw), (-hw, hw), (-hw, -hw), (hw, -hw)]
        faces.extend(_closed_prism(outline, 0.0, config.thickness_mm))

    # ── 2. Hole: subtract cylinder (overlapping, inverted normals) ──
    if config.hole_enabled and config.hole_diameter_mm:
        hole_r = config.hole_diameter_mm / 2
        hole_cy = half - config.border_mm - hole_r - (config.hole_offset_mm or 0)
        faces.extend(_closed_cylinder(
            0.0, hole_cy, hole_r,
            -0.01, config.thickness_mm + 0.01,
            32, invert=True,
        ))

    # ── 3. QR relief on top ──
    for r in range(qr_rows):
        for c in range(qr_cols):
            if not qr_matrix[r, c]:
                continue
            x0 = qr_left + c * module_size
            x1 = x0 + module_size
            y0 = qr_top - (r + 1) * module_size
            y1 = y0 + module_size

            if config.qr_style == ReliefStyle.EMBOSSED:
                z_bot = config.thickness_mm
                z_top = config.thickness_mm + config.qr_height_mm
            else:
                z_bot = config.thickness_mm - config.qr_height_mm
                z_top = config.thickness_mm

            faces.extend(_closed_box(x0, y0, x1, y1, z_bot, z_top))

    # ── 4. Number relief ──
    if config.show_number:
        if config.number_position == NumberPosition.BACK:
            pixels = get_number_pixels(nummer, 0.0, 0.0, config.number_size_mm)
            pixels = [(-px - pw, py, pw, ph) for px, py, pw, ph in pixels]
            for px, py, pw, ph in pixels:
                if config.number_style == ReliefStyle.EMBOSSED:
                    z_bot = -config.number_height_mm
                    z_top = 0.0
                else:
                    z_bot = 0.0
                    z_top = config.number_height_mm
                faces.extend(_closed_box(px, py, px + pw, py + ph, z_bot, z_top))
        else:
            margin = max(config.border_mm, config.qr_margin_mm)
            if config.number_position == NumberPosition.BOTTOM:
                num_y = -half + margin + config.number_size_mm / 2
            else:
                num_y = half - margin - config.number_size_mm / 2
            pixels = get_number_pixels(nummer, 0.0, num_y, config.number_size_mm)
            for px, py, pw, ph in pixels:
                if config.number_style == ReliefStyle.EMBOSSED:
                    z_bot = config.thickness_mm
                    z_top = config.thickness_mm + config.number_height_mm
                else:
                    z_bot = config.thickness_mm - config.number_height_mm
                    z_top = config.thickness_mm
                faces.extend(_closed_box(px, py, px + pw, py + ph, z_bot, z_top))

    logger.info("Built token mesh: %d faces", len(faces))
    return np.array(faces, dtype=np.float64)


# ──────────────────────────────────────────────
#  Primitives — each produces a fully watertight mesh
# ──────────────────────────────────────────────

def _closed_cylinder(cx, cy, radius, z_bot, z_top, segments, invert=False):
    """Watertight cylinder: top disc + bottom disc + side wall."""
    faces: list = []
    pts = [
        (cx + radius * math.cos(2 * math.pi * i / segments),
         cy + radius * math.sin(2 * math.pi * i / segments))
        for i in range(segments)
    ]

    for i in range(segments):
        p0 = pts[i]
        p1 = pts[(i + 1) % segments]

        if not invert:
            # Top disc (normal +Z): fan from center
            faces.append([[cx, cy, z_top], [p0[0], p0[1], z_top], [p1[0], p1[1], z_top]])
            # Bottom disc (normal -Z): fan from center, reversed
            faces.append([[cx, cy, z_bot], [p1[0], p1[1], z_bot], [p0[0], p0[1], z_bot]])
            # Side wall (normal outward)
            faces.append([[p0[0], p0[1], z_bot], [p1[0], p1[1], z_bot], [p0[0], p0[1], z_top]])
            faces.append([[p1[0], p1[1], z_bot], [p1[0], p1[1], z_top], [p0[0], p0[1], z_top]])
        else:
            # Inverted normals for hole subtraction
            faces.append([[cx, cy, z_top], [p1[0], p1[1], z_top], [p0[0], p0[1], z_top]])
            faces.append([[cx, cy, z_bot], [p0[0], p0[1], z_bot], [p1[0], p1[1], z_bot]])
            faces.append([[p0[0], p0[1], z_bot], [p0[0], p0[1], z_top], [p1[0], p1[1], z_bot]])
            faces.append([[p1[0], p1[1], z_bot], [p0[0], p0[1], z_top], [p1[0], p1[1], z_top]])

    return faces


def _closed_box(x0, y0, x1, y1, z_bot, z_top):
    """Watertight box with 6 faces (12 triangles), all normals outward."""
    return [
        # Top (+Z)
        [[x0, y0, z_top], [x1, y0, z_top], [x0, y1, z_top]],
        [[x1, y0, z_top], [x1, y1, z_top], [x0, y1, z_top]],
        # Bottom (-Z)
        [[x0, y0, z_bot], [x0, y1, z_bot], [x1, y0, z_bot]],
        [[x1, y0, z_bot], [x0, y1, z_bot], [x1, y1, z_bot]],
        # Front (+Y)
        [[x0, y1, z_bot], [x0, y1, z_top], [x1, y1, z_bot]],
        [[x1, y1, z_bot], [x0, y1, z_top], [x1, y1, z_top]],
        # Back (-Y)
        [[x0, y0, z_bot], [x1, y0, z_bot], [x0, y0, z_top]],
        [[x1, y0, z_bot], [x1, y0, z_top], [x0, y0, z_top]],
        # Right (+X)
        [[x1, y0, z_bot], [x1, y1, z_bot], [x1, y0, z_top]],
        [[x1, y1, z_bot], [x1, y1, z_top], [x1, y0, z_top]],
        # Left (-X)
        [[x0, y0, z_bot], [x0, y0, z_top], [x0, y1, z_bot]],
        [[x0, y1, z_bot], [x0, y0, z_top], [x0, y1, z_top]],
    ]


def _closed_prism(outline, z_bot, z_top):
    """Watertight prism from a 2D outline: top + bottom + side walls."""
    faces: list = []
    n = len(outline)
    cx = sum(v[0] for v in outline) / n
    cy = sum(v[1] for v in outline) / n

    for i in range(n):
        p0 = outline[i]
        p1 = outline[(i + 1) % n]

        # Top fan (+Z)
        faces.append([[cx, cy, z_top], [p0[0], p0[1], z_top], [p1[0], p1[1], z_top]])
        # Bottom fan (-Z)
        faces.append([[cx, cy, z_bot], [p1[0], p1[1], z_bot], [p0[0], p0[1], z_bot]])
        # Side wall
        faces.append([[p0[0], p0[1], z_bot], [p1[0], p1[1], z_bot], [p0[0], p0[1], z_top]])
        faces.append([[p1[0], p1[1], z_bot], [p1[0], p1[1], z_top], [p0[0], p0[1], z_top]])

    return faces


def _rounded_rect_outline(w, h, r, segments_per_corner=8):
    """Generate CCW outline for a rounded rectangle."""
    hw, hh = w / 2, h / 2
    r = min(r, hw, hh)
    pts: list[tuple[float, float]] = []
    corners = [
        (hw - r, hh - r, 0),
        (-hw + r, hh - r, math.pi / 2),
        (-hw + r, -hh + r, math.pi),
        (hw - r, -hh + r, 3 * math.pi / 2),
    ]
    for ccx, ccy, start in corners:
        for i in range(segments_per_corner + 1):
            a = start + (math.pi / 2) * i / segments_per_corner
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts
