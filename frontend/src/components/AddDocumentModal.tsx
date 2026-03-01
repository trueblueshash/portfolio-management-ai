import { useState, useRef, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { companiesApi, documentsApi } from '../api';
import { DocumentType } from '../types';

interface AddDocumentModalProps {
  companyId: string;
  companyName: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

type Tab = 'gdoc' | 'upload';

// Smart filename parsing
function parseFilename(filename: string): {
  title: string;
  docType: DocumentType | null;
  date: string | null;
} {
  const result = {
    title: filename.replace(/\.[^/.]+$/, ''),
    docType: null as DocumentType | null,
    date: null as string | null,
  };

  const lower = filename.toLowerCase();

  // Detect document type
  if (lower.includes('board') || lower.includes('board deck')) {
    result.docType = 'board_deck';
  } else if (lower.includes('ic memo') || lower.includes('investment memo')) {
    result.docType = 'ic_memo';
  } else if (lower.includes('diligence') || lower.includes('dd')) {
    result.docType = 'diligence';
  } else if (lower.includes('quarterly') || lower.includes('q1') || lower.includes('q2') || lower.includes('q3') || lower.includes('q4')) {
    result.docType = 'quarterly_review';
  } else if (lower.includes('valuation')) {
    result.docType = 'valuation';
  } else if (lower.includes('thesis')) {
    result.docType = 'thesis';
  } else if (lower.includes('update')) {
    result.docType = 'update';
  }

  // Detect date
  const quarterMatch = lower.match(/q([1-4])\s*(\d{4})/);
  if (quarterMatch) {
    const [, quarter, year] = quarterMatch;
    const month = parseInt(quarter) * 3;
    result.date = `${year}-${String(month).padStart(2, '0')}-01`;
  }

  return result;
}

export default function AddDocumentModal({
  companyId,
  companyName,
  onSuccess,
  onCancel,
}: AddDocumentModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('gdoc');
  const [gdocUrl, setGdocUrl] = useState('');
  const [gdocTitle, setGdocTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [docType, setDocType] = useState<DocumentType>('board_deck');
  const [documentDate, setDocumentDate] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const queryClient = useQueryClient();

  // Google Doc connection mutation
  const connectGdocMutation = useMutation({
    mutationFn: (data: { gdoc_url: string; title?: string }) =>
      companiesApi.addCompanyDocument(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-documents', companyId] });
      queryClient.invalidateQueries({ queryKey: ['documents', companyId] });
      onSuccess?.();
    },
  });

  // File upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      return documentsApi.upload(file, {
        company_id: companyId,
        title,
        doc_type: docType,
        document_date: documentDate,
        tags: [],
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', companyId] });
      onSuccess?.();
    },
  });

  const handleGdocSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!gdocUrl.trim()) {
      alert('Please enter a Google Doc URL');
      return;
    }

    connectGdocMutation.mutate({
      gdoc_url: gdocUrl.trim(),
      title: gdocTitle.trim() || undefined,
    });
  };

  const handleFileSelect = useCallback((selectedFile: File) => {
    setFile(selectedFile);
    const parsed = parseFilename(selectedFile.name);
    setTitle(parsed.title);
    if (parsed.docType) setDocType(parsed.docType);
    if (parsed.date) setDocumentDate(parsed.date);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, [handleFileSelect]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert('Please select a file');
      return;
    }
    if (!title || !documentDate) {
      alert('Please fill in all required fields');
      return;
    }
    uploadMutation.mutate(file);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">
            Add Document to {companyName}
          </h2>
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('gdoc')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${
                  activeTab === 'gdoc'
                    ? 'border-dawn text-dawn'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              📄 Link Google Doc
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${
                  activeTab === 'upload'
                    ? 'border-dawn text-dawn'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              📁 Upload File
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div>
          {/* Google Doc Tab */}
          {activeTab === 'gdoc' && (
            <form onSubmit={handleGdocSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Google Doc URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="url"
                  value={gdocUrl}
                  onChange={(e) => setGdocUrl(e.target.value)}
                  placeholder="https://docs.google.com/document/d/..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-dawn focus:border-dawn"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Paste the full Google Doc URL here
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Title (optional - will be auto-detected if not provided)
                </label>
                <input
                  type="text"
                  value={gdocTitle}
                  onChange={(e) => setGdocTitle(e.target.value)}
                  placeholder="e.g., Board Meeting Dec'25"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-dawn focus:border-dawn"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Example: "Board Meeting Dec'25" or "Portfolio Review Nov'25"
                </p>
              </div>

              {connectGdocMutation.isError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {connectGdocMutation.error instanceof Error
                    ? connectGdocMutation.error.message
                    : 'Failed to connect Google Doc'}
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={onCancel}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                  disabled={connectGdocMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 disabled:opacity-50 font-medium"
                  disabled={connectGdocMutation.isPending}
                >
                  {connectGdocMutation.isPending ? 'Connecting...' : 'Connect & Sync'}
                </button>
              </div>
            </form>
          )}

          {/* Upload File Tab */}
          {activeTab === 'upload' && (
            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Document File <span className="text-red-500">*</span>
                </label>
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    isDragging
                      ? 'border-dawn bg-dawn/5'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.pptx"
                    onChange={handleFileInput}
                    className="hidden"
                  />
                  {file ? (
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.name}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {(file.size / 1024 / 1024).toFixed(1)} MB
                      </p>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                        className="mt-2 text-sm text-red-600 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-600">
                        Drag and drop a file here, or click to browse
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        PDF, DOCX, PPTX only
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-dawn focus:border-dawn"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Document Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value as DocumentType)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-dawn focus:border-dawn"
                    required
                  >
                    <option value="board_deck">Board Deck</option>
                    <option value="ic_memo">IC Memo</option>
                    <option value="diligence">Due Diligence</option>
                    <option value="quarterly_review">Quarterly Review</option>
                    <option value="update">Update</option>
                    <option value="general">General</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Document Date <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={documentDate}
                    onChange={(e) => setDocumentDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-dawn focus:border-dawn"
                    required
                  />
                </div>
              </div>

              {uploadMutation.isError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {uploadMutation.error instanceof Error
                    ? uploadMutation.error.message
                    : 'Failed to upload document'}
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={onCancel}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                  disabled={uploadMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 disabled:opacity-50 font-medium"
                  disabled={uploadMutation.isPending || !file}
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Upload & Process'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
