import { apiClient } from "./client";
import type {
  Product,
  ProductDetailResponse,
  ProductListResponse,
  ProductCreateRequest,
  ProductUpdateRequest,
  ProductListParams,
  ImpaValidationResponse,
  SupplierProduct,
  SupplierProductCreateRequest,
  SupplierProductUpdateRequest,
  SupplierPriceResponse,
  SupplierPriceCreateRequest,
  TextSearchResponse,
  TextSearchParams,
  VectorSearchRequest,
  VectorSearchResponse,
  MatchLineItemRequest,
  MatchLineItemResponse,
  SearchResult,
  Category,
  CategoryTreeNode,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  Breadcrumb,
  TranslationResponse,
  TranslationCreateRequest,
  CategoryTagResponse,
  FacetedSearchResponse,
  FacetedSearchParams,
  SynonymEntry,
  GenerateEmbeddingsRequest,
  GenerateEmbeddingsResponse,
} from "./types";

const PRODUCTS_BASE = "/api/v1/products";
const CATEGORIES_BASE = "/api/v1/categories";
const SEARCH_BASE = "/api/v1/search";

// ---------------------------------------------------------------------------
// Product API
// ---------------------------------------------------------------------------

export async function listProducts(params?: ProductListParams): Promise<ProductListResponse> {
  return apiClient.get<ProductListResponse>(
    PRODUCTS_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getProduct(id: string): Promise<ProductDetailResponse> {
  return apiClient.get<ProductDetailResponse>(`${PRODUCTS_BASE}/${id}`);
}

export async function getProductByImpa(impaCode: string): Promise<Product> {
  return apiClient.get<Product>(`${PRODUCTS_BASE}/impa/${impaCode}`);
}

export async function createProduct(data: ProductCreateRequest): Promise<Product> {
  return apiClient.post<Product>(PRODUCTS_BASE, data);
}

export async function updateProduct(id: string, data: ProductUpdateRequest): Promise<Product> {
  return apiClient.patch<Product>(`${PRODUCTS_BASE}/${id}`, data);
}

export async function deleteProduct(id: string): Promise<void> {
  return apiClient.delete<void>(`${PRODUCTS_BASE}/${id}`);
}

export async function validateImpaCode(impaCode: string): Promise<ImpaValidationResponse> {
  return apiClient.post<ImpaValidationResponse>(`${PRODUCTS_BASE}/validate-impa`, {
    impa_code: impaCode,
  });
}

// ---------------------------------------------------------------------------
// Supplier Products
// ---------------------------------------------------------------------------

export async function addSupplierProduct(
  productId: string,
  data: SupplierProductCreateRequest,
): Promise<SupplierProduct> {
  return apiClient.post<SupplierProduct>(`${PRODUCTS_BASE}/${productId}/suppliers`, data);
}

export async function listSupplierProducts(
  productId: string,
  activeOnly?: boolean,
): Promise<SupplierProduct[]> {
  return apiClient.get<SupplierProduct[]>(`${PRODUCTS_BASE}/${productId}/suppliers`, {
    active_only: activeOnly,
  });
}

export async function updateSupplierProduct(
  productId: string,
  supplierProductId: string,
  data: SupplierProductUpdateRequest,
): Promise<SupplierProduct> {
  return apiClient.patch<SupplierProduct>(
    `${PRODUCTS_BASE}/${productId}/suppliers/${supplierProductId}`,
    data,
  );
}

// ---------------------------------------------------------------------------
// Supplier Prices
// ---------------------------------------------------------------------------

export async function addSupplierPrice(
  productId: string,
  supplierProductId: string,
  data: SupplierPriceCreateRequest,
): Promise<SupplierPriceResponse> {
  return apiClient.post<SupplierPriceResponse>(
    `${PRODUCTS_BASE}/${productId}/suppliers/${supplierProductId}/prices`,
    data,
  );
}

export async function listSupplierPrices(
  productId: string,
  supplierProductId: string,
): Promise<SupplierPriceResponse[]> {
  return apiClient.get<SupplierPriceResponse[]>(
    `${PRODUCTS_BASE}/${productId}/suppliers/${supplierProductId}/prices`,
  );
}

// ---------------------------------------------------------------------------
// Tags
// ---------------------------------------------------------------------------

export async function getProductTags(productId: string): Promise<CategoryTagResponse[]> {
  return apiClient.get<CategoryTagResponse[]>(`${PRODUCTS_BASE}/${productId}/tags`);
}

export async function removeProductTag(productId: string, tagId: string): Promise<void> {
  return apiClient.delete<void>(`${PRODUCTS_BASE}/${productId}/tags/${tagId}`);
}

// ---------------------------------------------------------------------------
// Translations
// ---------------------------------------------------------------------------

export async function setTranslation(
  productId: string,
  locale: string,
  data: TranslationCreateRequest,
): Promise<TranslationResponse> {
  return apiClient.put<TranslationResponse>(
    `${PRODUCTS_BASE}/${productId}/translations/${locale}`,
    data,
  );
}

export async function getTranslations(productId: string): Promise<TranslationResponse[]> {
  return apiClient.get<TranslationResponse[]>(`${PRODUCTS_BASE}/${productId}/translations`);
}

// ---------------------------------------------------------------------------
// Validate Specs
// ---------------------------------------------------------------------------

export async function validateProductSpecs(
  productId: string,
): Promise<{ valid: boolean; errors: Record<string, unknown>[]; schema_source: string | null }> {
  return apiClient.post(`${PRODUCTS_BASE}/${productId}/validate-specs`);
}

// ---------------------------------------------------------------------------
// Category API
// ---------------------------------------------------------------------------

export async function listCategories(maxDepth?: number): Promise<CategoryTreeNode[]> {
  return apiClient.get<CategoryTreeNode[]>(CATEGORIES_BASE, { max_depth: maxDepth });
}

export async function getCategory(id: string): Promise<Category> {
  return apiClient.get<Category>(`${CATEGORIES_BASE}/${id}`);
}

export async function getCategoryTree(
  id: string,
  maxDepth?: number,
): Promise<CategoryTreeNode[]> {
  return apiClient.get<CategoryTreeNode[]>(`${CATEGORIES_BASE}/${id}/tree`, {
    max_depth: maxDepth,
  });
}

export async function getCategoryBreadcrumbs(id: string): Promise<Breadcrumb[]> {
  return apiClient.get<Breadcrumb[]>(`${CATEGORIES_BASE}/${id}/breadcrumbs`);
}

export async function getCategoryChildren(id: string): Promise<Category[]> {
  return apiClient.get<Category[]>(`${CATEGORIES_BASE}/${id}/children`);
}

export async function createCategory(data: CategoryCreateRequest): Promise<Category> {
  return apiClient.post<Category>(CATEGORIES_BASE, data);
}

export async function updateCategory(id: string, data: CategoryUpdateRequest): Promise<Category> {
  return apiClient.patch<Category>(`${CATEGORIES_BASE}/${id}`, data);
}

export async function moveCategorySubtree(
  id: string,
  newParentId: string | null,
): Promise<Category> {
  return apiClient.post<Category>(`${CATEGORIES_BASE}/${id}/move`, {
    new_parent_id: newParentId,
  });
}

// ---------------------------------------------------------------------------
// Search API
// ---------------------------------------------------------------------------

export async function searchProductsVector(data: VectorSearchRequest): Promise<VectorSearchResponse> {
  return apiClient.post<VectorSearchResponse>(`${SEARCH_BASE}/products`, data);
}

export async function matchLineItem(data: MatchLineItemRequest): Promise<MatchLineItemResponse> {
  return apiClient.post<MatchLineItemResponse>(`${SEARCH_BASE}/match`, data);
}

export async function searchProductsText(params: TextSearchParams): Promise<TextSearchResponse> {
  return apiClient.get<TextSearchResponse>(
    `${SEARCH_BASE}/products/text`,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getSuggestions(query: string, limit?: number): Promise<SearchResult[]> {
  return apiClient.get<SearchResult[]>(`${SEARCH_BASE}/suggest`, { q: query, limit });
}

export async function searchProductsFaceted(
  params: FacetedSearchParams,
): Promise<FacetedSearchResponse> {
  return apiClient.get<FacetedSearchResponse>(
    `${SEARCH_BASE}/products/faceted`,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function listSynonyms(term?: string): Promise<SynonymEntry[]> {
  return apiClient.get<SynonymEntry[]>(`${SEARCH_BASE}/synonyms`, { term });
}

export async function generateEmbeddings(
  data: GenerateEmbeddingsRequest,
): Promise<GenerateEmbeddingsResponse> {
  return apiClient.post<GenerateEmbeddingsResponse>(
    `${SEARCH_BASE}/embeddings/generate`,
    data,
  );
}
