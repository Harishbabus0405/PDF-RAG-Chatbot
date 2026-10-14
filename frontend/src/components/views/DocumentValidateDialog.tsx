import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileCheck,
  RefreshCw,
  Send,
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
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

interface DocumentValidateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rawBaseUrl: string;
}

interface ValidationResult {
  success: boolean;
  message: string;
  data?: {
    filename: string;
    is_valid: boolean;
    file_type: string;
    message: string;
  };
  error_code?: string;
  details?: Array<{ field?: string; issue: string }>;
}

export function DocumentValidateDialog({
  open,
  onOpenChange,
  rawBaseUrl,
}: DocumentValidateDialogProps) {
  const { toast } = useToast();
  const [filename, setFilename] = useState("annual_audit_report.pdf");
  const [fileSizeMb, setFileSizeMb] = useState("2.5");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);

  const handleValidate = async () => {
    setLoading(true);
    setResult(null);

    const sizeBytes = Math.round(parseFloat(fileSizeMb || "1") * 1024 * 1024);

    try {
      const response = await fetch(`${rawBaseUrl}/api/v1/documents/validate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          filename: filename.trim(),
          file_size_bytes: sizeBytes,
        }),
      });

      const json = await response.json();
      setResult(json);

      if (response.ok && json.success) {
        toast.success(
          "Validation Passed",
          `Document '${filename}' meets format and size criteria.`
        );
      } else {
        toast.error(
          "Validation Failed",
          json.message || "Document does not satisfy backend constraints."
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error";
      setResult({
        success: false,
        message: `Failed to connect to backend: ${msg}`,
        error_code: "NETWORK_ERROR",
      });
      toast.error("Network Error", "Unable to contact FastAPI backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/20">
              <FileCheck className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle>Pre-Validate Document</DialogTitle>
              <DialogDescription>
                Live test against FastAPI <code className="text-violet-500 dark:text-violet-400 font-mono text-xs">POST /api/v1/documents/validate</code>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 my-2">
          {/* Filename Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Filename (with extension)
            </label>
            <Input
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              placeholder="e.g. quarterly_report.pdf, security.docx, log.txt"
              disabled={loading}
            />
            <div className="flex gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => setFilename("report.pdf")}
                className="text-[10px] text-violet-600 dark:text-violet-400 hover:underline"
              >
                Try .pdf
              </button>
              <span className="text-slate-400 text-[10px]">•</span>
              <button
                type="button"
                onClick={() => setFilename("contract.docx")}
                className="text-[10px] text-violet-600 dark:text-violet-400 hover:underline"
              >
                Try .docx
              </button>
              <span className="text-slate-400 text-[10px]">•</span>
              <button
                type="button"
                onClick={() => setFilename("unsupported.exe")}
                className="text-[10px] text-rose-500 hover:underline"
              >
                Try .exe (Invalid)
              </button>
            </div>
          </div>

          {/* File Size Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              File Size (in Megabytes)
            </label>
            <Input
              type="number"
              step="0.5"
              min="0.1"
              value={fileSizeMb}
              onChange={(e) => setFileSizeMb(e.target.value)}
              placeholder="2.5"
              disabled={loading}
            />
            <p className="text-[11px] text-slate-400">
              Maximum allowable file size: 50 MB
            </p>
          </div>

          {/* Live Result Feedback Banner */}
          {result && (
            <div
              className={`rounded-xl border p-3.5 text-xs animate-in fade-in duration-200 ${
                result.success
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200"
                  : "border-rose-500/30 bg-rose-500/10 text-rose-900 dark:text-rose-200"
              }`}
            >
              <div className="flex items-center gap-2 font-bold mb-1">
                {result.success ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    <span>Validation Passed (200 OK)</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4 text-rose-500" />
                    <span>Error: {result.error_code || "VALIDATION_FAILED"}</span>
                  </>
                )}
              </div>
              <p className="text-xs opacity-90 leading-relaxed">
                {result.message}
              </p>
              {result.details && result.details.length > 0 && (
                <ul className="mt-2 list-disc list-inside space-y-0.5 text-[11px] font-mono">
                  {result.details.map((d, i) => (
                    <li key={i}>
                      {d.field ? `${d.field}: ` : ""}
                      {d.issue}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            size="sm"
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleValidate}
            size="sm"
            disabled={loading || !filename.trim()}
            className="gap-1.5"
          >
            {loading ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            <span>Test Validation API</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
