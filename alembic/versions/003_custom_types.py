"""Custom types - vector embedding, ltree, trigram indexes, audit triggers

Revision ID: 003
Revises: 002
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Vector embedding column
    op.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'products' AND column_name = 'embedding'
          ) THEN
            ALTER TABLE products ADD COLUMN embedding vector(1536);
          END IF;
        END $$;
    """)

    # HNSW index for approximate nearest neighbor search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_embedding_hnsw
          ON products USING hnsw (embedding vector_cosine_ops)
          WITH (m = 16, ef_construction = 64);
    """)

    # GiST index on category path for ltree queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_categories_path_gist
          ON categories USING gist (("path"::ltree));
    """)

    # Trigram index for fuzzy product search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_name_trgm
          ON products USING gin (name gin_trgm_ops);
    """)

    # GIN indexes on JSONB columns
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_specifications_gin
          ON products USING gin (specifications);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_supplier_products_specifications_gin
          ON supplier_products USING gin (specifications);
    """)

    # Partial index for IHM-relevant products
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_ihm_relevant
          ON products (ihm_relevant) WHERE ihm_relevant = true;
    """)

    # GIN index on translation search keywords
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_product_translations_search_keywords
          ON product_translations USING gin (search_keywords);
    """)

    # Audit trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_product_audit_trigger()
        RETURNS TRIGGER AS $$
        DECLARE
          changed_fields_json JSONB;
          operation_type TEXT;
          entity_version INT;
        BEGIN
          operation_type := TG_OP;
          IF TG_OP = 'DELETE' THEN
            entity_version := OLD.version;
            changed_fields_json := to_jsonb(OLD);
            INSERT INTO product_audit_log (id, entity_type, entity_id, operation, changed_fields, version, created_at)
            VALUES (gen_random_uuid(), TG_TABLE_NAME, OLD.id, operation_type, changed_fields_json, entity_version, NOW());
            RETURN OLD;
          END IF;
          IF TG_OP = 'INSERT' THEN
            entity_version := NEW.version;
            changed_fields_json := to_jsonb(NEW);
          ELSIF TG_OP = 'UPDATE' THEN
            entity_version := NEW.version;
            SELECT jsonb_object_agg(key, value) INTO changed_fields_json
            FROM jsonb_each(to_jsonb(NEW))
            WHERE key != 'updated_at' AND (to_jsonb(OLD) ->> key) IS DISTINCT FROM (to_jsonb(NEW) ->> key);
          END IF;
          IF TG_OP = 'UPDATE' AND (changed_fields_json IS NULL OR changed_fields_json = '{}'::jsonb) THEN
            RETURN NEW;
          END IF;
          INSERT INTO product_audit_log (id, entity_type, entity_id, operation, changed_fields, version, created_at)
          VALUES (gen_random_uuid(), TG_TABLE_NAME, NEW.id, operation_type, changed_fields_json, entity_version, NOW());
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Attach audit triggers
    op.execute("DROP TRIGGER IF EXISTS trg_products_audit ON products;")
    op.execute("""
        CREATE TRIGGER trg_products_audit
          AFTER INSERT OR UPDATE OR DELETE ON products
          FOR EACH ROW EXECUTE FUNCTION fn_product_audit_trigger();
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_supplier_products_audit ON supplier_products;")
    op.execute("""
        CREATE TRIGGER trg_supplier_products_audit
          AFTER INSERT OR UPDATE OR DELETE ON supplier_products
          FOR EACH ROW EXECUTE FUNCTION fn_product_audit_trigger();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_supplier_products_audit ON supplier_products;")
    op.execute("DROP TRIGGER IF EXISTS trg_products_audit ON products;")
    op.execute("DROP FUNCTION IF EXISTS fn_product_audit_trigger();")

    op.execute("DROP INDEX IF EXISTS idx_product_translations_search_keywords;")
    op.execute("DROP INDEX IF EXISTS idx_products_ihm_relevant;")
    op.execute("DROP INDEX IF EXISTS idx_supplier_products_specifications_gin;")
    op.execute("DROP INDEX IF EXISTS idx_products_specifications_gin;")
    op.execute("DROP INDEX IF EXISTS idx_products_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_categories_path_gist;")
    op.execute("DROP INDEX IF EXISTS idx_products_embedding_hnsw;")

    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding;")
