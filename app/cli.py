from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from app.utils.logging_utils import setup_logging

app = typer.Typer(
    name="qr-token-stl",
    help="Generate 3D printable STL files for QR code tokens from JSON export.",
    add_completion=False,
)


@app.command()
def validate(
    input: Path = typer.Option(..., "--input", "-i", help="Path to input JSON file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Validate a token export JSON file without generating STL files."""
    setup_logging(verbose)
    from app.validator import load_and_validate

    export, result = load_and_validate(input)

    if result.warnings:
        for w in result.warnings:
            typer.echo(f"  WARNING: {w}", err=True)

    if result.errors:
        for e in result.errors:
            typer.echo(f"  ERROR: {e}", err=True)
        raise typer.Exit(code=1)

    assert export is not None
    typer.echo(f"Valid! {len(export.items)} items, config: {export.token_config.shape.value} "
               f"{export.token_config.size_mm}mm")


@app.command()
def generate(
    input: Path = typer.Option(..., "--input", "-i", help="Path to input JSON file"),
    output: Path = typer.Option(..., "--output", "-o", help="Output directory for STL files"),
    zip: bool = typer.Option(False, "--zip", "-z", help="Create a zip of all STL files"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of items to process"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Generate preview PNG images"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Generate STL files from a token export JSON file."""
    setup_logging(verbose)
    import logging

    from app.validator import load_and_validate
    from app.services.batch_generator import generate_batch
    from app.services.zip_service import create_zip

    logger = logging.getLogger(__name__)

    export, result = load_and_validate(input)

    for w in result.warnings:
        typer.echo(f"  WARNING: {w}", err=True)

    if not result.valid or export is None:
        for e in result.errors:
            typer.echo(f"  ERROR: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Processing {len(export.items)} items "
               f"({export.token_config.shape.value} {export.token_config.size_mm}mm)...")

    batch_result = generate_batch(export, output, limit=limit)

    if preview:
        _generate_previews(export, output, limit)

    typer.echo(f"\nDone in {batch_result.duration_seconds:.1f}s")
    typer.echo(f"  Successes: {batch_result.successes}")
    typer.echo(f"  Failures:  {batch_result.failures}")

    if batch_result.failures > 0:
        typer.echo("\nFailed items:")
        for item in batch_result.items:
            if not item.success:
                typer.echo(f"  - {item.output_name}: {item.error}")

    if zip and batch_result.successes > 0:
        zip_path = create_zip(output)
        typer.echo(f"\nZip created: {zip_path}")


def _generate_previews(export, output_dir: Path, limit: Optional[int]) -> None:
    from app.services.preview_service import generate_preview
    from app.qr_builder import generate_qr_matrix
    from app.geometry.token_builder import build_token_mesh

    items = export.items
    if limit is not None and limit > 0:
        items = items[:limit]

    preview_dir = output_dir / "previews"

    for item in items:
        if not item.qr_payload:
            continue
        try:
            qr_matrix = generate_qr_matrix(item.qr_payload)
            faces = build_token_mesh(export.token_config, qr_matrix, item.nummer)
            generate_preview(faces, preview_dir / f"{item.output_name}.png")
        except Exception:
            pass
