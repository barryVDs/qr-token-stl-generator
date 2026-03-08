from __future__ import annotations

import logging

import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_M

logger = logging.getLogger(__name__)


def generate_qr_matrix(payload: str) -> np.ndarray:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=1,
        border=0,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    return np.array(matrix, dtype=bool)
