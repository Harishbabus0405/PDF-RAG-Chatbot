import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  ExternalLink,
  GraduationCap,
  HardDrive,
  Moon,
  RefreshCw,
  ShieldCheck,
  Sun,
  XCircle,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useTheme } from "@/lib/theme";
import { api, type ChatStatusResponse } from "@/lib/api";
import type { HealthData } from "./OverviewView";

interface SettingsViewProps {
  health?: HealthData | null;
  loading?: boolean;
  latency?: number | null;
  rawBaseUrl?: string;
  onRefreshHealth?: () => void;
}

export function SettingsView({
  health,
  loading = false,
  latency = null,
  rawBaseUrl = "http://127.0.0.1:8000",
  onRefreshHealth,
}: SettingsViewProps) {
  const { theme, setTheme } = useTheme();
  const [chatStatus, setChatStatus] = useState<ChatStatusResponse | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadChatStatus() {
      try {
        const res = await api.getChatStatus(rawBaseUrl);
        if (isMounted) setChatStatus(res);
      } catch {
        // Handled silently; will use fallback display
      }
    }
    loadChatStatus();
    return () => {
      isMounted = false;
    };
  }, [rawBaseUrl]);

  const isConnected = Boolean(health);
  const currentModel = chatStatus?.model || (health?.groq_configured ? "openai/gpt-oss-120b" : "Not configured");

  return (
    <div className="space-y-6 max-w-4xl animate-in fade-in duration-300">
      {/* Settings Header */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-6 backdrop-blur-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              Settings &amp; System Information
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
              Inspect backend connectivity, active AI models, and customize interface preferences.
            </p>
          </div>

          {onRefreshHealth && (
            <Button
              onClick={onRefreshHealth}
              disabled={loading}
              variant="outline"
              size="sm"
              className="gap-2 text-xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh Status</span>
            </Button>
          )}
        </div>
      </div>

      {/* 1. Backend Connection Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-500" />
              <CardTitle className="text-base">Backend Connection Status</CardTitle>
            </div>
            {isConnected ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Connected</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-600 dark:text-rose-400">
                <XCircle className="h-3.5 w-3.5" />
                <span>Offline</span>
              </span>
            )}
          </div>
          <CardDescription>
            Live connectivity check with the FastAPI backend service
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.02] p-3.5">
              <span className="text-[11px] text-slate-400">API Endpoint</span>
              <p className="font-mono text-xs font-semibold text-slate-900 dark:text-white mt-1 truncate">
                {rawBaseUrl}
              </p>
              <span className="text-[10px] text-slate-500">FastAPI REST Server</span>
            </div>

            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.02] p-3.5">
              <span className="text-[11px] text-slate-400">Probe Latency</span>
              <p className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                {latency !== null ? `${latency} ms` : "—"}
              </p>
              <span className="text-[10px] text-slate-500">Round-trip response time</span>
            </div>

            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.02] p-3.5">
              <span className="text-[11px] text-slate-400">API Documentation</span>
              <div className="mt-1">
                <a
                  href={`${rawBaseUrl}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-violet-600 dark:text-violet-400 hover:underline"
                >
                  <span>Open Swagger Docs</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
              <span className="text-[10px] text-slate-500">Interactive OpenAPI schema</span>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/40 dark:bg-white/[0.01] p-3 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-slate-400" />
              <span className="text-slate-600 dark:text-slate-300">Local Storage Directories:</span>
              <code className="font-mono text-[11px] bg-slate-200/60 dark:bg-white/10 px-1.5 py-0.5 rounded">
                data/uploads
              </code>
              <span className="text-slate-400">&amp;</span>
              <code className="font-mono text-[11px] bg-slate-200/60 dark:bg-white/10 px-1.5 py-0.5 rounded">
                data/indexes
              </code>
            </div>
            <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
              Ready &amp; Writable
            </span>
          </div>
        </CardContent>
      </Card>

      {/* 2. Read-Only AI & Vector Model Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-500" />
            <CardTitle className="text-base">AI &amp; Retrieval Models</CardTitle>
          </div>
          <CardDescription>
            Active language model and vector embedding configurations (managed via backend settings)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {/* Groq LLM */}
            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.02] p-4 space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-medium">Inference Provider</span>
                <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-600 dark:text-amber-400">
                  Groq Cloud LPU
                </span>
              </div>
              <div className="text-sm font-bold text-slate-900 dark:text-white font-mono">
                {currentModel}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Ultra-fast token synthesis on specialized Groq Language Processing Units.
              </p>
            </div>

            {/* Embedding Model */}
            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.02] p-4 space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-medium">Embedding Architecture</span>
                <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">
                  Sentence Transformers
                </span>
              </div>
              <div className="text-sm font-bold text-slate-900 dark:text-white font-mono">
                all-MiniLM-L6-v2 (384d)
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Local CPU inference producing dense cosine-normalized vectors.
              </p>
            </div>

            {/* Vector Store */}
            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.02] p-4 space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-medium">Vector Similarity Store</span>
                <span className="rounded-full bg-sky-500/10 px-2 py-0.5 text-[10px] font-semibold text-sky-600 dark:text-sky-400">
                  FAISS IndexFlatIP
                </span>
              </div>
              <div className="text-sm font-bold text-slate-900 dark:text-white">
                In-Memory + File Persistence
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Exact inner product search without requiring external database servers.
              </p>
            </div>

            {/* Ingestion & Chunking */}
            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.02] p-4 space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-medium">Chunking Parameters</span>
                <span className="rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold text-violet-600 dark:text-violet-400">
                  Recursive Text Splitter
                </span>
              </div>
              <div className="text-sm font-bold text-slate-900 dark:text-white">
                1000 Chars / 200 Overlap
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Preserves semantic boundaries and sentence context across chunks.
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 dark:bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-500 flex-shrink-0" />
            <span>
              <strong>Secure Architecture</strong>: Model parameters and Groq API keys remain strictly in backend environment variables and are never exposed to the client.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* 3. Theme Preferences */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sun className="h-5 w-5 text-violet-500" />
            <CardTitle className="text-base">Appearance &amp; Theme</CardTitle>
          </div>
          <CardDescription>
            Select your preferred interface color theme
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 max-w-sm">
            <button
              type="button"
              onClick={() => setTheme("dark")}
              className={`flex items-center justify-center gap-2 rounded-xl border p-3 text-xs font-semibold transition-all ${
                theme === "dark"
                  ? "border-violet-500 bg-violet-500/10 text-violet-700 dark:text-white shadow-sm"
                  : "border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5"
              }`}
            >
              <Moon className="h-4 w-4 text-violet-500" />
              <span>Dark Navy (Default)</span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("light")}
              className={`flex items-center justify-center gap-2 rounded-xl border p-3 text-xs font-semibold transition-all ${
                theme === "light"
                  ? "border-violet-500 bg-violet-500/10 text-violet-700 dark:text-white shadow-sm"
                  : "border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5"
              }`}
            >
              <Sun className="h-4 w-4 text-amber-500" />
              <span>Light Clean</span>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* 4. About DocuMind AI (Portfolio Project) */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-indigo-500" />
            <CardTitle className="text-base">About DocuMind AI</CardTitle>
          </div>
          <CardDescription>
            AI Engineering Portfolio Project • B.Tech Artificial Intelligence and Data Science
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
          <p>
            <strong>DocuMind AI</strong> is an end-to-end Retrieval-Augmented Generation (RAG)
            document assistant designed to deliver private, factual question answering over
            PDF, DOCX, and TXT documents without relying on heavyweight external database servers.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.02] p-3 space-y-1">
              <span className="font-semibold text-slate-900 dark:text-white block">
                Frontend Architecture
              </span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui design tokens, Lucide icons.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.02] p-3 space-y-1">
              <span className="font-semibold text-slate-900 dark:text-white block">
                Backend Architecture
              </span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Python 3.12, FastAPI, Pydantic v2 schemas, Uvicorn asynchronous server.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.02] p-3 space-y-1">
              <span className="font-semibold text-slate-900 dark:text-white block">
                AI &amp; Retrieval Engine
              </span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Groq Cloud LPU inference, sentence-transformers/all-MiniLM-L6-v2 embeddings, FAISS vector search.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.02] p-3 space-y-1">
              <span className="font-semibold text-slate-900 dark:text-white block">
                Document Parsers &amp; Storage
              </span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                PyMuPDF (fitz), python-docx, native text. Zero-database local filesystem storage.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
