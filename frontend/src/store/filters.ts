import { create } from 'zustand';
import { IntelligenceFilters } from '../types';

interface FiltersState {
  filters: IntelligenceFilters;
  setFilters: (filters: Partial<IntelligenceFilters>) => void;
  resetFilters: () => void;
}

export const useFiltersStore = create<FiltersState>((set) => ({
  filters: {},
  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    })),
  resetFilters: () => set({ filters: {} }),
}));

