import { useQuery } from '@tanstack/react-query';
import { intelligenceApi } from '../api/intelligence';
import { useFiltersStore } from '../store/filters';
import IntelligenceItem from './IntelligenceItem';

interface IntelligenceFeedProps {
  companyId: string;
}

export default function IntelligenceFeed({ companyId }: IntelligenceFeedProps) {
  const { filters } = useFiltersStore();

  const { data: items, isLoading, error } = useQuery({
    queryKey: ['intelligence', companyId, filters],
    queryFn: () => intelligenceApi.getByCompany(companyId, filters),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        Error loading intelligence items. Please try again.
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg mb-2">No intelligence items yet</p>
        <p className="text-sm">New items will appear here as they are collected.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <IntelligenceItem key={item.id} item={item} companyId={companyId} />
      ))}
    </div>
  );
}

