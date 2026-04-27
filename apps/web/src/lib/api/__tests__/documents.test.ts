/**
 * Comprehensive tests for documents.ts
 *
 * Covers all exported functions:
 * - Document Management: uploadDocument, getDocuments, getExpiringDocuments,
 *   getDocumentDownloadUrl, updateDocument, deleteDocument
 * - E-Signature: createSignatureRequest, getSignatureRequests, getSignatureRequest,
 *   cancelSignatureRequest, sendSignatureReminder, getSignedDocumentDownloadUrl
 * - Document Templates: getDocumentTemplates, getDocumentTemplate,
 *   createDocumentTemplate, updateDocumentTemplate, deleteDocumentTemplate
 */

import { jest } from '@jest/globals';
import {
  uploadDocument,
  getDocuments,
  getExpiringDocuments,
  getDocumentDownloadUrl,
  updateDocument,
  deleteDocument,
  createSignatureRequest,
  getSignatureRequests,
  getSignatureRequest,
  cancelSignatureRequest,
  sendSignatureReminder,
  getSignedDocumentDownloadUrl,
  getDocumentTemplates,
  getDocumentTemplate,
  createDocumentTemplate,
  updateDocumentTemplate,
  deleteDocumentTemplate,
} from '../documents';
import { ApiError } from '../client';
import type {
  DocumentUploadResponse,
  DocumentListResponse,
  Document,
  ExpiringDocumentsResponse,
  SignatureRequest,
  SignatureRequestListResponse,
  DocumentTemplate,
  DocumentTemplateListResponse,
} from '../../types';

// Mock fetch globally
global.fetch = jest.fn();

const mockFetch = global.fetch as jest.Mock;

