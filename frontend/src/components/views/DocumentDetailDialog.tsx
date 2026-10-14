import { useState, useEffect } from "react";
import {
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Copy,
  Cpu,
  Database,
  FileCheck,
  FileCode,
  FileText,
  Layers,
  RefreshCw,
  Search,
  Trash2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, type DocumentDetail, type DocumentMetadata } from "@/lib/api";

interface DocumentDetailDialogProps {
  documentId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRequestDelete?: (doc: DocumentMetadata) => void;
  rawBaseUrl?: string;
}

export function DocumentDetailDialog({
  documentId,
  open,
  onOpenChange,
  onRequestDelete,
  rawBaseUrl,
}: DocumentDetailDialogProps) {
  const { toast } = useToast();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePageIndex, setActivePageIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const [textSearch, setTextSearch] = useState("");

  const fetchDetail = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDocumentDetail(id, rawBaseUrl);
      setDoc(data);
      setActivePageIndex(0);
    } catch (err: any) {
      setError(err.message || "Failed to load document details from server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && documentId) {
      fetchDetail(documentId);
    } else {
      setDoc(null);
      setError(null);
      setActivePageIndex(0);
      setTextSearch("");
    }
  }, [open, documentId]);

  if (!open) return null;

  const formatBytes = (bytes?: number) => {
    if (!bytes) return "0 B";
    if (bytes >= 1048576) {
      return (bytes / 1048576).toFixed(2) + " MB";
    }
    return (bytes / 1024).toFixed(1) + " KB";
  };

  const getFileIcon = (type?: string) => {
    switch (type) {
      case "pdf":
        return <FileText className="h-5 w-5 text-rose-500" />;
      case "docx":
        return <FileCheck className="h-5 w-5 text-blue-500" />;
      default:
        return <FileCode className="h-5 w-5 text-emerald-500" />;
    }
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Copied to Clipboard", "Document text copied to clipboard.");
    setTimeout(() => setCopied(false), 2000);
  };

  const isPdf = doc?.file_type?.toLowerCase() === "pdf";
  const pages = doc?.pages || [];
  const totalPages = pages.length;
  const currentPage = pages[activePageIndex];

  // Active text to display
  let displayText = "";
  if (isPdf && totalPages > 0) {
    displayText = currentPage?.text || "No text extracted on this page.";
  } else if (doc?.sections && doc.sections.length > 0) {
    displayText = doc.sections
      .map((s) => (s.heading ? `### ${s.heading}\n${s.text}` : s.text))
      .join("\n\n---\n\n");
  } else {
    displayText = doc?.raw_text_preview || "No extracted text preview available.";
  }

  // Filter text if searching
  const highlighted = textSearch.trim()
    ? displayText.toLowerCase().includes(textSearch.toLowerCase())
    : true;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        {loading ? (
          <div className="space-y-4 p-4">
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-xl" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-5 w-1/3" />
                <Skeleton className="h-3 w-1/4" />
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <Skeleton className="h-16 rounded-xl" />
              <Skeleton className="h-16 rounded-xl" />
              <Skeleton className="h-16 rounded-xl" />
              <Skeleton className="h-16 rounded-xl" />
            </div>
            <Skeleton className="h-64 rounded-xl" />
          </div>
        ) : error ? (
          <div className="p-6 text-center space-y-4">
            <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-2xl bg-rose-500/10 text-rose-500">
              <XCircle className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                Failed to Load Document
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                {error}
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => documentId && fetchDetail(documentId)}
              className="gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </Button>
          </div>
        ) : doc ? (
          <>
            <DialogHeader className="pb-2 border-b border-slate-200/80 dark:border-white/10">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-slate-100 dark:bg-white/[0.05] border border-slate-200 dark:border-white/10">
                    {getFileIcon(doc.file_type)}
                  </div>
                  <div>
                    <DialogTitle className="text-base sm:text-lg font-bold break-all text-slate-900 dark:text-white">
                      {doc.filename}
                    </DialogTitle>
                    <DialogDescription className="flex items-center gap-2 mt-0.5 text-xs">
                      <span className="uppercase font-mono font-semibold text-violet-600 dark:text-violet-400">
                        {doc.file_type}
                      </span>
                      <span>•</span>
                      <span>{formatBytes(doc.file_size_bytes)}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        <span className="capitalize">{doc.status}</span>
                      </span>
                    </DialogDescription>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {onRequestDelete && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        onOpenChange(false);
                        onRequestDelete(doc);
                      }}
                      className="text-rose-500 hover:text-rose-600 hover:bg-rose-500/10 h-8 px-2.5 gap-1.5 text-xs"
                      title="Delete document"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">Delete</span>
                    </Button>
                  )}
                </div>
              </div>
            </DialogHeader>

            {/* Metadata Badges Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-3 flex-shrink-0">
              <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] p-2.5 text-xs">
                <div className="flex items-center gap-1.5 text-slate-400 mb-0.5">
                  <Layers className="h-3.5 w-3.5 text-violet-500" />
                  <span>{isPdf ? "Total Pages" : "Sections"}</span>
                </div>
                <div className="font-bold text-slate-800 dark:text-slate-100">
                  {isPdf
                    ? `${doc.page_count ?? totalPages} Page(s)`
                    : `${doc.section_count ?? 1} Section(s)`}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] p-2.5 text-xs">
                <div className="flex items-center gap-1.5 text-slate-400 mb-0.5">
                  <Cpu className="h-3.5 w-3.5 text-indigo-500" />
                  <span>Word Count</span>
                </div>
                <div className="font-bold text-slate-800 dark:text-slate-100">
                  {doc.word_count?.toLocaleString() || "N/A"} words
                </div>
              </div>

              <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] p-2.5 text-xs">
                <div className="flex items-center gap-1.5 text-slate-400 mb-0.5">
                  <FileText className="h-3.5 w-3.5 text-sky-500" />
                  <span>Characters</span>
                </div>
                <div className="font-bold text-slate-800 dark:text-slate-100">
                  {doc.character_count?.toLocaleString() || "N/A"} chars
                </div>
              </div>

              <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] p-2.5 text-xs">
                <div className="flex items-center gap-1.5 text-slate-400 mb-0.5">
                  <Database className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Vector Index</span>
                </div>
                <div className="font-bold text-emerald-600 dark:text-emerald-400 truncate">
                  FAISS 384d (IP)
                </div>
              </div>
            </div>

            {/* Extracted Content Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-b border-slate-200/60 dark:border-white/10 py-2 px-1 text-xs">
              {/* PDF Page Navigation Controls */}
              {isPdf && totalPages > 1 ? (
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={activePageIndex <= 0}
                    onClick={() => setActivePageIndex((prev) => Math.max(0, prev - 1))}
                    className="h-7 w-7 p-0"
                    title="Previous page"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="font-mono text-xs text-slate-700 dark:text-slate-200 font-semibold">
                    Page {activePageIndex + 1} of {totalPages}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={activePageIndex >= totalPages - 1}
                    onClick={() =>
                      setActivePageIndex((prev) => Math.min(totalPages - 1, prev + 1))
                    }
                    className="h-7 w-7 p-0"
                    title="Next page"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>

                  {currentPage && (
                    <span className="text-[11px] text-slate-400 ml-1">
                      ({currentPage.word_count} words, {currentPage.char_count} chars)
                    </span>
                  )}
                </div>
              ) : (
                <div className="font-semibold text-slate-700 dark:text-slate-300">
                  {isPdf ? "Page 1 Content" : "Extracted Structured Text"}
                </div>
              )}

              {/* Copy & Search in Document */}
              <div className="flex items-center gap-2 ml-auto">
                <div className="relative">
                  <Search className="h-3 w-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={textSearch}
                    onChange={(e) => setTextSearch(e.target.value)}
                    placeholder="Find in text..."
                    className="h-7 pl-7 pr-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/[0.03] text-[11px] text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-violet-500 w-32 sm:w-44"
                  />
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopyText(displayText)}
                  className="h-7 px-2.5 gap-1.5 text-[11px]"
                  title="Copy text"
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-emerald-500" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                  <span>{copied ? "Copied" : "Copy Text"}</span>
                </Button>
              </div>
            </div>

            {/* Text Viewport */}
            <div className="flex-1 overflow-y-auto rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-[#070c18]/50 p-4 text-xs font-mono text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap select-text max-h-[46vh]">
              {!highlighted ? (
                <div className="text-center py-8 text-slate-400">
                  No text matches for "{textSearch}".
                </div>
              ) : (
                displayText
              )}
            </div>

            <DialogFooter className="pt-2 border-t border-slate-200/60 dark:border-white/10">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
              >
                Close
              </Button>
            </DialogFooter>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
