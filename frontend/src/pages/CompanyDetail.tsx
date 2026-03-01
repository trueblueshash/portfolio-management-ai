import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { companiesApi, documentsApi } from '../api';
import QuestionAnswer from '../components/QuestionAnswer';
import IntelligenceWidget from '../components/IntelligenceWidget';
import AddDocumentModal from '../components/AddDocumentModal';
import { DocumentQuestionResponse } from '../types';
import { formatDistanceToNow } from 'date-fns';

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [answer, setAnswer] = useState<DocumentQuestionResponse | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  const queryClient = useQueryClient();

  const { data: company, isLoading, error } = useQuery({
    queryKey: ['company', id],
    queryFn: () => companiesApi.getById(id!),
    enabled: !!id,
  });

  // Fetch all Google Docs for this company
  const { data: companyDocuments } = useQuery({
    queryKey: ['company-documents', id],
    queryFn: () => companiesApi.getCompanyDocuments(id!),
    enabled: !!id,
  });

  // Fetch all documents (including reference files)
  const { data: allDocuments } = useQuery({
    queryKey: ['documents', id],
    queryFn: async () => {
      const response = await documentsApi.getAll(id);
      return response.documents;
    },
    enabled: !!id,
  });

  // Get latest document by date (most recent document_date)
  const latestDoc = companyDocuments && companyDocuments.length > 0
    ? [...companyDocuments].sort((a: any, b: any) => 
        new Date(b.document_date).getTime() - new Date(a.document_date).getTime()
      )[0]
    : null;

  // Combine Google Docs and reference documents, sort by date
  const allDocs = allDocuments 
    ? [...allDocuments].sort((a: any, b: any) => 
        new Date(b.document_date).getTime() - new Date(a.document_date).getTime()
      )
    : [];

  const askMutation = useMutation({
    mutationFn: (question: string) =>
      documentsApi.ask({
        question,
        company_id: id,
        search_scope: 'primary_only',
      }),
    onSuccess: (data) => {
      setAnswer(data);
      setCurrentQuestion(searchQuery);
    },
  });

  const syncDocumentMutation = useMutation({
    mutationFn: () => {
      // Sync all active documents for the company
      return companiesApi.syncGoogleDoc(id!);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-documents', id] });
      queryClient.invalidateQueries({ queryKey: ['documents', id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => companiesApi.deleteCompanyDocument(id!, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-documents', id] });
      queryClient.invalidateQueries({ queryKey: ['documents', id] });
    },
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      askMutation.mutate(searchQuery.trim());
    }
  };

  const exampleQuestions = [
    "What's the current ARR?",
    "What went well in Q3?",
    "What are the key challenges?",
    "How does ARR compare to plan?",
    "What's the cash burn rate?",
  ];

  const getStatusBadge = (doc: any) => {
    if (doc.google_doc_id) {
      // Google Doc
      if (doc.is_processed) {
        return (
          <span className="px-2 py-1 text-xs rounded bg-moss/20 text-moss font-semibold">
            ✅ Ready
          </span>
        );
      } else {
        return (
          <span className="px-2 py-1 text-xs rounded bg-rise/20 text-gray-700">
            🔄 Processing
          </span>
        );
      }
    } else {
      // Uploaded file
      if (doc.is_processed) {
        return (
          <span className="px-2 py-1 text-xs rounded bg-moss/20 text-moss font-semibold">
            ✅ Ready
          </span>
        );
      } else {
        return (
          <span className="px-2 py-1 text-xs rounded bg-rise/20 text-gray-700">
            ⏸️ Pending
          </span>
        );
      }
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    // Try to format as "Dec'25" if possible
    const month = date.toLocaleDateString('en-US', { month: 'short' });
    const year = date.getFullYear().toString().slice(-2);
    return `${month}'${year}`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-dawn"></div>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="min-h-screen bg-gray-50 flex justify-center items-center">
        <div className="text-center">
          <p className="text-dawn mb-4">Company not found</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90"
          >
            Back to Search
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Bar - Sticky */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="text-gray-600 hover:text-gray-900 flex items-center gap-2"
              >
                ← Back to Search
              </button>
              <div className="h-6 w-px bg-gray-300"></div>
              <h1 className="text-2xl font-bold text-gray-900">{company.name}</h1>
              {company.market_tags.length > 0 && (
                <div className="flex gap-2">
                  {company.market_tags.slice(0, 3).map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-night/10 text-night text-xs rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={() => navigate('/admin')}
              className="text-gray-600 hover:text-gray-900"
            >
              ⚙️ Admin
            </button>
          </div>
        </div>
      </header>

      {/* Search Bar - Sticky */}
      <div className="bg-white border-b border-gray-200 sticky top-[73px] z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <form onSubmit={handleSearchSubmit} className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`🔍 Ask anything about ${company.name}...`}
              className="w-full px-6 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-dawn focus:ring-2 focus:ring-dawn/20"
            />
            <button
              type="submit"
              disabled={askMutation.isPending || !searchQuery.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 disabled:opacity-50 font-medium"
            >
              {askMutation.isPending ? 'Asking...' : 'Ask'}
            </button>
          </form>
          
          {/* Example Questions */}
          {!currentQuestion && (
            <div className="mt-3 flex flex-wrap gap-2">
              {exampleQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setSearchQuery(q);
                    askMutation.mutate(q);
                  }}
                  className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700"
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* CENTER COLUMN - Q/A or Summary (75%) */}
          <div className="lg:col-span-9">
            {currentQuestion && answer ? (
              <QuestionAnswer
                question={currentQuestion}
                answer={answer}
                isLoading={askMutation.isPending}
                onAskFollowup={(followup) => {
                  setSearchQuery(followup);
                  askMutation.mutate(followup);
                }}
              />
            ) : latestDoc && latestDoc.summary ? (
              <div className="bg-white rounded-lg p-6 border border-gray-200">
                <div className="mb-4">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">Latest Summary</h2>
                  <p className="text-sm text-gray-500">
                    From {latestDoc.title} ({formatDate(latestDoc.document_date)})
                  </p>
                </div>
                <div className="prose max-w-none">
                  <p className="text-gray-700 whitespace-pre-wrap">{latestDoc.summary}</p>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg p-6 border border-gray-200 text-center">
                <p className="text-gray-500">Ask a question to get started</p>
                <p className="text-sm text-gray-400 mt-2">
                  Try: "What's the current ARR?" or "What went well in Q3?"
                </p>
              </div>
            )}

            {currentQuestion && (
              <button
                onClick={() => {
                  setCurrentQuestion('');
                  setAnswer(null);
                  setSearchQuery('');
                }}
                className="mt-4 text-dawn hover:underline text-sm"
              >
                Clear search
              </button>
            )}
          </div>

          {/* RIGHT COLUMN - Market Intelligence (25%) */}
          <div className="lg:col-span-3">
            <IntelligenceWidget companyId={company.id} limit={10} />
          </div>
        </div>

        {/* Unified Documents Section - Full Width */}
        <div className="mt-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">📄 Documents</h2>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 font-medium text-sm"
            >
              + Add Document
            </button>
          </div>

          {allDocs.length > 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Synced
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {allDocs.map((doc: any) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <span className="text-xl">
                            {doc.google_doc_id ? '📄' : '📁'}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-gray-900">{doc.title}</div>
                            {doc.summary && (
                              <div className="text-xs text-gray-500 mt-1 line-clamp-1">
                                {doc.summary}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs rounded bg-night/10 text-night">
                          {doc.doc_type.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(doc.document_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(doc)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {doc.updated_at
                          ? formatDistanceToNow(new Date(doc.updated_at), { addSuffix: true })
                          : 'Never'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        {doc.google_doc_id && (
                          <button
                            onClick={() => syncDocumentMutation.mutate()}
                            disabled={syncDocumentMutation.isPending}
                            className="text-dawn hover:text-dawn/80 disabled:opacity-50"
                            title="Sync all Google Docs for this company"
                          >
                            {syncDocumentMutation.isPending ? 'Syncing...' : 'Sync'}
                          </button>
                        )}
                        {doc.file_url && (
                          <a
                            href={doc.file_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-dawn hover:text-dawn/80"
                            title="Open in Google Docs"
                          >
                            View
                          </a>
                        )}
                        {doc.file_path && !doc.google_doc_id && (
                          <a
                            href={`/api/documents/${doc.id}/download`}
                            download
                            className="text-dawn hover:text-dawn/80"
                            title="Download file"
                          >
                            Download
                          </a>
                        )}
                        <button
                          onClick={() => {
                            if (confirm(`Are you sure you want to delete "${doc.title}"?`)) {
                              deleteMutation.mutate(doc.id);
                            }
                          }}
                          className="text-red-600 hover:text-red-800"
                          title="Delete document"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <p className="text-gray-500 mb-2">No documents yet</p>
              <p className="text-sm text-gray-400 mb-4">
                Add Google Docs or upload files to get started
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 font-medium text-sm"
              >
                + Add Document
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Add Document Modal */}
      {showAddModal && (
        <AddDocumentModal
          companyId={company.id}
          companyName={company.name}
          onSuccess={() => {
            setShowAddModal(false);
            queryClient.invalidateQueries({ queryKey: ['company-documents', id] });
            queryClient.invalidateQueries({ queryKey: ['documents', id] });
          }}
          onCancel={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
}
