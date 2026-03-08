from __future__ import annotations

import math

import numpy as np


def create_circle_vertices(
    cx: float, cy: float, radius: float, segments: int = 64
) -> list[tuple[float, float]]:
    verts = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        verts.append((x, y))
    return verts


def create_rounded_rect_vertices(
    cx: float,
    cy: float,
    width: float,
    height: float,
    corner_radius: float,
    segments_per_corner: int = 8,
) -> list[tuple[float, float]]:
    r = min(corner_radius, width / 2, height / 2)
    hw = width / 2
    hh = height / 2

    verts: list[tuple[float, float]] = []
    corners = [
        (cx + hw - r, cy + hh - r, 0),
        (cx - hw + r, cy + hh - r, math.pi / 2),
        (cx - hw + r, cy - hh + r, math.pi),
        (cx + hw - r, cy - hh + r, 3 * math.pi / 2),
    ]

    for corner_cx, corner_cy, start_angle in corners:
        for i in range(segments_per_corner + 1):
            angle = start_angle + (math.pi / 2) * i / segments_per_corner
            x = corner_cx + r * math.cos(angle)
            y = corner_cy + r * math.sin(angle)
            verts.append((x, y))

    return verts


def create_rect_vertices(
    cx: float, cy: float, width: float, height: float
) -> list[tuple[float, float]]:
    hw = width / 2
    hh = height / 2
    return [
        (cx + hw, cy + hh),
        (cx - hw, cy + hh),
        (cx - hw, cy - hh),
        (cx + hw, cy - hh),
    ]


def extrude_polygon(
    outline: list[tuple[float, float]], z_bottom: float, z_top: float
) -> np.ndarray:
    n = len(outline)
    faces = []

    center_x = sum(v[0] for v in outline) / n
    center_y = sum(v[1] for v in outline) / n

    for i in range(n):
        x, y = outline[i]
        nx, ny = outline[(i + 1) % n]

        faces.append([
            [x, y, z_bottom],
            [nx, ny, z_bottom],
            [nx, ny, z_top],
        ])
        faces.append([
            [x, y, z_bottom],
            [nx, ny, z_top],
            [x, y, z_top],
        ])

    for i in range(1, n - 1):
        faces.append([
            [center_x, center_y, z_top],
            [outline[i][0], outline[i][1], z_top],
            [outline[i + 1][0], outline[i + 1][1], z_top],
        ])
        faces.append([
            [center_x, center_y, z_bottom],
            [outline[i + 1][0], outline[i + 1][1], z_bottom],
            [outline[i][0], outline[i][1], z_bottom],
        ])

    faces.append([
        [center_x, center_y, z_top],
        [outline[0][0], outline[0][1], z_top],
        [outline[1][0], outline[1][1], z_top],
    ])
    faces.append([
        [center_x, center_y, z_bottom],
        [outline[1][0], outline[1][1], z_bottom],
        [outline[0][0], outline[0][1], z_bottom],
    ])

    return np.array(faces, dtype=np.float64)


def create_cylinder_faces(
    cx: float,
    cy: float,
    radius: float,
    z_bottom: float,
    z_top: float,
    segments: int = 32,
) -> np.ndarray:
    verts = create_circle_vertices(cx, cy, radius, segments)
    return extrude_polygon(verts, z_bottom, z_top)
