from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.models import TokenConfig, TokenExport, TokenItem
from app.qr_builder import generate_qr_matrix
from app.png_fallback import load_qr_from_png
from app.geometry.token_builder import build_token_mesh
from app.geometry.stl_export import save_faces_as_stl

logger = logging.getLogger(__name__)


@dataclass
class ItemResult:
    output_name: str
    success: bool
    stl_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BatchResult:
    total: int = 0
    successes: int = 0
    failures: int = 0
    items: list[ItemResult] = field(default_factory=list)
    duration_seconds: float = 0.0


def generate_batch(
    export: TokenExport,
    output_dir: Path,
    limit: Optional[int] = None,
) -> BatchResult:
    items = export.items
    if limit is not None and limit > 0:
        items = items[:limit]

    result = BatchResult(total=len(items))
    output_dir.mkdir(parents=True, exist_ok=True)
    config = export.token_config
    start_time = time.time()

    for item in items:
        item_result = _process_item(item, config, output_dir)
        result.items.append(item_result)
        if item_result.success:
            result.successes += 1
        else:
            result.failures += 1

    result.duration_seconds = time.time() - start_time
    _write_summary(result, output_dir)

    return result


def _process_item(
    item: TokenItem, config: TokenConfig, output_dir: Path
) -> ItemResult:
    try:
        if item.qr_payload:
            logger.info("Generating QR from payload for %s", item.output_name)
            qr_matrix = generate_qr_matrix(item.qr_payload)
        elif item.png_path:
            logger.info("Loading QR from PNG for %s", item.output_name)
            qr_matrix = load_qr_from_png(item.png_path)
        else:
            return ItemResult(
                output_name=item.output_name,
                success=False,
                error="No qr_payload or png_path provided",
            )

        logger.info("Building 3D mesh for %s", item.output_name)
        faces = build_token_mesh(config, qr_matrix, item.nummer)

        stl_path = output_dir / f"{item.output_name}.stl"
        save_faces_as_stl(faces, stl_path)

        return ItemResult(
            output_name=item.output_name,
            success=True,
            stl_path=str(stl_path),
        )

    except Exception as e:
        logger.error("Failed to process %s: %s", item.output_name, e)
        return ItemResult(
            output_name=item.output_name,
            success=False,
            error=str(e),
        )


def _write_summary(result: BatchResult, output_dir: Path) -> None:
    summary = {
        "total_items": result.total,
        "successes": result.successes,
        "failures": result.failures,
        "duration_seconds": round(result.duration_seconds, 2),
        "generated_files": [
            r.stl_path for r in result.items if r.success and r.stl_path
        ],
        "errors": [
            {"output_name": r.output_name, "error": r.error}
            for r in result.items
            if not r.success
        ],
    }

    summary_path = output_dir / "generation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Summary written to %s", summary_path)
