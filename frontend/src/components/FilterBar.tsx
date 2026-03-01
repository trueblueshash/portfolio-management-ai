import { useFiltersStore } from '../store/filters';

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'product', label: 'Product' },
  { value: 'gtm', label: 'GTM' },
  { value: 'traction', label: 'Traction' },
  { value: 'market_position', label: 'Market Position' },
  { value: 'corporate', label: 'Corporate' },
  { value: 'regulatory', label: 'Regulatory' },
];

const SOURCE_TYPES = [
  { value: '', label: 'All Sources' },
  { value: 'blog', label: 'Blog' },
  { value: 'twitter', label: 'Twitter' },
  { value: 'g2', label: 'G2' },
  { value: 'reddit', label: 'Reddit' },
];

export default function FilterBar() {
  const { filters, setFilters, resetFilters } = useFiltersStore();

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-6 border border-gray-200">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Date From
          </label>
          <input
            type="date"
            value={filters.date_from || ''}
            onChange={(e) => setFilters({ date_from: e.target.value || undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Date To
          </label>
          <input
            type="date"
            value={filters.date_to || ''}
            onChange={(e) => setFilters({ date_to: e.target.value || undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Category
          </label>
          <select
            value={filters.category || ''}
            onChange={(e) => setFilters({ category: e.target.value || undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Source Type
          </label>
          <select
            value={filters.source_type || ''}
            onChange={(e) => setFilters({ source_type: e.target.value || undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {SOURCE_TYPES.map((source) => (
              <option key={source.value} value={source.value}>
                {source.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-end">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.is_read === false}
              onChange={(e) => setFilters({ is_read: e.target.checked ? false : undefined })}
              className="w-4 h-4 text-blue-500 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">Only unread</span>
          </label>
        </div>

        <div className="flex items-end">
          <button
            onClick={resetFilters}
            className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Reset Filters
          </button>
        </div>
      </div>
    </div>
  );
}

