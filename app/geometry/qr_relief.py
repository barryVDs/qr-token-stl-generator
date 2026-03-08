from __future__ import annotations

import numpy as np

from app.models import ReliefStyle


def generate_qr_relief_faces(
    qr_matrix: np.ndarray,
    qr_area_size_mm: float,
    qr_offset_x: float,
    qr_offset_y: float,
    base_z: float,
    relief_height: float,
    style: ReliefStyle,
) -> np.ndarray:
    rows, cols = qr_matrix.shape
    module_size = qr_area_size_mm / max(rows, cols)

    qr_width = cols * module_size
    qr_height = rows * module_size
    start_x = qr_offset_x - qr_width / 2
    start_y = qr_offset_y - qr_height / 2

    faces = []

    if style == ReliefStyle.EMBOSSED:
        z_bottom = base_z
        z_top = base_z + relief_height
    else:
        z_bottom = base_z - relief_height
        z_top = base_z

    for r in range(rows):
        for c in range(cols):
            is_dark = qr_matrix[r, c]

            if style == ReliefStyle.EMBOSSED and is_dark:
                _add_module_box(
                    faces, start_x, start_y, r, c, rows,
                    module_size, z_bottom, z_top,
                )
            elif style == ReliefStyle.ENGRAVED and is_dark:
                _add_module_box(
                    faces, start_x, start_y, r, c, rows,
                    module_size, z_bottom, z_top,
                )

    return np.array(faces, dtype=np.float64) if faces else np.empty((0, 3, 3), dtype=np.float64)


def _add_module_box(
    faces: list,
    start_x: float,
    start_y: float,
    row: int,
    col: int,
    total_rows: int,
    module_size: float,
    z_bottom: float,
    z_top: float,
) -> None:
    x0 = start_x + col * module_size
    x1 = x0 + module_size
    y0 = start_y + (total_rows - 1 - row) * module_size
    y1 = y0 + module_size

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
