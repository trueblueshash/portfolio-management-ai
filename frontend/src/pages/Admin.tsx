import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { companiesApi, documentsApi } from '../api';
import ConnectGoogleDoc from '../components/ConnectGoogleDoc';
import DocumentUpload from '../components/DocumentUpload';
import { CompanyWithStats } from '../types';
import { formatDistanceToNow } from 'date-fns';

type AdminTab = 'gdocs' | 'uploads' | 'scrapers' | 'settings';

export default function Admin() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<AdminTab>('gdocs');
  const [selectedCompany, setSelectedCompany] = useState<CompanyWithStats | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const { data: companies, isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.getAll(),
  });

  const syncMutation = useMutation({
    mutationFn: (companyId: string) => companiesApi.syncGoogleDoc(companyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['gdoc-status'] });
    },
  });

  const tabs = [
    { id: 'gdocs' as AdminTab, label: '📄 Google Docs', icon: '📄' },
    { id: 'uploads' as AdminTab, label: '📤 File Uploads', icon: '📤' },
    { id: 'scrapers' as AdminTab, label: '🤖 Scrapers', icon: '🤖' },
    { id: 'settings' as AdminTab, label: '⚙️ Settings', icon: '⚙️' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-dawn rounded-sm flex items-center justify-center">
                <span className="text-white font-bold text-sm">L</span>
              </div>
              <span className="text-gray-900 font-semibold">Admin Dashboard</span>
            </div>
            <button
              onClick={() => navigate('/')}
              className="text-gray-600 hover:text-gray-900"
            >
              🏠 Home
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm
                  ${
                    activeTab === tab.id
                      ? 'border-dawn text-dawn'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div>
          {/* Google Docs Tab */}
          {activeTab === 'gdocs' && (
            <div>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Google Docs Management</h2>
                  <p className="text-gray-600 mt-1">Connect and manage Google Docs for each portfolio company</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Companies can have multiple Google Docs. Each doc is synced automatically when active.
                  </p>
                </div>
              </div>

              {isLoading ? (
                <div className="animate-pulse space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-20 bg-gray-200 rounded"></div>
                  ))}
                </div>
              ) : (
                <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Company
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Last Synced
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Next Sync
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {companies?.map((company) => (
                        <tr key={company.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="font-medium text-gray-900">{company.name}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {/* Note: We check documents via API, not primary_gdoc_id */}
                            <span className="px-2 py-1 bg-moss/20 text-moss text-xs font-semibold rounded">
                              ✅ Check Documents
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {company.gdoc_last_synced
                              ? formatDistanceToNow(new Date(company.gdoc_last_synced), { addSuffix: true })
                              : 'Never'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {company.gdoc_last_synced && company.gdoc_sync_frequency_minutes
                              ? formatDistanceToNow(
                                  new Date(
                                    new Date(company.gdoc_last_synced).getTime() +
                                      company.gdoc_sync_frequency_minutes * 60 * 1000
                                  ),
                                  { addSuffix: true }
                                )
                              : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                            <button
                              onClick={() => syncMutation.mutate(company.id)}
                              disabled={syncMutation.isPending}
                              className="text-dawn hover:text-dawn/80 disabled:opacity-50"
                            >
                              Sync Now
                            </button>
                            <button
                              onClick={() => {
                                window.location.href = `/company/${company.id}`;
                              }}
                              className="text-night hover:text-night/80"
                            >
                              View Docs
                            </button>
                            <button
                              onClick={() => setSelectedCompany(company)}
                              className="text-dawn hover:text-dawn/80 font-medium"
                            >
                              Add Doc
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* File Uploads Tab */}
          {activeTab === 'uploads' && (
            <div>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">File Uploads</h2>
                  <p className="text-gray-600 mt-1">Upload reference documents (board decks, IC memos, etc.)</p>
                </div>
                <button
                  onClick={() => setShowUpload(!showUpload)}
                  className="px-6 py-3 bg-dawn text-white rounded-lg hover:bg-dawn/90 font-medium"
                >
                  {showUpload ? 'Cancel' : '+ Upload Document'}
                </button>
              </div>

              {showUpload && (
                <div className="mb-8">
                  <DocumentUpload
                    onUploadComplete={() => {
                      setShowUpload(false);
                      queryClient.invalidateQueries({ queryKey: ['documents'] });
                    }}
                  />
                </div>
              )}

              {/* File list would go here - can reuse DocumentList component */}
            </div>
          )}

          {/* Scrapers Tab */}
          {activeTab === 'scrapers' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Scraper Status</h2>
              <div className="grid md:grid-cols-2 gap-4">
                {[
                  { name: 'Google News Scraper', status: 'Active', lastRun: '2 hours ago', items: 15 },
                  { name: 'Reddit Scraper', status: 'Active', lastRun: '1 hour ago', items: 8 },
                  { name: 'Competitor Monitor', status: 'Active', lastRun: '3 hours ago', items: 12 },
                  { name: 'Company Content', status: 'Active', lastRun: '4 hours ago', items: 5 },
                ].map((scraper) => (
                  <div key={scraper.name} className="bg-white rounded-lg shadow border border-gray-200 p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-gray-900">{scraper.name}</h3>
                      <span className={`px-2 py-1 text-xs rounded ${
                        scraper.status === 'Active' ? 'bg-moss/20 text-moss' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {scraper.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p>Last run: {scraper.lastRun}</p>
                      <p>Items found: {scraper.items}</p>
                    </div>
                    <button className="mt-4 px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 text-sm font-medium">
                      Run Now
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>
              <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
                <p className="text-gray-600">App configuration settings coming soon...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Connect Google Doc Modal */}
      {selectedCompany && (
        <ConnectGoogleDoc
          companyId={selectedCompany.id}
          companyName={selectedCompany.name}
          onSuccess={() => {
            setSelectedCompany(null);
            queryClient.invalidateQueries({ queryKey: ['companies'] });
          }}
          onCancel={() => setSelectedCompany(null)}
        />
      )}
    </div>
  );
}

