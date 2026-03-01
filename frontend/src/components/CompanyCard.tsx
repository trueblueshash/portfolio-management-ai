import { useNavigate } from 'react-router-dom';
import { CompanyWithStats } from '../types';
import { formatDistanceToNow } from 'date-fns';

interface CompanyCardProps {
  company: CompanyWithStats;
}

export default function CompanyCard({ company }: CompanyCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/company/${company.id}`);
  };

  const lastUpdateText = company.last_update
    ? formatDistanceToNow(new Date(company.last_update), { addSuffix: true })
    : 'Never';

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow border border-gray-200"
    >
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-900">{company.name}</h3>
        {company.unread_count > 0 && (
          <span className="bg-red-500 text-white text-xs font-semibold px-2 py-1 rounded-full">
            {company.unread_count}
          </span>
        )}
      </div>

      <div className="space-y-2 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <span className="font-medium">Last update:</span>
          <span>{lastUpdateText}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-medium">Total items:</span>
          <span>{company.total_items}</span>
        </div>
      </div>

      {company.market_tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {company.market_tags.slice(0, 3).map((tag, idx) => (
            <span
              key={idx}
              className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
            >
              {tag}
            </span>
          ))}
          {company.market_tags.length > 3 && (
            <span className="text-xs text-gray-500">+{company.market_tags.length - 3} more</span>
          )}
        </div>
      )}
    </div>
  );
}

