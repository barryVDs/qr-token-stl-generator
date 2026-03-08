from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class Shape(str, Enum):
    ROUND = "round"
    SQUARE = "square"


class ReliefStyle(str, Enum):
    EMBOSSED = "embossed"
    ENGRAVED = "engraved"


class NumberPosition(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    BACK = "back"


class TokenConfig(BaseModel):
    shape: Shape
    size_mm: float
    thickness_mm: float
    qr_style: ReliefStyle
    qr_height_mm: float
    qr_margin_mm: float
    show_number: bool = False
    number_position: NumberPosition = NumberPosition.BOTTOM
    number_style: ReliefStyle = ReliefStyle.ENGRAVED
    number_height_mm: float = 0.6
    number_size_mm: float = 6.0
    border_enabled: bool = True
    border_mm: float = 1.2
    corner_radius_mm: float = 2.0
    hole_enabled: bool = False
    hole_diameter_mm: Optional[float] = None
    hole_offset_mm: Optional[float] = None

    @field_validator("size_mm")
    @classmethod
    def size_must_be_reasonable(cls, v: float) -> float:
        if v < 15:
            raise ValueError("size_mm must be at least 15mm for a scannable QR code")
        if v > 200:
            raise ValueError("size_mm exceeds 200mm — are you sure?")
        return v

    @field_validator("thickness_mm")
    @classmethod
    def thickness_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("thickness_mm must be greater than 0")
        if v < 1.0:
            raise ValueError("thickness_mm below 1.0mm may be too fragile to print")
        return v

    @field_validator("qr_height_mm")
    @classmethod
    def qr_height_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("qr_height_mm must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_hole_settings(self) -> TokenConfig:
        if self.hole_enabled:
            if self.hole_diameter_mm is None or self.hole_diameter_mm <= 0:
                raise ValueError("hole_diameter_mm must be > 0 when hole_enabled is true")
            if self.hole_offset_mm is None or self.hole_offset_mm < 0:
                raise ValueError("hole_offset_mm must be >= 0 when hole_enabled is true")
        return self

    @model_validator(mode="after")
    def validate_qr_fits(self) -> TokenConfig:
        available = self.size_mm - 2 * self.qr_margin_mm
        if self.border_enabled:
            available -= 2 * self.border_mm
        if self.show_number and self.number_position != NumberPosition.BACK:
            available -= self.number_size_mm + 1.0
        if available < 10:
            raise ValueError(
                f"Not enough space for QR code: only {available:.1f}mm available "
                f"(minimum 10mm needed). Reduce margins, border, or number size."
            )
        return self


SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


class TokenItem(BaseModel):
    qr_code_id: str
    nummer: int
    token: str
    url: str
    qr_payload: Optional[str] = None
    png_path: Optional[str] = None
    output_name: str

    @field_validator("nummer")
    @classmethod
    def nummer_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("nummer must be a non-negative integer")
        return v

    @field_validator("output_name")
    @classmethod
    def output_name_safe(cls, v: str) -> str:
        if not SAFE_FILENAME_RE.match(v):
            raise ValueError(
                f"output_name '{v}' contains unsafe characters. "
                "Only alphanumeric, underscore, and hyphen are allowed."
            )
        return v

    @model_validator(mode="after")
    def must_have_payload_or_png(self) -> TokenItem:
        if not self.qr_payload and not self.png_path:
            raise ValueError(
                f"Item '{self.output_name}' has neither qr_payload nor png_path. "
                "At least one is required to generate a QR code."
            )
        return self


class BatchInfo(BaseModel):
    actie_id: str
    actie_naam: str
    preset_name: str
    output_folder_name: str


class TokenExport(BaseModel):
    export_version: int
    generated_at: str
    batch: BatchInfo
    token_config: TokenConfig
    items: list[TokenItem]

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list[TokenItem]) -> list[TokenItem]:
        if len(v) == 0:
            raise ValueError("items list must not be empty")
        return v
