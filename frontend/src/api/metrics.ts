import apiClient from './client';

export interface HeadlineMetric {
  name: string;
  raw_name: string;
  value: number | null;
  previous_value: number | null;
  change_pct: number | null;
  unit: string;
  category: string;
}

export interface HeadlineResponse {
  company_name: string;
  period: string | null;
  period_date: string | null;
  headlines: HeadlineMetric[];
}

export interface MetricsPeriod {
  period: string;
  period_label: string;
  is_projected: boolean;
  metrics: Record<string, number>;
  source: string;
}

export interface MetricsCatalogEntry {
  display_name: string;
  category: string;
  unit: string;
  is_headline: boolean;
}

export interface MetricsResponse {
  company_id: string;
  company_name: string;
  periods: MetricsPeriod[];
  catalog: Record<string, MetricsCatalogEntry>;
}

export const metricsApi = {
  getHeadline: async (companyId: string): Promise<HeadlineResponse> => {
    const response = await apiClient.get(`/metrics/companies/${companyId}/headline`);
    return response.data;
  },

  getTimeSeries: async (companyId: string, limit = 12): Promise<MetricsResponse> => {
    const response = await apiClient.get(`/metrics/companies/${companyId}?limit=${limit}&include_projected=false`);
    return response.data;
  },

  syncFromDrive: async (companyId: string, folderUrl: string): Promise<any> => {
    const response = await apiClient.post(
      `/metrics/companies/${companyId}/sync-from-drive?folder_url=${encodeURIComponent(folderUrl)}`
    );
    return response.data;
  },
};
