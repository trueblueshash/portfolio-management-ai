import { useState, type ReactNode } from 'react';

const STORAGE_KEY = 'app_api_key';

export default function LoginGate({ children }: { children: ReactNode }) {
  const [hasKey, setHasKey] = useState(() => typeof window !== 'undefined' && !!localStorage.getItem(STORAGE_KEY));
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch('/api/companies?limit=1', {
        headers: { 'X-API-Key': password },
      });
      if (!res.ok) {
        setError('Invalid password. Please try again.');
        setSubmitting(false);
        return;
      }
      localStorage.setItem(STORAGE_KEY, password);
      setHasKey(true);
    } catch {
      setError('Could not reach the server. Check your connection.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!hasKey) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center px-4">
        <div className="w-full max-w-md border border-gray-200 rounded-2xl shadow-sm p-8">
          <div className="flex items-center justify-center gap-2 mb-6">
            <div className="w-10 h-10 bg-dawn rounded-lg flex items-center justify-center">
              <span className="text-white font-bold">L</span>
            </div>
          </div>
          <h1 className="font-serif text-2xl text-gray-900 text-center mb-1">Lightspeed</h1>
          <p className="text-center text-sm text-gray-500 mb-8">Portfolio Intelligence Platform</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="app-password" className="sr-only">
                Password
              </label>
              <input
                id="app-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter access key"
                className="w-full px-4 py-3 text-sm border border-gray-200 rounded-xl focus:outline-none focus:border-dawn focus:ring-1 focus:ring-dawn/20"
              />
            </div>
            {error && <p className="text-sm text-red-600 text-center">{error}</p>}
            <button
              type="submit"
              disabled={submitting || !password.trim()}
              className="w-full py-3 rounded-xl text-sm font-semibold text-white bg-dawn hover:bg-dawn/90 disabled:opacity-50 transition-colors"
            >
              {submitting ? 'Checking…' : 'Enter'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
