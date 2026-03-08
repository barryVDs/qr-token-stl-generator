from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

DARK_THRESHOLD = 128


def load_qr_from_png(png_path: str) -> np.ndarray:
    path = Path(png_path)
    if not path.exists():
        raise FileNotFoundError(f"PNG file not found: {png_path}")

    img = Image.open(path).convert("L")
    arr = np.array(img)

    rows, cols = arr.shape
    if rows < 21 or cols < 21:
        raise ValueError(f"Image too small ({cols}x{rows}px) to contain a valid QR code")

    binary = arr < DARK_THRESHOLD

    top = 0
    while top < rows and not binary[top].any():
        top += 1
    bottom = rows - 1
    while bottom > top and not binary[bottom].any():
        bottom -= 1
    left = 0
    while left < cols and not binary[:, left].any():
        left += 1
    right = cols - 1
    while right > left and not binary[:, right].any():
        right -= 1

    cropped = binary[top : bottom + 1, left : right + 1]
    h, w = cropped.shape

    if h < 21 or w < 21:
        raise ValueError("Cropped QR region is too small")

    module_size_h = h // 21
    module_size_w = w // 21
    module_size = max(module_size_h, module_size_w, 1)

    modules_h = h // module_size
    modules_w = w // module_size

    matrix = np.zeros((modules_h, modules_w), dtype=bool)
    for r in range(modules_h):
        for c in range(modules_w):
            block = cropped[
                r * module_size : (r + 1) * module_size,
                c * module_size : (c + 1) * module_size,
            ]
            matrix[r, c] = block.sum() > block.size * 0.5

    return matrix
