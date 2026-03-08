from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.models import TokenExport

logger = logging.getLogger(__name__)


class ValidationResult:
    def __init__(self) -> None:
        self.valid = True
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, msg: str) -> None:
        self.valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def load_and_validate(input_path: Path) -> tuple[Optional[TokenExport], ValidationResult]:
    result = ValidationResult()

    if not input_path.exists():
        result.add_error(f"Input file not found: {input_path}")
        return None, result

    if not input_path.suffix.lower() == ".json":
        result.add_warning("Input file does not have .json extension")

    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON: {e}")
        return None, result

    try:
        export = TokenExport(**raw)
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            result.add_error(f"Validation error at {loc}: {err['msg']}")
        return None, result

    config = export.token_config

    if config.qr_height_mm > config.thickness_mm * 0.5:
        result.add_warning(
            f"qr_height_mm ({config.qr_height_mm}) is more than half the thickness "
            f"({config.thickness_mm}). This may weaken the token."
        )

    if config.size_mm < 25:
        result.add_warning(
            f"size_mm ({config.size_mm}) is small. QR may be hard to scan."
        )

    if config.hole_enabled and config.hole_diameter_mm:
        if config.hole_diameter_mm > config.size_mm * 0.2:
            result.add_warning(
                f"hole_diameter_mm ({config.hole_diameter_mm}) is large relative to "
                f"token size ({config.size_mm}). May interfere with QR."
            )

    seen_names: set[str] = set()
    for item in export.items:
        if item.output_name in seen_names:
            result.add_error(f"Duplicate output_name: '{item.output_name}'")
        seen_names.add(item.output_name)

    return export, result
