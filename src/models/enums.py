import enum


class OrganizationType(str, enum.Enum):
    BUYER = "BUYER"
    SUPPLIER = "SUPPLIER"
    BOTH = "BOTH"
    PLATFORM = "PLATFORM"


class MembershipStatus(str, enum.Enum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class CategoryStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    PENDING_MIGRATION = "PENDING_MIGRATION"
    ARCHIVED = "ARCHIVED"


class UnitType(str, enum.Enum):
    QUANTITY = "QUANTITY"
    VOLUME = "VOLUME"
    WEIGHT = "WEIGHT"
    LENGTH = "LENGTH"


class TagType(str, enum.Enum):
    RELATED = "RELATED"
    ALSO_IN = "ALSO_IN"
    SUBSTITUTE = "SUBSTITUTE"
    ACCESSORY = "ACCESSORY"


class TagSource(str, enum.Enum):
    MANUAL = "MANUAL"
    ML_MODEL = "ML_MODEL"
    IMPA_MAPPING = "IMPA_MAPPING"


class SchemaStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class SupplierTier(str, enum.Enum):
    PENDING = "PENDING"
    BASIC = "BASIC"
    VERIFIED = "VERIFIED"
    PREFERRED = "PREFERRED"
    PREMIUM = "PREMIUM"


class OnboardingStatus(str, enum.Enum):
    STARTED = "STARTED"
    DOCUMENTS_PENDING = "DOCUMENTS_PENDING"
    DOCUMENTS_SUBMITTED = "DOCUMENTS_SUBMITTED"
    VERIFICATION_IN_PROGRESS = "VERIFICATION_IN_PROGRESS"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    MANUAL_REVIEW_PENDING = "MANUAL_REVIEW_PENDING"
    MANUAL_REVIEW_IN_PROGRESS = "MANUAL_REVIEW_IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class KycDocumentType(str, enum.Enum):
    GST_CERTIFICATE = "GST_CERTIFICATE"
    PAN_CARD = "PAN_CARD"
    ADDRESS_PROOF = "ADDRESS_PROOF"
    INCORPORATION_CERT = "INCORPORATION_CERT"
    BANK_STATEMENT = "BANK_STATEMENT"
    REFERENCE_LETTER = "REFERENCE_LETTER"
    AUDITED_FINANCIALS = "AUDITED_FINANCIALS"
    INSURANCE_CERTIFICATE = "INSURANCE_CERTIFICATE"
    QUALITY_CERTIFICATION = "QUALITY_CERTIFICATION"
    DIRECTOR_ID = "DIRECTOR_ID"


class KycDocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ReviewAction(str, enum.Enum):
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    REVIEW_STARTED = "REVIEW_STARTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    REACTIVATED = "REACTIVATED"
    TIER_UPGRADE_REQUESTED = "TIER_UPGRADE_REQUESTED"
    TIER_UPGRADED = "TIER_UPGRADED"


# ── Phase 1.1: Maritime Data Feeds ────────────────────────────────────────


class VesselType(str, enum.Enum):
    BULK_CARRIER = "BULK_CARRIER"
    CONTAINER = "CONTAINER"
    TANKER = "TANKER"
    GENERAL_CARGO = "GENERAL_CARGO"
    PASSENGER = "PASSENGER"
    RO_RO = "RO_RO"
    OFFSHORE = "OFFSHORE"
    FISHING = "FISHING"
    TUG = "TUG"
    OTHER = "OTHER"


class VesselStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DECOMMISSIONED = "DECOMMISSIONED"


class NavigationStatus(str, enum.Enum):
    UNDER_WAY = "UNDER_WAY"
    AT_ANCHOR = "AT_ANCHOR"
    NOT_UNDER_COMMAND = "NOT_UNDER_COMMAND"
    RESTRICTED_MANOEUVRABILITY = "RESTRICTED_MANOEUVRABILITY"
    MOORED = "MOORED"
    AGROUND = "AGROUND"
    FISHING = "FISHING"
    UNDER_WAY_SAILING = "UNDER_WAY_SAILING"
    UNKNOWN = "UNKNOWN"


class PortCallStatus(str, enum.Enum):
    APPROACHING = "APPROACHING"
    ARRIVED = "ARRIVED"
    BERTHED = "BERTHED"
    DEPARTED = "DEPARTED"
    CANCELLED = "CANCELLED"


class AisProvider(str, enum.Enum):
    VESSEL_FINDER = "VESSEL_FINDER"
    PCS1X = "PCS1X"
    MANUAL = "MANUAL"


class EventStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ── Phase 3.3: RFQ & Bidding ────────────────────────────────────────────


class RfqStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    BIDDING_OPEN = "BIDDING_OPEN"
    BIDDING_CLOSED = "BIDDING_CLOSED"
    EVALUATION = "EVALUATION"
    AWARDED = "AWARDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RfqTransitionType(str, enum.Enum):
    PUBLISH = "PUBLISH"
    OPEN_BIDDING = "OPEN_BIDDING"
    CLOSE_BIDDING = "CLOSE_BIDDING"
    START_EVALUATION = "START_EVALUATION"
    AWARD = "AWARD"
    COMPLETE = "COMPLETE"
    CANCEL = "CANCEL"


class AuctionType(str, enum.Enum):
    SEALED_BID = "SEALED_BID"


class QuoteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    REVISED = "REVISED"
    WITHDRAWN = "WITHDRAWN"
    AWARDED = "AWARDED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class InvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


# ── Phase 4.3: Document AI ────────────────────────────────────────────


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    NORMALIZING = "NORMALIZING"
    MATCHING = "MATCHING"
    ROUTING = "ROUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractionConfidenceTier(str, enum.Enum):
    AUTO = "AUTO"           # >= 95% — auto-accepted
    QUICK_REVIEW = "QUICK_REVIEW"  # 80-94% — quick review
    FULL_REVIEW = "FULL_REVIEW"    # < 80% — full human review


class DocumentType(str, enum.Enum):
    SYSTEM_REQUISITION = "SYSTEM_REQUISITION"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    INVENTORY_LIST = "INVENTORY_LIST"
    MAINTENANCE_EXPORT = "MAINTENANCE_EXPORT"
    HANDWRITTEN_FORM = "HANDWRITTEN_FORM"
    MARKED_CATALOG = "MARKED_CATALOG"
    NAMEPLATE_PHOTO = "NAMEPLATE_PHOTO"
    MIXED_FORM = "MIXED_FORM"


# ── Phase 3.4: TCO Engine ────────────────────────────────────────────


class TcoCalculationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CALCULATING = "CALCULATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STALE = "STALE"


class TcoTemplateType(str, enum.Enum):
    COMMODITY = "COMMODITY"
    TECHNICAL = "TECHNICAL"
    URGENT = "URGENT"
    STRATEGIC = "STRATEGIC"
    QUALITY_CRITICAL = "QUALITY_CRITICAL"
    CUSTOM = "CUSTOM"


# ── Phase 4.4-4.6: Order, Delivery, Disputes ────────────────────────────────


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class VendorOrderStatus(str, enum.Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class FulfillmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PICKING = "PICKING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"


class FulfillmentLineItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    ALLOCATED = "ALLOCATED"
    PICKED = "PICKED"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    BACKORDERED = "BACKORDERED"
    CANCELLED = "CANCELLED"


class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


class DeliveryItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"


class DeliveryPhotoType(str, enum.Enum):
    DELIVERY = "DELIVERY"
    DAMAGE = "DAMAGE"
    PACKAGING = "PACKAGING"
    QUANTITY = "QUANTITY"
    DISPUTE = "DISPUTE"


class DeliveryType(str, enum.Enum):
    ALONGSIDE = "ALONGSIDE"
    WAREHOUSE = "WAREHOUSE"
    AGENT = "AGENT"
    ANCHORAGE = "ANCHORAGE"


class DisputeType(str, enum.Enum):
    QUANTITY_SHORTAGE = "QUANTITY_SHORTAGE"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    WRONG_PRODUCT = "WRONG_PRODUCT"
    DAMAGED_GOODS = "DAMAGED_GOODS"
    PRICE_DISPUTE = "PRICE_DISPUTE"
    LATE_DELIVERY = "LATE_DELIVERY"
    OTHER = "OTHER"


class DisputeStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    AWAITING_SUPPLIER = "AWAITING_SUPPLIER"
    AWAITING_BUYER = "AWAITING_BUYER"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class DisputePriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DisputeResolutionType(str, enum.Enum):
    CREDIT_NOTE = "CREDIT_NOTE"
    REFUND = "REFUND"
    REPLACEMENT = "REPLACEMENT"
    PRICE_ADJUSTMENT = "PRICE_ADJUSTMENT"
    NO_ACTION = "NO_ACTION"
    SPLIT = "SPLIT"


# ── Phase 5.3-5.4: Settlement, Invoicing, Export ────────────────────────────────


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISPUTED = "DISPUTED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    CREDIT_NOTE = "CREDIT_NOTE"


class SettlementPeriodType(str, enum.Enum):
    PORT_CALL = "PORT_CALL"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class SettlementPeriodStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RECONCILED = "RECONCILED"


class ExportType(str, enum.Enum):
    INVOICES = "INVOICES"
    ORDERS = "ORDERS"
    DELIVERIES = "DELIVERIES"
    SETTLEMENTS = "SETTLEMENTS"
    INVOICE_SINGLE = "INVOICE_SINGLE"
    DELIVERY_REPORT = "DELIVERY_REPORT"


class ExportFormat(str, enum.Enum):
    CSV = "CSV"
    XLSX = "XLSX"
    PDF = "PDF"


class ExportJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


# ── Phase 2.1: Port Call Demand Planning ────────────────────────────────


class RequirementCategory(str, enum.Enum):
    PROVISIONS = "PROVISIONS"
    TECHNICAL = "TECHNICAL"
    SAFETY = "SAFETY"
    DECK = "DECK"
    ENGINE = "ENGINE"
    CABIN = "CABIN"
    SERVICES = "SERVICES"
    COMPLIANCE = "COMPLIANCE"
    OTHER = "OTHER"


class RequirementPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RequirementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    RFQ_CREATED = "RFQ_CREATED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
