# Import all models so SQLAlchemy metadata is populated for Alembic autogenerate
from src.models.audit import ProductAuditLog
from src.models.category import Category, CategoryClosure
from src.models.category_schema import CategorySchema
from src.models.enums import (
    AisProvider,
    AuctionType,
    CategoryStatus,
    DocumentType,
    EventStatus,
    ExtractionConfidenceTier,
    ExtractionStatus,
    InvitationStatus,
    KycDocumentStatus,
    KycDocumentType,
    MembershipStatus,
    NavigationStatus,
    OnboardingStatus,
    OrganizationStatus,
    OrganizationType,
    PortCallStatus,
    QuoteStatus,
    ReviewAction,
    RfqStatus,
    RfqTransitionType,
    SchemaStatus,
    SupplierTier,
    TagSource,
    TagType,
    TcoCalculationStatus,
    TcoTemplateType,
    UnitType,
    UserRole,
    UserStatus,
    VesselStatus,
    VesselType,
)
from src.models.event_outbox import EventOutbox
from src.models.impa_mapping import ImpaCategoryMapping, IssaCategoryMapping
from src.models.organization import Organization
from src.models.organization_membership import OrganizationMembership
from src.models.port_call import PortCall
from src.models.processed_event import ProcessedEvent
from src.models.product import Product
from src.models.product_category_tag import ProductCategoryTag
from src.models.role import Role
from src.models.search_synonym import SearchSynonym
from src.models.supplier_kyc_document import SupplierKycDocument
from src.models.supplier_product import SupplierProduct, SupplierProductPrice
from src.models.supplier_profile import SupplierProfile
from src.models.supplier_review_log import SupplierReviewLog
from src.models.translation import ProductTranslation
from src.models.unit import UnitConversion, UnitOfMeasure
from src.models.user import User
from src.models.quote import Quote
from src.models.quote_line_item import QuoteLineItem
from src.models.rfq import Rfq
from src.models.rfq_invitation import RfqInvitation
from src.models.rfq_line_item import RfqLineItem
from src.models.rfq_transition import RfqTransition
from src.models.document_extraction import DocumentExtraction, ExtractedLineItem
from src.models.vessel import Vessel
from src.models.vessel_position import VesselPosition
from src.models.tco_configuration import TcoConfiguration
from src.models.tco_calculation import TcoCalculation
from src.models.tco_audit_trail import TcoAuditTrail
from src.models.conversation_session import ConversationSession

__all__ = [
    "AisProvider",
    "AuctionType",
    "Category",
    "CategoryClosure",
    "CategorySchema",
    "CategoryStatus",
    "DocumentExtraction",
    "DocumentType",
    "EventOutbox",
    "EventStatus",
    "ExtractionConfidenceTier",
    "ExtractionStatus",
    "ExtractedLineItem",
    "ImpaCategoryMapping",
    "InvitationStatus",
    "IssaCategoryMapping",
    "KycDocumentStatus",
    "KycDocumentType",
    "MembershipStatus",
    "NavigationStatus",
    "OnboardingStatus",
    "Organization",
    "OrganizationMembership",
    "OrganizationStatus",
    "OrganizationType",
    "PortCall",
    "PortCallStatus",
    "ProcessedEvent",
    "Product",
    "ProductAuditLog",
    "ProductCategoryTag",
    "ProductTranslation",
    "Quote",
    "QuoteLineItem",
    "QuoteStatus",
    "ReviewAction",
    "Rfq",
    "RfqInvitation",
    "RfqLineItem",
    "RfqStatus",
    "RfqTransition",
    "RfqTransitionType",
    "Role",
    "SchemaStatus",
    "SearchSynonym",
    "SupplierKycDocument",
    "SupplierProduct",
    "SupplierProductPrice",
    "SupplierProfile",
    "SupplierReviewLog",
    "SupplierTier",
    "TagSource",
    "TagType",
    "UnitConversion",
    "UnitOfMeasure",
    "UnitType",
    "User",
    "TcoAuditTrail",
    "TcoCalculation",
    "TcoCalculationStatus",
    "TcoConfiguration",
    "TcoTemplateType",
    "ConversationSession",
    "UserRole",
    "UserStatus",
    "Vessel",
    "VesselPosition",
    "VesselStatus",
    "VesselType",
]
