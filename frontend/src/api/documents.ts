import apiClient from './client';
import {
  PortfolioDocument,
  DocumentUploadRequest,
  DocumentListResponse,
  DocumentSearchRequest,
  DocumentSearchResult,
  DocumentQuestionRequest,
  DocumentQuestionResponse,
} from '../types';

export const documentsApi = {
  upload: async (
    file: File,
    metadata: DocumentUploadRequest,
    uploadedBy?: string
  ): Promise<PortfolioDocument> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', metadata.title);
    formData.append('doc_type', metadata.doc_type);
    formData.append('document_date', metadata.document_date);
    formData.append('tags', JSON.stringify(metadata.tags || []));
    if (metadata.company_id) {
      formData.append('company_id', metadata.company_id);
    }
    if (metadata.notes) {
      formData.append('notes', metadata.notes);
    }
    if (uploadedBy) {
      formData.append('uploaded_by', uploadedBy);
    }

    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getAll: async (
    companyId?: string,
    docType?: string,
    limit = 50,
    offset = 0
  ): Promise<DocumentListResponse> => {
    const params = new URLSearchParams();
    if (companyId) params.append('company_id', companyId);
    if (docType) params.append('doc_type', docType);
    params.append('limit', String(limit));
    params.append('offset', String(offset));

    const response = await apiClient.get(`/documents?${params.toString()}`);
    return response.data;
  },

  getById: async (id: string): Promise<PortfolioDocument> => {
    const response = await apiClient.get(`/documents/${id}`);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/documents/${id}`);
  },

  search: async (request: DocumentSearchRequest): Promise<DocumentSearchResult[]> => {
    const response = await apiClient.post('/documents/search', request);
    return response.data;
  },

  ask: async (request: DocumentQuestionRequest): Promise<DocumentQuestionResponse> => {
    const response = await apiClient.post('/documents/ask', request);
    return response.data;
  },

  updateMetadata: async (
    id: string,
    metadata: Partial<DocumentUploadRequest>
  ): Promise<PortfolioDocument> => {
    const response = await apiClient.patch(`/documents/${id}`, metadata);
    return response.data;
  },
};

