import { useState, useMemo, useEffect, useRef } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Eye,
  FileCheck,
  FileCode,
  FileText,
  FileUp,
  Filter,
  Grid,
  List,
  RefreshCw,
  Search,
  Trash2,
  UploadCloud,
  X,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, type DocumentMetadata } from "@/lib/api";
import { DocumentDetailDialog } from "@/components/views/DocumentDetailDialog";
import { DeleteConfirmDialog } from "@/components/views/DeleteConfirmDialog";

interface DocumentsViewProps {
  rawBaseUrl: string;
  onDocumentCountChange?: (count: number) => void;
}

interface UploadTask {
  id: string;
  filename: string;
  sizeBytes: number;
  progress: number;
  status: "uploading" | "processing" | "completed" | "failed";
  errorMessage?: string;
}

export function DocumentsView({ rawBaseUrl, onDocumentCountChange }: DocumentsViewProps) {
  const { toast } = useToast();

  // Document list state
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filters
  const [search, setSearch] = useState("");
  const [selectedFormat, setSelectedFormat] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "name" | "size">("newest");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // Drag & Drop / Upload state
  const [isDragOver, setIsDragOver] = useState(false);
  const [activeUploads, setActiveUploads] = useState<UploadTask[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Modals state
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<DocumentMetadata | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch documents from backend
  const fetchDocuments = async (showLoadingSkeleton = true) => {
    if (showLoadingSkeleton) setLoading(true);
    setError(null);
    try {
      const data = await api.getDocuments({ limit: 100 }, rawBaseUrl);
      setDocuments(data.documents);
      if (onDocumentCountChange) {
        onDocumentCountChange(data.total);
      }
    } catch (err: any) {
      setError(err.message || "Unable to connect to DocuMind backend to retrieve documents.");
    } finally {
      if (showLoadingSkeleton) setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments(true);
  }, [rawBaseUrl]);

  // Upload handler supporting single & multi-file drops
  const handleUploadFiles = async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    for (const file of fileArray) {
      const taskId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
      const newTask: UploadTask = {
        id: taskId,
        filename: file.name,
        sizeBytes: file.size,
        progress: 10,
        status: "uploading",
      };

      setActiveUploads((prev) => [newTask, ...prev]);

      try {
        await api.uploadDocument(
          file,
          (percent) => {
            setActiveUploads((prev) =>
              prev.map((t) =>
                t.id === taskId
                  ? {
                      ...t,
                      progress: percent,
                      status: percent >= 100 ? "processing" : "uploading",
                    }
                  : t
              )
            );
          },
          rawBaseUrl
        );

        setActiveUploads((prev) =>
          prev.map((t) =>
            t.id === taskId ? { ...t, progress: 100, status: "completed" } : t
          )
        );

        toast.success(
          "Document Ingested",
          `Successfully extracted and indexed "${file.name}" into FAISS.`
        );

        // Refresh document list silently
        fetchDocuments(false);

        // Clear completed task after 4 seconds
        setTimeout(() => {
          setActiveUploads((prev) => prev.filter((t) => t.id !== taskId));
        }, 4000);
      } catch (uploadErr: any) {
        const errorMsg = uploadErr.message || "Failed to upload document.";
        setActiveUploads((prev) =>
          prev.map((t) =>
            t.id === taskId
              ? { ...t, status: "failed", errorMessage: errorMsg }
              : t
          )
        );
        toast.error("Upload Failed", `${file.name}: ${errorMsg}`);
      }
    }
  };

  // Delete document handler
  const handleConfirmDelete = async (doc: DocumentMetadata) => {
    setIsDeleting(true);
    try {
      await api.deleteDocument(doc.id, rawBaseUrl);
      toast.success(
        "Document Deleted",
        `Permanently removed "${doc.filename}" and purged its FAISS vectors.`
      );
      setDeleteModalOpen(false);
      setDocToDelete(null);
      // Immediately filter out locally and re-fetch
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      fetchDocuments(false);
    } catch (err: any) {
      toast.error("Delete Failed", err.message || "Unable to delete document.");
    } finally {
      setIsDeleting(false);
    }
  };

  // Formatting helpers
  const formatBytes = (bytes?: number) => {
    if (!bytes) return "0 B";
    if (bytes >= 1048576) {
      return (bytes / 1048576).toFixed(2) + " MB";
    }
    return (bytes / 1024).toFixed(1) + " KB";
  };

  const getDocDate = (doc: DocumentMetadata) => doc.uploaded_at || doc.created_at || "";

  const formatDate = (isoString?: string) => {
    if (!isoString) return "N/A";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  const getFileIcon = (type?: string) => {
    switch (type?.toLowerCase()) {
      case "pdf":
        return <FileText className="h-5 w-5 text-rose-500" />;
      case "docx":
        return <FileCheck className="h-5 w-5 text-blue-500" />;
      default:
        return <FileCode className="h-5 w-5 text-emerald-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case "indexed":
      case "ready":
        return (
          <Badge variant="success" className="gap-1 text-[11px] capitalize">
            <CheckCircle2 className="h-3 w-3" />
            {status}
          </Badge>
        );
      case "processing":
      case "uploaded":
        return (
          <Badge variant="warning" className="gap-1 text-[11px] capitalize">
            <Clock className="h-3 w-3 animate-spin" />
            {status}
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="destructive" className="gap-1 text-[11px] capitalize">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-[11px] capitalize">
            {status}
          </Badge>
        );
    }
  };

  // Summary Metrics calculations
  const totalDocs = documents.length;
  const readyDocs = documents.filter((d) => d.status === "indexed" || d.status === "ready").length;
  const processingDocs = documents.filter((d) => d.status === "processing" || d.status === "uploaded").length;
  const failedDocs = documents.filter((d) => d.status === "failed").length;
  const totalStorageBytes = documents.reduce((acc, d) => acc + (d.file_size_bytes || 0), 0);

  // Filter & sort documents
  const filteredDocs = useMemo(() => {
    return documents
      .filter((doc) => {
        const matchesSearch =
          doc.filename.toLowerCase().includes(search.toLowerCase()) ||
          doc.id.toLowerCase().includes(search.toLowerCase()) ||
          (doc.summary && doc.summary.toLowerCase().includes(search.toLowerCase()));

        const matchesFormat =
          selectedFormat === "all" || doc.file_type.toLowerCase() === selectedFormat.toLowerCase();

        const matchesStatus =
          selectedStatus === "all" ||
          (selectedStatus === "ready" && (doc.status === "ready" || doc.status === "indexed")) ||
          (selectedStatus === "processing" && (doc.status === "processing" || doc.status === "uploaded")) ||
          (selectedStatus === "failed" && doc.status === "failed");

        return matchesSearch && matchesFormat && matchesStatus;
      })
      .sort((a, b) => {
        if (sortBy === "newest") {
          return new Date(getDocDate(b)).getTime() - new Date(getDocDate(a)).getTime();
        }
        if (sortBy === "oldest") {
          return new Date(getDocDate(a)).getTime() - new Date(getDocDate(b)).getTime();
        }
        if (sortBy === "name") {
          return a.filename.localeCompare(b.filename);
        }
        if (sortBy === "size") {
          return (b.file_size_bytes || 0) - (a.file_size_bytes || 0);
        }
        return 0;
      });
  }, [documents, search, selectedFormat, selectedStatus, sortBy]);

  return (
    <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-300">
      {/* Hidden File Picker */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        onChange={(e) => {
          if (e.target.files) handleUploadFiles(e.target.files);
          e.target.value = "";
        }}
        className="hidden"
      />

      {/* Workspace Metric KPI Banner */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Total Ingested
            </span>
            <FileText className="h-4 w-4 text-violet-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
            {totalDocs}
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            {formatBytes(totalStorageBytes)} disk allocation
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Indexed & Ready
            </span>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">
            {readyDocs}
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            Searchable in FAISS vector space
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              In Flight
            </span>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-amber-600 dark:text-amber-400">
            {processingDocs}
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            Extracting text & generating embeddings
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Failed Files
            </span>
            <XCircle className="h-4 w-4 text-rose-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-rose-600 dark:text-rose-400">
            {failedDocs}
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            {failedDocs === 0 ? "All extractions successful" : "Scanned/unsupported formats"}
          </p>
        </div>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files) handleUploadFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`group relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 sm:p-8 text-center cursor-pointer transition-all ${
          isDragOver
            ? "border-violet-500 bg-violet-500/10 shadow-lg shadow-violet-500/10 scale-[1.005]"
            : "border-slate-300 dark:border-white/15 bg-white/50 dark:bg-[#0a101f]/50 hover:border-violet-500/50 hover:bg-violet-500/5 backdrop-blur-xl"
        }`}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/25 group-hover:scale-110 transition-transform mb-3">
          <UploadCloud className="h-7 w-7" />
        </div>

        <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
          Drag & Drop Document Files Here
        </h3>
        <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-md">
          Or click to browse from your device. Files are automatically chunked, embedded via MiniLM, and indexed into FAISS.
        </p>

        {/* Format Support Badges */}
        <div className="flex flex-wrap items-center justify-center gap-2 mt-4">
          <Badge variant="destructive" className="gap-1 text-[11px]">
            <FileText className="h-3 w-3" /> PDF (Native Text)
          </Badge>
          <Badge variant="blue" className="gap-1 text-[11px]">
            <FileCheck className="h-3 w-3" /> DOCX (Word)
          </Badge>
          <Badge variant="success" className="gap-1 text-[11px]">
            <FileCode className="h-3 w-3" /> TXT (UTF-8)
          </Badge>
          <span className="text-[11px] text-slate-400 ml-1">Up to 50 MB per file</span>
        </div>
      </div>

      {/* Active Upload Tasks Progress Cards */}
      {activeUploads.length > 0 && (
        <div className="space-y-2.5">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            In-Progress Document Ingestion ({activeUploads.length})
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {activeUploads.map((task) => (
              <div
                key={task.id}
                className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-white/80 dark:bg-[#0e1628]/80 p-3.5 backdrop-blur-md shadow-sm space-y-2 animate-in slide-in-from-top-2 duration-200"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 truncate max-w-[70%]">
                    <FileUp className="h-4 w-4 text-violet-500 flex-shrink-0" />
                    <span className="font-semibold truncate text-slate-800 dark:text-slate-200">
                      {task.filename}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {formatBytes(task.sizeBytes)}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-100 dark:bg-white/10 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      task.status === "failed"
                        ? "bg-rose-500"
                        : task.status === "completed"
                        ? "bg-emerald-500"
                        : "bg-gradient-to-r from-violet-600 to-indigo-600"
                    }`}
                    style={{ width: `${task.progress}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px]">
                  <span
                    className={
                      task.status === "failed"
                        ? "text-rose-500 font-medium truncate max-w-[85%]"
                        : task.status === "completed"
                        ? "text-emerald-500 font-medium"
                        : "text-violet-600 dark:text-violet-400"
                    }
                  >
                    {task.status === "uploading" && `Uploading file (${task.progress}%)...`}
                    {task.status === "processing" && "Extracting & Embedding into FAISS..."}
                    {task.status === "completed" && "Successfully indexed!"}
                    {task.status === "failed" && (task.errorMessage || "Upload failed")}
                  </span>

                  {task.status === "failed" && (
                    <button
                      onClick={() =>
                        setActiveUploads((prev) => prev.filter((t) => t.id !== task.id))
                      }
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-white"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Control Bar: Search, Filters, Sorting & View Toggle */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative w-full lg:w-80">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by filename or ID..."
            className="pl-9 pr-8 h-9 text-xs"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-white"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Format Chips */}
          <div className="flex items-center rounded-xl border border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/[0.02] p-0.5 text-xs">
            {["all", "pdf", "docx", "txt"].map((fmt) => (
              <button
                key={fmt}
                onClick={() => setSelectedFormat(fmt)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium uppercase transition-colors ${
                  selectedFormat === fmt
                    ? "bg-violet-600 text-white shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="h-9 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0c1424] px-2.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500"
          >
            <option value="all">All Statuses</option>
            <option value="ready">Ready / Indexed</option>
            <option value="processing">In Progress</option>
            <option value="failed">Failed</option>
          </select>

          {/* Sorting */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="h-9 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0c1424] px-2.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500"
          >
            <option value="newest">Sort: Newest</option>
            <option value="oldest">Sort: Oldest</option>
            <option value="name">Sort: Name (A-Z)</option>
            <option value="size">Sort: Size</option>
          </select>

          {/* Refresh Action */}
          <Button
            size="sm"
            variant="outline"
            disabled={loading}
            onClick={() => fetchDocuments(true)}
            className="h-9 px-2.5 gap-1.5 text-xs"
            title="Refresh document list"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>

          {/* View Mode Switcher */}
          <div className="flex items-center rounded-xl border border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/[0.02] p-0.5">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-lg transition-colors ${
                viewMode === "grid"
                  ? "bg-violet-600 text-white"
                  : "text-slate-400 hover:text-slate-700 dark:hover:text-white"
              }`}
              title="Grid view"
            >
              <Grid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded-lg transition-colors ${
                viewMode === "table"
                  ? "bg-violet-600 text-white"
                  : "text-slate-400 hover:text-slate-700 dark:hover:text-white"
              }`}
              title="Table view"
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Document Content Area */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/60 dark:bg-[#0c1424]/60 p-4 space-y-3"
            >
              <div className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-xl" />
                <div className="space-y-1.5 flex-1">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
              <Skeleton className="h-14 rounded-xl" />
              <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/10">
                <Skeleton className="h-4 w-1/4" />
                <Skeleton className="h-8 w-1/3 rounded-lg" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-8 text-center space-y-3">
          <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-2xl bg-rose-500/10 text-rose-500">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white">
            Failed to Load Documents
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">{error}</p>
          <Button
            size="sm"
            onClick={() => fetchDocuments(true)}
            className="gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Retry Connection</span>
          </Button>
        </div>
      ) : filteredDocs.length === 0 ? (
        documents.length === 0 ? (
          <EmptyState
            title="No Documents Uploaded Yet"
            description="Drag and drop PDF, DOCX, or TXT documents above to extract text and build your FAISS semantic index."
            actionLabel="Browse Documents"
            onAction={() => fileInputRef.current?.click()}
          />
        ) : (
          <div className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/40 dark:bg-white/[0.02] p-8 text-center space-y-3">
            <Filter className="h-8 w-8 mx-auto text-slate-400" />
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
              No Matching Documents Found
            </h4>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              No documents match your active search and filter combination.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setSearch("");
                setSelectedFormat("all");
                setSelectedStatus("all");
              }}
            >
              Clear Filters
            </Button>
          </div>
        )
      ) : viewMode === "grid" ? (
        /* Grid View of Document Cards */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDocs.map((doc) => (
            <div
              key={doc.id}
              className="group rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 p-4 sm:p-5 backdrop-blur-xl transition-all hover:border-violet-500/40 hover:shadow-lg hover:shadow-violet-500/5 flex flex-col justify-between"
            >
              <div className="space-y-3">
                {/* Header: Icon, filename, status */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-slate-100 dark:bg-white/[0.05] border border-slate-200 dark:border-white/10">
                      {getFileIcon(doc.file_type)}
                    </div>
                    <div>
                      <h4
                        className="font-bold text-sm text-slate-900 dark:text-white truncate max-w-[160px] sm:max-w-[200px]"
                        title={doc.filename}
                      >
                        {doc.filename}
                      </h4>
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5 font-mono">
                        <span className="uppercase">{doc.file_type}</span>
                        <span>•</span>
                        <span>{formatBytes(doc.file_size_bytes)}</span>
                      </div>
                    </div>
                  </div>

                  <div>{getStatusBadge(doc.status)}</div>
                </div>

                {/* Metadata details */}
                <div className="grid grid-cols-2 gap-2 text-xs py-2 border-t border-b border-slate-100 dark:border-white/10 font-mono text-slate-600 dark:text-slate-300">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block font-sans">
                      {doc.file_type === "pdf" ? "Pages" : "Sections"}
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-100">
                      {doc.page_count ?? doc.section_count ?? "1"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block font-sans">
                      Words
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-100">
                      {doc.word_count ? doc.word_count.toLocaleString() : "N/A"}
                    </span>
                  </div>
                </div>

                {/* Upload timestamp */}
                <div className="text-[11px] text-slate-400">
                  Indexed on {formatDate(getDocDate(doc))}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100 dark:border-white/10">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSelectedDocId(doc.id);
                    setDetailModalOpen(true);
                  }}
                  className="gap-1.5 text-xs h-8 px-3"
                >
                  <Eye className="h-3.5 w-3.5 text-violet-500" />
                  <span>Inspect Text</span>
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setDocToDelete(doc);
                    setDeleteModalOpen(true);
                  }}
                  className="text-rose-500 hover:text-rose-600 hover:bg-rose-500/10 h-8 px-2"
                  title="Delete document"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="overflow-x-auto rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/70 dark:bg-[#0c1424]/60 backdrop-blur-xl">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.02] text-slate-400 uppercase text-[10px] font-bold tracking-wider">
              <tr>
                <th className="py-3 px-4">Document</th>
                <th className="py-3 px-4">Format</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Pages/Sections</th>
                <th className="py-3 px-4">Words</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Ingested At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
              {filteredDocs.map((doc) => (
                <tr
                  key={doc.id}
                  className="hover:bg-violet-500/[0.03] transition-colors"
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 dark:bg-white/[0.04]">
                        {getFileIcon(doc.file_type)}
                      </div>
                      <div className="truncate max-w-xs font-semibold text-slate-900 dark:text-white" title={doc.filename}>
                        {doc.filename}
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 font-mono uppercase text-slate-500">
                    {doc.file_type}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-500">
                    {formatBytes(doc.file_size_bytes)}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-500">
                    {doc.page_count ?? doc.section_count ?? "1"}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-500">
                    {doc.word_count ? doc.word_count.toLocaleString() : "N/A"}
                  </td>
                  <td className="py-3 px-4">
                    {getStatusBadge(doc.status)}
                  </td>
                  <td className="py-3 px-4 text-slate-400">
                    {formatDate(getDocDate(doc))}
                  </td>
                  <td className="py-3 px-4 text-right space-x-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setSelectedDocId(doc.id);
                        setDetailModalOpen(true);
                      }}
                      className="h-8 w-8 p-0 text-violet-500"
                      title="Inspect extracted text"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setDocToDelete(doc);
                        setDeleteModalOpen(true);
                      }}
                      className="h-8 w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-500/10"
                      title="Delete document"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Document Detail Preview Dialog */}
      <DocumentDetailDialog
        documentId={selectedDocId}
        open={detailModalOpen}
        onOpenChange={(open) => {
          setDetailModalOpen(open);
          if (!open) setSelectedDocId(null);
        }}
        onRequestDelete={(doc) => {
          setDocToDelete(doc);
          setDeleteModalOpen(true);
        }}
        rawBaseUrl={rawBaseUrl}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        open={deleteModalOpen}
        onOpenChange={(open) => {
          setDeleteModalOpen(open);
          if (!open) setDocToDelete(null);
        }}
        document={docToDelete}
        onConfirm={handleConfirmDelete}
        isDeleting={isDeleting}
      />
    </div>
  );
}
