import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('app_api_key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('app_api_key');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

// One-pager API
export const getOnePager = async (companyId: string) => {
  const { data } = await apiClient.get(`/onepager/companies/${companyId}`);
  return data;
};

export const generateOnePager = async (companyId: string) => {
  const { data } = await apiClient.post(`/onepager/companies/${companyId}/generate`);
  return data;
};

export const updateOnePagerField = async (
  onepagerId: string,
  field: string,
  value: any
) => {
  const { data } = await apiClient.patch(`/onepager/${onepagerId}`, { field, value });
  return data;
};

// Comps API
export const getComps = async (companyId: string) => {
  const { data } = await apiClient.get(`/comps/companies/${companyId}`);
  return data;
};

export const refreshComps = async (companyId: string) => {
  const { data } = await apiClient.post(`/comps/companies/${companyId}/refresh`);
  return data;
};

export default apiClient;

