import { Link } from 'react-router-dom';
import CompanyList from '../components/CompanyList';

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Portfolio Intelligence
            </h1>
            <p className="text-gray-600">
              Monitor intelligence for 23 portfolio companies
            </p>
          </div>
          <Link
            to="/documents"
            className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium"
          >
            📄 Documents
          </Link>
        </div>
        <CompanyList />
      </div>
    </div>
  );
}

