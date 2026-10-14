import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-slate-700 dark:text-slate-200 border-slate-200 dark:border-white/10",
        success:
          "border-emerald-500/30 bg-emerald-500/10 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 font-medium",
        violet:
          "border-violet-500/30 bg-violet-500/10 dark:bg-violet-500/15 text-violet-700 dark:text-violet-300 font-medium",
        blue:
          "border-blue-500/30 bg-blue-500/10 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 font-medium",
        warning:
          "border-amber-500/30 bg-amber-500/10 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 font-medium",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
