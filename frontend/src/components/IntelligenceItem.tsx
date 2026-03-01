import { IntelligenceItem as IntelligenceItemType } from '../types';
import { format } from 'date-fns';
import { intelligenceApi } from '../api/intelligence';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

interface IntelligenceItemProps {
  item: IntelligenceItemType;
  companyId: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  product: 'bg-blue-100 text-blue-800',
  gtm: 'bg-green-100 text-green-800',
  traction: 'bg-purple-100 text-purple-800',
  market_position: 'bg-yellow-100 text-yellow-800',
  corporate: 'bg-gray-100 text-gray-800',
  regulatory: 'bg-red-100 text-red-800',
};

const SOURCE_ICONS: Record<string, string> = {
  blog: '📝',
  twitter: '🐦',
  g2: '⭐',
  reddit: '💬',
};

export default function IntelligenceItem({ item, companyId }: IntelligenceItemProps) {
  const queryClient = useQueryClient();
  const [isUpdating, setIsUpdating] = useState(false);

  const handleToggleRead = async () => {
    setIsUpdating(true);
    try {
      await intelligenceApi.markAsRead(item.id, !item.is_read);
      // Invalidate queries to refetch
      queryClient.invalidateQueries({ queryKey: ['intelligence', companyId] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
    } catch (error) {
      console.error('Error updating read status:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const publishedDate = item.published_date
    ? format(new Date(item.published_date), 'MMM d, yyyy')
    : 'Date unknown';

  const categoryColor = item.result_category
    ? CATEGORY_COLORS[item.result_category] || 'bg-gray-100 text-gray-800'
    : 'bg-gray-100 text-gray-800';

  const sourceIcon = SOURCE_ICONS[item.source_type] || '📄';

  return (
    <div
      className={`bg-white rounded-lg shadow-md p-6 border-l-4 ${
        !item.is_read ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{sourceIcon}</span>
            <span className="text-sm text-gray-500">{publishedDate}</span>
            {item.result_category && (
              <span
                className={`text-xs font-semibold px-2 py-1 rounded ${categoryColor}`}
              >
                {item.result_category}
              </span>
            )}
          </div>
          <h4 className="text-lg font-semibold text-gray-900 mb-2">
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-500 transition-colors"
            >
              {item.title}
            </a>
          </h4>
        </div>
      </div>

      {item.summary && (
        <p className="text-gray-700 mb-4 leading-relaxed">{item.summary}</p>
      )}

      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <div className="flex items-center gap-2">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={item.is_read}
              onChange={handleToggleRead}
              disabled={isUpdating}
              className="w-4 h-4 text-blue-500 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-600">
              {item.is_read ? 'Read' : 'Mark as read'}
            </span>
          </label>
        </div>
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 hover:underline text-sm font-medium"
        >
          View original →
        </a>
      </div>
    </div>
  );
}

