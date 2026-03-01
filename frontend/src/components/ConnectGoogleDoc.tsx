import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { companiesApi } from '../api';
import { ConnectGoogleDocRequest } from '../types';

interface ConnectGoogleDocProps {
  companyId: string;
  companyName: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export default function ConnectGoogleDoc({
  companyId,
  companyName,
  onSuccess,
  onCancel,
}: ConnectGoogleDocProps) {
  const [googleDocUrl, setGoogleDocUrl] = useState('');
  const [syncEnabled, setSyncEnabled] = useState(true);
  const [syncFrequency, setSyncFrequency] = useState(60);

  const queryClient = useQueryClient();

  const connectMutation = useMutation({
    mutationFn: (request: ConnectGoogleDocRequest) =>
      companiesApi.connectGoogleDoc(companyId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company', companyId] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      onSuccess?.();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!googleDocUrl.trim()) {
      alert('Please enter a Google Doc URL');
      return;
    }

    connectMutation.mutate({
      google_doc_url: googleDocUrl.trim(),
      sync_enabled: syncEnabled,
      sync_frequency_minutes: syncFrequency,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4">Connect Google Doc</h2>
        <p className="text-gray-600 mb-6">
          Connect a Google Doc for <strong>{companyName}</strong>
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Google Doc URL
            </label>
            <input
              type="url"
              value={googleDocUrl}
              onChange={(e) => setGoogleDocUrl(e.target.value)}
              placeholder="https://docs.google.com/document/d/..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Paste the full Google Doc URL here
            </p>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="sync-enabled"
              checked={syncEnabled}
              onChange={(e) => setSyncEnabled(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="sync-enabled" className="ml-2 block text-sm text-gray-700">
              Enable auto-sync
            </label>
          </div>

          {syncEnabled && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sync Frequency
              </label>
              <select
                value={syncFrequency}
                onChange={(e) => setSyncFrequency(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={30}>Every 30 minutes</option>
                <option value={60}>Every hour</option>
                <option value={360}>Every 6 hours</option>
                <option value={1440}>Daily</option>
              </select>
            </div>
          )}

          {connectMutation.isError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {connectMutation.error instanceof Error
                ? connectMutation.error.message
                : 'Failed to connect Google Doc'}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              disabled={connectMutation.isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              disabled={connectMutation.isPending}
            >
              {connectMutation.isPending ? 'Connecting...' : 'Connect & Sync Now'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

