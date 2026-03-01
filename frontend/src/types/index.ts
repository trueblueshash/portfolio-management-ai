export interface Company {
  id: string;
  name: string;
  market_tags: string[];
  competitors: string[];
  sources: {
    blog?: string;
    twitter?: string;
    linkedin?: string;
  };
  created_at: string;
}

export interface CompanyWithStats extends Company {
  unread_count: number;
  total_items: number;
  last_update: string | null;
  primary_gdoc_id?: string | null;
  primary_gdoc_url?: string | null;
  gdoc_sync_enabled?: boolean;
  gdoc_last_synced?: string | null;
  gdoc_sync_frequency_minutes?: number;
}

export interface IntelligenceItem {
  id: string;
  company_id: string;
  title: string;
  summary: string | null;
  full_content: string | null;
  source_type: string;
  source_url: string;
  result_category: string | null;
  published_date: string | null;
  captured_date: string;
  relevance_score: number;
  is_read: boolean;
  metadata: Record<string, any>;
}

export interface IntelligenceFilters {
  date_from?: string;
  date_to?: string;
  category?: string;
  source_type?: string;
  is_read?: boolean;
}

export type DocumentType =
  | 'board_deck'
  | 'ic_memo'
  | 'diligence'
  | 'quarterly_review'
  | 'valuation'
  | 'thesis'
  | 'update'
  | 'general';

export interface PortfolioDocument {
  id: string;
  company_id: string | null;
  company_name: string | null;
  title: string;
  doc_type: DocumentType;
  document_date: string;
  file_path: string | null;
  file_url: string | null;
  file_name: string;
  file_size_bytes: number | null;
  mime_type: string;
  full_text: string | null;
  summary: string | null;
  tags: string[];
  notes: string | null;
  is_processed: boolean;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
  processing_status: 'processed' | 'processing' | 'failed' | 'pending';
  is_primary_source?: boolean;
  google_doc_id?: string | null;
  requires_processing?: boolean;
  storage_purpose?: string;
}

export interface DocumentUploadRequest {
  company_id?: string;
  title: string;
  doc_type: DocumentType;
  document_date: string;
  tags?: string[];
  notes?: string;
}

export interface DocumentListResponse {
  documents: PortfolioDocument[];
  total: number;
}

export interface DocumentSearchRequest {
  query: string;
  company_id?: string;
  doc_type?: string;
  limit?: number;
}

export interface DocumentSearchResult {
  chunk_text: string;
  document_title: string;
  company_name: string | null;
  page_number: number | null;
  similarity_score: number;
  document_id: string;
}

export interface DocumentQuestionRequest {
  question: string;
  company_id?: string;
  doc_type?: string;
  search_scope?: 'primary_only' | 'all' | 'reference_only';
}

export interface DocumentCitation {
  document_title: string;
  company_name: string | null;
  page_number: number | null;
  chunk_text: string;
}

export interface DocumentQuestionResponse {
  answer: string;
  sources: DocumentCitation[];
  confidence: number;
}

export interface ConnectGoogleDocRequest {
  google_doc_url: string;
  sync_enabled: boolean;
  sync_frequency_minutes?: number;
}

export interface GoogleDocStatus {
  connected: boolean;
  doc_id?: string;
  doc_url?: string;
  sync_enabled?: boolean;
  last_synced?: string | null;
  next_sync?: string | null;
  sync_frequency_minutes?: number;
  message?: string;
}

