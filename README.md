# QR Token STL Generator

Command-line tool dat een JSON-export inleest en 3D-printbare STL-bestanden genereert voor QR-code tokens.

## Wat doet het?

- Leest een JSON-bestand met batch-configuratie en token-items
- Genereert per token een QR-code op basis van de `qr_payload`
- Bouwt een 3D-model met de QR als reliëf (embossed of engraved)
- Exporteert elk token als STL-bestand, klaar voor 3D-printen
- Optioneel: volgnummer, rand, ophanggatje, zip-export, preview

## Vereisten

- Python 3.11 of hoger
- pip

## Installatie

```bash
cd qr-token-stl-generator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Gebruik

### Valideer een JSON-bestand

```bash
python -m app validate --input ./examples/sample_tokens_round.json
```

### Genereer STL-bestanden

```bash
python -m app generate --input ./examples/sample_tokens_round.json --output ./out
```

### Met zip-export

```bash
python -m app generate --input ./examples/sample_tokens_round.json --output ./out --zip
```

### Met limiet en verbose logging

```bash
python -m app generate --input ./examples/sample_tokens_round.json --output ./out --limit 5 --verbose
```

### Met preview afbeeldingen

```bash
python -m app generate --input ./examples/sample_tokens_round.json --output ./out --preview
```

## Input JSON structuur

```json
{
  "export_version": 1,
  "generated_at": "2026-03-08T21:15:00Z",
  "batch": {
    "actie_id": "uuid",
    "actie_naam": "Naam van de actie",
    "preset_name": "Preset naam",
    "output_folder_name": "mapnaam"
  },
  "token_config": {
    "shape": "round | square",
    "size_mm": 50,
    "thickness_mm": 2.4,
    "qr_style": "embossed | engraved",
    "qr_height_mm": 0.8,
    "qr_margin_mm": 2.0,
    "show_number": true,
    "number_position": "top | bottom | back",
    "number_style": "embossed | engraved",
    "number_height_mm": 0.6,
    "number_size_mm": 6.0,
    "border_enabled": true,
    "border_mm": 1.2,
    "corner_radius_mm": 2.0,
    "hole_enabled": false,
    "hole_diameter_mm": null,
    "hole_offset_mm": null
  },
  "items": [
    {
      "qr_code_id": "uuid",
      "nummer": 1,
      "token": "abc123",
      "url": "https://example.com/q/abc123",
      "qr_payload": "https://example.com/q/abc123",
      "png_path": null,
      "output_name": "token_001"
    }
  ]
}
```

## Output

- Per item een `{output_name}.stl` bestand
- `generation_summary.json` met overzicht van successen en fouten
- Optioneel: `tokens.zip` met alle STL-bestanden
- Optioneel: `previews/` map met PNG previews

## Token configuratie opties

| Parameter | Beschrijving |
|---|---|
| `shape` | `round` of `square` |
| `size_mm` | Diameter (rond) of zijde (vierkant) in mm |
| `thickness_mm` | Basisdikte van het token |
| `qr_style` | `embossed` (verhoogd) of `engraved` (verdiept) |
| `qr_height_mm` | Hoogte/diepte van het QR-reliëf |
| `qr_margin_mm` | Marge rond de QR-code (quiet zone) |
| `show_number` | Toon volgnummer op het token |
| `number_position` | `top`, `bottom` (voorkant) of `back` (achterkant) |
| `hole_enabled` | Ophanggatje toevoegen |
| `hole_diameter_mm` | Diameter van het gat |
| `hole_offset_mm` | Afstand van de rand tot het gat |

## Tests

```bash
pip install -r requirements.txt
pytest
```

## Beperkingen en aannames

- QR-codes worden gegenereerd met Error Correction Level M
- Nummers worden weergegeven als pixelfonts (bitmap digits)
- Het ophanggatje wordt als cylinder-mesh toegevoegd (geen boolean subtractie)
- De preview is een simpele 2D projectie, geen echte 3D render
- PNG-fallback voor QR probeert de module-grootte te detecteren maar is niet altijd accuraat
- Minimale tokengrootte is 15mm; daaronder past geen scanbare QR

## Toekomstige uitbreidingen

- Boolean mesh operations voor correcte gaten
- Logo/icoon in het midden van de QR
- Tekst naast nummers (bijv. naam)
- Betere 3D preview met belichting
- Meerdere tokens op één printplaat
- STEP-export naast STL
- Web-interface voor configuratie
