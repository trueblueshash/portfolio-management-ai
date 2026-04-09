import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import DocumentUpload from '../components/DocumentUpload';
import DocumentList from '../components/DocumentList';
import DocumentQA from '../components/DocumentQA';
import GoogleDocStatus from '../components/GoogleDocStatus';
import { companiesApi } from '../api';
import LogoutButton from '../components/LogoutButton';
import { PortfolioDocument, CompanyWithStats } from '../types';

type Tab = 'ask' | 'gdocs' | 'upload';

export default function Documents() {
  const [activeTab, setActiveTab] = useState<Tab>('ask');
  const [selectedDocument, setSelectedDocument] = useState<PortfolioDocument | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.getAll(),
  });

  const tabs = [
    { id: 'ask' as Tab, label: 'Ask Questions', icon: '💬' },
    { id: 'gdocs' as Tab, label: 'Google Docs Status', icon: '📊' },
    { id: 'upload' as Tab, label: 'Upload Files', icon: '📎' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Portfolio Knowledge Hub
            </h1>
            <p className="text-gray-600">
              Ask questions, manage Google Docs, and upload reference documents
            </p>
          </div>
          <LogoutButton className="text-sm" />
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setSelectedDocument(null);
                  setShowUpload(false);
                }}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm
                  ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div>
          {activeTab === 'ask' && (
            <DocumentQA companies={companies || []} />
          )}

          {activeTab === 'gdocs' && (
            <div className="space-y-4">
              <div className="mb-6">
                <h2 className="text-xl font-semibold mb-2">Google Docs Status</h2>
                <p className="text-gray-600 text-sm">
                  Manage Google Doc connections for each portfolio company. Primary knowledge base syncs automatically.
                </p>
              </div>
              {companies && companies.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {companies.map((company) => (
                    <GoogleDocStatus key={company.id} company={company} />
                  ))}
                </div>
              ) : (
                <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
                  No companies found
                </div>
              )}
            </div>
          )}

          {activeTab === 'upload' && (
            <div>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold mb-2">Reference Files</h2>
                  <p className="text-gray-600 text-sm">
                    Upload board decks, IC memos, and other reference documents. These are stored for archival and download.
                  </p>
                </div>
                <button
                  onClick={() => setShowUpload(!showUpload)}
                  className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium"
                >
                  {showUpload ? 'Cancel' : '+ Upload Document'}
                </button>
              </div>

              {showUpload && (
                <div className="mb-8">
                  <DocumentUpload
                    onUploadComplete={(doc) => {
                      setShowUpload(false);
                      setSelectedDocument(doc);
                    }}
                  />
                </div>
              )}

              {selectedDocument ? (
                <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                  <button
                    onClick={() => setSelectedDocument(null)}
                    className="mb-4 text-blue-500 hover:underline"
                  >
                    ← Back to List
                  </button>
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">
                    {selectedDocument.title}
                  </h2>
                  <div className="space-y-2 text-gray-600">
                    <p>
                      <strong>Type:</strong> {selectedDocument.doc_type}
                    </p>
                    <p>
                      <strong>Date:</strong> {new Date(selectedDocument.document_date).toLocaleDateString()}
                    </p>
                    {selectedDocument.company_name && (
                      <p>
                        <strong>Company:</strong> {selectedDocument.company_name}
                      </p>
                    )}
                    {selectedDocument.summary && (
                      <div className="mt-4">
                        <strong>Summary:</strong>
                        <p className="mt-1">{selectedDocument.summary}</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <DocumentList onDocumentSelect={setSelectedDocument} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
