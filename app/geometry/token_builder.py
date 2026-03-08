from __future__ import annotations

import logging
import math

import numpy as np

from app.models import NumberPosition, ReliefStyle, Shape, TokenConfig
from app.geometry.text_relief import get_number_pixels

logger = logging.getLogger(__name__)


def build_token_mesh(
    config: TokenConfig,
    qr_matrix: np.ndarray,
    nummer: int,
) -> np.ndarray:
    """Build a watertight manifold token mesh using a heightmap grid approach.

    The top surface (positive Z) holds the QR code.
    The bottom surface (Z=0) holds the number when number_position is 'back'.
    """
    qr_rows, qr_cols = qr_matrix.shape

    # Compute available QR area
    qr_area = config.size_mm - 2 * config.qr_margin_mm
    if config.border_enabled:
        qr_area -= 2 * config.border_mm

    # Shift QR center if number is on the front side
    qr_center_y = 0.0
    if config.show_number and config.number_position == NumberPosition.BOTTOM:
        qr_center_y += (config.number_size_mm + 1.0) / 2
        qr_area -= config.number_size_mm + 1.0
    elif config.show_number and config.number_position == NumberPosition.TOP:
        qr_center_y -= (config.number_size_mm + 1.0) / 2
        qr_area -= config.number_size_mm + 1.0

    module_size = qr_area / max(qr_rows, qr_cols)
    cell_size = module_size

    # QR boundaries in model space
    qr_width = qr_cols * module_size
    qr_height_model = qr_rows * module_size
    qr_left = -qr_width / 2
    qr_top = qr_center_y + qr_height_model / 2

    # Grid dimensions covering full token
    half = config.size_mm / 2
    grid_w = math.ceil(config.size_mm / cell_size) + 2
    grid_h = math.ceil(config.size_mm / cell_size) + 2
    origin_x = -grid_w * cell_size / 2
    origin_y = -grid_h * cell_size / 2

    # Precompute number pixel rectangles
    back_pixels: list[tuple[float, float, float, float]] = []
    front_pixels: list[tuple[float, float, float, float]] = []

    if config.show_number:
        if config.number_position == NumberPosition.BACK:
            back_pixels = get_number_pixels(nummer, 0.0, 0.0, config.number_size_mm)
            # Mirror X so number reads correctly when token is flipped
            back_pixels = [(-px - pw, py, pw, ph) for px, py, pw, ph in back_pixels]
        else:
            margin = max(config.border_mm, config.qr_margin_mm)
            if config.number_position == NumberPosition.BOTTOM:
                num_y = -half + margin + config.number_size_mm / 2
            else:
                num_y = half - margin - config.number_size_mm / 2
            front_pixels = get_number_pixels(nummer, 0.0, num_y, config.number_size_mm)

    # Hole parameters
    hole_r_sq = 0.0
    hole_cy = 0.0
    if config.hole_enabled and config.hole_diameter_mm:
        hole_r = config.hole_diameter_mm / 2
        hole_r_sq = hole_r * hole_r
        hole_cy = half - config.border_mm - hole_r - (config.hole_offset_mm or 0)

    # Build heightmap
    inside = np.zeros((grid_h, grid_w), dtype=bool)
    top_z = np.full((grid_h, grid_w), config.thickness_mm)
    bottom_z = np.zeros((grid_h, grid_w))

    r_sq = half * half
    cr = config.corner_radius_mm

    for gy in range(grid_h):
        for gx in range(grid_w):
            cx = origin_x + (gx + 0.5) * cell_size
            cy = origin_y + (gy + 0.5) * cell_size

            # Token boundary check
            if config.shape == Shape.ROUND:
                if cx * cx + cy * cy > r_sq:
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

            # Hole check
            if hole_r_sq > 0:
                dx = cx
                dy = cy - hole_cy
                if dx * dx + dy * dy < hole_r_sq:
                    continue

            inside[gy, gx] = True

            # Top surface: QR relief
            qr_col = int((cx - qr_left) / module_size)
            qr_row = int((qr_top - cy) / module_size)

            if 0 <= qr_row < qr_rows and 0 <= qr_col < qr_cols:
                if qr_matrix[qr_row, qr_col]:
                    if config.qr_style == ReliefStyle.EMBOSSED:
                        top_z[gy, gx] = config.thickness_mm + config.qr_height_mm
                    else:
                        top_z[gy, gx] = config.thickness_mm - config.qr_height_mm

            # Top surface: front number relief
            for px, py, pw, ph in front_pixels:
                if px <= cx < px + pw and py <= cy < py + ph:
                    if config.number_style == ReliefStyle.EMBOSSED:
                        top_z[gy, gx] = config.thickness_mm + config.number_height_mm
                    else:
                        top_z[gy, gx] = config.thickness_mm - config.number_height_mm
                    break

            # Bottom surface: back number relief
            for px, py, pw, ph in back_pixels:
                if px <= cx < px + pw and py <= cy < py + ph:
                    if config.number_style == ReliefStyle.EMBOSSED:
                        bottom_z[gy, gx] = -config.number_height_mm
                    else:
                        bottom_z[gy, gx] = config.number_height_mm
                    break

    # Generate mesh from heightmap
    faces = _heightmap_to_mesh(inside, top_z, bottom_z, cell_size,
                               origin_x, origin_y, grid_w, grid_h)

    logger.info("Built token mesh: %d cells inside, %d faces", int(inside.sum()), len(faces))
    return np.array(faces, dtype=np.float64)


