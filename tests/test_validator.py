import json
import pytest
from pathlib import Path

from app.validator import load_and_validate


@pytest.fixture
def sample_json(tmp_path):
    data = {
        "export_version": 1,
        "generated_at": "2026-03-08T21:15:00Z",
        "batch": {
            "actie_id": "abc",
            "actie_naam": "Test",
            "preset_name": "Test preset",
            "output_folder_name": "test_output",
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
            "hole_diameter_mm": None,
            "hole_offset_mm": None,
        },
        "items": [
            {
                "qr_code_id": "id1",
                "nummer": 1,
                "token": "tok1",
                "url": "https://example.com/q/tok1",
                "qr_payload": "https://example.com/q/tok1",
                "png_path": None,
                "output_name": "token_001",
            }
        ],
    }
    path = tmp_path / "test.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_valid_file(sample_json):
    export, result = load_and_validate(sample_json)
    assert result.valid
    assert export is not None
    assert len(export.items) == 1


def test_missing_file(tmp_path):
    export, result = load_and_validate(tmp_path / "nonexistent.json")
    assert not result.valid
    assert "not found" in result.errors[0]


def test_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")
    export, result = load_and_validate(path)
    assert not result.valid
    assert export is None


def test_duplicate_output_names(tmp_path):
    data = {
        "export_version": 1,
        "generated_at": "2026-01-01T00:00:00Z",
        "batch": {
            "actie_id": "abc",
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
                "token": "tok1",
                "url": "https://example.com/q/tok1",
                "qr_payload": "https://example.com/q/tok1",
                "output_name": "same_name",
            },
            {
                "qr_code_id": "id2",
                "nummer": 2,
                "token": "tok2",
                "url": "https://example.com/q/tok2",
                "qr_payload": "https://example.com/q/tok2",
                "output_name": "same_name",
            },
        ],
    }
    path = tmp_path / "dupes.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    export, result = load_and_validate(path)
    assert not result.valid
    assert any("Duplicate" in e for e in result.errors)
