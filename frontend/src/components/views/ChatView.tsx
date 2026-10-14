import { useState, useEffect, useRef } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Brain,
  Check,
  Copy,
  Filter,
  Layers,
  RefreshCw,
  RotateCcw,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  User,
  X,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import {
  api,
  type ChatRequest,
  type ChatSource,
  type ChatStatusResponse,
  type DocumentMetadata,
  ApiError,
} from "@/lib/api";
import { MarkdownRenderer } from "@/components/chat/MarkdownRenderer";
import { CitationCard } from "@/components/chat/CitationCard";

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  timestamp: string;
  content: string;
  sources?: ChatSource[];
  model?: string;
  evidenceFound?: boolean;
  totalSources?: number;
  tokensUsed?: number;
  isError?: boolean;
  errorCode?: string;
  retryQuestion?: string;
  retryScope?: string | null;
}

interface ChatViewProps {
  rawBaseUrl?: string;
  onNavigateToDocuments?: () => void;
}

const SUGGESTED_PROMPTS = [
  {
    title: "Executive Summary",
    category: "Synthesis",
    prompt: "Summarize the primary conclusions, key findings, and main themes across the ingested documents.",
  },
  {
    title: "Action Items & Steps",
    category: "Operations",
    prompt: "Extract all key recommendations, next steps, deadlines, and actionable items cited in the text.",
  },
  {
    title: "Risk & Limitations",
    category: "Governance",
    prompt: "Identify any potential risks, liabilities, compliance issues, or limitations mentioned in the documents.",
  },
  {
    title: "Key Metrics & Statistics",
    category: "Data",
    prompt: "List the most significant quantitative metrics, financial figures, dates, or performance statistics cited.",
  },
];

