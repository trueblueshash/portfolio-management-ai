import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '../api/documents';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';

interface PortfolioSummaryProps {
  companyId: string;
}

export default function PortfolioSummary({ companyId }: PortfolioSummaryProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['latest']));

  const { data: documents } = useQuery({
    queryKey: ['company-documents', companyId],
    queryFn: async () => {
      const { companiesApi } = await import('../api');
      return companiesApi.getCompanyDocuments(companyId);
    },
    enabled: !!companyId,
  });

  // Sort by document_date descending to get latest first
  const sortedDocs = documents 
    ? [...documents].sort((a: any, b: any) => 
        new Date(b.document_date).getTime() - new Date(a.document_date).getTime()
      )
    : [];
  
  const latestDoc = sortedDocs[0];

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  if (!latestDoc) {
    return (
      <div className="bg-dusk/30 rounded-lg p-6 border border-gray-200">
        <p className="text-gray-600 text-center">📄 No portfolio updates yet</p>
        <p className="text-sm text-gray-500 text-center mt-2">
          Connect a Google Doc to see summaries and metrics
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Latest Section - Always Expanded */}
      <div className="bg-dusk/30 rounded-lg p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {latestDoc.title.includes("Nov'25") ? "Nov'25" : "Latest Update"}
          </h3>
          <span className="text-xs text-gray-500">
            {latestDoc.updated_at && formatDistanceToNow(new Date(latestDoc.updated_at), { addSuffix: true })}
          </span>
        </div>

        {latestDoc.summary && (
          <div className="prose max-w-none">
            <p className="text-gray-700 whitespace-pre-wrap">{latestDoc.summary}</p>
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-gray-200">
          <a
            href={latestDoc.file_url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="text-dawn hover:underline text-sm font-medium"
          >
            📄 View in Google Docs →
          </a>
        </div>
      </div>

      {/* Older Sections - Collapsed by Default */}
      {sortedDocs && sortedDocs.length > 1 && (
        <div className="space-y-2">
          {sortedDocs.slice(1).map((doc: any) => {
            const sectionKey = doc.id;
            const isExpanded = expandedSections.has(sectionKey);
            const sectionName = doc.title.match(/(\w{3}'?\d{2})/)?.[1] || 'Previous Update';

            return (
              <div key={doc.id} className="bg-white rounded-lg border border-gray-200">
                <button
                  onClick={() => toggleSection(sectionKey)}
                  className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50"
                >
                  <span className="font-medium text-gray-900">{sectionName} ▼</span>
                  <span className="text-xs text-gray-500">
                    {doc.updated_at && formatDistanceToNow(new Date(doc.updated_at), { addSuffix: true })}
                  </span>
                </button>

                {isExpanded && (
                  <div className="px-6 pb-4 border-t border-gray-200">
                    {doc.summary && (
                      <p className="text-gray-700 mt-4 whitespace-pre-wrap">{doc.summary}</p>
                    )}
                    {doc.file_url && (
                      <a
                        href={doc.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-dawn hover:underline text-sm font-medium mt-4 inline-block"
                      >
                        📄 View in Google Docs →
                      </a>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

