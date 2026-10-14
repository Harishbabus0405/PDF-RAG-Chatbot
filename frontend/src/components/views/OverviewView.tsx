import { useState, useEffect } from "react";
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  FileText,
  FileUp,
  Layers,
  Sparkles,
  XCircle,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type DocumentMetadata } from "@/lib/api";

export interface HealthData {
  status: string;
  service: string;
  version: string;
  environment?: string;
  timestamp: string;
  uptime_seconds?: number;
  groq_configured: boolean;
  embedding_model: string;
  dependencies?: {
    groq_api_configured: boolean;
    embedding_model: string;
    uploads_directory_ready: boolean;
    indexes_directory_ready: boolean;
  };
}

interface OverviewViewProps {
  rawBaseUrl: string;
  backendError?: string | null;
  onNavigateToDocuments: () => void;
  onNavigateToChat: () => void;
}

export function OverviewView({
  rawBaseUrl,
  backendError,
  onNavigateToDocuments,
  onNavigateToChat,
}: OverviewViewProps) {
  const [stats, setStats] = useState<{
    totalDocs: number;
    readyDocs: number;
    processingDocs: number;
    failedDocs: number;
    vectorCount: number;
    storageBytes: number;
    recentDocs: DocumentMetadata[];
    loading: boolean;
  }>({
    totalDocs: 0,
    readyDocs: 0,
    processingDocs: 0,
    failedDocs: 0,
    vectorCount: 0,
    storageBytes: 0,
    recentDocs: [],
    loading: true,
  });

  const fetchOverviewData = async () => {
    try {
      const [docsData, indexStatus] = await Promise.allSettled([
        api.getDocuments({ limit: 50 }, rawBaseUrl),
        api.getIndexStatus(rawBaseUrl),
      ]);

      const docs = docsData.status === "fulfilled" ? docsData.value.documents : [];
      const totalDocs = docsData.status === "fulfilled" ? docsData.value.total : 0;
      const vectors = indexStatus.status === "fulfilled" ? indexStatus.value.total_vectors : 0;

      const ready = docs.filter((d) => d.status === "indexed" || d.status === "ready").length;
      const processing = docs.filter(
        (d) => d.status === "processing" || d.status === "uploaded"
      ).length;
      const failed = docs.filter((d) => d.status === "failed").length;
      const storage = docs.reduce((acc, d) => acc + (d.file_size_bytes || 0), 0);

      setStats({
        totalDocs,
        readyDocs: ready,
        processingDocs: processing,
        failedDocs: failed,
        vectorCount: vectors,
        storageBytes: storage,
        recentDocs: docs.slice(0, 5),
        loading: false,
      });
    } catch {
      setStats((prev) => ({ ...prev, loading: false }));
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, [rawBaseUrl]);

  const formatBytes = (bytes: number) => {
    if (!bytes) return "0 B";
    if (bytes >= 1048576) {
      return (bytes / 1048576).toFixed(1) + " MB";
    }
    return (bytes / 1024).toFixed(1) + " KB";
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-300">
      {/* Welcome Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 dark:border-white/10 bg-gradient-to-br from-violet-600/10 via-indigo-600/5 to-blue-600/10 p-6 sm:p-8 backdrop-blur-xl">
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/15 px-3 py-1 text-xs font-medium text-violet-700 dark:text-violet-300">
            <Sparkles className="h-3.5 w-3.5" />
            <span>AI Document Assistant</span>
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Welcome to{" "}
              <span className="bg-gradient-to-r from-violet-600 via-indigo-500 to-sky-500 dark:from-violet-400 dark:via-indigo-300 dark:to-sky-400 bg-clip-text text-transparent">
                DocuMind AI
              </span>
            </h1>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed">
              Upload documents, automatically extract knowledge with local vector embeddings,
              and query your documents using Groq-powered Retrieval-Augmented Generation (RAG).
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              onClick={onNavigateToDocuments}
              size="sm"
              className="gap-2 shadow-md shadow-violet-500/20"
            >
              <FileUp className="h-4 w-4" />
              <span>Upload Documents</span>
            </Button>
            <Button
              onClick={onNavigateToChat}
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <Brain className="h-4 w-4 text-violet-500" />
              <span>Open AI Workspace</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Backend Offline Warning (if applicable) */}
      {backendError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-700 dark:text-rose-300 flex items-center gap-2.5">
          <AlertCircle className="h-4 w-4 text-rose-500 flex-shrink-0" />
          <span>
            <strong>Backend Offline:</strong> Unable to connect to FastAPI at {rawBaseUrl}. Ensure the server is running on port 8000.
          </span>
        </div>
      )}

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Metric 1: Total Documents */}
        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between text-slate-400 dark:text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Total Documents
            </span>
            <FileText className="h-4 w-4 text-violet-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
            {stats.loading ? <Skeleton className="h-8 w-14" /> : stats.totalDocs}
          </div>
          <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            {formatBytes(stats.storageBytes)} total storage
          </p>
        </div>

        {/* Metric 2: Ready & Indexed */}
        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between text-slate-400 dark:text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Ready &amp; Indexed
            </span>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">
            {stats.loading ? <Skeleton className="h-8 w-14" /> : stats.readyDocs}
          </div>
          <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            Ready for instant RAG queries
          </p>
        </div>

        {/* Metric 3: Processing / In Flight */}
        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between text-slate-400 dark:text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Processing
            </span>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-amber-600 dark:text-amber-400">
            {stats.loading ? <Skeleton className="h-8 w-14" /> : stats.processingDocs}
          </div>
          <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            {stats.processingDocs === 0 ? "No active pipeline tasks" : "Extracting & vectorizing"}
          </p>
        </div>

        {/* Metric 4: Vector Chunks */}
        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between text-slate-400 dark:text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Vector Chunks
            </span>
            <Layers className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
            {stats.loading ? <Skeleton className="h-8 w-14" /> : stats.vectorCount}
          </div>
          <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            FAISS 384d dense embeddings
          </p>
        </div>
      </div>

      {/* Two Column Layout: Recent Documents & RAG Architecture */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Documents Section */}
        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-5 sm:p-6 backdrop-blur-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <FileText className="h-4 w-4 text-violet-500" />
                <span>Recent Documents</span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Latest files uploaded to the local knowledge base
              </p>
            </div>
            <Button
              onClick={onNavigateToDocuments}
              variant="ghost"
              size="sm"
              className="text-xs text-violet-600 dark:text-violet-400 hover:text-violet-700"
            >
              View All ({stats.totalDocs})
            </Button>
          </div>

          {stats.loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full rounded-xl" />
              ))}
            </div>
          ) : stats.recentDocs.length > 0 ? (
            <div className="space-y-2.5">
              {stats.recentDocs.map((doc) => {
                const isReady = doc.status === "ready" || doc.status === "indexed";
                const isFailed = doc.status === "failed";
                const isProcessing = doc.status === "processing" || doc.status === "uploaded";

                return (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-slate-200/70 dark:border-white/[0.06] bg-slate-50/50 dark:bg-white/[0.02] p-3 transition-colors hover:border-violet-500/30"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-500/10 text-violet-500 font-semibold text-xs flex-shrink-0">
                        {doc.file_type.toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                          {doc.filename}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {formatBytes(doc.file_size_bytes)}
                          {doc.page_count ? ` • ${doc.page_count} pages` : ""}
                          {doc.chunk_count ? ` • ${doc.chunk_count} chunks` : ""}
                        </div>
                      </div>
                    </div>

                    <div className="flex-shrink-0">
                      {isReady && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3 w-3" />
                          <span>Ready</span>
                        </span>
                      )}
                      {isProcessing && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                          <Clock className="h-3 w-3 animate-spin" />
                          <span>Processing</span>
                        </span>
                      )}
                      {isFailed && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] font-medium text-rose-600 dark:text-rose-400">
                          <XCircle className="h-3 w-3" />
                          <span>Failed</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 dark:border-white/10 p-6 text-center space-y-3">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-violet-500/10 text-violet-500">
                <FileUp className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  No documents uploaded yet
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Upload a PDF, DOCX, or TXT file to start asking questions.
                </p>
              </div>
              <Button
                onClick={onNavigateToDocuments}
                size="sm"
                variant="outline"
                className="text-xs gap-1.5"
              >
                <FileUp className="h-3.5 w-3.5" />
                <span>Upload First Document</span>
              </Button>
            </div>
          )}
        </div>

        {/* How DocuMind Works (RAG Pipeline) */}
        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-5 sm:p-6 backdrop-blur-xl space-y-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Layers className="h-4 w-4 text-indigo-500" />
              <span>How DocuMind AI Works</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              The 4-step Retrieval-Augmented Generation (RAG) architecture
            </p>
          </div>

          <div className="space-y-3">
            {[
              {
                step: "1",
                title: "Document Ingestion & Text Extraction",
                desc: "Uploaded PDF, DOCX, and TXT files are processed on the backend using pure Python parsers without external dependencies.",
                icon: FileText,
                accent: "text-violet-500",
              },
              {
                step: "2",
                title: "Recursive Chunking & Local Embeddings",
                desc: "Extracted text is split into overlapping chunks and converted into 384-dimensional dense vectors using sentence-transformers/all-MiniLM-L6-v2.",
                icon: Cpu,
                accent: "text-indigo-500",
              },
              {
                step: "3",
                title: "FAISS In-Memory Vector Similarity Search",
                desc: "Queries are transformed to vectors and matched using cosine similarity against the local FAISS index for sub-millisecond retrieval.",
                icon: Database,
                accent: "text-sky-500",
              },
              {
                step: "4",
                title: "Grounded Generation via Groq Cloud LLM",
                desc: "The retrieved context and question are sent to the Groq API for rapid inference, generating factual answers with verifiable citations.",
                icon: Zap,
                accent: "text-amber-500",
              },
            ].map((stage) => {
              const Icon = stage.icon;
              return (
                <div
                  key={stage.step}
                  className="flex items-start gap-3 rounded-xl border border-slate-200/70 dark:border-white/[0.06] bg-slate-50/50 dark:bg-white/[0.02] p-3 text-xs"
                >
                  <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-slate-200/70 dark:bg-white/10 font-mono font-bold text-slate-700 dark:text-slate-300 text-xs">
                    {stage.step}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 font-semibold text-slate-900 dark:text-white">
                      <Icon className={`h-3.5 w-3.5 ${stage.accent}`} />
                      <span>{stage.title}</span>
                    </div>
                    <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                      {stage.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
