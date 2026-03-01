import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { documentsApi } from '../api';
import { DocumentQuestionRequest, DocumentQuestionResponse, CompanyWithStats } from '../types';

interface DocumentQAProps {
  companies?: CompanyWithStats[];
}

export default function DocumentQA({ companies = [] }: DocumentQAProps) {
  const [question, setQuestion] = useState('');
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('');
  const [searchScope, setSearchScope] = useState<'primary_only' | 'all' | 'reference_only'>('primary_only');
  const [recentQuestions, setRecentQuestions] = useState<string[]>([]);

  const askMutation = useMutation({
    mutationFn: (request: DocumentQuestionRequest) => documentsApi.ask(request),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    askMutation.mutate({
      question: question.trim(),
      company_id: selectedCompanyId || undefined,
      search_scope: searchScope,
    });

    // Add to recent questions
    if (!recentQuestions.includes(question.trim())) {
      setRecentQuestions([question.trim(), ...recentQuestions.slice(0, 4)]);
    }
  };

  const handleRecentQuestionClick = (q: string) => {
    setQuestion(q);
    askMutation.mutate({
      question: q,
      company_id: selectedCompanyId || undefined,
      search_scope: searchScope,
    });
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">Ask Questions</h2>
        <p className="text-gray-600 mb-6">
          Ask anything about your portfolio companies. Answers come from Google Docs and uploaded documents.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Question
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What were Acceldata's Q3 ARR numbers?"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Company (optional)
              </label>
              <select
                value={selectedCompanyId}
                onChange={(e) => setSelectedCompanyId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Companies</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Scope
              </label>
              <select
                value={searchScope}
                onChange={(e) => setSearchScope(e.target.value as any)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="primary_only">Primary (Google Docs)</option>
                <option value="all">All Sources</option>
                <option value="reference_only">Reference Files Only</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={askMutation.isPending || !question.trim()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {askMutation.isPending ? 'Asking...' : 'Ask'}
          </button>
        </form>

        {recentQuestions.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-gray-600 mb-2">Recent questions:</p>
            <div className="flex flex-wrap gap-2">
              {recentQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleRecentQuestionClick(q)}
                  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {askMutation.isSuccess && askMutation.data && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold">Answer</h3>
              {askMutation.data.confidence > 0 && (
                <span className="text-sm text-gray-600">
                  Confidence: {Math.round(askMutation.data.confidence * 100)}%
                </span>
              )}
            </div>
            <div className="prose max-w-none">
              <p className="whitespace-pre-wrap">{askMutation.data.answer}</p>
            </div>
          </div>

          {askMutation.data.sources && askMutation.data.sources.length > 0 && (
            <div className="mt-6 border-t pt-4">
              <h4 className="font-semibold mb-3">Sources:</h4>
              <div className="space-y-2">
                {askMutation.data.sources.map((source, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-gray-500">📄</span>
                    <div>
                      <p className="font-medium">
                        {source.document_title}
                        {source.company_name && ` - ${source.company_name}`}
                      </p>
                      {source.chunk_text && (
                        <p className="text-gray-600 text-xs mt-1 line-clamp-2">
                          {source.chunk_text}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {askMutation.isError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {askMutation.error instanceof Error
            ? askMutation.error.message
            : 'Failed to get answer. Please try again.'}
        </div>
      )}
    </div>
  );
}

