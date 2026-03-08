from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def generate_preview(
    faces: np.ndarray,
    output_path: Path,
    image_size: int = 512,
) -> Optional[Path]:
    try:
        all_verts = faces.reshape(-1, 3)
        x_vals = all_verts[:, 0]
        y_vals = all_verts[:, 1]
        z_vals = all_verts[:, 2]

        x_min, x_max = x_vals.min(), x_vals.max()
        y_min, y_max = y_vals.min(), y_vals.max()

        padding = 20
        usable = image_size - 2 * padding
        x_range = x_max - x_min or 1.0
        y_range = y_max - y_min or 1.0
        scale = usable / max(x_range, y_range)

        img = Image.new("RGB", (image_size, image_size), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        z_median = np.median(z_vals)

        face_data = []
        for face in faces:
            z_avg = face[:, 2].mean()
            face_data.append((z_avg, face))

        face_data.sort(key=lambda x: x[0])

        for z_avg, face in face_data:
            pts = []
            for v in face:
                px = padding + (v[0] - x_min) * scale
                py = image_size - padding - (v[1] - y_min) * scale
                pts.append((px, py))

            brightness = int(120 + min(135, max(0, (z_avg - z_median) * 200)))
            color = (brightness, brightness, brightness)

            draw.polygon(pts, fill=color, outline=(100, 100, 100))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))
        logger.info("Preview saved: %s", output_path)
        return output_path

    except Exception as e:
        logger.warning("Preview generation failed: %s", e)
        return None
