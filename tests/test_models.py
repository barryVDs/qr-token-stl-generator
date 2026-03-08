import pytest
from pydantic import ValidationError

from app.models import TokenConfig, TokenItem, TokenExport, BatchInfo, Shape, ReliefStyle, NumberPosition


def _make_config(**overrides):
    defaults = {
        "shape": "round",
        "size_mm": 50,
        "thickness_mm": 2.4,
        "qr_style": "engraved",
        "qr_height_mm": 0.8,
        "qr_margin_mm": 2.0,
        "show_number": False,
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
    }
    defaults.update(overrides)
    return TokenConfig(**defaults)


def _make_item(**overrides):
    defaults = {
        "qr_code_id": "abc-123",
        "nummer": 1,
        "token": "tok1",
        "url": "https://example.com/q/tok1",
        "qr_payload": "https://example.com/q/tok1",
        "png_path": None,
        "output_name": "token_001",
    }
    defaults.update(overrides)
    return TokenItem(**defaults)


class TestTokenConfig:
    def test_valid_round(self):
        config = _make_config()
        assert config.shape == Shape.ROUND

    def test_valid_square(self):
        config = _make_config(shape="square")
        assert config.shape == Shape.SQUARE

    def test_invalid_shape(self):
        with pytest.raises(ValidationError):
            _make_config(shape="triangle")

    def test_size_too_small(self):
        with pytest.raises(ValidationError, match="at least 15mm"):
            _make_config(size_mm=5)

    def test_thickness_zero(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            _make_config(thickness_mm=0)

    def test_thickness_too_thin(self):
        with pytest.raises(ValidationError, match="too fragile"):
            _make_config(thickness_mm=0.5)

    def test_hole_enabled_without_diameter(self):
        with pytest.raises(ValidationError, match="hole_diameter_mm"):
            _make_config(hole_enabled=True, hole_diameter_mm=None, hole_offset_mm=3.0)

    def test_hole_enabled_valid(self):
        config = _make_config(hole_enabled=True, hole_diameter_mm=4.0, hole_offset_mm=3.0)
        assert config.hole_enabled is True

    def test_qr_no_space(self):
        with pytest.raises(ValidationError, match="Not enough space"):
            _make_config(size_mm=15, qr_margin_mm=3.0, border_mm=2.0)


class TestTokenItem:
    def test_valid_item(self):
        item = _make_item()
        assert item.nummer == 1

    def test_negative_nummer(self):
        with pytest.raises(ValidationError, match="non-negative"):
            _make_item(nummer=-1)

    def test_unsafe_output_name(self):
        with pytest.raises(ValidationError, match="unsafe characters"):
            _make_item(output_name="bad name!!")

    def test_no_payload_or_png(self):
        with pytest.raises(ValidationError, match="neither qr_payload nor png_path"):
            _make_item(qr_payload=None, png_path=None)

    def test_png_fallback(self):
        item = _make_item(qr_payload=None, png_path="/tmp/qr.png")
        assert item.png_path == "/tmp/qr.png"


class TestTokenExport:
    def test_empty_items(self):
        with pytest.raises(ValidationError, match="must not be empty"):
            TokenExport(
                export_version=1,
                generated_at="2026-01-01T00:00:00Z",
                batch=BatchInfo(
                    actie_id="id",
                    actie_naam="naam",
                    preset_name="preset",
                    output_folder_name="folder",
                ),
                token_config=_make_config(),
                items=[],
            )
