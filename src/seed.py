"""Database seeder for PortiQ — populates all reference and demo data.

Run via: python -m src.seed
"""

import json
import re
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.engine import sync_engine
from src.seed_data.categories import IMPA_CATEGORIES
from src.seed_data.organizations import ORGANIZATIONS
from src.seed_data.products import PRODUCTS
from src.seed_data.supplier_products import SUPPLIER_PRODUCTS
from src.seed_data.suppliers import SUPPLIER_PROFILES
from src.seed_data.users import PASSWORD_HASH, USERS
from src.seed_data.vessels import VESSELS

# ---------------------------------------------------------------------------
# Seed data (units — kept inline as they're small)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_snake_case(name: str) -> str:
    """Convert category name to snake_case for ltree path segments."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    return re.sub(r"\s+", "_", cleaned.strip()).lower()


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


def delete_old_categories(session: Session) -> None:
    """Remove old sequential categories (CAT-01..CAT-35) and their related data."""
    # Find old categories that don't match new IMPA prefixes
    new_prefixes = {cat["prefix"] for cat in IMPA_CATEGORIES}
    old_codes = []
    for i in range(1, 36):
        code = f"CAT-{i:02d}"
        prefix = f"{i:02d}"
        if prefix not in new_prefixes:
            old_codes.append(code)

    if not old_codes:
        return

    # Delete IMPA mappings for old prefixes first
    for i in range(1, 36):
        prefix = f"{i:02d}"
        if prefix not in new_prefixes:
            session.execute(
                text("DELETE FROM impa_category_mappings WHERE impa_prefix = :prefix"),
                {"prefix": prefix},
            )

    # Delete closures and categories for old codes
    for code in old_codes:
        cat_id = session.execute(
            text("SELECT id FROM categories WHERE code = :code"),
            {"code": code},
        ).scalar_one_or_none()
        if cat_id:
            session.execute(
                text("DELETE FROM category_closures WHERE ancestor_id = :id OR descendant_id = :id"),
                {"id": cat_id},
            )
            session.execute(
                text("DELETE FROM categories WHERE id = :id"),
                {"id": cat_id},
            )

    print(f"  Deleted {len(old_codes)} old sequential categories.")


def seed_categories(session: Session) -> None:
    """Upsert root + 34 real IMPA categories with closure table entries and IMPA mappings."""
    now = datetime.now(UTC)

    # Upsert root category
    session.execute(
        text("""
            INSERT INTO categories (code, impa_prefix, name, path, level, display_order)
            VALUES (:code, :impa_prefix, :name, :path, :level, :display_order)
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, path = EXCLUDED.path
        """),
        {
            "code": "CAT-ROOT", "impa_prefix": None, "name": "All Categories",
            "path": "root", "level": 0, "display_order": 0,
        },
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

    for index, cat in enumerate(IMPA_CATEGORIES, start=1):
        impa_prefix = cat["prefix"]
        category_name = cat["name"]
        code = f"CAT-{impa_prefix}"
        path = f"root.{_to_snake_case(category_name)}"

        # Upsert category
        session.execute(
            text("""
                INSERT INTO categories (code, impa_prefix, name, path, level, display_order)
                VALUES (:code, :impa_prefix, :name, :path, :level, :display_order)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    impa_prefix = EXCLUDED.impa_prefix,
                    path = EXCLUDED.path,
                    display_order = EXCLUDED.display_order
            """),
            {
                "code": code, "impa_prefix": impa_prefix, "name": category_name,
                "path": path, "level": 1, "display_order": index,
            },
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
                INSERT INTO impa_category_mappings
                    (impa_prefix, impa_category_name, internal_category_id,
                     mapping_confidence, last_verified)
                VALUES (:impa_prefix, :impa_category_name, :internal_category_id,
                    :mapping_confidence, :last_verified)
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

    print(f"  Seeded {len(IMPA_CATEGORIES)} categories + root with closure entries and IMPA mappings.")


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


def seed_organizations(session: Session) -> None:
    """Upsert organizations."""
    for org in ORGANIZATIONS:
        session.execute(
            text("""
                INSERT INTO organizations (name, type, slug, legal_name, registration_number,
                    address, primary_email, primary_phone, website, status, is_active)
                VALUES (:name, :type, :slug, :legal_name, :registration_number,
                    :address, :primary_email, :primary_phone, :website, 'ACTIVE', true)
                ON CONFLICT (slug) WHERE slug IS NOT NULL DO UPDATE SET
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    legal_name = EXCLUDED.legal_name,
                    registration_number = EXCLUDED.registration_number,
                    address = EXCLUDED.address,
                    primary_email = EXCLUDED.primary_email,
                    primary_phone = EXCLUDED.primary_phone,
                    website = EXCLUDED.website
            """),
            {
                "name": org["name"],
                "type": org["type"],
                "slug": org["slug"],
                "legal_name": org["legal_name"],
                "registration_number": org["registration_number"],
                "address": json.dumps(org["address"]),
                "primary_email": org["primary_email"],
                "primary_phone": org["primary_phone"],
                "website": org["website"],
            },
        )

    print(f"  Seeded {len(ORGANIZATIONS)} organizations.")


def seed_users(session: Session) -> None:
    """Upsert users (all with shared password hash)."""
    for user in USERS:
        org_id = session.execute(
            text("SELECT id FROM organizations WHERE slug = :slug"),
            {"slug": user["org_slug"]},
        ).scalar_one()

        session.execute(
            text("""
                INSERT INTO users (email, password_hash, first_name, last_name,
                    organization_id, role, phone, is_active, status, email_verified,
                    default_organization_id, locale, timezone)
                VALUES (:email, :password_hash, :first_name, :last_name,
                    :organization_id, :role, :phone, true, 'ACTIVE', true,
                    :organization_id, 'en', 'Asia/Kolkata')
                ON CONFLICT (email) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    organization_id = EXCLUDED.organization_id,
                    role = EXCLUDED.role,
                    phone = EXCLUDED.phone,
                    password_hash = EXCLUDED.password_hash
            """),
            {
                "email": user["email"],
                "password_hash": PASSWORD_HASH,
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "organization_id": org_id,
                "role": user["role"],
                "phone": user.get("phone"),
            },
        )

    print(f"  Seeded {len(USERS)} users.")


def seed_memberships(session: Session) -> None:
    """Create organization memberships linking users to orgs with roles."""
    # Map user role (enum) + org type → role table name
    role_mapping = {
        ("OWNER", "PLATFORM"): "super_admin",
        ("ADMIN", "PLATFORM"): "operations_admin",
        ("MEMBER", "PLATFORM"): "support_agent",
        ("OWNER", "BUYER"): "buyer_admin",
        ("ADMIN", "BUYER"): "buyer_admin",
        ("MEMBER", "BUYER"): "procurement_officer",
        ("VIEWER", "BUYER"): "buyer_viewer",
        ("OWNER", "SUPPLIER"): "supplier_admin",
        ("ADMIN", "SUPPLIER"): "supplier_admin",
        ("MEMBER", "SUPPLIER"): "sales_rep",
        ("VIEWER", "SUPPLIER"): "both_viewer",
    }
    now = datetime.now(UTC)
    count = 0

    for user in USERS:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": user["email"]},
        ).scalar_one()

        org_id = session.execute(
            text("SELECT id FROM organizations WHERE slug = :slug"),
            {"slug": user["org_slug"]},
        ).scalar_one()

        org_type = session.execute(
            text("SELECT type FROM organizations WHERE slug = :slug"),
            {"slug": user["org_slug"]},
        ).scalar_one()

        role_name = role_mapping.get((user["role"], org_type))
        if role_name is None:
            print(f"  WARNING: No role mapping for ({user['role']}, {org_type}), skipping {user['email']}")
            continue

        role_id = session.execute(
            text("SELECT id FROM roles WHERE name = :name"),
            {"name": role_name},
        ).scalar_one_or_none()

        if role_id is None:
            print(f"  WARNING: Role '{role_name}' not found in DB, skipping membership for {user['email']}")
            continue

        session.execute(
            text("""
                INSERT INTO organization_memberships (user_id, organization_id, role_id, status, joined_at)
                VALUES (:user_id, :organization_id, :role_id, 'ACTIVE', :joined_at)
                ON CONFLICT ON CONSTRAINT uq_membership_user_org DO UPDATE SET
                    role_id = EXCLUDED.role_id,
                    status = EXCLUDED.status
            """),
            {
                "user_id": user_id,
                "organization_id": org_id,
                "role_id": role_id,
                "joined_at": now,
            },
        )
        count += 1

    print(f"  Seeded {count} memberships.")


def seed_products(session: Session) -> None:
    """Upsert products with category lookups by IMPA prefix."""
    count = 0
    for product in PRODUCTS:
        category_code = f"CAT-{product['category_prefix']}"
        category_id = session.execute(
            text("SELECT id FROM categories WHERE code = :code"),
            {"code": category_code},
        ).scalar_one_or_none()

        if category_id is None:
            print(f"  WARNING: Category {category_code} not found, skipping product {product['impa_code']}")
            continue

        session.execute(
            text("""
                INSERT INTO products (impa_code, name, description, category_id,
                    unit_of_measure, ihm_relevant, hazmat_class, specifications)
                VALUES (:impa_code, :name, :description, :category_id,
                    :unit_of_measure, :ihm_relevant, :hazmat_class, :specifications)
                ON CONFLICT (impa_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    category_id = EXCLUDED.category_id,
                    unit_of_measure = EXCLUDED.unit_of_measure,
                    ihm_relevant = EXCLUDED.ihm_relevant,
                    hazmat_class = EXCLUDED.hazmat_class,
                    specifications = EXCLUDED.specifications
            """),
            {
                "impa_code": product["impa_code"],
                "name": product["name"],
                "description": product.get("description", ""),
                "category_id": category_id,
                "unit_of_measure": product["unit_of_measure"],
                "ihm_relevant": product.get("ihm_relevant", False),
                "hazmat_class": product.get("hazmat_class"),
                "specifications": json.dumps(product.get("specifications", {})),
            },
        )
        count += 1

    print(f"  Seeded {count} products.")


def seed_supplier_profiles(session: Session) -> None:
    """Upsert supplier profiles."""
    for profile in SUPPLIER_PROFILES:
        org_id = session.execute(
            text("SELECT id FROM organizations WHERE slug = :slug"),
            {"slug": profile["org_slug"]},
        ).scalar_one()

        session.execute(
            text("""
                INSERT INTO supplier_profiles (organization_id, tier, onboarding_status,
                    company_name, contact_name, contact_email, contact_phone,
                    gst_number, pan_number, address_line1, city, state, pincode, country,
                    categories, port_coverage)
                VALUES (:organization_id, :tier, :onboarding_status,
                    :company_name, :contact_name, :contact_email, :contact_phone,
                    :gst_number, :pan_number, :address_line1, :city, :state, :pincode, :country,
                    :categories, :port_coverage)
                ON CONFLICT (organization_id) DO UPDATE SET
                    tier = EXCLUDED.tier,
                    onboarding_status = EXCLUDED.onboarding_status,
                    company_name = EXCLUDED.company_name,
                    contact_name = EXCLUDED.contact_name,
                    contact_email = EXCLUDED.contact_email,
                    contact_phone = EXCLUDED.contact_phone,
                    gst_number = EXCLUDED.gst_number,
                    pan_number = EXCLUDED.pan_number,
                    categories = EXCLUDED.categories,
                    port_coverage = EXCLUDED.port_coverage
            """),
            {
                "organization_id": org_id,
                "tier": profile["tier"],
                "onboarding_status": profile["onboarding_status"],
                "company_name": profile["company_name"],
                "contact_name": profile["contact_name"],
                "contact_email": profile["contact_email"],
                "contact_phone": profile.get("contact_phone"),
                "gst_number": profile.get("gst_number"),
                "pan_number": profile.get("pan_number"),
                "address_line1": profile.get("address_line1"),
                "city": profile.get("city"),
                "state": profile.get("state"),
                "pincode": profile.get("pincode"),
                "country": profile.get("country", "India"),
                "categories": json.dumps(profile["categories"]),
                "port_coverage": json.dumps(profile["port_coverage"]),
            },
        )

    print(f"  Seeded {len(SUPPLIER_PROFILES)} supplier profiles.")


def seed_vessels(session: Session) -> None:
    """Upsert vessels."""
    for vessel in VESSELS:
        owner_org_id = session.execute(
            text("SELECT id FROM organizations WHERE slug = :slug"),
            {"slug": vessel["owner_org_slug"]},
        ).scalar_one()

        session.execute(
            text("""
                INSERT INTO vessels (imo_number, mmsi, name, vessel_type, flag_state,
                    owner_organization_id, gross_tonnage, crew_size, year_built, last_known_port,
                    status, metadata_extra)
                VALUES (:imo_number, :mmsi, :name, :vessel_type, :flag_state,
                    :owner_organization_id, :gross_tonnage, :crew_size, :year_built, :last_known_port,
                    'ACTIVE', '{}')
                ON CONFLICT (imo_number) DO UPDATE SET
                    mmsi = EXCLUDED.mmsi,
                    name = EXCLUDED.name,
                    vessel_type = EXCLUDED.vessel_type,
                    flag_state = EXCLUDED.flag_state,
                    owner_organization_id = EXCLUDED.owner_organization_id,
                    gross_tonnage = EXCLUDED.gross_tonnage,
                    crew_size = EXCLUDED.crew_size,
                    year_built = EXCLUDED.year_built,
                    last_known_port = EXCLUDED.last_known_port
            """),
            {
                "imo_number": vessel["imo_number"],
                "mmsi": vessel["mmsi"],
                "name": vessel["name"],
                "vessel_type": vessel["vessel_type"],
                "flag_state": vessel["flag_state"],
                "owner_organization_id": owner_org_id,
                "gross_tonnage": vessel["gross_tonnage"],
                "crew_size": vessel["crew_size"],
                "year_built": vessel["year_built"],
                "last_known_port": vessel["last_known_port"],
            },
        )

    print(f"  Seeded {len(VESSELS)} vessels.")


def seed_supplier_products(session: Session) -> None:
    """Upsert supplier products with prices."""
    product_count = 0
    price_count = 0

    for sp in SUPPLIER_PRODUCTS:
        supplier_id = session.execute(
            text("SELECT id FROM organizations WHERE slug = :slug"),
            {"slug": sp["supplier_org_slug"]},
        ).scalar_one_or_none()

        if supplier_id is None:
            print(f"  WARNING: Supplier org '{sp['supplier_org_slug']}' not found, skipping")
            continue

        product_id = session.execute(
            text("SELECT id FROM products WHERE impa_code = :impa_code"),
            {"impa_code": sp["product_impa_code"]},
        ).scalar_one_or_none()

        if product_id is None:
            print(f"  WARNING: Product '{sp['product_impa_code']}' not found, skipping")
            continue

        # Set tenant context for RLS trigger
        session.execute(
            text("SET app.current_organization_id = :org_id"),
            {"org_id": str(supplier_id)},
        )

        # Upsert supplier_product
        session.execute(
            text("""
                INSERT INTO supplier_products (product_id, supplier_id, supplier_sku,
                    manufacturer, brand, lead_time_days, min_order_quantity, is_active)
                VALUES (:product_id, :supplier_id, :supplier_sku,
                    :manufacturer, :brand, :lead_time_days, :min_order_quantity, true)
                ON CONFLICT ON CONSTRAINT uq_supplier_products DO UPDATE SET
                    manufacturer = EXCLUDED.manufacturer,
                    brand = EXCLUDED.brand,
                    lead_time_days = EXCLUDED.lead_time_days,
                    min_order_quantity = EXCLUDED.min_order_quantity
            """),
            {
                "product_id": product_id,
                "supplier_id": supplier_id,
                "supplier_sku": sp["supplier_sku"],
                "manufacturer": sp.get("manufacturer"),
                "brand": sp.get("brand"),
                "lead_time_days": sp.get("lead_time_days", 7),
                "min_order_quantity": sp.get("min_order_quantity", 1),
            },
        )
        product_count += 1

        # Get supplier_product_id for prices
        supplier_product_id = session.execute(
            text("""
                SELECT id FROM supplier_products
                WHERE product_id = :product_id AND supplier_id = :supplier_id AND supplier_sku = :supplier_sku
            """),
            {"product_id": product_id, "supplier_id": supplier_id, "supplier_sku": sp["supplier_sku"]},
        ).scalar_one()

        # Delete existing prices and re-insert (simpler than upserting multi-row)
        session.execute(
            text("DELETE FROM supplier_product_prices WHERE supplier_product_id = :sp_id"),
            {"sp_id": supplier_product_id},
        )

        for price_entry in sp.get("prices", []):
            session.execute(
                text("""
                    INSERT INTO supplier_product_prices (supplier_product_id, price, currency,
                        min_quantity, valid_from, valid_to)
                    VALUES (:supplier_product_id, :price, :currency,
                        :min_quantity, :valid_from, :valid_to)
                """),
                {
                    "supplier_product_id": supplier_product_id,
                    "price": Decimal(price_entry["price"]),
                    "currency": price_entry.get("currency", "INR"),
                    "min_quantity": price_entry.get("min_quantity", 1),
                    "valid_from": price_entry["valid_from"],
                    "valid_to": price_entry.get("valid_to"),
                },
            )
            price_count += 1

    print(f"  Seeded {product_count} supplier products with {price_count} price entries.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all seed functions inside a single transaction."""
    print("Seeding PortiQ database...")

    with Session(sync_engine) as session:
        with session.begin():
            # Bypass RLS / tenant triggers for seeding
            session.execute(text("SET app.admin_bypass = 'true'"))
            # 1. Clean up old sequential categories
            delete_old_categories(session)

            # 2. Categories (with closures + IMPA mappings)
            seed_categories(session)

            # 3. Units and conversions
            seed_units(session)
            seed_conversions(session)

            # 4. Organizations
            seed_organizations(session)

            # 5. Users (FK → organizations)
            seed_users(session)

            # 6. Memberships (FK → users, organizations, roles)
            seed_memberships(session)

            # 7. Products (FK → categories)
            seed_products(session)

            # 8. Supplier profiles (FK → organizations)
            seed_supplier_profiles(session)

            # 9. Vessels (FK → organizations)
            seed_vessels(session)

            # 10. Supplier products + prices (FK → products, organizations)
            seed_supplier_products(session)

    print("Seeding complete.")


if __name__ == "__main__":
    main()
