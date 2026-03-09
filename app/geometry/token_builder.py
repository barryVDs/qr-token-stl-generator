from __future__ import annotations

import logging
import math

import numpy as np

from app.models import NumberPosition, ReliefStyle, Shape, TokenConfig
from app.geometry.text_relief import get_number_pixels

logger = logging.getLogger(__name__)

CIRCLE_SEGMENTS = 128
MAX_CELL_SIZE = 0.4  # only used for square tokens


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

    # Cell size: round tokens use module_size (smooth ring handles boundary);
    # square tokens subdivide for smooth corners.
    if config.shape == Shape.ROUND:
        cell_size = module_size
    else:
        subdivisions = max(1, math.ceil(module_size / MAX_CELL_SIZE))
        cell_size = module_size / subdivisions

    # QR boundaries in model space
    qr_width = qr_cols * module_size
    qr_height_model = qr_rows * module_size
    qr_left = -qr_width / 2
    qr_top = qr_center_y + qr_height_model / 2

    # Grid
    half = config.size_mm / 2
    grid_w = math.ceil(config.size_mm / cell_size) + 2
    grid_h = math.ceil(config.size_mm / cell_size) + 2
    origin_x = -grid_w * cell_size / 2
    origin_y = -grid_h * cell_size / 2

    # Number pixels
    back_pixels: list[tuple[float, float, float, float]] = []
    front_pixels: list[tuple[float, float, float, float]] = []
    if config.show_number:
        if config.number_position == NumberPosition.BACK:
            back_pixels = get_number_pixels(nummer, 0.0, 0.0, config.number_size_mm)
            back_pixels = [(-px - pw, py, pw, ph) for px, py, pw, ph in back_pixels]
        else:
            margin = max(config.border_mm, config.qr_margin_mm)
            if config.number_position == NumberPosition.BOTTOM:
                num_y = -half + margin + config.number_size_mm / 2
            else:
                num_y = half - margin - config.number_size_mm / 2
            front_pixels = get_number_pixels(nummer, 0.0, num_y, config.number_size_mm)

    # Hole
    hole_r_sq = 0.0
    hole_cy = 0.0
    if config.hole_enabled and config.hole_diameter_mm:
        hole_r = config.hole_diameter_mm / 2
        hole_r_sq = hole_r * hole_r
        hole_cy = half - config.border_mm - hole_r - (config.hole_offset_mm or 0)

    # --- Build heightmap ---
    inside = np.zeros((grid_h, grid_w), dtype=bool)
    top_z = np.full((grid_h, grid_w), config.thickness_mm)
    bottom_z = np.zeros((grid_h, grid_w))

    r_sq = half * half
    cr = config.corner_radius_mm

    # For round tokens the grid stays inside the circle; the smooth ring fills the gap.
    if config.shape == Shape.ROUND:
        grid_r = half - cell_size
        grid_r_sq = grid_r * grid_r

    for gy in range(grid_h):
        for gx in range(grid_w):
            cx = origin_x + (gx + 0.5) * cell_size
            cy = origin_y + (gy + 0.5) * cell_size

            if config.shape == Shape.ROUND:
                if cx * cx + cy * cy > grid_r_sq:
                    continue
            else:
                if abs(cx) > half or abs(cy) > half:
                    continue
                if cr > 0:
                    ax, ay = abs(cx), abs(cy)
                    if ax > half - cr and ay > half - cr:
                        dx = ax - (half - cr)
                        dy = ay - (half - cr)
                        if dx * dx + dy * dy > cr * cr:
                            continue

            if hole_r_sq > 0:
                dx = cx
                dy = cy - hole_cy
                if dx * dx + dy * dy < hole_r_sq:
                    continue

            inside[gy, gx] = True

            # QR relief on top
            qr_col = int((cx - qr_left) / module_size)
            qr_row = int((qr_top - cy) / module_size)
            if 0 <= qr_row < qr_rows and 0 <= qr_col < qr_cols:
                if qr_matrix[qr_row, qr_col]:
                    if config.qr_style == ReliefStyle.EMBOSSED:
                        top_z[gy, gx] = config.thickness_mm + config.qr_height_mm
                    else:
                        top_z[gy, gx] = config.thickness_mm - config.qr_height_mm

            for px, py, pw, ph in front_pixels:
                if px <= cx < px + pw and py <= cy < py + ph:
                    if config.number_style == ReliefStyle.EMBOSSED:
                        top_z[gy, gx] = config.thickness_mm + config.number_height_mm
                    else:
                        top_z[gy, gx] = config.thickness_mm - config.number_height_mm
                    break

            for px, py, pw, ph in back_pixels:
                if px <= cx < px + pw and py <= cy < py + ph:
                    if config.number_style == ReliefStyle.EMBOSSED:
                        bottom_z[gy, gx] = -config.number_height_mm
                    else:
                        bottom_z[gy, gx] = config.number_height_mm
                    break

    # --- Generate mesh ---
    if config.shape == Shape.ROUND:
        faces = _build_round_mesh(
            inside, top_z, bottom_z, cell_size,
            origin_x, origin_y, grid_w, grid_h,
            half, config.thickness_mm,
        )
    else:
        faces = _heightmap_to_mesh(
            inside, top_z, bottom_z, cell_size,
            origin_x, origin_y, grid_w, grid_h,
        )

    logger.info("Built token mesh: %d cells, %d faces", int(inside.sum()), len(faces))
    return np.array(faces, dtype=np.float64)


