import * as React from "react";
import { FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.01] px-6 py-12 text-center",
        className
      )}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-500/10 dark:bg-violet-500/10 text-violet-600 dark:text-violet-400 mb-4 ring-1 ring-violet-500/20">
        {icon || <FolderOpen className="h-7 w-7" />}
      </div>
      <h3 className="text-base font-semibold text-slate-900 dark:text-white">
        {title}
      </h3>
      <p className="mt-1.5 max-w-sm text-sm text-slate-500 dark:text-slate-400">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-6">
          <Button onClick={onAction} size="sm" variant="outline">
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
