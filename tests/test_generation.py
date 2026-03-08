import json
import pytest
from pathlib import Path

from app.models import TokenExport
from app.services.batch_generator import generate_batch
from app.qr_builder import generate_qr_matrix
from app.geometry.token_builder import build_token_mesh


@pytest.fixture
def round_export():
    data = {
        "export_version": 1,
        "generated_at": "2026-03-08T21:15:00Z",
        "batch": {
            "actie_id": "test-id",
            "actie_naam": "Test Batch",
            "preset_name": "Test Preset",
            "output_folder_name": "test_out",
        },
        "token_config": {
            "shape": "round",
            "size_mm": 50,
            "thickness_mm": 2.4,
            "qr_style": "engraved",
            "qr_height_mm": 0.8,
            "qr_margin_mm": 2.0,
            "show_number": True,
            "number_position": "bottom",
            "number_style": "engraved",
            "number_height_mm": 0.6,
            "number_size_mm": 6.0,
            "border_enabled": True,
            "border_mm": 1.2,
            "corner_radius_mm": 2.0,
            "hole_enabled": False,
        },
        "items": [
            {
                "qr_code_id": "id1",
                "nummer": 1,
                "token": "abc",
                "url": "https://example.com/q/abc",
                "qr_payload": "https://example.com/q/abc",
                "output_name": "test_token_001",
            },
            {
                "qr_code_id": "id2",
                "nummer": 2,
                "token": "def",
                "url": "https://example.com/q/def",
                "qr_payload": "https://example.com/q/def",
                "output_name": "test_token_002",
            },
        ],
    }
    return TokenExport(**data)


def test_qr_matrix_generation():
    matrix = generate_qr_matrix("https://example.com/q/abc123")
    assert matrix.shape[0] >= 21
    assert matrix.shape[1] >= 21
    assert matrix.dtype.name == "bool"


def test_build_token_mesh(round_export):
    matrix = generate_qr_matrix("https://example.com/q/abc")
    faces = build_token_mesh(round_export.token_config, matrix, 1)
    assert faces.shape[0] > 0
    assert faces.shape[1] == 3
    assert faces.shape[2] == 3


def test_batch_generation(round_export, tmp_path):
    result = generate_batch(round_export, tmp_path / "output")
    assert result.total == 2
    assert result.successes == 2
    assert result.failures == 0

    stl_files = list((tmp_path / "output").glob("*.stl"))
    assert len(stl_files) == 2

    summary = tmp_path / "output" / "generation_summary.json"
    assert summary.exists()


def test_batch_with_limit(round_export, tmp_path):
    result = generate_batch(round_export, tmp_path / "output", limit=1)
    assert result.total == 1
    assert result.successes == 1


def test_batch_with_bad_item(tmp_path):
    data = {
        "export_version": 1,
        "generated_at": "2026-01-01T00:00:00Z",
        "batch": {
            "actie_id": "test",
            "actie_naam": "Test",
            "preset_name": "Test",
            "output_folder_name": "test",
        },
        "token_config": {
            "shape": "round",
            "size_mm": 50,
            "thickness_mm": 2.4,
            "qr_style": "engraved",
            "qr_height_mm": 0.8,
            "qr_margin_mm": 2.0,
        },
        "items": [
            {
                "qr_code_id": "id1",
                "nummer": 1,
                "token": "good",
                "url": "https://example.com/q/good",
                "qr_payload": "https://example.com/q/good",
                "output_name": "good_token",
            },
            {
                "qr_code_id": "id2",
                "nummer": 2,
                "token": "bad",
                "url": "https://example.com/q/bad",
                "qr_payload": "https://example.com/q/bad",
                "png_path": "/nonexistent/qr.png",
                "output_name": "bad_token",
            },
        ],
    }
    export = TokenExport(**data)
    result = generate_batch(export, tmp_path / "output")
    assert result.successes == 2  # qr_payload takes priority over png_path