# ──────────────────────────────────────────────
#  Round token: grid interior + smooth ring + cylinder
# ──────────────────────────────────────────────

def _build_round_mesh(inside, top_z, bottom_z, cs, ox, oy, gw, gh, radius, thickness):
    # 1. Interior grid (with perimeter walls between grid cells and the ring gap)
    faces = _heightmap_to_mesh(inside, top_z, bottom_z, cs, ox, oy, gw, gh)

    # 2. Extract ordered CCW boundary polygon of the grid
    boundary = _extract_boundary(inside, cs, ox, oy, gw, gh)
    if not boundary:
        return faces

    # 3. Smooth circle (CCW)
    circle = _circle_vertices(radius, CIRCLE_SEGMENTS)

    # 4. Stitch ring – top face (z = thickness, normal +Z)
    faces.extend(_stitch_ring(boundary, circle, thickness, normal_up=True))

    # 5. Stitch ring – bottom face (z = 0, normal –Z)
    faces.extend(_stitch_ring(boundary, circle, 0.0, normal_up=False))

    # 6. Smooth cylinder side wall
    faces.extend(_cylinder_wall(circle, 0.0, thickness))

    return faces


def _circle_vertices(radius: float, segments: int) -> list[tuple[float, float]]:
    return [
        (radius * math.cos(2 * math.pi * i / segments),
         radius * math.sin(2 * math.pi * i / segments))
        for i in range(segments)
    ]


def _extract_boundary(inside, cs, ox, oy, gw, gh) -> list[tuple[float, float]]:
    """Extract the outer boundary of the grid as an ordered CCW polygon."""
    edge_map: dict[tuple[float, float], tuple[float, float]] = {}

    def rp(x, y):
        return (round(x, 4), round(y, 4))

    for gy in range(gh):
        for gx in range(gw):
            if not inside[gy, gx]:
                continue
            x0 = ox + gx * cs
            x1 = ox + (gx + 1) * cs
            y0 = oy + gy * cs
            y1 = oy + (gy + 1) * cs

            if gy == 0 or not inside[gy - 1, gx]:
                edge_map[rp(x0, y0)] = rp(x1, y0)
            if gx + 1 >= gw or not inside[gy, gx + 1]:
                edge_map[rp(x1, y0)] = rp(x1, y1)
            if gy + 1 >= gh or not inside[gy + 1, gx]:
                edge_map[rp(x1, y1)] = rp(x0, y1)
            if gx == 0 or not inside[gy, gx - 1]:
                edge_map[rp(x0, y1)] = rp(x0, y0)

    if not edge_map:
        return []

    # There may be multiple loops (outer boundary + hole boundaries).
    # Extract all loops, then return the longest one (the outer boundary).
    remaining = dict(edge_map)
    loops: list[list[tuple[float, float]]] = []
    while remaining:
        start = next(iter(remaining))
        loop = [start]
        current = remaining.pop(start)
        while current != start:
            loop.append(current)
            if current not in remaining:
                break
            current = remaining.pop(current)
        loops.append(loop)

    return max(loops, key=len)


def _stitch_ring(inner, outer, z, normal_up):
    """Triangulate the ring between two CCW polygons at height z."""
    faces: list = []
    M = len(inner)
    N = len(outer)
    if M == 0 or N == 0:
        return faces

    def ang(p):
        a = math.atan2(p[1], p[0])
        return a if a >= 0 else a + 2 * math.pi

    inner_a = [ang(p) for p in inner]
    outer_a = [ang(p) for p in outer]

    i0 = min(range(M), key=lambda k: inner_a[k])
    o0 = min(range(N), key=lambda k: outer_a[k])

    i = 0
    o = 0

    for _ in range(M + N):
        ci = (i0 + i) % M
        co = (o0 + o) % N
        ci1 = (i0 + i + 1) % M
        co1 = (o0 + o + 1) % N

        pi = inner[ci]
        po = outer[co]

        if i >= M:
            do_inner = False
        elif o >= N:
            do_inner = True
        else:
            a_cur = inner_a[ci]
            ai1 = inner_a[ci1] - a_cur
            ao1 = outer_a[co1] - a_cur
            if ai1 < -0.01:
                ai1 += 2 * math.pi
            if ao1 < -0.01:
                ao1 += 2 * math.pi
            do_inner = ai1 <= ao1

        if do_inner:
            pi1 = inner[ci1]
            if normal_up:
                faces.append([[pi[0], pi[1], z], [po[0], po[1], z], [pi1[0], pi1[1], z]])
            else:
                faces.append([[pi[0], pi[1], z], [pi1[0], pi1[1], z], [po[0], po[1], z]])
            i += 1
        else:
            po1 = outer[co1]
            if normal_up:
                faces.append([[pi[0], pi[1], z], [po[0], po[1], z], [po1[0], po1[1], z]])
            else:
                faces.append([[pi[0], pi[1], z], [po1[0], po1[1], z], [po[0], po[1], z]])
            o += 1

    return faces


