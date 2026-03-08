from __future__ import annotations

import logging

import numpy as np

from app.models import NumberPosition, ReliefStyle, Shape, TokenConfig
from app.geometry.base_shapes import (
    create_circle_vertices,
    create_cylinder_faces,
    create_rounded_rect_vertices,
    extrude_polygon,
)
from app.geometry.qr_relief import generate_qr_relief_faces
from app.geometry.text_relief import generate_number_relief_faces

logger = logging.getLogger(__name__)


def build_token_mesh(
    config: TokenConfig,
    qr_matrix: np.ndarray,
    nummer: int,
) -> np.ndarray:
    all_faces: list[np.ndarray] = []

    base_faces = _build_base(config)
    all_faces.append(base_faces)

    qr_faces = _build_qr(config, qr_matrix)
    if qr_faces.shape[0] > 0:
        all_faces.append(qr_faces)

    if config.show_number and config.number_position != NumberPosition.BACK:
        num_faces = _build_number_front(config, nummer)
        if num_faces.shape[0] > 0:
            all_faces.append(num_faces)

    if config.show_number and config.number_position == NumberPosition.BACK:
        num_faces = _build_number_back(config, nummer)
        if num_faces.shape[0] > 0:
            all_faces.append(num_faces)

    if config.hole_enabled and config.hole_diameter_mm and config.hole_offset_mm is not None:
        hole_faces = _build_hole(config)
        all_faces.append(hole_faces)

    return np.concatenate(all_faces, axis=0)


def _build_base(config: TokenConfig) -> np.ndarray:
    if config.shape == Shape.ROUND:
        outline = create_circle_vertices(0, 0, config.size_mm / 2, segments=64)
    else:
        if config.corner_radius_mm > 0:
            outline = create_rounded_rect_vertices(
                0, 0, config.size_mm, config.size_mm, config.corner_radius_mm
            )
        else:
            from app.geometry.base_shapes import create_rect_vertices
            outline = create_rect_vertices(0, 0, config.size_mm, config.size_mm)

    return extrude_polygon(outline, 0.0, config.thickness_mm)


def _build_qr(config: TokenConfig, qr_matrix: np.ndarray) -> np.ndarray:
    available = config.size_mm - 2 * config.qr_margin_mm
    if config.border_enabled:
        available -= 2 * config.border_mm

    qr_center_y = 0.0
    if config.show_number and config.number_position == NumberPosition.BOTTOM:
        shift = (config.number_size_mm + 1.0) / 2
        qr_center_y += shift
        available -= config.number_size_mm + 1.0
    elif config.show_number and config.number_position == NumberPosition.TOP:
        shift = (config.number_size_mm + 1.0) / 2
        qr_center_y -= shift
        available -= config.number_size_mm + 1.0

    if config.hole_enabled and config.hole_diameter_mm and config.hole_offset_mm is not None:
        if config.shape == Shape.ROUND:
            qr_center_y -= (config.hole_diameter_mm / 2 + config.hole_offset_mm) / 2

    qr_area_size = available

    if config.qr_style == ReliefStyle.EMBOSSED:
        base_z = config.thickness_mm
    else:
        base_z = config.thickness_mm

    return generate_qr_relief_faces(
        qr_matrix=qr_matrix,
        qr_area_size_mm=qr_area_size,
        qr_offset_x=0.0,
        qr_offset_y=qr_center_y,
        base_z=base_z,
        relief_height=config.qr_height_mm,
        style=config.qr_style,
    )


def _build_number_front(config: TokenConfig, nummer: int) -> np.ndarray:
    if config.number_position == NumberPosition.BOTTOM:
        num_y = -(config.size_mm / 2) + config.border_mm + config.number_size_mm / 2
        if config.qr_margin_mm > config.border_mm:
            num_y = -(config.size_mm / 2) + config.qr_margin_mm + config.number_size_mm / 2
    else:
        num_y = (config.size_mm / 2) - config.border_mm - config.number_size_mm / 2
        if config.qr_margin_mm > config.border_mm:
            num_y = (config.size_mm / 2) - config.qr_margin_mm - config.number_size_mm / 2

    if config.number_style == ReliefStyle.EMBOSSED:
        base_z = config.thickness_mm
    else:
        base_z = config.thickness_mm

    return generate_number_relief_faces(
        number=nummer,
        center_x=0.0,
        center_y=num_y,
        char_height_mm=config.number_size_mm,
        base_z=base_z,
        relief_height=config.number_height_mm,
        style=config.number_style,
    )


def _build_number_back(config: TokenConfig, nummer: int) -> np.ndarray:
    base_z = 0.0

    faces = generate_number_relief_faces(
        number=nummer,
        center_x=0.0,
        center_y=0.0,
        char_height_mm=config.number_size_mm,
        base_z=base_z,
        relief_height=config.number_height_mm,
        style=config.number_style,
    )

    if config.number_style == ReliefStyle.EMBOSSED:
        faces[:, :, 2] = -faces[:, :, 2]

    return faces


def _build_hole(config: TokenConfig) -> np.ndarray:
    assert config.hole_diameter_mm is not None
    assert config.hole_offset_mm is not None

    radius = config.hole_diameter_mm / 2

    if config.shape == Shape.ROUND:
        hole_y = config.size_mm / 2 - config.border_mm - radius - config.hole_offset_mm
    else:
        hole_y = config.size_mm / 2 - config.border_mm - radius - config.hole_offset_mm

    return create_cylinder_faces(
        cx=0.0,
        cy=hole_y,
        radius=radius,
        z_bottom=-0.1,
        z_top=config.thickness_mm + 0.1,
        segments=32,
    )
