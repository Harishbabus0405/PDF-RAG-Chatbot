import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/35 hover:brightness-110",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-slate-200 dark:border-white/10 bg-white/50 dark:bg-white/[0.02] hover:bg-slate-100 dark:hover:bg-white/5 text-slate-700 dark:text-slate-200",
        secondary:
          "bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-slate-100 hover:bg-slate-200 dark:hover:bg-white/15",
        ghost:
          "hover:bg-slate-100 dark:hover:bg-white/5 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white",
        glass:
          "bg-white/80 dark:bg-white/[0.05] border border-slate-200/80 dark:border-white/10 backdrop-blur-md hover:bg-white dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 shadow-sm",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-lg px-3 text-xs",
        lg: "h-11 rounded-xl px-6 text-base",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
