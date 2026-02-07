"""Database seeder for PortiQ — populates categories, units, and conversions.

Run via: python -m src.seed
"""

import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.engine import sync_engine

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

CATEGORY_NAMES: list[str] = [
    "Deck Stores",
    "Deck Equipment",
    "Mooring",
    "Hoses",
    "Paints",
    "Chemicals & Gases",
    "Cleaning Equipment",
    "Electrical Stores",
    "Electrical Equipment",
    "Engine Stores",
    "Engine Equipment",
    "Fasteners",
    "Fittings (Pipes & Tubes)",
    "Gaskets & Packing",
    "Hand Tools",
    "Power Tools",
    "Welding & Cutting",
    "Workshop Equipment",
    "Lubricants",
    "Raw Material",
    "Valves",
    "Fire Fighting Equipment",
    "Life Saving Equipment",
    "Safety Equipment",
    "Medical Stores",
    "Stationery & Books",
    "Laundry & Sewing",
    "Galley & Tableware",
    "Cabin Stores & Linen",
    "Provisions",
    "Navigation Equipment",
    "Communication Equipment",
    "Entertainment & Sport",
    "Refrigeration & AC",
    "Spare Parts",
]

UNITS_OF_MEASURE: list[dict] = [
    {"code": "EA", "name": "Each", "unit_type": "QUANTITY", "base_unit": None, "display_order": 1},
    {"code": "PCS", "name": "Pieces", "unit_type": "QUANTITY", "base_unit": None, "display_order": 2},
    {"code": "SET", "name": "Set", "unit_type": "QUANTITY", "base_unit": None, "display_order": 3},
    {"code": "PKT", "name": "Packet", "unit_type": "QUANTITY", "base_unit": None, "display_order": 4},
    {"code": "BOX", "name": "Box", "unit_type": "QUANTITY", "base_unit": None, "display_order": 5},
    {"code": "CTN", "name": "Carton", "unit_type": "QUANTITY", "base_unit": None, "display_order": 6},
    {"code": "PAL", "name": "Pallet", "unit_type": "QUANTITY", "base_unit": None, "display_order": 7},
    {"code": "DZN", "name": "Dozen", "unit_type": "QUANTITY", "base_unit": None, "display_order": 8},
    {"code": "PR", "name": "Pair", "unit_type": "QUANTITY", "base_unit": None, "display_order": 9},
    {"code": "ROL", "name": "Roll", "unit_type": "QUANTITY", "base_unit": None, "display_order": 10},
    {"code": "CAN", "name": "Can", "unit_type": "QUANTITY", "base_unit": None, "display_order": 11},
    {"code": "BTL", "name": "Bottle", "unit_type": "QUANTITY", "base_unit": None, "display_order": 12},
    {"code": "DRM", "name": "Drum", "unit_type": "QUANTITY", "base_unit": None, "display_order": 13},
    {"code": "M", "name": "Metre", "unit_type": "LENGTH", "base_unit": None, "display_order": 14},
    {"code": "MM", "name": "Millimetre", "unit_type": "LENGTH", "base_unit": "M", "display_order": 15},
    {"code": "CM", "name": "Centimetre", "unit_type": "LENGTH", "base_unit": "M", "display_order": 16},
    {"code": "FT", "name": "Foot", "unit_type": "LENGTH", "base_unit": "M", "display_order": 17},
    {"code": "IN", "name": "Inch", "unit_type": "LENGTH", "base_unit": "M", "display_order": 18},
    {"code": "FM", "name": "Fathom", "unit_type": "LENGTH", "base_unit": "M", "display_order": 19},
    {"code": "KG", "name": "Kilogram", "unit_type": "WEIGHT", "base_unit": None, "display_order": 20},
    {"code": "G", "name": "Gram", "unit_type": "WEIGHT", "base_unit": "KG", "display_order": 21},
    {"code": "T", "name": "Tonne", "unit_type": "WEIGHT", "base_unit": "KG", "display_order": 22},
    {"code": "LB", "name": "Pound", "unit_type": "WEIGHT", "base_unit": "KG", "display_order": 23},
    {"code": "OZ", "name": "Ounce", "unit_type": "WEIGHT", "base_unit": "KG", "display_order": 24},
    {"code": "LTR", "name": "Litre", "unit_type": "VOLUME", "base_unit": None, "display_order": 25},
    {"code": "ML", "name": "Millilitre", "unit_type": "VOLUME", "base_unit": "LTR", "display_order": 26},
    {"code": "GAL", "name": "Gallon (US)", "unit_type": "VOLUME", "base_unit": "LTR", "display_order": 27},
    {"code": "M3", "name": "Cubic Metre", "unit_type": "VOLUME", "base_unit": "LTR", "display_order": 28},
]

UNIT_CONVERSIONS: list[tuple[str, str, str]] = [
    ("MM", "M", "0.001"),
    ("CM", "M", "0.01"),
    ("M", "MM", "1000"),
    ("M", "CM", "100"),
    ("FT", "M", "0.3048"),
    ("M", "FT", "3.28084"),
    ("IN", "M", "0.0254"),
    ("M", "IN", "39.3701"),
    ("FM", "M", "1.8288"),
    ("M", "FM", "0.546807"),
    ("IN", "CM", "2.54"),
    ("FT", "IN", "12"),
    ("G", "KG", "0.001"),
    ("KG", "G", "1000"),
    ("T", "KG", "1000"),
    ("KG", "T", "0.001"),
    ("LB", "KG", "0.453592"),
    ("KG", "LB", "2.20462"),
    ("OZ", "KG", "0.0283495"),
    ("KG", "OZ", "35.274"),
    ("ML", "LTR", "0.001"),
    ("LTR", "ML", "1000"),
    ("GAL", "LTR", "3.78541"),
    ("LTR", "GAL", "0.264172"),
    ("M3", "LTR", "1000"),
    ("LTR", "M3", "0.001"),
    ("DZN", "EA", "12"),
    ("PR", "EA", "2"),
    ("PCS", "EA", "1"),
]


