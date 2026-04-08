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

export interface MetricRow {
  metric_name: string;
  current_value: string;
  previous_value: string;
  change_pct: string;
  trend: "up" | "down" | "flat";
  unit: string;
}

export interface OnePager {
  id: string;
  company_id: string;
  generated_at: string;
  generated_by: "ai" | "manual";
  is_latest: boolean;
  period_label: string;
  stance: "green" | "yellow" | "red";
  stance_summary: string;
  next_milestone: string;
  metrics_table: MetricRow[];
  performance_narrative: string[];
  working_well: string[];
  needs_improvement: string[];
  value_creation: string[];
  data_sources: {
    metrics_periods: string[];
    documents_used: boolean | Array<{ id: string; title: string; date: string | null }>;
    intelligence_count: number;
  };
  last_edited_at: string | null;
  edit_history?: Array<{ field: string; edited_at: string; old_value?: any; new_value?: any }>;
}

export interface PublicComp {
  id: string;
  company_id: string;
  comp_name: string;
  ticker: string | null;
  is_portfolio_company: boolean;
  revenue_ttm_millions: number | null;
  revenue_currency: string;
  revenue_growth_pct: number | null;
  gross_margin_pct: number | null;
  operating_margin_pct: number | null;
  fcf_margin_pct: number | null;
  sm_pct_of_revenue: number | null;
  rd_pct_of_revenue: number | null;
  rule_of_40: number | null;
  nrr_pct: number | null;
  employees: number | null;
  revenue_per_employee_k: number | null;
  data_source: string;
  fiscal_period: string | null;
  fetched_at: string | null;
}

