import apiClient from './client';
import { CompanyWithStats, Company, ConnectGoogleDocRequest, GoogleDocStatus } from '../types';

export const companiesApi = {
  getAll: async (): Promise<CompanyWithStats[]> => {
    const response = await apiClient.get('/companies');
    return response.data;
  },

  getById: async (id: string): Promise<CompanyWithStats> => {
    const response = await apiClient.get(`/companies/${id}`);
    return response.data;
  },

  create: async (company: Omit<Company, 'id' | 'created_at'>): Promise<Company> => {
    const response = await apiClient.post('/companies', company);
    return response.data;
  },

  triggerScrape: async (id: string): Promise<{ task_id: string; message: string }> => {
    const response = await apiClient.post(`/companies/${id}/scrape`);
    return response.data;
  },

  connectGoogleDoc: async (id: string, request: ConnectGoogleDocRequest): Promise<any> => {
    const response = await apiClient.post(`/companies/${id}/connect-gdoc`, request);
    return response.data;
  },

  syncGoogleDoc: async (id: string): Promise<any> => {
    const response = await apiClient.post(`/companies/${id}/sync-gdoc`);
    return response.data;
  },

  getGoogleDocStatus: async (id: string): Promise<GoogleDocStatus> => {
    const response = await apiClient.get(`/companies/${id}/gdoc-status`);
    return response.data;
  },

  getCompanyDocuments: async (id: string): Promise<any[]> => {
    const response = await apiClient.get(`/companies/${id}/documents`);
    return response.data;
  },

  addCompanyDocument: async (id: string, data: { gdoc_url: string; title?: string }): Promise<any> => {
    const response = await apiClient.post(`/companies/${id}/documents`, data);
    return response.data;
  },

  deleteCompanyDocument: async (companyId: string, documentId: string): Promise<any> => {
    const response = await apiClient.delete(`/companies/${companyId}/documents/${documentId}`);
    return response.data;
  },
};

