/**
 * Document Management API (Task #43), E-Signature API (Task #57),
 * and Document Template API (Task #57).
 */

import type {
  Document,
  DocumentUploadResponse,
  DocumentListResponse,
  DocumentUpdateRequest,
  ExpiringDocumentsResponse,
  SignatureRequest,
  SignatureRequestCreate,
  SignatureRequestListResponse,
  SignatureRequestFilters,
  DocumentTemplate,
  DocumentTemplateCreate,
  DocumentTemplateUpdate,
  DocumentTemplateListResponse,
} from '../types';

import {
  getApiUrl,
  buildHeaders,
  buildMultipartHeaders,
  safeFetch,
  ApiError,
  handleResponse,
} from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';

// =============================================================================
// Document Management API (Task #43)
// =============================================================================

/**
 * Upload a document file.
 */
export async function uploadDocument(
  file: File,
  metadata?: {
    property_id?: string;
    category?: string;
    tags?: string[];
    description?: string;
    expiry_date?: string;
  }
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (metadata?.property_id) formData.append('property_id', metadata.property_id);
  if (metadata?.category) formData.append('category', metadata.category);
  if (metadata?.tags) formData.append('tags', JSON.stringify(metadata.tags));
  if (metadata?.description) formData.append('description', metadata.description);
  if (metadata?.expiry_date) formData.append('expiry_date', metadata.expiry_date);

  const response = await safeFetch(`${getApiUrl()}/documents`, {
    method: 'POST',
    headers: buildMultipartHeaders(),
    credentials: 'include',
    body: formData,
  });
  return handleResponse<DocumentUploadResponse>(response);
}

/**
 * List documents with optional filters.
 */
export async function getDocuments(params?: {
  property_id?: string;
  category?: string;
  ocr_status?: string;
  search_query?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}): Promise<DocumentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.property_id) searchParams.append('property_id', params.property_id);
  if (params?.category) searchParams.append('category', params.category);
  if (params?.ocr_status) searchParams.append('ocr_status', params.ocr_status);
  if (params?.search_query) searchParams.append('search_query', params.search_query);
  if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
  if (params?.sort_order) searchParams.append('sort_order', params.sort_order);
  if (params?.page) searchParams.append('page', String(params.page));
  if (params?.page_size) searchParams.append('page_size', String(params.page_size));

  const queryString = searchParams.toString();
  const url = queryString ? `${getApiUrl()}/documents?${queryString}` : `${getApiUrl()}/documents`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<DocumentListResponse>(response);
}

/**
 * Get expiring documents.
 */
export async function getExpiringDocuments(
  daysAhead: number = 30
): Promise<ExpiringDocumentsResponse> {
  const response = await safeFetch(`${getApiUrl()}/documents/expiring?days_ahead=${daysAhead}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<ExpiringDocumentsResponse>(response);
}

/**
 * Get document download URL.
 */
export function getDocumentDownloadUrl(documentId: string): string {
  return `${getApiUrl()}/documents/${encodeURIComponent(documentId)}`;
}

/**
 * Update document metadata.
 */
export async function updateDocument(
  documentId: string,
  data: DocumentUpdateRequest
): Promise<Document> {
  const response = await safeFetch(`${getApiUrl()}/documents/${encodeURIComponent(documentId)}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Document>(response);
}

/**
 * Delete a document.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to delete document', response.status);
  }
}

// =============================================================================
// E-Signature API Functions (Task #57)
// =============================================================================

/**
 * Create a signature request
 */
export async function createSignatureRequest(
  data: SignatureRequestCreate
): Promise<SignatureRequest> {
  const response = await fetch(`${getApiUrl()}/signatures/request`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to create signature request', response.status);
  }
  return response.json();
}

/**
 * Get signature requests with optional filters
 */
export async function getSignatureRequests(
  filters?: SignatureRequestFilters
): Promise<SignatureRequestListResponse> {
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.property_id) params.append('property_id', filters.property_id);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());
  if (filters?.sort_by) params.append('sort_by', filters.sort_by);
  if (filters?.sort_order) params.append('sort_order', filters.sort_order);

  const response = await fetch(`${getApiUrl()}/signatures?${params.toString()}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to get signature requests', response.status);
  }
  return response.json();
}

/**
 * Get a single signature request by ID
 */
export async function getSignatureRequest(id: string): Promise<SignatureRequest> {
  const response = await fetch(`${getApiUrl()}/signatures/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to get signature request', response.status);
  }
  return response.json();
}

/**
 * Cancel a signature request
 */
export async function cancelSignatureRequest(
  id: string
): Promise<{ status: string; request_id: string }> {
  const response = await fetch(`${getApiUrl()}/signatures/${id}/cancel`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to cancel signature request', response.status);
  }
  return response.json();
}

/**
 * Send a reminder to pending signers
 */
export async function sendSignatureReminder(
  id: string
): Promise<{ status: string; request_id: string }> {
  const response = await fetch(`${getApiUrl()}/signatures/${id}/reminder`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to send reminder', response.status);
  }
  return response.json();
}

/**
 * Get the download URL for a signed document
 */
export function getSignedDocumentDownloadUrl(requestId: string): string {
  return `${getApiUrl()}/signatures/${requestId}/download`;
}

// =============================================================================
// Document Template API Functions (Task #57)
// =============================================================================

/**
 * Get document templates with optional filters
 */
export async function getDocumentTemplates(filters?: {
  template_type?: string;
  page?: number;
  page_size?: number;
}): Promise<DocumentTemplateListResponse> {
  const params = new URLSearchParams();
  if (filters?.template_type) params.append('template_type', filters.template_type);
  if (filters?.page) params.append('page', filters.page.toString());
  if (filters?.page_size) params.append('page_size', filters.page_size.toString());

  const response = await fetch(`${getApiUrl()}/signatures/templates?${params.toString()}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to get templates', response.status);
  }
  return response.json();
}

/**
 * Get a single document template by ID
 */
export async function getDocumentTemplate(id: string): Promise<DocumentTemplate> {
  const response = await fetch(`${getApiUrl()}/signatures/templates/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to get template', response.status);
  }
  return response.json();
}

/**
 * Create a new document template
 */
export async function createDocumentTemplate(
  data: DocumentTemplateCreate
): Promise<DocumentTemplate> {
  const response = await fetch(`${getApiUrl()}/signatures/templates`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to create template', response.status);
  }
  return response.json();
}

/**
 * Update an existing document template
 */
export async function updateDocumentTemplate(
  id: string,
  data: DocumentTemplateUpdate
): Promise<DocumentTemplate> {
  const response = await fetch(`${getApiUrl()}/signatures/templates/${id}`, {
    method: 'PUT',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to update template', response.status);
  }
  return response.json();
}

/**
 * Delete a document template
 */
export async function deleteDocumentTemplate(id: string): Promise<void> {
  const response = await fetch(`${getApiUrl()}/signatures/templates/${id}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(error.detail || 'Failed to delete template', response.status);
  }
}
