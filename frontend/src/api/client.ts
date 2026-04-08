import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

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

