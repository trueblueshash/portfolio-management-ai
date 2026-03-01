import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi, companiesApi } from '../api';
import { PortfolioDocument, DocumentType, CompanyWithStats } from '../types';
import { format } from 'date-fns';

const DOCUMENT_TYPE_LABELS: Record<DocumentType, { label: string; icon: string }> = {
  board_deck: { label: 'Board Deck', icon: '📊' },
  ic_memo: { label: 'IC Memo', icon: '📝' },
  diligence: { label: 'Due Diligence', icon: '🔍' },
  quarterly_review: { label: 'Quarterly Review', icon: '📅' },
  valuation: { label: 'Valuation', icon: '💰' },
  thesis: { label: 'Thesis', icon: '💡' },
  update: { label: 'Update', icon: '📰' },
  general: { label: 'General', icon: '📄' },
};

interface DocumentListProps {
  onDocumentSelect?: (document: PortfolioDocument) => void;
}

export default function DocumentList({ onDocumentSelect }: DocumentListProps) {
  const [selectedCompany, setSelectedCompany] = useState<string>('');
  const [selectedDocType, setSelectedDocType] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  const queryClient = useQueryClient();

  // Fetch companies
  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: companiesApi.getAll,
  });

  // Fetch documents
  const { data: documentsData, isLoading } = useQuery({
    queryKey: ['documents', selectedCompany, selectedDocType],
    queryFn: () =>
      documentsApi.getAll(
        selectedCompany || undefined,
        selectedDocType || undefined
      ),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleDelete = async (id: string, title: string) => {
    if (confirm(`Are you sure you want to delete "${title}"?`)) {
      deleteMutation.mutate(id);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'processed':
        return (
          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">
            ✅ Processed
          </span>
        );
      case 'processing':
        return (
          <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded">
            ⏳ Processing
          </span>
        );
      case 'failed':
        return (
          <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded">
            ❌ Failed
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs font-semibold rounded">
            ⏸️ Pending
          </span>
        );
    }
  };

  const filteredDocuments =
    documentsData?.documents.filter((doc) => {
      if (selectedStatus && doc.processing_status !== selectedStatus) {
        return false;
      }
      return true;
    }) || [];

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Company
            </label>
            <select
              value={selectedCompany}
              onChange={(e) => setSelectedCompany(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Companies</option>
              <option value="">General/Fund-level</option>
              {companies?.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Document Type
            </label>
            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Types</option>
              {Object.entries(DOCUMENT_TYPE_LABELS).map(([value, { label, icon }]) => (
                <option key={value} value={value}>
                  {icon} {label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Statuses</option>
              <option value="processed">✅ Processed</option>
              <option value="processing">⏳ Processing</option>
              <option value="pending">⏸️ Pending</option>
              <option value="failed">❌ Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Company
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tags
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredDocuments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    No documents found. Upload your first document to get started.
                  </td>
                </tr>
              ) : (
                filteredDocuments.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => onDocumentSelect?.(doc)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {doc.title}
                      </div>
                      <div className="text-xs text-gray-500">{doc.file_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {doc.company_name ? (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                          {doc.company_name}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">Fund-level</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">
                        {DOCUMENT_TYPE_LABELS[doc.doc_type]?.icon}{' '}
                        {DOCUMENT_TYPE_LABELS[doc.doc_type]?.label}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(doc.document_date), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {doc.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                          >
                            {tag}
                          </span>
                        ))}
                        {doc.tags.length > 3 && (
                          <span className="text-xs text-gray-500">
                            +{doc.tags.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(doc.processing_status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(doc.id, doc.title);
                        }}
                        className="text-red-600 hover:text-red-800"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary */}
      {documentsData && (
        <div className="text-sm text-gray-600">
          Showing {filteredDocuments.length} of {documentsData.total} documents
        </div>
      )}
    </div>
  );
}

