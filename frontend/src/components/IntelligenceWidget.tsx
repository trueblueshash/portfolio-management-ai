import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { intelligenceApi } from '../api';
import { IntelligenceItem } from '../types';
import { formatDistanceToNow } from 'date-fns';

interface IntelligenceWidgetProps {
  companyId: string;
  limit?: number;
}

type TabType = 'all' | 'news' | 'reddit' | 'competitors';

export default function IntelligenceWidget({ companyId, limit = 10 }: IntelligenceWidgetProps) {
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const [expandedItem, setExpandedItem] = useState<string | null>(null);

  const { data: items, isLoading } = useQuery({
    queryKey: ['intelligence', companyId, activeTab],
    queryFn: () => intelligenceApi.getByCompany(companyId, {
      source_type: activeTab === 'all' ? undefined : activeTab === 'news' ? 'news' : activeTab === 'reddit' ? 'reddit' : 'competitor',
    }, limit),
    enabled: !!companyId,
  });

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'news':
        return '📰';
      case 'reddit':
        return '💬';
      case 'competitor':
        return '🎯';
      default:
        return '📊';
    }
  };

  const getCategoryColor = (category: string | null) => {
    switch (category) {
      case 'product':
        return 'bg-sky/20 text-night';
      case 'gtm':
        return 'bg-rise/20 text-gray-700';
      case 'traction':
        return 'bg-moss/20 text-moss';
      case 'corporate':
        return 'bg-dawn/20 text-dawn';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <p className="text-gray-500 text-center text-sm">📊 No market intelligence yet</p>
        <p className="text-xs text-gray-400 text-center mt-1">
          Run scrapers to collect updates
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Market Intelligence</h3>
        <p className="text-sm text-gray-600 mb-3">Latest from scrapers</p>
        
        {/* Tabs */}
        <div className="flex gap-2">
          {(['all', 'news', 'reddit', 'competitors'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-dawn text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {items.map((item: IntelligenceItem) => {
          const isExpanded = expandedItem === item.id;
          
          return (
            <div key={item.id} className="p-4 hover:bg-gray-50 transition-colors">
              <button
                onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                className="w-full text-left"
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl">{getSourceIcon(item.source_type)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-500">
                        {item.published_date
                          ? formatDistanceToNow(new Date(item.published_date), { addSuffix: true })
                          : 'Recently'}
                      </span>
                      {item.result_category && (
                        <span className={`px-2 py-0.5 text-xs rounded ${getCategoryColor(item.result_category)}`}>
                          {item.result_category}
                        </span>
                      )}
                    </div>
                    <p className="font-medium text-gray-900 line-clamp-1">{item.title}</p>
                    {isExpanded && item.summary && (
                      <p className="text-sm text-gray-600 mt-2">{item.summary}</p>
                    )}
                  </div>
                </div>
              </button>

              {isExpanded && (
                <div className="mt-3 ml-8 space-y-2">
                  {item.summary && (
                    <p className="text-sm text-gray-700">{item.summary}</p>
                  )}
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-dawn hover:underline text-sm inline-block"
                  >
                    View source →
                  </a>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="p-4 border-t border-gray-200">
        <a
          href={`/company/${companyId}`}
          className="text-dawn hover:underline text-sm font-medium"
        >
          View All Intelligence →
        </a>
      </div>
    </div>
  );
}

