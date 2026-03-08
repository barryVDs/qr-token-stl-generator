from __future__ import annotations

import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def create_zip(output_dir: Path, zip_name: str = "tokens.zip") -> Path:
    stl_files = sorted(output_dir.glob("*.stl"))
    if not stl_files:
        raise FileNotFoundError(f"No STL files found in {output_dir}")

    zip_path = output_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for stl_file in stl_files:
            zf.write(stl_file, stl_file.name)

        summary = output_dir / "generation_summary.json"
        if summary.exists():
            zf.write(summary, summary.name)

    logger.info("Created zip: %s (%d files)", zip_path, len(stl_files))
    return zip_path
