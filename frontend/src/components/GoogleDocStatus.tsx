import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { companiesApi } from '../api';
import { CompanyWithStats } from '../types';
import { formatDistanceToNow } from 'date-fns';
import ConnectGoogleDoc from './ConnectGoogleDoc';
import { useState } from 'react';

interface GoogleDocStatusProps {
  company: CompanyWithStats;
}

export default function GoogleDocStatus({ company }: GoogleDocStatusProps) {
  const [showConnectModal, setShowConnectModal] = useState(false);
  const queryClient = useQueryClient();

  // Check if company has any Google Docs
  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ['company-documents', company.id],
    queryFn: () => companiesApi.getCompanyDocuments(company.id),
  });

  // Sort documents by date to get latest
  const sortedDocuments = documents 
    ? [...documents].sort((a: any, b: any) => 
        new Date(b.document_date).getTime() - new Date(a.document_date).getTime()
      )
    : [];
  
  const latestDoc = sortedDocuments[0];

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['gdoc-status', company.id],
    queryFn: () => companiesApi.getGoogleDocStatus(company.id),
  });

  const syncMutation = useMutation({
    mutationFn: () => companiesApi.syncGoogleDoc(company.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gdoc-status', company.id] });
      queryClient.invalidateQueries({ queryKey: ['company', company.id] });
      queryClient.invalidateQueries({ queryKey: ['company-documents', company.id] });
    },
  });

  if (docsLoading || statusLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  const hasDocuments = documents && documents.length > 0;
  const isConnected = hasDocuments;

  return (
    <>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">📊 {company.name}</h3>
          {isConnected && (
            <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
              ✅ Connected
            </span>
          )}
        </div>

        {isConnected && documents ? (
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-gray-900">
                {documents.length} document{documents.length !== 1 ? 's' : ''} connected
              </p>
              {status?.last_synced && (
                <p className="text-sm text-gray-600 mt-1">
                  Last synced:{' '}
                  {formatDistanceToNow(new Date(status.last_synced), { addSuffix: true })}
                </p>
              )}
            </div>

            {/* Show latest document */}
            {latestDoc && (
              <div className="text-sm">
                <p className="text-gray-600">Latest:</p>
                <a
                  href={latestDoc.file_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  {latestDoc.title} ({new Date(latestDoc.document_date).toLocaleDateString()}) →
                </a>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
              >
                {syncMutation.isPending ? 'Syncing...' : 'Sync Now'}
              </button>
              <button
                onClick={() => setShowConnectModal(true)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 text-sm"
              >
                Add More
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">❌ No Google Doc connected</p>
            <button
              onClick={() => setShowConnectModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              + Connect Google Doc
            </button>
          </div>
        )}
      </div>

      {showConnectModal && (
        <ConnectGoogleDoc
          companyId={company.id}
          companyName={company.name}
          onSuccess={() => setShowConnectModal(false)}
          onCancel={() => setShowConnectModal(false)}
        />
      )}
    </>
  );
}

