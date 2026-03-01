import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { companiesApi } from '../api';
import { CompanyWithStats } from '../types';

export default function Home() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const { data: companies, isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.getAll(),
  });

  const filteredCompanies = companies?.filter((company) =>
    company.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const topCompanies = companies?.slice(0, 8) || [];

  const handleCompanySelect = (companyId: string) => {
    navigate(`/company/${companyId}`);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (filteredCompanies.length === 1) {
      handleCompanySelect(filteredCompanies[0].id);
    }
  };

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
              <span className="text-gray-900 font-semibold">Lightspeed</span>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/admin')}
                className="text-gray-600 hover:text-gray-900"
              >
                ⚙️ Admin
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Portfolio Intelligence Platform
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Real-time insights across your portfolio
          </p>

          {/* Search Bar */}
          <form onSubmit={handleSearchSubmit} className="relative mb-8">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                placeholder="🔍 Search for a company..."
                className="w-full px-6 py-4 text-lg border-2 border-gray-300 rounded-lg focus:outline-none focus:border-dawn focus:ring-2 focus:ring-dawn/20"
              />
              {showSuggestions && filteredCompanies.length > 0 && (
                <div className="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto">
                  {filteredCompanies.map((company) => (
                    <button
                      key={company.id}
                      type="button"
                      onClick={() => handleCompanySelect(company.id)}
                      className="w-full px-6 py-4 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0"
                    >
                      <div className="font-semibold text-gray-900">{company.name}</div>
                      <div className="text-sm text-gray-500 mt-1">
                        {company.market_tags.slice(0, 3).join(' • ')}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </form>

          {/* Popular Companies */}
          {topCompanies.length > 0 && (
            <div>
              <p className="text-sm text-gray-600 mb-3">Popular:</p>
              <div className="flex flex-wrap justify-center gap-2">
                {topCompanies.map((company) => (
                  <button
                    key={company.id}
                    onClick={() => handleCompanySelect(company.id)}
                    className="px-4 py-2 bg-white border border-gray-300 rounded-full text-sm font-medium text-gray-700 hover:bg-dawn hover:text-white hover:border-dawn transition-colors"
                  >
                    {company.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Features Section */}
        <div className="grid md:grid-cols-3 gap-6 mt-16">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
            <div className="text-4xl mb-4">📊</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Track Your Portfolio
            </h3>
            <p className="text-gray-600">
              Get real-time updates on your portfolio companies, competitors, and market trends. Ask questions and get instant answers from board decks and market data.
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Market Intelligence
            </h3>
            <p className="text-gray-600">
              Monitor competitor moves, product launches, funding rounds, and customer sentiment across news, Reddit, and social media.
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              AI-Powered Insights
            </h3>
            <p className="text-gray-600">
              Ask natural language questions about any company: "What's Acceldata's current ARR?" or "What went well in Q3?" Get answers with source citations.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

