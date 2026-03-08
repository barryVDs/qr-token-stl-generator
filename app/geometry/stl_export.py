from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from stl import mesh as stl_mesh

logger = logging.getLogger(__name__)


def save_faces_as_stl(faces: np.ndarray, output_path: Path) -> None:
    num_faces = faces.shape[0]
    token_mesh = stl_mesh.Mesh(np.zeros(num_faces, dtype=stl_mesh.Mesh.dtype))

    for i in range(num_faces):
        token_mesh.vectors[i] = faces[i]

    token_mesh.update_normals()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    token_mesh.save(str(output_path))
    logger.info("Saved STL: %s (%d faces)", output_path, num_faces)
