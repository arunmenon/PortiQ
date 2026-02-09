// ---------------------------------------------------------------------------
// Shared / Error
// ---------------------------------------------------------------------------

export interface ApiErrorDetail {
  field?: string;
  message: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: ApiErrorDetail[];
    requestId: string;
  };
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// Products
// ---------------------------------------------------------------------------

export interface Product {
  id: string;
  impa_code: string;
  issa_code: string | null;
  name: string;
  description: string | null;
  category_id: string;
  category_name: string | null;
  unit_of_measure: string;
  ihm_relevant: boolean;
  hazmat_class: string | null;
  specifications: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ProductDetailResponse extends Product {
  supplier_products: SupplierProduct[];
  translations: TranslationResponse[];
  tags: CategoryTagResponse[];
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductCreateRequest {
  impa_code: string;
  name: string;
  description?: string | null;
  category_id: string;
  unit_of_measure: string;
  ihm_relevant?: boolean;
  hazmat_class?: string | null;
  specifications?: Record<string, unknown>;
  issa_code?: string | null;
}

export interface ProductUpdateRequest {
  impa_code?: string;
  name?: string;
  description?: string | null;
  category_id?: string;
  unit_of_measure?: string;
  ihm_relevant?: boolean;
  hazmat_class?: string | null;
  specifications?: Record<string, unknown>;
  issa_code?: string | null;
  version: number;
}

export interface ProductListParams extends PaginationParams {
  category_id?: string;
  ihm_relevant?: boolean;
  search?: string;
}

// ---------------------------------------------------------------------------
// IMPA Validation
// ---------------------------------------------------------------------------

export interface ImpaValidationResponse {
  is_valid_format: boolean;
  is_known_code: boolean;
  suggested_category_id: string | null;
  suggested_category_name: string | null;
}

// ---------------------------------------------------------------------------
// Supplier Products
// ---------------------------------------------------------------------------

export interface SupplierProduct {
  id: string;
  product_id: string;
  supplier_id: string;
  supplier_sku: string | null;
  manufacturer: string | null;
  brand: string | null;
  part_number: string | null;
  lead_time_days: number | null;
  min_order_quantity: number;
  pack_size: number;
  specifications: Record<string, unknown>;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface SupplierProductCreateRequest {
  supplier_id: string;
  supplier_sku?: string | null;
  manufacturer?: string | null;
  brand?: string | null;
  part_number?: string | null;
  lead_time_days?: number | null;
  min_order_quantity?: number;
  pack_size?: number;
  specifications?: Record<string, unknown>;
}

export interface SupplierProductUpdateRequest {
  supplier_sku?: string | null;
  manufacturer?: string | null;
  brand?: string | null;
  part_number?: string | null;
  lead_time_days?: number | null;
  min_order_quantity?: number | null;
  pack_size?: number | null;
  specifications?: Record<string, unknown> | null;
  is_active?: boolean | null;
  version: number;
}

// ---------------------------------------------------------------------------
// Supplier Prices
// ---------------------------------------------------------------------------

export interface SupplierPriceResponse {
  id: string;
  supplier_product_id: string;
  price: string; // Decimal serialized as string
  currency: string;
  min_quantity: number;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}

export interface SupplierPriceCreateRequest {
  price: string; // Decimal
  currency?: string;
  min_quantity?: number;
  valid_from: string;
  valid_to?: string | null;
}

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export type CategoryStatus = "ACTIVE" | "DEPRECATED" | "PENDING_MIGRATION" | "ARCHIVED";

export interface Category {
  id: string;
  code: string;
  impa_prefix: string | null;
  name: string;
  description: string | null;
  path: string;
  level: number;
  attribute_schema: Record<string, unknown> | null;
  ihm_category: boolean;
  icon: string | null;
  display_order: number;
  status: CategoryStatus;
  product_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface CategoryTreeNode {
  id: string;
  code: string;
  name: string;
  path: string;
  level: number;
  icon: string | null;
  display_order: number;
  status: CategoryStatus;
  children_count: number;
  product_count: number;
}

export interface Breadcrumb {
  id: string;
  code: string;
  name: string;
  level: number;
}

export interface CategoryCreateRequest {
  code: string;
  name: string;
  description?: string | null;
  parent_id?: string | null;
  impa_prefix?: string | null;
  attribute_schema?: Record<string, unknown> | null;
  ihm_category?: boolean;
  icon?: string | null;
  display_order?: number;
}

export interface CategoryUpdateRequest {
  name?: string;
  description?: string | null;
  attribute_schema?: Record<string, unknown> | null;
  ihm_category?: boolean;
  icon?: string | null;
  display_order?: number;
  status?: CategoryStatus;
}

// ---------------------------------------------------------------------------
// Category Tags
// ---------------------------------------------------------------------------

export type TagType = "RELATED" | "ALSO_IN" | "SUBSTITUTE" | "ACCESSORY";
export type TagSource = "MANUAL" | "ML_MODEL" | "IMPA_MAPPING";

export interface CategoryTagResponse {
  id: string;
  product_id: string;
  category_id: string;
  tag_type: TagType;
  confidence: string; // Decimal serialized as string
  created_by: TagSource;
  created_at: string;
  category_name: string | null;
}

// ---------------------------------------------------------------------------
// Translations
// ---------------------------------------------------------------------------

export interface TranslationResponse {
  id: string;
  product_id: string;
  locale: string;
  name: string;
  description: string | null;
  search_keywords: string[];
}

export interface TranslationCreateRequest {
  name: string;
  description?: string | null;
  search_keywords?: string[];
}

// ---------------------------------------------------------------------------
// Category Schemas
// ---------------------------------------------------------------------------

export type SchemaStatus = "DRAFT" | "ACTIVE" | "DEPRECATED";

export interface CategorySchemaResponse {
  id: string;
  category_id: string;
  version: number;
  schema_json: Record<string, unknown>;
  status: SchemaStatus;
  created_by: string | null;
  created_at: string;
  activated_at: string | null;
}

export interface SchemaHistoryResponse {
  items: CategorySchemaResponse[];
  category_id: string;
  total: number;
}

export interface SpecsValidationResponse {
  valid: boolean;
  errors: Record<string, unknown>[];
  schema_source: string | null;
}

// ---------------------------------------------------------------------------
// IMPA / ISSA Mappings
// ---------------------------------------------------------------------------

export interface ImpaMappingResponse {
  impa_prefix: string;
  impa_category_name: string;
  internal_category_id: string;
  mapping_confidence: string;
  notes: string | null;
  last_verified: string;
}

export interface IssaMappingResponse {
  issa_prefix: string;
  issa_category_name: string;
  internal_category_id: string;
  impa_equivalent: string | null;
  mapping_confidence: string;
  notes: string | null;
  last_verified: string;
}

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

export type UnitType = "QUANTITY" | "VOLUME" | "WEIGHT" | "LENGTH";

export interface UnitResponse {
  code: string;
  name: string;
  unit_type: UnitType;
  base_unit: string | null;
  display_order: number;
}

export interface ConversionResult {
  original_value: string; // Decimal
  converted_value: string; // Decimal
  conversion_factor: string; // Decimal
  conversion_path: string[];
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export interface SearchResult {
  id: string;
  impa_code: string;
  name: string;
  description: string | null;
  category_name: string | null;
  score: number;
  highlight: string | null;
}

export interface SimilarProductResult {
  id: string;
  impa_code: string;
  name: string;
  description: string | null;
  category_name: string | null;
  similarity: number;
}

export interface VectorSearchRequest {
  query: string;
  limit?: number;
  min_similarity?: number;
  category_id?: string;
  precision?: "fast" | "balanced" | "accurate";
}

export interface VectorSearchResponse {
  results: SimilarProductResult[];
  query: string;
  total: number;
}

export interface MatchLineItemRequest {
  product_name: string;
  specifications?: string | null;
  impa_code?: string | null;
  unit?: string | null;
  confidence?: number;
  expected_category?: string | null;
}

export interface ProductMatchResult {
  product: SimilarProductResult;
  confidence: number;
  match_reason: string;
}

export interface MatchLineItemResponse {
  match: ProductMatchResult | null;
  candidates_evaluated: number;
}

export interface TextSearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
  page: number;
  total_pages: number;
}

export interface TextSearchParams {
  query: string;
  limit?: number;
  page?: number;
  category_id?: string;
  mode?: "keyword" | "fuzzy" | "hybrid";
}

export interface FacetCount {
  value: string;
  count: number;
}

export interface FacetedSearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
  page: number;
  total_pages: number;
  facets: Record<string, FacetCount[]>;
}

export interface FacetedSearchParams {
  query: string;
  limit?: number;
  page?: number;
  category_id?: string;
  ihm_relevant?: boolean;
  hazmat_class?: string;
}

export interface SynonymEntry {
  term: string;
  synonyms: string[];
  domain: string;
}

export interface GenerateEmbeddingsRequest {
  product_ids: string[];
}

export interface GenerateEmbeddingsResponse {
  task_id: string;
  product_count: number;
  message: string;
}

// ---------------------------------------------------------------------------
// Supplier Profiles
// ---------------------------------------------------------------------------

export type SupplierTier = "PENDING" | "BASIC" | "VERIFIED" | "PREFERRED" | "PREMIUM";

export type OnboardingStatus =
  | "STARTED"
  | "DOCUMENTS_PENDING"
  | "DOCUMENTS_SUBMITTED"
  | "VERIFICATION_IN_PROGRESS"
  | "VERIFICATION_PASSED"
  | "VERIFICATION_FAILED"
  | "MANUAL_REVIEW_PENDING"
  | "MANUAL_REVIEW_IN_PROGRESS"
  | "APPROVED"
  | "REJECTED"
  | "SUSPENDED";

export type KycDocumentType =
  | "GST_CERTIFICATE"
  | "PAN_CARD"
  | "ADDRESS_PROOF"
  | "INCORPORATION_CERT"
  | "BANK_STATEMENT"
  | "REFERENCE_LETTER"
  | "AUDITED_FINANCIALS"
  | "INSURANCE_CERTIFICATE"
  | "QUALITY_CERTIFICATION"
  | "DIRECTOR_ID";

export type KycDocumentStatus = "PENDING" | "VERIFIED" | "REJECTED" | "EXPIRED";

export type ReviewAction =
  | "SUBMITTED_FOR_REVIEW"
  | "REVIEW_STARTED"
  | "APPROVED"
  | "REJECTED"
  | "SUSPENDED"
  | "REACTIVATED"
  | "TIER_UPGRADE_REQUESTED"
  | "TIER_UPGRADED";

export interface SupplierProfileResponse {
  id: string;
  organization_id: string;
  organization_name: string | null;
  tier: SupplierTier;
  onboarding_status: OnboardingStatus;
  company_name: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string | null;
  gst_number: string | null;
  pan_number: string | null;
  cin_number: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  country: string;
  categories: string[];
  port_coverage: string[];
  verification_results: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SupplierProfileCreateRequest {
  organization_id: string;
  company_name: string;
  contact_name: string;
  contact_email: string;
  contact_phone?: string | null;
  gst_number?: string | null;
  pan_number?: string | null;
  cin_number?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  country?: string;
  categories?: string[];
  port_coverage?: string[];
}

export interface SupplierProfileUpdateRequest {
  company_name?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string | null;
  gst_number?: string | null;
  pan_number?: string | null;
  cin_number?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  country?: string;
  categories?: string[];
  port_coverage?: string[];
}

export interface SupplierListParams extends PaginationParams {
  tier?: SupplierTier;
  onboarding_status?: OnboardingStatus;
  search?: string;
}

export interface SupplierListResponse {
  items: SupplierProfileResponse[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Supplier KYC Documents
// ---------------------------------------------------------------------------

export interface SupplierKycDocumentResponse {
  id: string;
  supplier_id: string;
  document_type: KycDocumentType;
  file_key: string;
  file_name: string;
  status: KycDocumentStatus;
  verified_at: string | null;
  verified_by: string | null;
  expiry_date: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupplierKycDocumentCreateRequest {
  document_type: KycDocumentType;
  file_key: string;
  file_name: string;
  expiry_date?: string | null;
}

export interface SupplierKycDocumentUpdateRequest {
  status: KycDocumentStatus;
  rejection_reason?: string | null;
}

// ---------------------------------------------------------------------------
// Supplier Review Logs
// ---------------------------------------------------------------------------

export interface SupplierReviewLogResponse {
  id: string;
  supplier_id: string;
  reviewer_id: string | null;
  reviewer_name: string | null;
  action: ReviewAction;
  from_status: OnboardingStatus;
  to_status: OnboardingStatus;
  notes: string | null;
  created_at: string;
}

export interface SupplierReviewRequest {
  action: ReviewAction;
  notes?: string | null;
}

// ---------------------------------------------------------------------------
// Tier Capabilities
// ---------------------------------------------------------------------------

export interface TierCapabilities {
  tier: SupplierTier;
  max_quotes: number | null;
  can_bid_rfq: boolean;
  financing_eligible: boolean;
  visibility: string;
  commission_percent: number;
  payment_terms: string | null;
}

// ---------------------------------------------------------------------------
// RFQ & Bidding
// ---------------------------------------------------------------------------

export type RfqStatus =
  | "DRAFT"
  | "PUBLISHED"
  | "BIDDING_OPEN"
  | "BIDDING_CLOSED"
  | "EVALUATION"
  | "AWARDED"
  | "COMPLETED"
  | "CANCELLED";

export type RfqTransitionType =
  | "PUBLISH"
  | "OPEN_BIDDING"
  | "CLOSE_BIDDING"
  | "START_EVALUATION"
  | "AWARD"
  | "COMPLETE"
  | "CANCEL";

export type AuctionType = "SEALED_BID";

export type QuoteStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "REVISED"
  | "WITHDRAWN"
  | "AWARDED"
  | "REJECTED"
  | "EXPIRED";

export type InvitationStatus = "PENDING" | "ACCEPTED" | "DECLINED" | "EXPIRED";

// RFQ Line Items

export interface RfqLineItemCreate {
  line_number: number;
  product_id?: string | null;
  impa_code?: string | null;
  description: string;
  quantity: number;
  unit_of_measure: string;
  specifications?: Record<string, unknown> | null;
  notes?: string | null;
}

export interface RfqLineItemUpdate {
  product_id?: string | null;
  impa_code?: string | null;
  description?: string;
  quantity?: number;
  unit_of_measure?: string;
  specifications?: Record<string, unknown> | null;
  notes?: string | null;
}

export interface RfqLineItemResponse {
  id: string;
  rfq_id: string;
  line_number: number;
  product_id: string | null;
  impa_code: string | null;
  description: string;
  quantity: string; // Decimal
  unit_of_measure: string;
  specifications: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// RFQ

export interface RfqCreate {
  title: string;
  description?: string | null;
  auction_type?: AuctionType;
  currency?: string;
  vessel_id?: string | null;
  delivery_port?: string | null;
  delivery_date?: string | null;
  bidding_deadline?: string | null;
  allow_partial_quotes?: boolean;
  allow_quote_revision?: boolean;
  require_all_line_items?: boolean;
  notes?: string | null;
  line_items?: RfqLineItemCreate[];
}

export interface RfqUpdate {
  title?: string;
  description?: string | null;
  auction_type?: AuctionType;
  currency?: string;
  vessel_id?: string | null;
  delivery_port?: string | null;
  delivery_date?: string | null;
  bidding_deadline?: string | null;
  allow_partial_quotes?: boolean;
  allow_quote_revision?: boolean;
  require_all_line_items?: boolean;
  notes?: string | null;
}

export interface RfqResponse {
  id: string;
  reference_number: string;
  buyer_organization_id: string;
  title: string;
  description: string | null;
  status: RfqStatus;
  auction_type: AuctionType;
  currency: string;
  vessel_id: string | null;
  delivery_port: string | null;
  delivery_date: string | null;
  bidding_start: string | null;
  bidding_deadline: string | null;
  allow_partial_quotes: boolean;
  allow_quote_revision: boolean;
  require_all_line_items: boolean;
  awarded_quote_id: string | null;
  awarded_supplier_id: string | null;
  awarded_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  notes: string | null;
  metadata_extra: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
  line_items: RfqLineItemResponse[];
}

export interface RfqListResponse {
  items: RfqResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface RfqListParams extends PaginationParams {
  status?: RfqStatus;
  search?: string;
}

// Invitations

export interface InvitationCreate {
  supplier_organization_ids: string[];
}

export interface InvitationResponse {
  id: string;
  rfq_id: string;
  supplier_organization_id: string;
  status: InvitationStatus;
  invited_by: string;
  invited_at: string;
  responded_at: string | null;
  decline_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvitationRespondRequest {
  accept: boolean;
  decline_reason?: string | null;
}

// Quote Line Items

export interface QuoteLineItemCreate {
  rfq_line_item_id: string;
  unit_price: number;
  quantity: number;
  total_price: number;
  lead_time_days?: number | null;
  notes?: string | null;
}

export interface QuoteLineItemResponse {
  id: string;
  quote_id: string;
  rfq_line_item_id: string;
  unit_price: string; // Decimal
  quantity: string; // Decimal
  total_price: string; // Decimal
  lead_time_days: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// Quotes

export interface QuoteCreate {
  currency?: string;
  valid_until?: string | null;
  delivery_port?: string | null;
  estimated_delivery_days?: number | null;
  payment_terms?: string | null;
  shipping_terms?: string | null;
  warranty_terms?: string | null;
  notes?: string | null;
  line_items?: QuoteLineItemCreate[];
}

export interface QuoteResponse {
  id: string;
  rfq_id: string;
  supplier_organization_id: string;
  status: QuoteStatus;
  version: number;
  total_amount: string | null; // Decimal
  currency: string;
  valid_until: string | null;
  delivery_port: string | null;
  estimated_delivery_days: number | null;
  payment_terms: string | null;
  shipping_terms: string | null;
  warranty_terms: string | null;
  price_rank: number | null;
  is_complete: boolean;
  notes: string | null;
  metadata_extra: Record<string, unknown>;
  submitted_by: string | null;
  submitted_at: string | null;
  withdrawn_at: string | null;
  withdrawal_reason: string | null;
  created_at: string;
  updated_at: string;
  line_items: QuoteLineItemResponse[];
}

export interface QuoteListResponse {
  items: QuoteResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Transitions

export interface TransitionResponse {
  id: string;
  rfq_id: string;
  from_status: RfqStatus;
  to_status: RfqStatus;
  transition_type: RfqTransitionType;
  triggered_by: string | null;
  trigger_source: string;
  reason: string | null;
  metadata_extra: Record<string, unknown>;
  created_at: string;
}

// Action Requests

export interface AwardRequest {
  quote_id: string;
}

export interface CancelRequest {
  reason: string;
}
