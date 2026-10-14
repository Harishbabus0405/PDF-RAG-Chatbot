import { useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  FileCheck,
  FileCode,
  FileText,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ChatSource } from "@/lib/api";

interface CitationCardProps {
  source: ChatSource;
  index: number;
}

export function CitationCard({ source, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    switch (ext) {
      case "pdf":
        return <FileText className="h-3.5 w-3.5 text-rose-500" />;
      case "docx":
        return <FileCheck className="h-3.5 w-3.5 text-blue-500" />;
      default:
        return <FileCode className="h-3.5 w-3.5 text-emerald-500" />;
    }
  };

  const copyExcerpt = () => {
    navigator.clipboard.writeText(source.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const scorePercentage = Math.round(Math.max(0, Math.min(1, source.score)) * 100);
  const isLongText = source.text.length > 220;
  const displayText = expanded || !isLongText ? source.text : `${source.text.slice(0, 220)}...`;

  return (
    <div className="group rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] p-3 text-xs transition-all hover:border-violet-500/40 hover:bg-slate-50 dark:hover:bg-white/[0.04] shadow-sm">
      {/* Citation Header */}
      <div className="flex flex-wrap items-center justify-between gap-1.5 pb-2 border-b border-slate-200/60 dark:border-white/5">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-white dark:bg-white/10 text-[10px] font-bold text-slate-500 dark:text-slate-400">
            {index + 1}
          </span>
          {getFileIcon(source.filename)}
          <span
            className="font-semibold text-slate-900 dark:text-slate-100 truncate max-w-[180px] sm:max-w-xs"
            title={source.filename}
          >
            {source.filename}
          </span>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {source.page_number && (
            <Badge variant="outline" className="text-[10px] py-0 px-1.5">
              Page {source.page_number}
            </Badge>
          )}

          {source.section_index && !source.page_number && (
            <Badge variant="outline" className="text-[10px] py-0 px-1.5">
              Sec {source.section_index}
            </Badge>
          )}

          <Badge variant="violet" className="text-[10px] py-0 px-1.5 gap-1">
            <Sparkles className="h-2.5 w-2.5" />
            {scorePercentage}% Match
          </Badge>

          <button
            onClick={copyExcerpt}
            aria-label="Copy cited excerpt"
            className="p-1 rounded hover:bg-slate-200 dark:hover:bg-white/10 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
            title="Copy cited text"
          >
            {copied ? (
              <Check className="h-3 w-3 text-emerald-500" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </button>
        </div>
      </div>

      {/* Heading context if available */}
      {source.heading && (
        <div className="mt-1.5 text-[11px] font-medium text-violet-700 dark:text-violet-300">
          § {source.heading}
        </div>
      )}

      {/* Excerpt Body */}
      <div className="mt-2 text-slate-600 dark:text-slate-300 italic leading-relaxed text-[11px] sm:text-xs">
        "{displayText}"
      </div>

      {/* Expand/Collapse Toggle if text is long */}
      {isLongText && (
        <div className="mt-1.5 flex justify-end">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-[10px] font-semibold text-violet-600 dark:text-violet-400 hover:underline"
          >
            {expanded ? (
              <>
                Show less <ChevronUp className="h-3 w-3" />
              </>
            ) : (
              <>
                Show full excerpt <ChevronDown className="h-3 w-3" />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
