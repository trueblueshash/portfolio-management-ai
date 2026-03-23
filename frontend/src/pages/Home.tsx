import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { companiesApi } from '../api';

export default function Home() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.getAll(),
  });

  const filteredCompanies = companies?.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const topCompanies = companies?.slice(0, 8) || [];

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-dawn rounded flex items-center justify-center">
              <span className="text-white font-bold text-sm">L</span>
            </div>
            <span className="text-gray-900 font-semibold text-sm">Lightspeed India</span>
            <span className="text-gray-400 text-sm font-light">/ Portfolio Intelligence</span>
          </div>
          <button onClick={() => navigate('/admin')} className="text-gray-400 hover:text-gray-600 text-sm">
            Settings
          </button>
        </div>
      </header>

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 pt-24 pb-16 text-center">
        <h1 className="font-serif text-5xl md:text-6xl text-gray-900 mb-5 leading-tight tracking-tight">
          Portfolio Intelligence
        </h1>
        <p className="text-lg text-gray-500 font-light max-w-lg mx-auto leading-relaxed mb-12">
          Real-time insights across your portfolio companies. Track performance, monitor markets, and surface what matters.
        </p>

        {/* Search */}
        <form onSubmit={(e) => { e.preventDefault(); if (filteredCompanies.length === 1) navigate(`/company/${filteredCompanies[0].id}`); }} className="relative mb-12">
          <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
            <svg className="w-5 h-5 text-gray-300" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35" strokeLinecap="round"/></svg>
          </div>
          <input
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setShowSuggestions(true); }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="Search for a company..."
            className="w-full pl-14 pr-6 py-4 text-base border border-gray-200 rounded-xl focus:outline-none focus:border-dawn focus:ring-1 focus:ring-dawn/20 bg-gray-50/50 placeholder:text-gray-400"
          />
          {showSuggestions && searchQuery && filteredCompanies.length > 0 && (
            <div className="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-lg max-h-80 overflow-y-auto">
              {filteredCompanies.map((c) => (
                <button key={c.id} type="button" onClick={() => navigate(`/company/${c.id}`)}
                  className="w-full px-5 py-3.5 text-left hover:bg-gray-50 border-b border-gray-50 last:border-0">
                  <div className="font-medium text-gray-900 text-sm">{c.name}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{c.market_tags?.slice(0, 3).join(' · ') ?? ''}</div>
                </button>
              ))}
            </div>
          )}
        </form>

        {/* Company chips */}
        {topCompanies.length > 0 && (
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-widest font-medium mb-4">Portfolio Companies</p>
            <div className="flex flex-wrap justify-center gap-2">
              {topCompanies.map((c) => (
                <button key={c.id} onClick={() => navigate(`/company/${c.id}`)}
                  className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:border-dawn hover:text-dawn transition-all">
                  {c.name}
                </button>
              ))}
              {companies && companies.length > 8 && (
                <span className="px-4 py-2 text-sm text-gray-400">+{companies.length - 8} more</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Features */}
      <div className="border-t border-gray-100">
        <div className="max-w-4xl mx-auto px-6 py-20 grid md:grid-cols-3 gap-12">
          {[
            { title: "Portfolio Tracking", desc: "Real-time MIS metrics — ARR, growth, burn, efficiency — synced from Salesforce." },
            { title: "Market Intelligence", desc: "Competitor moves, funding rounds, product launches from news, Reddit, and reviews." },
            { title: "AI-Powered Q&A", desc: "Ask questions about any company and get sourced answers from board decks and portfolio updates." },
          ].map((f) => (
            <div key={f.title}>
              <h3 className="font-serif text-xl text-gray-900 mb-2">{f.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <footer className="border-t border-gray-100 py-8">
        <p className="text-xs text-gray-400 text-center">Portfolio Intelligence Platform · Lightspeed India Partners</p>
      </footer>
    </div>
  );
}