def _heightmap_to_mesh(
    inside: np.ndarray,
    top_z: np.ndarray,
    bottom_z: np.ndarray,
    cs: float,
    ox: float,
    oy: float,
    gw: int,
    gh: int,
) -> list:
    """Convert heightmap grid to triangle faces with correct outward normals."""
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

            # --- Top face (normal +Z) ---
            faces.append([[x0, y0, zt], [x1, y0, zt], [x0, y1, zt]])
            faces.append([[x1, y0, zt], [x1, y1, zt], [x0, y1, zt]])

            # --- Bottom face (normal -Z) ---
            faces.append([[x0, y0, zb], [x0, y1, zb], [x1, y0, zb]])
            faces.append([[x1, y0, zb], [x0, y1, zb], [x1, y1, zb]])

            # --- Neighbor checks ---
            r_in = gx + 1 < gw and inside[gy, gx + 1]
            l_in = gx > 0 and inside[gy, gx - 1]
            u_in = gy + 1 < gh and inside[gy + 1, gx]
            d_in = gy > 0 and inside[gy - 1, gx]

            # Right edge (+X)
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

            # Left edge (-X)
            if not l_in:
                _wall_nx(faces, x0, y0, y1, zb, zt)
            # (height transitions handled by left neighbor's right-edge check)

            # Up edge (+Y)
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

            # Down edge (-Y)
            if not d_in:
                _wall_ny(faces, y0, x0, x1, zb, zt)
            # (height transitions handled by lower neighbor's up-edge check)

    return faces


# --- Wall helpers with verified outward normals ---
# All normals verified via cross product of edge vectors.

def _wall_px(faces: list, x: float, y0: float, y1: float, z0: float, z1: float) -> None:
    """Wall at x facing +X."""
    faces.append([[x, y0, z0], [x, y1, z0], [x, y0, z1]])
    faces.append([[x, y1, z0], [x, y1, z1], [x, y0, z1]])


def _wall_nx(faces: list, x: float, y0: float, y1: float, z0: float, z1: float) -> None:
    """Wall at x facing -X."""
    faces.append([[x, y0, z0], [x, y0, z1], [x, y1, z0]])
    faces.append([[x, y1, z0], [x, y0, z1], [x, y1, z1]])


def _wall_py(faces: list, y: float, x0: float, x1: float, z0: float, z1: float) -> None:
    """Wall at y facing +Y."""
    faces.append([[x0, y, z0], [x0, y, z1], [x1, y, z0]])
    faces.append([[x1, y, z0], [x0, y, z1], [x1, y, z1]])


def _wall_ny(faces: list, y: float, x0: float, x1: float, z0: float, z1: float) -> None:
    """Wall at y facing -Y."""
    faces.append([[x0, y, z0], [x1, y, z0], [x0, y, z1]])
    faces.append([[x1, y, z0], [x1, y, z1], [x0, y, z1]])
