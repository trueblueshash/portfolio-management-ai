import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { intelligenceApi } from '../api';
import { IntelligenceItem } from '../types';
import { formatDistanceToNow } from 'date-fns';

const SOURCE_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  news: { label: 'News', color: 'text-blue-700', bg: 'bg-blue-50' },
  competitor: { label: 'Competitor', color: 'text-red-600', bg: 'bg-red-50' },
  blog: { label: 'Blog', color: 'text-emerald-700', bg: 'bg-emerald-50' },
  reddit: { label: 'Reddit', color: 'text-orange-600', bg: 'bg-orange-50' },
};

const CAT_STYLES: Record<string, { color: string; bg: string }> = {
  product: { color: 'text-indigo-700', bg: 'bg-indigo-50' },
  gtm: { color: 'text-pink-700', bg: 'bg-pink-50' },
  traction: { color: 'text-emerald-700', bg: 'bg-emerald-50' },
  funding: { color: 'text-amber-700', bg: 'bg-amber-50' },
  market_position: { color: 'text-cyan-700', bg: 'bg-cyan-50' },
  corporate: { color: 'text-gray-600', bg: 'bg-gray-100' },
  regulatory: { color: 'text-violet-700', bg: 'bg-violet-50' },
};

type TabType = 'all' | 'news' | 'reddit' | 'competitor';

export default function IntelligenceWidget({ companyId, limit = 10 }: { companyId: string; limit?: number }) {
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const [expandedItem, setExpandedItem] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(limit);

  const { data: items, isLoading } = useQuery({
    queryKey: ['intelligence', companyId, activeTab, visibleCount],
    queryFn: () => intelligenceApi.getByCompany(companyId, {
      source_type: activeTab === 'all' ? undefined : activeTab,
    }, visibleCount),
    enabled: !!companyId,
  });

  if (isLoading) {
    return (
      <div className="border border-gray-200 rounded-xl p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-5 bg-gray-100 rounded w-1/2" />
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-3 bg-gray-100 rounded w-3/4" />
              <div className="h-3 bg-gray-100 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 pt-5 pb-4">
        <h3 className="font-serif text-lg text-gray-900 mb-1">Market Intelligence</h3>
        <p className="text-xs text-gray-400 mb-4">Latest signals · {items?.length ?? 0} items</p>
        <div className="flex gap-1.5">
          {(['all', 'news', 'reddit', 'competitor'] as TabType[]).map((tab) => (
            <button key={tab} onClick={() => { setActiveTab(tab); setVisibleCount(limit); }}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                activeTab === tab ? 'bg-dawn text-white' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
              }`}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {(!items || items.length === 0) ? (
        <div className="p-8 text-center">
          <p className="text-gray-400 text-sm">
            No {activeTab === 'all' ? 'market intelligence' : activeTab} found
          </p>
          <p className="text-xs text-gray-300 mt-1">
            {activeTab !== 'all' ? 'Try switching to "All"' : 'Run scrapers to collect updates'}
          </p>
        </div>
      ) : (
        <>
          <div className="divide-y divide-gray-100 max-h-[700px] overflow-y-auto">
            {items.map((item: IntelligenceItem) => {
              const src = SOURCE_STYLES[item.source_type] || SOURCE_STYLES.news;
              const cat = item.result_category ? CAT_STYLES[item.result_category] || CAT_STYLES.corporate : null;
              const isExpanded = expandedItem === item.id;

              return (
                <div key={item.id} className={`px-5 py-4 transition-colors ${isExpanded ? 'bg-gray-50/80' : 'hover:bg-gray-50/50'}`}>
                  <button onClick={() => setExpandedItem(isExpanded ? null : item.id)} className="w-full text-left">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className={`px-2 py-0.5 text-[10px] font-semibold rounded ${src.bg} ${src.color} uppercase tracking-wide`}>{src.label}</span>
                      {cat && <span className={`px-2 py-0.5 text-[10px] font-semibold rounded ${cat.bg} ${cat.color} uppercase tracking-wide`}>{item.result_category?.replace('_', ' ')}</span>}
                      <span className="text-[11px] text-gray-300 ml-auto">
                        {item.published_date ? formatDistanceToNow(new Date(item.published_date), { addSuffix: true }) : 'Recently'}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-800 leading-snug">{item.title}</p>
                  </button>

                  {/* Expanded detail view */}
                  {isExpanded && (
                    <div className="mt-3 ml-0 border-l-2 border-dawn/30 pl-4 space-y-2">
                      {item.summary ? (
                        <p className="text-xs text-gray-600 leading-relaxed">{item.summary}</p>
                      ) : (
                        <p className="text-xs text-gray-400 italic">No summary available</p>
                      )}
                      <div className="flex items-center gap-4 pt-1">
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-dawn hover:underline text-xs font-medium inline-flex items-center gap-1"
                        >
                          Read source
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </a>
                        {item.relevance_score > 0 && (
                          <span className="text-[10px] text-gray-400">
                            Relevance: {Math.round(item.relevance_score * 100)}%
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Load More / Pagination */}
          <div className="px-5 py-3 border-t border-gray-100 bg-gray-50/50 flex items-center justify-between">
            <span className="text-xs text-gray-400">Showing {items.length} items</span>
            {items.length >= visibleCount && (
              <button
                onClick={() => setVisibleCount(prev => prev + 20)}
                className="text-xs font-medium text-dawn hover:text-dawn/80 transition-colors"
              >
                Load more →
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
