import apiClient from './client';
import { IntelligenceItem, IntelligenceFilters } from '../types';

export const intelligenceApi = {
  getByCompany: async (
    companyId: string,
    filters: IntelligenceFilters = {},
    limit = 50,
    offset = 0
  ): Promise<IntelligenceItem[]> => {
    const params = new URLSearchParams();
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.category) params.append('category', filters.category);
    if (filters.source_type) params.append('source_type', filters.source_type);
    if (filters.is_read !== undefined) params.append('is_read', String(filters.is_read));
    params.append('limit', String(limit));
    params.append('offset', String(offset));

    const response = await apiClient.get(
      `/intelligence/companies/${companyId}/intelligence?${params.toString()}`
    );
    return response.data;
  },

  markAsRead: async (itemId: string, isRead: boolean): Promise<{ id: string; is_read: boolean }> => {
    const response = await apiClient.put(`/intelligence/${itemId}/read`, { is_read: isRead });
    return response.data;
  },
};

