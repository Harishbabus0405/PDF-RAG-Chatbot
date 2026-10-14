/**
 * Mock data definitions for DocuMind AI Phase 3 Frontend.
 *
 * NOTE: These documents and activities represent sample dataset structures
 * to facilitate UI testing and layout verification. Upload, chunking, and Groq
 * streaming will be integrated with the backend in subsequent phases.
 */

export interface MockDocument {
  id: string;
  filename: string;
  fileType: "pdf" | "docx" | "txt";
  fileSizeBytes: number;
  uploadedAt: string;
  chunkCount: number;
  status: "Indexed" | "Processing" | "Ready";
  category: string;
  author: string;
  summary: string;
  chunksPreview: string[];
}

export const MOCK_DOCUMENTS: MockDocument[] = [
  {
    id: "doc_q3_fin",
    filename: "Q3_2026_Financial_Performance_Report.pdf",
    fileType: "pdf",
    fileSizeBytes: 2457600, // 2.34 MB
    uploadedAt: "2026-10-14 14:20:00",
    chunkCount: 14,
    status: "Indexed",
    category: "Financials",
    author: "Treasury & Strategy Group",
    summary:
      "Comprehensive consolidated balance sheet, revenue breakdown across cloud subscription lines, and operating margin forecasts for FY2026.",
    chunksPreview: [
      "Operating revenue reached $48.2M, representing an annualized growth rate of 34% driven by enterprise AI adoption...",
      "Cloud infrastructure expenditures decreased by 12% following migration to local inference and private vector embeddings...",
      "Net operating margin expanded to 28.5%, with cash reserves closing at $94.6M at the end of the quarter...",
    ],
  },
  {
    id: "doc_sec_arch",
    filename: "Enterprise_ZeroTrust_Security_Architecture.docx",
    fileType: "docx",
    fileSizeBytes: 1843200, // 1.76 MB
    uploadedAt: "2026-10-13 18:45:00",
    chunkCount: 22,
    status: "Indexed",
    category: "Security & Compliance",
    author: "Information Security Office",
    summary:
      "Zero-trust credential governance, role-based access control (RBAC), end-to-end vector encryption at rest, and audit trail specifications.",
    chunksPreview: [
      "All persistent index files stored in data/indexes must be encrypted using AES-GCM-256 with key rotation cycles...",
      "API authorization tokens require short-lived HMAC verification; external credentials must never traverse client browsers...",
      "Local document storage in data/uploads enforces strict POSIX filesystem permissions (0600) restricting root daemon access...",
    ],
  },
  {
    id: "doc_api_spec",
    filename: "Cloud_Inference_and_RAG_Pipeline_Spec.txt",
    fileType: "txt",
    fileSizeBytes: 420800, // 411 KB
    uploadedAt: "2026-10-12 11:10:00",
    chunkCount: 6,
    status: "Indexed",
    category: "Engineering",
    author: "AI Core Infrastructure Team",
    summary:
      "Technical specifications for Sentence Transformer 384d embedding generation, local FAISS IndexFlatL2 search, and Groq LPU prompt formatting.",
    chunksPreview: [
      "The embedding pipeline utilizes sentence-transformers/all-MiniLM-L6-v2 yielding 384-dimensional dense vectors with cosine metric...",
      "Document ingestion applies recursive chunking with default 1000 character chunks and 200 character boundary overlap...",
      "Groq inference streams tokens from llama-3.3-70b-versatile with temperature 0.2 and top_p 0.9 for factual document grounding...",
    ],
  },
];

export interface MockActivity {
  id: string;
  type: "upload" | "index" | "query" | "system";
  title: string;
  timestamp: string;
  status: "success" | "pending" | "info";
  details: string;
}

export const MOCK_ACTIVITIES: MockActivity[] = [
  {
    id: "act-1",
    type: "index",
    title: "FAISS Vector Index Synchronized",
    timestamp: "12 minutes ago",
    status: "success",
    details: "42 chunks mapped across 3 documents in data/indexes.",
  },
  {
    id: "act-2",
    type: "upload",
    title: "Q3_2026_Financial_Performance_Report.pdf Ingested",
    timestamp: "1 hour ago",
    status: "success",
    details: "Extracted 14 chunks using PyPDF text parsing.",
  },
  {
    id: "act-3",
    type: "query",
    title: "Grounded Query: Operating Margin Trends",
    timestamp: "3 hours ago",
    status: "success",
    details: "Retrieved 3 chunks (mean cosine similarity 0.91).",
  },
  {
    id: "act-4",
    type: "system",
    title: "FastAPI Core & Uvicorn Started",
    timestamp: "5 hours ago",
    status: "info",
    details: "Port 8000 listening with CORS configured.",
  },
];

export interface MockChatMessage {
  id: string;
  sender: "user" | "ai";
  timestamp: string;
  content: string;
  citations?: {
    docId: string;
    docName: string;
    page: number;
    text: string;
  }[];
  tokensUsed?: number;
}

export const INITIAL_CHAT_MESSAGES: MockChatMessage[] = [
  {
    id: "msg-1",
    sender: "user",
    timestamp: "14:24",
    content:
      "What were the primary revenue drivers and cash reserves reported in Q3?",
  },
  {
    id: "msg-2",
    sender: "ai",
    timestamp: "14:24",
    content:
      "According to the **Q3 2026 Financial Performance Report**, the primary growth drivers were:\n\n1. **Enterprise AI Adoption**: Operating revenue reached **$48.2M** (+34% annualized growth).\n2. **Infrastructure Cost Reduction**: Cloud infrastructure expenditures fell by **12%** due to private local vector embedding execution.\n3. **Cash Reserves**: Liquid cash reserves concluded at **$94.6M** with a net operating margin of **28.5%**.",
    citations: [
      {
        docId: "doc_q3_fin",
        docName: "Q3_2026_Financial_Performance_Report.pdf",
        page: 4,
        text: "Operating revenue reached $48.2M, representing an annualized growth rate of 34% driven by enterprise AI adoption... Cloud expenditures fell 12%...",
      },
      {
        docId: "doc_q3_fin",
        docName: "Q3_2026_Financial_Performance_Report.pdf",
        page: 7,
        text: "Net operating margin expanded to 28.5%, with cash reserves closing at $94.6M at the end of the quarter.",
      },
    ],
    tokensUsed: 388,
  },
];
