import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi, companiesApi } from '../api';
import { DocumentType, PortfolioDocument, CompanyWithStats } from '../types';

interface DocumentUploadProps {
  onUploadComplete?: (document: PortfolioDocument) => void;
}

const DOCUMENT_TYPES: { value: DocumentType; label: string; icon: string }[] = [
  { value: 'board_deck', label: 'Board Deck', icon: '📊' },
  { value: 'ic_memo', label: 'IC Memo', icon: '📝' },
  { value: 'diligence', label: 'Due Diligence Report', icon: '🔍' },
  { value: 'quarterly_review', label: 'Quarterly Review', icon: '📅' },
  { value: 'valuation', label: 'Valuation Analysis', icon: '💰' },
  { value: 'thesis', label: 'Investment Thesis', icon: '💡' },
  { value: 'update', label: 'Portfolio Company Update', icon: '📰' },
  { value: 'general', label: 'General Document', icon: '📄' },
];

// Smart filename parsing
function parseFilename(filename: string): {
  title: string;
  companyName: string | null;
  docType: DocumentType | null;
  date: string | null;
  tags: string[];
} {
  const result = {
    title: filename.replace(/\.[^/.]+$/, ''), // Remove extension
    companyName: null as string | null,
    docType: null as DocumentType | null,
    date: null as string | null,
    tags: [] as string[],
  };

  const lower = filename.toLowerCase();

  // Detect company name (check against common patterns)
  const companyPatterns = [
    /(acceldata|zluri|scrut|triomics|emergent|sarvam|exponent|portkey|pintu|airbound|pixxel|rattle|thena|logicflo|coral|qure|gushworks|pepper|aqqrue|bridgetown|yellow|darwinbox)/i,
  ];
  for (const pattern of companyPatterns) {
    const match = filename.match(pattern);
    if (match) {
      result.companyName = match[1];
      break;
    }
  }

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

  // Detect date/quarter
  const quarterMatch = lower.match(/q([1-4])\s*(\d{4})/);
  if (quarterMatch) {
    const [, quarter, year] = quarterMatch;
    const month = parseInt(quarter) * 3;
    result.date = `${year}-${String(month).padStart(2, '0')}-01`;
    result.tags.push(`Q${quarter} ${year}`);
  } else {
    const yearMatch = lower.match(/(\d{4})/);
    if (yearMatch) {
      result.tags.push(yearMatch[1]);
    }
  }

  return result;
}

export default function DocumentUpload({ onUploadComplete }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [companyId, setCompanyId] = useState<string>('');
  const [title, setTitle] = useState('');
  const [docType, setDocType] = useState<DocumentType>('general');
  const [documentDate, setDocumentDate] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [notes, setNotes] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const queryClient = useQueryClient();

  // Fetch companies for dropdown
  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: companiesApi.getAll,
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      return documentsApi.upload(file, {
        company_id: companyId || undefined,
        title,
        doc_type: docType,
        document_date: documentDate,
        tags,
        notes: notes || undefined,
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      if (onUploadComplete) {
        onUploadComplete(data);
      }
      // Reset form
      setFile(null);
      setTitle('');
      setCompanyId('');
      setDocType('general');
      setDocumentDate('');
      setTags([]);
      setNotes('');
      setShowPreview(false);
    },
  });

  const handleFileSelect = useCallback((selectedFile: File) => {
    setFile(selectedFile);

    // Auto-fill from filename
    const parsed = parseFilename(selectedFile.name);
    setTitle(parsed.title);

    if (parsed.companyName && companies) {
      const company = companies.find(
        (c) => c.name.toLowerCase().includes(parsed.companyName!.toLowerCase())
      );
      if (company) {
        setCompanyId(company.id);
      }
    }

    if (parsed.docType) {
      setDocType(parsed.docType);
    }

    if (parsed.date) {
      setDocumentDate(parsed.date);
    }

    if (parsed.tags.length > 0) {
      setTags(parsed.tags);
    }

    setShowPreview(true);
  }, [companies]);

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

  const handleTagAdd = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleTagRemove = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove));
  };

  const handleSubmit = async (e: React.FormEvent) => {
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

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Upload Document</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Upload */}
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
                ? 'border-blue-500 bg-blue-50'
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
                  {formatFileSize(file.size)} • {file.type}
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    setShowPreview(false);
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

        {/* Auto-fill Preview */}
        {showPreview && file && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm font-medium text-blue-900 mb-2">
              ✨ Auto-detected from filename:
            </p>
            <div className="text-sm text-blue-800 space-y-1">
              {companyId && (
                <p>
                  Company: {companies?.find((c) => c.id === companyId)?.name} ✓
                </p>
              )}
              {docType && (
                <p>
                  Type:{' '}
                  {DOCUMENT_TYPES.find((t) => t.value === docType)?.label} ✓
                </p>
              )}
              {documentDate && <p>Date: {documentDate} ✓</p>}
              {tags.length > 0 && <p>Tags: {tags.join(', ')} ✓</p>}
            </div>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => setShowPreview(false)}
                className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Looks Good
              </button>
              <button
                type="button"
                onClick={() => setShowPreview(false)}
                className="text-xs px-3 py-1 bg-white text-blue-600 border border-blue-600 rounded hover:bg-blue-50"
              >
                Edit
              </button>
            </div>
          </div>
        )}

        {/* Company Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Company
          </label>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">General/Fund-level</option>
            {companies?.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
          {companyId && (
            <p className="mt-1 text-xs text-gray-500">
              Documents are linked to this company for search and organization
            </p>
          )}
        </div>

        {/* Document Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Document Type <span className="text-red-500">*</span>
          </label>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value as DocumentType)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          >
            {DOCUMENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.icon} {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Document Date */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Document Date <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            value={documentDate}
            onChange={(e) => setDocumentDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tags
          </label>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleTagAdd();
                }
              }}
              placeholder="Add tag and press Enter"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="button"
              onClick={handleTagAdd}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Add
            </button>
          </div>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => handleTagRemove(tag)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Notes (Internal)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Internal notes about this document..."
          />
        </div>

        {/* Submit Button */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={uploadMutation.isPending || !file}
            className="flex-1 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>

        {/* Upload Progress */}
        {uploadMutation.isPending && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              <span>Uploading file...</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-500 h-2 rounded-full animate-pulse" style={{ width: '30%' }}></div>
            </div>
          </div>
        )}

        {uploadMutation.isSuccess && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
            ✅ Document uploaded successfully! Processing in background...
          </div>
        )}

        {uploadMutation.isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            ❌ Error uploading document. Please try again.
          </div>
        )}
      </form>
    </div>
  );
}