def _to_snake_case(name: str) -> str:
    """Convert category name to snake_case for ltree path segments."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    return re.sub(r"\s+", "_", cleaned.strip()).lower()


def seed_categories(session: Session) -> None:
    """Upsert root + 35 IMPA categories with closure table entries and IMPA mappings."""
    now = datetime.now(timezone.utc)

    # Upsert root category
    session.execute(
        text("""
            INSERT INTO categories (code, impa_prefix, name, path, level, display_order)
            VALUES (:code, :impa_prefix, :name, :path, :level, :display_order)
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, path = EXCLUDED.path
        """),
        {"code": "CAT-ROOT", "impa_prefix": None, "name": "All Categories", "path": "root", "level": 0, "display_order": 0},
    )

    root_id = session.execute(
        text("SELECT id FROM categories WHERE code = 'CAT-ROOT'")
    ).scalar_one()

    # Self-referencing closure for root
    session.execute(
        text("""
            INSERT INTO category_closures (ancestor_id, descendant_id, depth)
            VALUES (:ancestor_id, :descendant_id, :depth)
            ON CONFLICT (ancestor_id, descendant_id) DO NOTHING
        """),
        {"ancestor_id": root_id, "descendant_id": root_id, "depth": 0},
    )

    for index, category_name in enumerate(CATEGORY_NAMES, start=1):
        impa_prefix = f"{index:02d}"
        code = f"CAT-{impa_prefix}"
        path = f"root.{_to_snake_case(category_name)}"

        # Upsert category
        session.execute(
            text("""
                INSERT INTO categories (code, impa_prefix, name, path, level, display_order)
                VALUES (:code, :impa_prefix, :name, :path, :level, :display_order)
                ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, path = EXCLUDED.path
            """),
            {"code": code, "impa_prefix": impa_prefix, "name": category_name, "path": path, "level": 1, "display_order": index},
        )

        category_id = session.execute(
            text("SELECT id FROM categories WHERE code = :code"),
            {"code": code},
        ).scalar_one()

        # Self-referencing closure entry (depth=0)
        session.execute(
            text("""
                INSERT INTO category_closures (ancestor_id, descendant_id, depth)
                VALUES (:ancestor_id, :descendant_id, :depth)
                ON CONFLICT (ancestor_id, descendant_id) DO NOTHING
            """),
            {"ancestor_id": category_id, "descendant_id": category_id, "depth": 0},
        )

        # Root -> Category closure entry (depth=1)
        session.execute(
            text("""
                INSERT INTO category_closures (ancestor_id, descendant_id, depth)
                VALUES (:ancestor_id, :descendant_id, :depth)
                ON CONFLICT (ancestor_id, descendant_id) DO NOTHING
            """),
            {"ancestor_id": root_id, "descendant_id": category_id, "depth": 1},
        )

        # IMPA category mapping
        session.execute(
            text("""
                INSERT INTO impa_category_mappings (impa_prefix, impa_category_name, internal_category_id, mapping_confidence, last_verified)
                VALUES (:impa_prefix, :impa_category_name, :internal_category_id, :mapping_confidence, :last_verified)
                ON CONFLICT (impa_prefix) DO UPDATE SET
                    impa_category_name = EXCLUDED.impa_category_name,
                    internal_category_id = EXCLUDED.internal_category_id,
                    last_verified = EXCLUDED.last_verified
            """),
            {
                "impa_prefix": impa_prefix,
                "impa_category_name": category_name,
                "internal_category_id": category_id,
                "mapping_confidence": "EXACT",
                "last_verified": now,
            },
        )

    print(f"  Seeded {len(CATEGORY_NAMES)} categories + root with closure entries and IMPA mappings.")


def seed_units(session: Session) -> None:
    """Upsert units of measure."""
    for unit in UNITS_OF_MEASURE:
        session.execute(
            text("""
                INSERT INTO units_of_measure (code, name, unit_type, base_unit, display_order)
                VALUES (:code, :name, :unit_type, :base_unit, :display_order)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    unit_type = EXCLUDED.unit_type,
                    base_unit = EXCLUDED.base_unit,
                    display_order = EXCLUDED.display_order
            """),
            unit,
        )

    print(f"  Seeded {len(UNITS_OF_MEASURE)} units of measure.")


def seed_conversions(session: Session) -> None:
    """Upsert unit conversion factors."""
    for from_unit, to_unit, factor in UNIT_CONVERSIONS:
        session.execute(
            text("""
                INSERT INTO unit_conversions (from_unit, to_unit, conversion_factor)
                VALUES (:from_unit, :to_unit, :factor)
                ON CONFLICT ON CONSTRAINT uq_unit_conversions DO UPDATE SET
                    conversion_factor = EXCLUDED.conversion_factor
            """),
            {"from_unit": from_unit, "to_unit": to_unit, "factor": Decimal(factor)},
        )

    print(f"  Seeded {len(UNIT_CONVERSIONS)} unit conversions.")


def main() -> None:
    """Run all seed functions inside a single transaction."""
    print("Seeding PortiQ database...")

    with Session(sync_engine) as session:
        with session.begin():
            seed_categories(session)
            seed_units(session)
            seed_conversions(session)

    print("Seeding complete.")


if __name__ == "__main__":
    main()
