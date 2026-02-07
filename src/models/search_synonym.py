"""SQLAlchemy model for the search_synonyms table."""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SearchSynonym(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores domain-specific synonym mappings for search query expansion."""

    __tablename__ = "search_synonyms"

    term: Mapped[str] = mapped_column(String(100), nullable=False)
    synonyms: Mapped[list] = mapped_column(JSONB, nullable=False)
    domain: Mapped[str] = mapped_column(String(50), server_default="maritime")

    __table_args__ = (
        UniqueConstraint("term", "domain", name="uq_search_synonyms_term_domain"),
    )
