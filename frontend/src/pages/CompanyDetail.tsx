import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { companiesApi, documentsApi, metricsApi } from '../api';
import { HeadlineMetric } from '../api/metrics';
import QuestionAnswer from '../components/QuestionAnswer';
import IntelligenceWidget from '../components/IntelligenceWidget';
import MetricsCard from '../components/MetricsCard';
import AddDocumentModal from '../components/AddDocumentModal';
import OnePagerSection from '../components/OnePagerSection';
import LogoutButton from '../components/LogoutButton';
import CompsTable from '../components/CompsTable';
import { DocumentQuestionResponse } from '../types';
import { formatDistanceToNow } from 'date-fns';

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [answer, setAnswer] = useState<DocumentQuestionResponse | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [activeSection, setActiveSection] = useState<'overview' | 'metrics' | 'documents' | 'comps'>('overview');

  const { data: company, isLoading, error } = useQuery({
    queryKey: ['company', id],
    queryFn: () => companiesApi.getById(id!),
    enabled: !!id,
  });

  const { data: headlines } = useQuery({
    queryKey: ['headlines', id],
    queryFn: () => metricsApi.getHeadline(id!),
    enabled: !!id,
  });

  const { data: metricsData } = useQuery({
    queryKey: ['metrics', id],
    queryFn: () => metricsApi.getTimeSeries(id!, 12),
    enabled: !!id,
  });

  const { data: allDocuments } = useQuery({
    queryKey: ['documents', id],
    queryFn: async () => { const r = await documentsApi.getAll(id); return r.documents; },
    enabled: !!id,
  });

  const allDocs = allDocuments ? [...allDocuments].sort((a: any, b: any) => new Date(b.document_date).getTime() - new Date(a.document_date).getTime()) : [];

  const askMutation = useMutation({
    mutationFn: (question: string) => documentsApi.ask({ question, company_id: id, search_scope: 'primary_only' }),
    onSuccess: (data) => { setAnswer(data); setCurrentQuestion(searchQuery); },
  });

  const syncMutation = useMutation({
    mutationFn: () => companiesApi.syncGoogleDoc(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-documents', id] });
      queryClient.invalidateQueries({ queryKey: ['documents', id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (docId: string) => companiesApi.deleteCompanyDocument(id!, docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-documents', id] });
      queryClient.invalidateQueries({ queryKey: ['documents', id] });
    },
  });

  const formatDate = (d: string) => {
    const date = new Date(d);
    return `${date.toLocaleDateString('en-US', { month: 'short' })}'${date.getFullYear().toString().slice(-2)}`;
  };

  const exampleQuestions = ["What's the current ARR?", "What went well last quarter?", "Key challenges?", "Growth vs plan?"];

  const priorityHeadlines = headlines?.headlines?.slice(0, 6) || [];

  if (isLoading) return (
    <div className="min-h-screen bg-white flex justify-center items-center">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-200 border-t-dawn" />
    </div>
  );

  if (error || !company) return (
    <div className="min-h-screen bg-white flex justify-center items-center">
      <div className="text-center">
        <p className="text-gray-500 mb-4 font-serif text-xl">Company not found</p>
        <button onClick={() => navigate('/')} className="text-dawn hover:underline text-sm">← Back</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-100 sticky top-0 z-50 bg-white/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-600 text-sm">← Back</button>
            <div className="h-5 w-px bg-gray-200" />
            <h1 className="font-serif text-2xl text-gray-900">{company.name}</h1>
          </div>
          <div className="flex items-center gap-3">
            {(company.market_tags || []).slice(0, 3).map((tag: string, i: number) => (
              <span key={i} className="px-2.5 py-1 bg-gray-50 text-gray-500 text-xs rounded-md font-medium">{tag}</span>
            ))}
            <LogoutButton />
          </div>
        </div>
      </header>

      {/* Search Bar */}
      <div className="border-b border-gray-100 bg-gray-50/50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <form onSubmit={(e) => { e.preventDefault(); if (searchQuery.trim()) askMutation.mutate(searchQuery.trim()); }} className="flex gap-3">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35" strokeLinecap="round"/></svg>
              </div>
              <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Ask anything about ${company.name}...`}
                className="w-full pl-11 pr-4 py-3 text-sm border border-gray-200 rounded-xl focus:outline-none focus:border-dawn focus:ring-1 focus:ring-dawn/20 bg-white placeholder:text-gray-400" />
            </div>
            <button type="submit" disabled={askMutation.isPending}
              className="px-5 py-3 bg-dawn text-white rounded-xl text-sm font-semibold hover:bg-dawn/90 disabled:opacity-50 whitespace-nowrap">
              {askMutation.isPending ? 'Thinking...' : 'Ask AI'}
            </button>
          </form>
          {!currentQuestion && (
            <div className="flex items-center gap-2 mt-3">
              <span className="text-xs text-gray-400">Try:</span>
              {exampleQuestions.map((q, i) => (
                <button key={i} onClick={() => { setSearchQuery(q); askMutation.mutate(q); }}
                  className="px-2.5 py-1 text-xs text-gray-500 bg-white border border-gray-200 rounded-md hover:border-dawn hover:text-dawn transition-all">
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Headline Metrics */}
      {priorityHeadlines.length > 0 && (
        <div className="border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-6 py-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h3 className="text-xs text-gray-400 uppercase tracking-widest font-medium">Key Metrics</h3>
                {headlines?.period && <span className="text-xs text-gray-300">· {headlines.period}</span>}
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {priorityHeadlines.map((m: HeadlineMetric) => (
                <MetricsCard key={m.raw_name} metric={m} currency={headlines?.currency} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 flex gap-0">
          {(['overview', 'metrics', 'documents', 'comps'] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveSection(tab)}
              className={`px-5 py-3 text-sm font-medium capitalize transition-colors ${
                activeSection === tab ? 'text-gray-900 border-b-2 border-dawn' : 'text-gray-400 hover:text-gray-600 border-b-2 border-transparent'
              }`}>
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* OVERVIEW TAB */}
        {activeSection === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-8">
              {currentQuestion && answer ? (
                <div>
                  <QuestionAnswer question={currentQuestion} answer={answer} isLoading={askMutation.isPending}
                    onAskFollowup={(f) => { setSearchQuery(f); askMutation.mutate(f); }} />
                  <button onClick={() => { setCurrentQuestion(''); setAnswer(null); setSearchQuery(''); }}
                    className="mt-4 text-dawn hover:underline text-sm font-medium">← Clear search</button>
                </div>
              ) : askMutation.isPending ? (
                <div className="border border-gray-200 rounded-xl p-8 text-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-200 border-t-dawn mx-auto mb-3" />
                  <p className="text-sm text-gray-500">Searching across documents...</p>
                </div>
              ) : (
                <OnePagerSection companyId={company.id} />
              )}

              {/* Company Info */}
              {(company.competitors?.length ?? 0) > 0 && (
                <div className="border border-gray-200 rounded-xl mt-6 overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                    <h3 className="font-serif text-lg text-gray-900">Competitors</h3>
                  </div>
                  <div className="px-6 py-5 flex flex-wrap gap-1.5">
                    {company.competitors.map((c: string, i: number) => (
                      <span key={i} className="px-2.5 py-1 text-xs rounded-md bg-red-50 text-red-600 font-medium">{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="lg:col-span-4">
              <IntelligenceWidget companyId={company.id} limit={10} />
            </div>
          </div>
        )}

        {/* METRICS TAB */}
        {activeSection === 'metrics' && metricsData && (
          <div>
            {/* Group metrics by category */}
            {Object.entries(
              Object.entries(metricsData.catalog).reduce((acc, [rawName, entry]) => {
                const cat = entry.category;
                if (!acc[cat]) acc[cat] = [];
                acc[cat].push({ rawName, ...entry });
                return acc;
              }, {} as Record<string, any[]>)
            ).filter(([cat]) => cat !== 'other').map(([category, metrics]) => (
              <div key={category} className="mb-8">
                <h3 className="font-serif text-lg text-gray-900 mb-4 capitalize">{category.replace('_', ' ')}</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50/80">
                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider sticky left-0 bg-gray-50/80">Metric</th>
                        {metricsData.periods.slice(-12).map((p) => (
                          <th key={p.period} className="px-3 py-2 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap">
                            {p.period_label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {metrics.map((m: any) => (
                        <tr key={m.rawName} className="hover:bg-gray-50/50">
                          <td className="px-4 py-2.5 text-gray-700 font-medium whitespace-nowrap sticky left-0 bg-white text-xs">
                            {m.display_name}
                            {m.unit && <span className="text-gray-400 ml-1">({m.unit})</span>}
                          </td>
                          {metricsData.periods.slice(-12).map((p) => {
                            const val = p.metrics[m.rawName];
                            return (
                              <td key={p.period} className="px-3 py-2.5 text-right text-xs text-gray-600 whitespace-nowrap">
                                {val !== undefined ? (
                                  m.unit === '%' ? (Math.abs(val) <= 1 ? `${(val * 100).toFixed(1)}%` : `${val.toFixed(1)}%`)
                                  : m.unit === 'x' ? `${val.toFixed(1)}x`
                                  : m.unit === '#' ? val.toLocaleString(undefined, { maximumFractionDigits: 0 })
                                  : val.toLocaleString(undefined, { maximumFractionDigits: 1 })
                                ) : <span className="text-gray-300">—</span>}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* DOCUMENTS TAB */}
        {activeSection === 'documents' && (
          <div>
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-serif text-xl text-gray-900">Documents</h2>
              <button onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 text-sm font-semibold">
                + Add Document
              </button>
            </div>
            {allDocs.length > 0 ? (
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-gray-50/80">
                      {['Title', 'Type', 'Date', 'Status', 'Last Synced', 'Actions'].map((h) => (
                        <th key={h} className="px-6 py-3 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {allDocs.map((doc: any) => (
                      <tr key={doc.id} className="hover:bg-gray-50/50">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${doc.google_doc_id ? 'bg-blue-50' : 'bg-red-50'}`}>
                              <span className="text-xs">{doc.google_doc_id ? '📄' : '📁'}</span>
                            </div>
                            <div className="min-w-0">
                              <div className="text-sm font-medium text-gray-800 truncate">{doc.title}</div>
                              {doc.summary && <div className="text-xs text-gray-400 mt-0.5 line-clamp-1">{doc.summary}</div>}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2 py-1 text-xs rounded-md bg-gray-50 text-gray-500 font-medium">{doc.doc_type?.replace('_', ' ') ?? '—'}</span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">{formatDate(doc.document_date)}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 text-xs rounded-md font-medium ${doc.is_processed ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}`}>
                            {doc.is_processed ? 'Ready' : 'Processing'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs text-gray-400">
                          {doc.updated_at ? formatDistanceToNow(new Date(doc.updated_at), { addSuffix: true }) : '—'}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3 text-xs font-medium">
                            {doc.google_doc_id && (
                              <button onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}
                                className="text-dawn hover:text-dawn/80 disabled:opacity-50">
                                {syncMutation.isPending ? 'Syncing...' : 'Sync'}
                              </button>
                            )}
                            {doc.file_url && (
                              <a href={doc.file_url} target="_blank" rel="noopener noreferrer" className="text-dawn hover:text-dawn/80">View</a>
                            )}
                            <button onClick={() => { if (confirm(`Delete "${doc.title}"?`)) deleteMutation.mutate(doc.id); }}
                              className="text-gray-400 hover:text-red-500">Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="border border-gray-200 rounded-xl p-10 text-center">
                <p className="text-gray-400 text-sm mb-4">No documents yet</p>
                <button onClick={() => setShowAddModal(true)}
                  className="px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 text-sm font-semibold">
                  + Add Document
                </button>
              </div>
            )}
          </div>
        )}

        {/* COMPS TAB */}
        {activeSection === 'comps' && (
          <CompsTable companyId={company.id} />
        )}
      </div>

      {showAddModal && (
        <AddDocumentModal companyId={company.id} companyName={company.name}
          onSuccess={() => { setShowAddModal(false); queryClient.invalidateQueries({ queryKey: ['company-documents', id] }); queryClient.invalidateQueries({ queryKey: ['documents', id] }); }}
          onCancel={() => setShowAddModal(false)} />
      )}
    </div>
  );
}
