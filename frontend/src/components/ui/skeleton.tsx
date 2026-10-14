import { cn } from "@/lib/utils";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg bg-slate-200/80 dark:bg-white/[0.06]",
        className
      )}
      {...props}
    />
  );
}
