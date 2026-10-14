/**
 * Centralized Typed API Client for DocuMind AI Backend.
 *
 * Provides end-to-end typed contracts for document ingestion, retrieval,
 * status checks, deletion, and search.
 */

export interface APIResponse<T> {
  success: boolean;
  message: string;
  data: T;
  error_code?: string;
  details?: Array<{ field?: string; issue: string }> | null;
  timestamp?: string;
  path?: string;
}

export interface DocumentMetadata {
  id: string;
  filename: string;
  file_type: "pdf" | "docx" | "txt" | string;
  file_size_bytes: number;
  status: "uploaded" | "processing" | "ready" | "indexed" | "failed" | string;
  uploaded_at?: string;
  created_at?: string;
  updated_at?: string;
  processed_at?: string | null;
  page_count?: number | null;
  section_count?: number | null;
  word_count?: number | null;
  character_count?: number | null;
  chunk_count?: number | null;
  has_extractable_text?: boolean;
  error_message?: string | null;
  summary?: string | null;
}

export interface DocumentContentPage {
  page_number: number;
  text: string;
  char_count: number;
  word_count: number;
}

export interface DocumentContentSection {
  section_index: number;
  heading?: string | null;
  text: string;
  char_count: number;
  word_count: number;
}

export interface DocumentDetail extends DocumentMetadata {
  pages?: DocumentContentPage[] | null;
  sections?: DocumentContentSection[] | null;
  raw_text_preview?: string | null;
}

export interface DocumentListResponse {
  total: number;
  limit: number;
  offset: number;
  documents: DocumentMetadata[];
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  status: string;
  uploaded_at?: string;
  page_count?: number | null;
  section_count?: number | null;
  word_count?: number | null;
  character_count?: number | null;
  chunk_count?: number | null;
  message: string;
}

export interface DocumentDeleteResponse {
  id?: string;
  document_id?: string;
  filename: string;
  deleted: boolean;
  message: string;
}

export interface DocumentValidateResponse {
  filename: string;
  is_valid: boolean;
  file_type: string;
  message: string;
}

export interface IndexStatusResponse {
  total_vectors: number;
  total_documents: number;
  dimension: number;
  metric: string;
  ready: boolean;
  index_file_exists: boolean;
  metadata_file_exists: boolean;
}

export interface ChatSource {
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  page_number?: number | null;
  section_index?: number | null;
  heading?: string | null;
  text: string;
  score: number;
}

export interface ChatRequest {
  question: string;
  document_ids?: string[] | null;
  top_k?: number;
  score_threshold?: number;
  temperature?: number;
  max_tokens?: number;
}

export interface ChatResponse {
  answer: string;
  question: string;
  sources: ChatSource[];
  model: string;
  evidence_found: boolean;
  total_sources: number;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  } | null;
}

export interface ChatStatusResponse {
  ready: boolean;
  model: string;
  groq_configured: boolean;
  max_context_chars: number;
  default_top_k: number;
}

export class ApiError extends Error {
  status: number;
  errorCode: string;
  details?: Array<{ field?: string; issue: string }> | null;

  constructor(
    message: string,
    status: number = 500,
    errorCode: string = "INTERNAL_ERROR",
    details: Array<{ field?: string; issue: string }> | null = null
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
    this.details = details;
  }
}

/**
 * Resolve the backend base URL from environment or fallback default.
 */
export function getBackendBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string") {
    // Strip trailing /api or slash to get origin
    return envUrl.replace(/\/api\/?$/, "").replace(/\/$/, "");
  }
  return "http://127.0.0.1:8000";
}

/**
 * Standard HTTP JSON request helper with typed error propagation.
 */
