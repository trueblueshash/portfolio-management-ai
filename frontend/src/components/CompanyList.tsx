import { useQuery } from '@tanstack/react-query';
import { companiesApi } from '../api/companies';
import CompanyCard from './CompanyCard';
import { useState } from 'react';

export default function CompanyList() {
  const [searchQuery, setSearchQuery] = useState('');

  const { data: companies, isLoading, error } = useQuery({
    queryKey: ['companies'],
    queryFn: companiesApi.getAll,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        Error loading companies. Please try again.
      </div>
    );
  }

  const filteredCompanies = companies?.filter((company) =>
    company.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div>
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search companies..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {filteredCompanies.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          {searchQuery ? 'No companies found matching your search.' : 'No companies found.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCompanies.map((company) => (
            <CompanyCard key={company.id} company={company} />
          ))}
        </div>
      )}
    </div>
  );
}