export function ChatView({ rawBaseUrl, onNavigateToDocuments }: ChatViewProps) {
  const { toast } = useToast();

  // Chat message history (client-side state for active session)
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Document Scope & Knowledge Base State
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [docsLoading, setDocsLoading] = useState(true);

  // Groq Service Diagnostics
  const [chatStatus, setChatStatus] = useState<ChatStatusResponse | null>(null);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on new messages or loading state
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Fetch available documents & chat service status on mount
  useEffect(() => {
    let isMounted = true;

    async function loadInitialContext() {
      setDocsLoading(true);
      try {
        const [docsData, statusData] = await Promise.allSettled([
          api.getDocuments({}, rawBaseUrl),
          api.getChatStatus(rawBaseUrl),
        ]);

        if (!isMounted) return;

        if (docsData.status === "fulfilled") {
          setDocuments(docsData.value.documents || []);
        } else {
          console.error("Failed to fetch documents for chat:", docsData.reason);
        }

        if (statusData.status === "fulfilled") {
          setChatStatus(statusData.value);
        } else {
          console.error("Failed to fetch chat status:", statusData.reason);
        }
      } finally {
        if (isMounted) setDocsLoading(false);
      }
    }

    loadInitialContext();

    return () => {
      isMounted = false;
    };
  }, [rawBaseUrl]);

  // Adjust textarea height on input change
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        160
      )}px`;
    }
  }, [input]);

  // Clear or start new conversation
  const handleStartNewConversation = () => {
    if (messages.length === 0) return;
    setMessages([]);
    setInput("");
    toast.info("Conversation Reset", "Started a new document research session.");
  };

  // Submit Question Handler
  const handleSend = async (overrideQuestion?: string, overrideScope?: string | null) => {
    const questionText = (overrideQuestion ?? input).trim();
    const effectiveScope = overrideScope !== undefined ? overrideScope : (selectedDocId || null);

    if (!questionText || isLoading) return;

    if (readyDocuments.length === 0) {
      toast.error(
        "No Documents Available",
        "Please upload and index at least one document before asking questions."
      );
      return;
    }

    // Verify document scope is ready and unprocessed/nonexistent documents cannot be submitted
    let validScope: string[] | null = null;
    if (effectiveScope) {
      const isDocReady = readyDocuments.some((d) => d.id === effectiveScope);
      if (!isDocReady) {
        toast.error(
          "Scope Unavailable",
          "The selected document is not ready or has been removed. Scope reset to all documents."
        );
        setSelectedDocId("");
        validScope = null;
      } else {
        validScope = [effectiveScope];
      }
    }

    const userMessageId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMessageId,
      sender: "user",
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      content: questionText,
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!overrideQuestion) {
      setInput("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
    setIsLoading(true);

    try {
      const chatReq: ChatRequest = {
        question: questionText,
        document_ids: validScope,
        top_k: 5,
        score_threshold: 0.15,
      };

      const result = await api.askQuestion(chatReq, rawBaseUrl);

      const aiMsg: ChatMessage = {
        id: `ai-${Date.now() + 1}`,
        sender: "assistant",
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        content: result.answer,
        sources: result.sources || [],
        model: result.model,
        evidenceFound: result.evidence_found,
        totalSources: result.total_sources,
        tokensUsed: result.usage?.total_tokens,
      };

      setMessages((prev) => [...prev, aiMsg]);

      if (result.evidence_found && result.sources.length > 0) {
        toast.success(
          "Answer Synthesized",
          `Grounded using ${result.total_sources} retrieved chunk(s) via Groq ${result.model}.`
        );
      } else {
        toast.info(
          "Context Insufficient",
          "No matching document excerpts met the confidence threshold."
        );
      }
    } catch (err: unknown) {
      let errorMessage = "Failed to communicate with Groq RAG engine.";
      let errorCode = "CHAT_ERROR";

      if (err instanceof ApiError) {
        errorMessage = err.message;
        errorCode = err.errorCode;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }

      const errorAiMsg: ChatMessage = {
        id: `ai-err-${Date.now() + 1}`,
        sender: "assistant",
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        content: errorMessage,
        isError: true,
        errorCode,
        retryQuestion: questionText,
        retryScope: effectiveScope,
      };

      setMessages((prev) => [...prev, errorAiMsg]);
      toast.error("Generation Failed", errorMessage);
    } finally {
      setIsLoading(false);
      // Refocus textarea on desktop
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  };

  // Keyboard shortcut: Enter sends, Shift+Enter newlines
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Copy answer to clipboard
  const copyAnswer = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast.success("Copied to clipboard", "Answer copied to system clipboard.");
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Helper to get active document label
  const activeDocument = documents.find((d) => d.id === selectedDocId);
  const readyDocuments = documents.filter(
    (d) => d.status.toLowerCase() === "ready" || d.status.toLowerCase() === "indexed"
  );

  return (
    <div className="flex h-[calc(100vh-8.5rem)] min-h-[580px] flex-col rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 backdrop-blur-xl overflow-hidden shadow-xl animate-in fade-in duration-300">
      {/* Top Navigation & Scope Control Header */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/80 dark:bg-white/[0.02] px-4 py-2.5 text-xs">
        {/* Document Scope Selector */}
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 flex-shrink-0">
            <Filter className="h-3.5 w-3.5 text-violet-500" />
            <span className="font-semibold text-slate-700 dark:text-slate-300">Scope:</span>
          </div>

          <div className="relative">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              disabled={isLoading || docsLoading || readyDocuments.length === 0}
              aria-label="Select Document Retrieval Scope"
              className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111c33] px-2.5 py-1 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:opacity-50 max-w-[220px] sm:max-w-xs truncate"
            >
              <option value="">
                Entire Collection ({readyDocuments.length} Indexed{" "}
                {readyDocuments.length === 1 ? "Doc" : "Docs"})
              </option>
              {readyDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename} (
                  {doc.page_count
                    ? `${doc.page_count} pgs`
                    : `${Math.round(doc.file_size_bytes / 1024)} KB`}
                  )
                </option>
              ))}
            </select>
          </div>

          {selectedDocId && (
            <button
              onClick={() => setSelectedDocId("")}
              className="rounded-md p-1 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
              title="Reset to entire document collection"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* Status Indicators & New Conversation Action */}
        <div className="flex items-center gap-2">
          {/* Groq Model Badge */}
          <div className="hidden sm:flex items-center gap-1.5 rounded-lg border border-slate-200/60 dark:border-white/10 bg-white/50 dark:bg-white/[0.03] px-2.5 py-1 text-[11px] text-slate-500 dark:text-slate-400">
            <Zap className="h-3.5 w-3.5 text-amber-500" />
            <span>{chatStatus?.model || "openai/gpt-oss-120b"}</span>
          </div>

          {/* New Chat Button */}
          {messages.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartNewConversation}
              className="h-7 text-xs gap-1.5 border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10"
              title="Clear conversation history and start fresh"
            >
              <RotateCcw className="h-3 w-3" />
              <span>New Chat</span>
            </Button>
          )}
        </div>
      </div>

      {/* Empty Collection Warning Banner */}
      {!docsLoading && readyDocuments.length === 0 && (
        <div className="flex items-center justify-between border-b border-amber-500/20 bg-amber-500/10 px-4 py-2 text-xs text-amber-900 dark:text-amber-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />
            <span>
              <strong>Knowledge Base is Empty</strong>: No indexed documents were found. Upload documents to query your private knowledge base.
            </span>
          </div>
          {onNavigateToDocuments && (
            <Button
              size="sm"
              variant="outline"
              onClick={onNavigateToDocuments}
              className="h-6 text-[11px] gap-1 border-amber-500/30 text-amber-800 dark:text-amber-200 hover:bg-amber-500/20"
            >
              <span>Upload Documents</span>
              <ArrowRight className="h-3 w-3" />
            </Button>
          )}
        </div>
      )}

      {/* Main Messages & Canvas Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {/* Empty State: Suggested Prompts Hero */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center min-h-[380px] max-w-2xl mx-auto text-center py-6 animate-in fade-in zoom-in-95 duration-300">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/25 mb-4">
              <Sparkles className="h-7 w-7" />
            </div>

            <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              Grounded Document Research Assistant
            </h2>

            <p className="mt-2 text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-md leading-relaxed">
              Ask deep questions, extract key findings, and synthesize insights across your documents with exact source citation provenance.
            </p>

            {/* Scope pill preview */}
            <div className="mt-4 flex items-center gap-2">
              <Badge variant="violet" className="gap-1 text-[11px]">
                <Layers className="h-3 w-3" />
                {selectedDocId && activeDocument
                  ? `Scoped to: ${activeDocument.filename}`
                  : `Scope: ${readyDocuments.length} Ingested Document${readyDocuments.length === 1 ? "" : "s"}`}
              </Badge>
            </div>

            {/* Suggested Prompt Cards */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
              {SUGGESTED_PROMPTS.map((item, idx) => (
                <button
                  key={idx}
                  disabled={isLoading}
                  onClick={() => handleSend(item.prompt)}
                  className="group relative flex flex-col justify-between rounded-xl border border-slate-200/80 dark:border-white/10 bg-white/60 dark:bg-white/[0.02] p-3.5 transition-all hover:border-violet-500/50 hover:bg-violet-50/50 dark:hover:bg-violet-500/[0.04] hover:shadow-md disabled:opacity-50"
                >
                  <div>
                    <div className="flex items-center justify-between text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      <span>{item.category}</span>
                      <ArrowRight className="h-3 w-3 text-slate-400 group-hover:text-violet-500 group-hover:translate-x-0.5 transition-all" />
                    </div>
                    <div className="font-semibold text-xs sm:text-sm text-slate-800 dark:text-slate-200 group-hover:text-violet-700 dark:group-hover:text-violet-300">
                      {item.title}
                    </div>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                      {item.prompt}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message Trajectory */}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3 sm:gap-4 ${
              msg.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {/* Assistant Avatar */}
            {msg.sender === "assistant" && (
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/20">
                <Brain className="h-5 w-5" />
              </div>
            )}

            {/* Message Bubble Card */}
            <div
              className={`max-w-2xl rounded-2xl p-4 sm:p-5 text-xs sm:text-sm space-y-3.5 ${
                msg.sender === "user"
                  ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/15"
                  : msg.isError
                  ? "border border-rose-500/30 bg-rose-500/10 dark:bg-rose-500/15 text-rose-900 dark:text-rose-200 shadow-sm"
                  : "border border-slate-200/80 dark:border-white/10 bg-white/85 dark:bg-[#111c33]/70 text-slate-800 dark:text-slate-200 shadow-sm"
              }`}
            >
              {/* Header Bar */}
              <div
                className={`flex items-center justify-between text-[11px] pb-1.5 border-b ${
                  msg.sender === "user"
                    ? "border-white/20 text-white/80"
                    : "border-slate-100 dark:border-white/10 text-slate-400"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="font-semibold">
                    {msg.sender === "user" ? "You" : "DocuMind Assistant"}
                  </span>
                  {msg.model && (
                    <Badge variant="outline" className="text-[9px] py-0 px-1 font-mono">
                      {msg.model}
                    </Badge>
                  )}
                </div>
                <span>{msg.timestamp}</span>
              </div>

              {/* Error Message Card with Retry */}
              {msg.isError ? (
                <div className="space-y-3">
                  <div className="flex items-start gap-2 text-rose-700 dark:text-rose-300">
                    <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-xs">
                        {msg.errorCode || "API_ERROR"}
                      </div>
                      <p className="mt-1 text-xs leading-relaxed">{msg.content}</p>
                    </div>
                  </div>

                  {msg.retryQuestion && (
                    <div className="pt-2 border-t border-rose-500/20 flex justify-end">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSend(msg.retryQuestion, msg.retryScope)}
                        disabled={isLoading}
                        className="h-7 text-xs gap-1.5 border-rose-500/30 text-rose-700 dark:text-rose-200 hover:bg-rose-500/20"
                      >
                        <RefreshCw className="h-3 w-3" />
                        <span>Retry Question</span>
                      </Button>
                    </div>
                  )}
                </div>
              ) : msg.sender === "assistant" ? (
                <>
                  {/* Insufficient Evidence Warning Pill if evidence_found is false */}
                  {msg.evidenceFound === false && (
                    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 dark:bg-amber-500/15 p-2.5 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <strong>Insufficient Evidence in Context</strong>: No document excerpts met the confidence threshold. The model answered based solely on the absence of verifiable proof.
                      </div>
                    </div>
                  )}

                  {/* Formatted Markdown Content */}
                  <MarkdownRenderer content={msg.content} />

                  {/* Grounded Source Citations Section */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-3 border-t border-slate-100 dark:border-white/10 space-y-2">
                      <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        <span>Retrieved Citations ({msg.sources.length})</span>
                        <span className="font-mono text-[9px] text-slate-400">
                          Sorted by FAISS Cosine Similarity
                        </span>
                      </div>

                      <div className="grid grid-cols-1 gap-2 pt-1">
                        {msg.sources.map((source, idx) => (
                          <CitationCard
                            key={`${source.chunk_id}-${idx}`}
                            source={source}
                            index={idx}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI Message Footer Actions */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/10 text-xs text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => copyAnswer(msg.content, msg.id)}
                        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-slate-100 dark:hover:bg-white/10 text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors"
                        title="Copy answer to clipboard"
                        aria-label="Copy answer"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-500" />
                            <span className="text-emerald-500 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => toast.success("Feedback Recorded", "Marked as helpful.")}
                        className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-white/10 text-slate-400 hover:text-slate-600 dark:hover:text-white"
                        title="Helpful response"
                        aria-label="Helpful"
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>

                      <button
                        onClick={() =>
                          toast.info("Feedback Recorded", "Feedback submitted for model tuning.")
                        }
                        className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-white/10 text-slate-400 hover:text-slate-600 dark:hover:text-white"
                        title="Needs improvement"
                        aria-label="Not helpful"
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    {msg.tokensUsed !== undefined && (
                      <span className="text-[10px] font-mono text-slate-400">
                        {msg.tokensUsed} tokens
                      </span>
                    )}
                  </div>
                </>
              ) : (
                /* User Message Content */
                <div className="whitespace-pre-wrap leading-relaxed font-normal">
                  {msg.content}
                </div>
              )}
            </div>

            {/* User Avatar */}
            {msg.sender === "user" && (
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-slate-200">
                <User className="h-5 w-5" />
              </div>
            )}
          </div>
        ))}

        {/* Live Processing Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 sm:gap-4 justify-start animate-in fade-in duration-200">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/20">
              <Brain className="h-5 w-5 animate-pulse" />
            </div>

            <div className="rounded-2xl border border-violet-500/30 bg-violet-500/10 dark:bg-violet-500/15 p-4 text-xs sm:text-sm text-violet-800 dark:text-violet-200 shadow-sm space-y-2 max-w-lg">
              <div className="flex items-center gap-2 font-medium">
                <Sparkles className="h-4 w-4 text-violet-500 animate-spin" />
                <span>DocuMind Engine is thinking...</span>
              </div>
              <p className="text-[11px] text-violet-700 dark:text-violet-300 leading-relaxed font-mono">
                Querying 384d FAISS vector index $\rightarrow$ Injecting grounded context chunks $\rightarrow$ Groq Llama 3.3 70B synthesizing answer...
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Chips (when in active conversation) */}
      {messages.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-slate-200/60 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.01] overflow-x-auto text-xs">
          <span className="text-[10px] uppercase font-bold text-slate-400 flex-shrink-0">
            Follow-up:
          </span>
          {SUGGESTED_PROMPTS.slice(0, 3).map((item, i) => (
            <button
              key={i}
              disabled={isLoading}
              onClick={() => handleSend(item.prompt)}
              className="flex-shrink-0 rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-white/[0.04] px-3 py-1 text-[11px] text-slate-600 dark:text-slate-300 hover:border-violet-500/40 hover:text-violet-600 dark:hover:text-violet-400 transition-colors disabled:opacity-50"
            >
              {item.title}
            </button>
          ))}
        </div>
      )}

      {/* Chat Multiline Input Dock */}
      <div className="border-t border-slate-200/80 dark:border-white/10 bg-white/80 dark:bg-[#070b14]/80 p-3 sm:p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-end gap-2"
        >
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              rows={1}
              disabled={isLoading}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isLoading
                  ? "Synthesizing grounded response..."
                  : readyDocuments.length === 0
                  ? "Upload documents first to ask grounded questions..."
                  : selectedDocId
                  ? `Ask about ${activeDocument?.filename || "selected document"}... (Enter to send, Shift+Enter for newline)`
                  : "Ask anything about your documents... (Enter to send, Shift+Enter for newline)"
              }
              aria-label="Ask Question about Ingested Documents"
              className="w-full resize-none rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/[0.03] px-4 py-3 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:opacity-60 max-h-40 leading-relaxed"
            />
          </div>

          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            size="sm"
            className="h-11 px-4 gap-1.5 shadow-md shadow-violet-500/20 flex-shrink-0"
            title="Send question (Enter)"
            aria-label="Send question"
          >
            <span>{isLoading ? "Thinking..." : "Send"}</span>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      </div>
    </div>
  );
}