async function request<T>(
  endpoint: string,
  options: RequestInit & { timeoutMs?: number } = {},
  baseUrl: string = getBackendBaseUrl()
): Promise<APIResponse<T>> {
  const url = `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const timeoutMs = options.timeoutMs ?? 45000;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      signal: options.signal || controller.signal,
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
    });
  } catch (err: any) {
    if (err?.name === "AbortError" || controller.signal.aborted) {
      throw new ApiError(
        `Request to ${endpoint} timed out after ${timeoutMs / 1000}s. Backend took too long to respond.`,
        408,
        "REQUEST_TIMEOUT"
      );
    }
    throw new ApiError(
      `Cannot connect to backend server at ${baseUrl}. Ensure FastAPI is running on port 8000.`,
      0,
      "NETWORK_CONNECTION_ERROR"
    );
  } finally {
    clearTimeout(timer);
  }

  let json: any = null;
  try {
    json = await response.json();
  } catch {
    if (!response.ok) {
      throw new ApiError(
        `Server returned HTTP ${response.status}: ${response.statusText}`,
        response.status,
        `HTTP_${response.status}`
      );
    }
  }

  if (!response.ok || (json && json.success === false)) {
    const errorMsg =
      json?.message ||
      json?.detail ||
      `Request failed with HTTP status ${response.status}`;
    const errorCode = json?.error_code || `HTTP_${response.status}`;
    throw new ApiError(errorMsg, response.status, errorCode, json?.details);
  }

  return json as APIResponse<T>;
}

export const api = {
  /**
   * Fetch paginated list of documents with optional status filtering.
   */
  async getDocuments(
    params: { limit?: number; offset?: number; status?: string } = {},
    baseUrl?: string
  ): Promise<DocumentListResponse> {
    const searchParams = new URLSearchParams();
    if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
    if (params.offset !== undefined) searchParams.set("offset", String(params.offset));
    if (params.status && params.status !== "all") searchParams.set("status", params.status);

    const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
    const res = await request<DocumentListResponse>(
      `/api/v1/documents${query}`,
      { method: "GET" },
      baseUrl
    );
    return res.data;
  },

  /**
   * Fetch complete document detail including pages and extracted sections.
   */
  async getDocumentDetail(
    documentId: string,
    baseUrl?: string
  ): Promise<DocumentDetail> {
    const res = await request<DocumentDetail>(
      `/api/v1/documents/${encodeURIComponent(documentId)}`,
      { method: "GET" },
      baseUrl
    );
    return res.data;
  },

  /**
   * Upload a document via multipart/form-data with progress reporting.
   */
  uploadDocument(
    file: File,
    onProgress?: (percent: number) => void,
    baseUrl: string = getBackendBaseUrl()
  ): Promise<DocumentUploadResponse> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const url = `${baseUrl}/api/v1/documents/upload`;

      xhr.open("POST", url, true);
      xhr.setRequestHeader("Accept", "application/json");

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        let json: any = null;
        try {
          json = JSON.parse(xhr.responseText);
        } catch {
          // ignore parse error
        }

        if (xhr.status >= 200 && xhr.status < 300 && json?.success) {
          resolve(json.data as DocumentUploadResponse);
        } else {
          const message =
            json?.message ||
            json?.detail ||
            `Upload failed with HTTP ${xhr.status}`;
          const errorCode = json?.error_code || `HTTP_${xhr.status}`;
          reject(new ApiError(message, xhr.status, errorCode, json?.details));
        }
      };

      xhr.onerror = () => {
        reject(
          new ApiError(
            `Network error uploading ${file.name}. Ensure backend is online.`,
            0,
            "NETWORK_ERROR"
          )
        );
      };

      xhr.timeout = 120000; // 120 seconds upload timeout
      xhr.ontimeout = () => {
        reject(
          new ApiError(
            `Upload of ${file.name} timed out after 120 seconds.`,
            408,
            "UPLOAD_TIMEOUT"
          )
        );
      };

      const formData = new FormData();
      formData.append("file", file);
      xhr.send(formData);
    });
  },

  /**
   * Permanently delete a document and purge vector embeddings.
   */
  async deleteDocument(
    documentId: string,
    baseUrl?: string
  ): Promise<DocumentDeleteResponse> {
    const res = await request<DocumentDeleteResponse>(
      `/api/v1/documents/${encodeURIComponent(documentId)}`,
      { method: "DELETE" },
      baseUrl
    );
    return res.data;
  },

  /**
   * Pre-validate document metadata before uploading.
   */
  async validateDocument(
    filename: string,
    fileSizeBytes: number,
    baseUrl?: string
  ): Promise<DocumentValidateResponse> {
    const res = await request<DocumentValidateResponse>(
      `/api/v1/documents/validate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, file_size_bytes: fileSizeBytes }),
      },
      baseUrl
    );
    return res.data;
  },

  /**
   * Inspect vector index status.
   */
  async getIndexStatus(baseUrl?: string): Promise<IndexStatusResponse> {
    const res = await request<IndexStatusResponse>(
      `/api/v1/search/status`,
      { method: "GET" },
      baseUrl
    );
    return res.data;
  },

  /**
   * Ask question grounded in indexed documents using Groq Cloud LLM and FAISS.
   */
  async askQuestion(
    req: ChatRequest,
    baseUrl?: string
  ): Promise<ChatResponse> {
    const res = await request<ChatResponse>(
      `/api/v1/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      },
      baseUrl
    );
    return res.data;
  },

  /**
   * Inspect Groq LLM service status and configuration.
   */
  async getChatStatus(baseUrl?: string): Promise<ChatStatusResponse> {
    const res = await request<ChatStatusResponse>(
      `/api/v1/chat/status`,
      { method: "GET" },
      baseUrl
    );
    return res.data;
  },
};