describe('documents.ts', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
    mockFetch.mockReset();
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  // ===========================================================================
  // Document Management API (Task #43)
  // ===========================================================================
  describe('uploadDocument', () => {
    const mockUploadResponse: DocumentUploadResponse = {
      id: 'doc-1',
      filename: 'contract.pdf',
      original_filename: 'contract.pdf',
      file_type: 'application/pdf',
      file_size: 1024,
      message: 'Document uploaded successfully',
    };

    it('uploads a file without metadata', async () => {
      const file = new File(['content'], 'contract.pdf', { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUploadResponse,
      });

      const result = await uploadDocument(file);

      expect(result).toEqual(mockUploadResponse);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/documents');
      expect(init.method).toBe('POST');
      expect(init.body).toBeInstanceOf(FormData);
      expect(init.credentials).toBe('include');
    });

    it('uploads a file with all metadata fields', async () => {
      const file = new File(['content'], 'lease.pdf', { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUploadResponse,
      });

      const metadata = {
        property_id: 'prop-123',
        category: 'contract',
        tags: ['lease', '2024'],
        description: 'Lease agreement for unit 4B',
        expiry_date: '2025-12-31',
      };

      await uploadDocument(file, metadata);

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/documents');
      expect(init.method).toBe('POST');

      const formData = init.body as FormData;
      expect(formData.get('file')).toBe(file);
      expect(formData.get('property_id')).toBe('prop-123');
      expect(formData.get('category')).toBe('contract');
      expect(formData.get('tags')).toBe(JSON.stringify(['lease', '2024']));
      expect(formData.get('description')).toBe('Lease agreement for unit 4B');
      expect(formData.get('expiry_date')).toBe('2025-12-31');
    });

    it('uploads a file with partial metadata (only property_id)', async () => {
      const file = new File(['data'], 'doc.pdf', { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUploadResponse,
      });

      await uploadDocument(file, { property_id: 'prop-456' });

      const formData = (mockFetch.mock.calls[0][1] as RequestInit).body as FormData;
      expect(formData.get('property_id')).toBe('prop-456');
      expect(formData.get('category')).toBeNull();
      expect(formData.get('tags')).toBeNull();
    });

    it('throws ApiError on server error', async () => {
      const file = new File(['data'], 'bad.pdf', { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => JSON.stringify({ detail: 'Internal server error' }),
        headers: new Headers(),
      });

      await expect(uploadDocument(file)).rejects.toThrow(ApiError);
    });
  });

  describe('getDocuments', () => {
    const mockListResponse: DocumentListResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    };

    it('fetches documents without params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockListResponse,
      });

      const result = await getDocuments();

      expect(result).toEqual(mockListResponse);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/documents');
    });

    it('fetches documents with all filter params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockListResponse,
      });

      await getDocuments({
        property_id: 'prop-1',
        category: 'contract',
        ocr_status: 'completed',
        search_query: 'lease',
        sort_by: 'created_at',
        sort_order: 'desc',
        page: 2,
        page_size: 10,
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/v1/documents?');
      expect(url).toContain('property_id=prop-1');
      expect(url).toContain('category=contract');
      expect(url).toContain('ocr_status=completed');
      expect(url).toContain('search_query=lease');
      expect(url).toContain('sort_by=created_at');
      expect(url).toContain('sort_order=desc');
      expect(url).toContain('page=2');
      expect(url).toContain('page_size=10');
    });

    it('fetches documents with partial params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockListResponse,
      });

      await getDocuments({ category: 'financial' });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('category=financial');
      expect(url).not.toContain('property_id');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: 'Unauthorized' }),
        headers: new Headers(),
      });

      await expect(getDocuments()).rejects.toThrow(ApiError);
    });
  });

  describe('getExpiringDocuments', () => {
    const mockExpiringResponse: ExpiringDocumentsResponse = {
      items: [],
      total: 0,
      days_ahead: 30,
    };

    it('fetches expiring documents with default days_ahead', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockExpiringResponse,
      });

      const result = await getExpiringDocuments();

      expect(result).toEqual(mockExpiringResponse);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/v1/documents/expiring?days_ahead=30');
    });

    it('fetches expiring documents with custom days_ahead', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockExpiringResponse, days_ahead: 60 }),
      });

      const result = await getExpiringDocuments(60);

      expect(result.days_ahead).toBe(60);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('days_ahead=60');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => JSON.stringify({ detail: 'Server error' }),
        headers: new Headers(),
      });

      await expect(getExpiringDocuments()).rejects.toThrow(ApiError);
    });
  });

  describe('getDocumentDownloadUrl', () => {
    it('returns correct download URL', () => {
      const url = getDocumentDownloadUrl('doc-123');
      expect(url).toBe('/api/v1/documents/doc-123');
    });

    it('encodes special characters in document ID', () => {
      const url = getDocumentDownloadUrl('doc/with/slashes');
      expect(url).toBe('/api/v1/documents/doc%2Fwith%2Fslashes');
    });

    it('uses custom API URL from env', () => {
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
      const url = getDocumentDownloadUrl('doc-456');
      expect(url).toBe('https://api.example.com/documents/doc-456');
    });
  });

  describe('updateDocument', () => {
    const mockDocument: Document = {
      id: 'doc-1',
      user_id: 'user-1',
      filename: 'contract.pdf',
      original_filename: 'contract.pdf',
      file_type: 'application/pdf',
      file_size: 1024,
      ocr_status: 'completed',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    };

    it('updates document metadata', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocument,
      });

      const updateData = {
        category: 'financial' as const,
        tags: ['updated'],
        description: 'Updated description',
      };

      const result = await updateDocument('doc-1', updateData);

      expect(result).toEqual(mockDocument);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/documents/doc-1');
      expect(init.method).toBe('PATCH');
      expect(JSON.parse(init.body as string)).toEqual(updateData);
    });

    it('encodes document ID in URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocument,
      });

      await updateDocument('doc special', { description: 'test' });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/documents/doc%20special');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => JSON.stringify({ detail: 'Document not found' }),
        headers: new Headers(),
      });

      await expect(updateDocument('missing-doc', { description: 'test' })).rejects.toThrow(
        ApiError
      );
    });
  });

  describe('deleteDocument', () => {
    it('deletes a document successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
      });

      await expect(deleteDocument('doc-1')).resolves.toBeUndefined();

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/documents/doc-1');
      expect(init.method).toBe('DELETE');
    });

    it('encodes document ID in URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
      });

      await deleteDocument('doc/special');

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/documents/doc%2Fspecial');
    });

    it('throws ApiError with server error detail on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Document not found' }),
      });

      try {
        await deleteDocument('missing');
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Document not found');
        expect((error as ApiError).status).toBe(404);
      }
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      try {
        await deleteDocument('doc-1');
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        // .catch(() => ({ detail: 'Unknown error' })) provides the detail
        expect((error as ApiError).message).toBe('Unknown error');
      }
    });
  });

  // ===========================================================================
  // E-Signature API Functions (Task #57)
  // ===========================================================================
  describe('createSignatureRequest', () => {
    const mockSignatureRequest: SignatureRequest = {
      id: 'sig-1',
      user_id: 'user-1',
      title: 'Rental Agreement',
      provider: 'hellosign',
      signers: [
        {
          email: 'tenant@example.com',
          name: 'John Doe',
          role: 'tenant',
          order: 1,
          status: 'pending',
        },
      ],
      status: 'draft',
      created_at: '2024-01-01T00:00:00Z',
    };

    it('creates a signature request successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSignatureRequest,
      });

      const createData = {
        title: 'Rental Agreement',
        signers: [
          { email: 'tenant@example.com', name: 'John Doe', role: 'tenant' as const, order: 1 },
        ],
      };

      const result = await createSignatureRequest(createData);

      expect(result).toEqual(mockSignatureRequest);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/request');
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(createData);
      expect(init.credentials).toBe('include');
    });

    it('creates a signature request with all optional fields', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSignatureRequest,
      });

      const createData = {
        title: 'Purchase Offer',
        template_id: 'tmpl-1',
        document_id: 'doc-1',
        subject: 'Please sign this offer',
        message: 'This is your purchase offer',
        signers: [
          { email: 'seller@example.com', name: 'Jane Smith', role: 'seller' as const, order: 1 },
        ],
        variables: { price: 500000 },
        property_id: 'prop-1',
        expires_in_days: 14,
        provider: 'docusign' as const,
      };

      await createSignatureRequest(createData);

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/request');
      expect(JSON.parse(init.body as string)).toEqual(createData);
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid signer data' }),
      });

      await expect(createSignatureRequest({ title: 'Test', signers: [] })).rejects.toThrow(
        'Invalid signer data'
      );
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse error');
        },
      });

      await expect(createSignatureRequest({ title: 'Test', signers: [] })).rejects.toThrow(
        'Unknown error'
      );
    });
  });

  describe('getSignatureRequests', () => {
    const mockListResponse: SignatureRequestListResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    };

    it('fetches signature requests without filters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockListResponse,
      });

      const result = await getSignatureRequests();

      expect(result).toEqual(mockListResponse);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/v1/signatures?');
      expect(init.method).toBe('GET');
    });

    it('fetches signature requests with all filters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockListResponse,
      });

      await getSignatureRequests({
        status: 'completed',
        property_id: 'prop-1',
        page: 2,
        page_size: 5,
        sort_by: 'created_at',
        sort_order: 'desc',
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('status=completed');
      expect(url).toContain('property_id=prop-1');
      expect(url).toContain('page=2');
      expect(url).toContain('page_size=5');
      expect(url).toContain('sort_by=created_at');
      expect(url).toContain('sort_order=desc');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Server error' }),
      });

      await expect(getSignatureRequests()).rejects.toThrow('Server error');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('no json');
        },
      });

      await expect(getSignatureRequests()).rejects.toThrow('Unknown error');
    });
  });

  describe('getSignatureRequest', () => {
    const mockRequest: SignatureRequest = {
      id: 'sig-1',
      user_id: 'user-1',
      title: 'Test Request',
      provider: 'hellosign',
      signers: [],
      status: 'sent',
      created_at: '2024-01-01T00:00:00Z',
    };

    it('fetches a single signature request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRequest,
      });

      const result = await getSignatureRequest('sig-1');

      expect(result).toEqual(mockRequest);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/sig-1');
      expect(init.method).toBe('GET');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      });

      await expect(getSignatureRequest('missing')).rejects.toThrow('Not found');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('parse fail');
        },
      });

      await expect(getSignatureRequest('sig-1')).rejects.toThrow('Unknown error');
    });
  });

  describe('cancelSignatureRequest', () => {
    const mockCancelResponse = { status: 'cancelled', request_id: 'sig-1' };

    it('cancels a signature request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCancelResponse,
      });

      const result = await cancelSignatureRequest('sig-1');

      expect(result).toEqual(mockCancelResponse);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/sig-1/cancel');
      expect(init.method).toBe('POST');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Already completed' }),
      });

      await expect(cancelSignatureRequest('sig-1')).rejects.toThrow('Already completed');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('fail');
        },
      });

      await expect(cancelSignatureRequest('sig-1')).rejects.toThrow('Unknown error');
    });
  });

  describe('sendSignatureReminder', () => {
    const mockReminderResponse = { status: 'reminder_sent', request_id: 'sig-1' };

    it('sends a reminder successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockReminderResponse,
      });

      const result = await sendSignatureReminder('sig-1');

      expect(result).toEqual(mockReminderResponse);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/sig-1/reminder');
      expect(init.method).toBe('POST');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Request not found' }),
      });

      await expect(sendSignatureReminder('missing')).rejects.toThrow('Request not found');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('fail');
        },
      });

      await expect(sendSignatureReminder('sig-1')).rejects.toThrow('Unknown error');
    });
  });

  describe('getSignedDocumentDownloadUrl', () => {
    it('returns correct download URL', () => {
      const url = getSignedDocumentDownloadUrl('sig-1');
      expect(url).toBe('/api/v1/signatures/sig-1/download');
    });

    it('uses custom API URL from env', () => {
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
      const url = getSignedDocumentDownloadUrl('sig-2');
      expect(url).toBe('https://api.example.com/signatures/sig-2/download');
    });
  });

  // ===========================================================================
  // Document Template API Functions (Task #57)
  // ===========================================================================
  describe('getDocumentTemplates', () => {
    const mockTemplatesResponse: DocumentTemplateListResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    };

    it('fetches templates without filters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTemplatesResponse,
      });

      const result = await getDocumentTemplates();

      expect(result).toEqual(mockTemplatesResponse);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/v1/signatures/templates?');
      expect(init.method).toBe('GET');
    });

    it('fetches templates with all filters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTemplatesResponse,
      });

      await getDocumentTemplates({
        template_type: 'rental_agreement',
        page: 3,
        page_size: 10,
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('template_type=rental_agreement');
      expect(url).toContain('page=3');
      expect(url).toContain('page_size=10');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Server error' }),
      });

      await expect(getDocumentTemplates()).rejects.toThrow('Server error');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('fail');
        },
      });

      await expect(getDocumentTemplates()).rejects.toThrow('Unknown error');
    });
  });

  describe('getDocumentTemplate', () => {
    const mockTemplate: DocumentTemplate = {
      id: 'tmpl-1',
      user_id: 'user-1',
      name: 'Rental Agreement Template',
      template_type: 'rental_agreement',
      content: 'This is a rental agreement...',
      is_default: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    it('fetches a single template', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTemplate,
      });

      const result = await getDocumentTemplate('tmpl-1');

      expect(result).toEqual(mockTemplate);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/templates/tmpl-1');
      expect(init.method).toBe('GET');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Template not found' }),
      });

      await expect(getDocumentTemplate('missing')).rejects.toThrow('Template not found');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('fail');
        },
      });

      await expect(getDocumentTemplate('tmpl-1')).rejects.toThrow('Unknown error');
    });
  });

  describe('createDocumentTemplate', () => {
    const mockTemplate: DocumentTemplate = {
      id: 'tmpl-new',
      user_id: 'user-1',
      name: 'New Template',
      template_type: 'custom',
      content: 'Template content here',
      is_default: false,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    it('creates a template successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTemplate,
      });

      const createData = {
        name: 'New Template',
        template_type: 'custom' as const,
        content: 'Template content here',
      };

      const result = await createDocumentTemplate(createData);

      expect(result).toEqual(mockTemplate);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/templates');
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(createData);
    });

    it('creates a template with all optional fields', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTemplate,
      });

      const createData = {
        name: 'Full Template',
        template_type: 'rental_agreement' as const,
        content: 'Content',
        description: 'A rental agreement template',
        variables: { landlord_name: 'string' },
        is_default: false,
        category: 'rental' as const,
        tags: ['rental', 'standard'],
        expiry_date: '2025-12-31',
      };

      await createDocumentTemplate(createData);

      const [, init] = mockFetch.mock.calls[0];
      expect(JSON.parse(init.body as string)).toEqual(createData);
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: 'Validation error' }),
      });

      await expect(
        createDocumentTemplate({ name: '', template_type: 'custom', content: '' })
      ).rejects.toThrow('Validation error');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('fail');
        },
      });

      await expect(
        createDocumentTemplate({ name: 'T', template_type: 'custom', content: 'C' })
      ).rejects.toThrow('Unknown error');
    });
  });

  describe('updateDocumentTemplate', () => {
    const mockUpdatedTemplate: DocumentTemplate = {
      id: 'tmpl-1',
      user_id: 'user-1',
      name: 'Updated Template',
      template_type: 'rental_agreement',
      content: 'Updated content',
      is_default: false,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    };

    it('updates a template successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdatedTemplate,
      });

      const updateData = {
        name: 'Updated Template',
        content: 'Updated content',
      };

      const result = await updateDocumentTemplate('tmpl-1', updateData);

      expect(result).toEqual(mockUpdatedTemplate);
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/templates/tmpl-1');
      expect(init.method).toBe('PUT');
      expect(JSON.parse(init.body as string)).toEqual(updateData);
    });

    it('updates template with all optional fields', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdatedTemplate,
      });

      const updateData = {
        name: 'New Name',
        description: 'New description',
        content: 'New content',
        variables: { key: 'value' },
        is_default: true,
        category: 'system' as const,
        tags: ['updated'],
        expiry_date: '2026-01-01',
      };

      await updateDocumentTemplate('tmpl-1', updateData);

      const [, init] = mockFetch.mock.calls[0];
      expect(JSON.parse(init.body as string)).toEqual(updateData);
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Template not found' }),
      });

      await expect(updateDocumentTemplate('missing', { name: 'test' })).rejects.toThrow(
        'Template not found'
      );
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('fail');
        },
      });

      await expect(updateDocumentTemplate('tmpl-1', { name: 'test' })).rejects.toThrow(
        'Unknown error'
      );
    });
  });

  describe('deleteDocumentTemplate', () => {
    it('deletes a template successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
      });

      await expect(deleteDocumentTemplate('tmpl-1')).resolves.toBeUndefined();

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/signatures/templates/tmpl-1');
      expect(init.method).toBe('DELETE');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Template not found' }),
      });

      await expect(deleteDocumentTemplate('missing')).rejects.toThrow('Template not found');
    });

    it('throws ApiError with Unknown error when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('fail');
        },
      });

      await expect(deleteDocumentTemplate('tmpl-1')).rejects.toThrow('Unknown error');
    });
  });

  // ===========================================================================
  // Cross-cutting concerns
  // ===========================================================================
  describe('credentials and headers', () => {
    it('includes credentials: include on fetch-based requests', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }),
      });

      await getSignatureRequests();

      const [, init] = mockFetch.mock.calls[0];
      expect(init.credentials).toBe('include');
    });

    it('includes Content-Type application/json for non-multipart requests', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'sig-1',
          user_id: 'user-1',
          title: 'Test',
          provider: 'hellosign',
          signers: [],
          status: 'draft',
          created_at: '2024-01-01T00:00:00Z',
        }),
      });

      await createSignatureRequest({ title: 'Test', signers: [] });

      const [, init] = mockFetch.mock.calls[0];
      expect(init.headers).toHaveProperty('Content-Type', 'application/json');
    });

    it('does NOT include Content-Type for multipart upload requests', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'doc-1',
          filename: 'test.pdf',
          original_filename: 'test.pdf',
          file_type: 'application/pdf',
          file_size: 100,
          message: 'ok',
        }),
      });

      const file = new File(['data'], 'test.pdf', { type: 'application/pdf' });
      await uploadDocument(file);

      const [, init] = mockFetch.mock.calls[0];
      expect(init.headers).not.toHaveProperty('Content-Type');
    });
  });
});
