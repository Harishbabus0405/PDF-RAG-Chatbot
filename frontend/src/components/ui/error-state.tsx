import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "An Error Occurred",
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-500/5 dark:bg-rose-500/10 p-8 text-center",
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-rose-500/20 text-rose-500 dark:text-rose-400 mb-4 ring-1 ring-rose-500/30">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold text-rose-950 dark:text-rose-200">
        {title}
      </h3>
      <p className="mt-1.5 max-w-md text-sm text-rose-800/80 dark:text-rose-300/80">
        {message}
      </p>
      {onRetry && (
        <div className="mt-5">
          <Button
            onClick={onRetry}
            size="sm"
            variant="outline"
            className="gap-2 border-rose-500/30 hover:bg-rose-500/10 text-rose-600 dark:text-rose-300"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Try Again</span>
          </Button>
        </div>
      )}
    </div>
  );
}