def _cylinder_wall(circle, z_bottom, z_top):
    """Smooth cylinder side wall with outward-facing normals."""
    faces: list = []
    N = len(circle)
    for i in range(N):
        p0 = circle[i]
        p1 = circle[(i + 1) % N]
        # Two triangles per quad, normals pointing radially outward.
        faces.append([
            [p0[0], p0[1], z_bottom],
            [p1[0], p1[1], z_bottom],
            [p0[0], p0[1], z_top],
        ])
        faces.append([
            [p1[0], p1[1], z_bottom],
            [p1[0], p1[1], z_top],
            [p0[0], p0[1], z_top],
        ])
    return faces


# ──────────────────────────────────────────────
#  Generic heightmap → mesh  (used for grid interior + square tokens)
# ──────────────────────────────────────────────

def _heightmap_to_mesh(inside, top_z, bottom_z, cs, ox, oy, gw, gh):
    faces: list = []

    for gy in range(gh):
        for gx in range(gw):
            if not inside[gy, gx]:
                continue

            x0 = ox + gx * cs
            x1 = x0 + cs
            y0 = oy + gy * cs
            y1 = y0 + cs
            zt = float(top_z[gy, gx])
            zb = float(bottom_z[gy, gx])

            # Top (+Z)
            faces.append([[x0, y0, zt], [x1, y0, zt], [x0, y1, zt]])
            faces.append([[x1, y0, zt], [x1, y1, zt], [x0, y1, zt]])
            # Bottom (-Z)
            faces.append([[x0, y0, zb], [x0, y1, zb], [x1, y0, zb]])
            faces.append([[x1, y0, zb], [x0, y1, zb], [x1, y1, zb]])

            r_in = gx + 1 < gw and inside[gy, gx + 1]
            l_in = gx > 0 and inside[gy, gx - 1]
            u_in = gy + 1 < gh and inside[gy + 1, gx]
            d_in = gy > 0 and inside[gy - 1, gx]

            # Right (+X)
            if not r_in:
                _wall_px(faces, x1, y0, y1, zb, zt)
            else:
                zt_r = float(top_z[gy, gx + 1])
                zb_r = float(bottom_z[gy, gx + 1])
                if zt > zt_r:
                    _wall_px(faces, x1, y0, y1, zt_r, zt)
                elif zt < zt_r:
                    _wall_nx(faces, x1, y0, y1, zt, zt_r)
                if zb < zb_r:
                    _wall_px(faces, x1, y0, y1, zb, zb_r)
                elif zb > zb_r:
                    _wall_nx(faces, x1, y0, y1, zb_r, zb)

            if not l_in:
                _wall_nx(faces, x0, y0, y1, zb, zt)

            # Up (+Y)
            if not u_in:
                _wall_py(faces, y1, x0, x1, zb, zt)
            else:
                zt_u = float(top_z[gy + 1, gx])
                zb_u = float(bottom_z[gy + 1, gx])
                if zt > zt_u:
                    _wall_py(faces, y1, x0, x1, zt_u, zt)
                elif zt < zt_u:
                    _wall_ny(faces, y1, x0, x1, zt, zt_u)
                if zb < zb_u:
                    _wall_py(faces, y1, x0, x1, zb, zb_u)
                elif zb > zb_u:
                    _wall_ny(faces, y1, x0, x1, zb_u, zb)

            if not d_in:
                _wall_ny(faces, y0, x0, x1, zb, zt)

    return faces


# ── wall helpers (verified normals) ──

def _wall_px(f, x, y0, y1, z0, z1):
    f.append([[x, y0, z0], [x, y1, z0], [x, y0, z1]])
    f.append([[x, y1, z0], [x, y1, z1], [x, y0, z1]])

def _wall_nx(f, x, y0, y1, z0, z1):
    f.append([[x, y0, z0], [x, y0, z1], [x, y1, z0]])
    f.append([[x, y1, z0], [x, y0, z1], [x, y1, z1]])

def _wall_py(f, y, x0, x1, z0, z1):
    f.append([[x0, y, z0], [x0, y, z1], [x1, y, z0]])
    f.append([[x1, y, z0], [x0, y, z1], [x1, y, z1]])

def _wall_ny(f, y, x0, x1, z0, z1):
    f.append([[x0, y, z0], [x1, y, z0], [x0, y, z1]])
    f.append([[x1, y, z0], [x1, y, z1], [x0, y, z1]])
