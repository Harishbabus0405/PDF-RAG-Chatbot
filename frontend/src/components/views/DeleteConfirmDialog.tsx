import { AlertTriangle, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { type DocumentMetadata } from "@/lib/api";

interface DeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  document: DocumentMetadata | null;
  onConfirm: (doc: DocumentMetadata) => Promise<void>;
  isDeleting: boolean;
}

export function DeleteConfirmDialog({
  open,
  onOpenChange,
  document,
  onConfirm,
  isDeleting,
}: DeleteConfirmDialogProps) {
  if (!document) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-500">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-base sm:text-lg text-slate-900 dark:text-white">
                Delete Document
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                This action is permanent and cannot be undone.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="my-4 space-y-3">
          <div className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] p-3 text-xs">
            <div className="font-semibold text-slate-800 dark:text-slate-200 break-all">
              {document.filename}
            </div>
            <div className="flex items-center gap-2 mt-1 text-slate-400 font-mono text-[11px]">
              <span className="uppercase">{document.file_type}</span>
              <span>•</span>
              <span>ID: {document.id}</span>
            </div>
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Deleting this document will permanently remove the original file and metadata from server storage, and immediately purge all associated vector embeddings from the FAISS search index.
          </p>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            size="sm"
            disabled={isDeleting}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            disabled={isDeleting}
            onClick={() => onConfirm(document)}
            className="gap-1.5"
          >
            {isDeleting ? (
              <>
                <span className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete Permanently</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
