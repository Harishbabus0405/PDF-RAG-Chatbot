import * as React from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: string;
  children: React.ReactElement;
  side?: "top" | "bottom" | "left" | "right";
  className?: string;
}

export function Tooltip({
  content,
  children,
  side = "top",
  className,
}: TooltipProps) {
  const [visible, setVisible] = React.useState(false);
  const timeoutRef = React.useRef<number | undefined>(undefined);

  const showTooltip = () => {
    timeoutRef.current = window.setTimeout(() => {
      setVisible(true);
    }, 150);
  };

  const hideTooltip = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  };

  const sideClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}
      {visible && (
        <div
          role="tooltip"
          className={cn(
            "pointer-events-none absolute z-50 whitespace-nowrap rounded-md bg-slate-900/95 dark:bg-slate-950/95 px-2.5 py-1 text-[11px] font-medium text-slate-100 shadow-xl border border-white/10 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-md",
            sideClasses[side],
            className
          )}
        >
          {content}
        </div>
      )}
    </div>
  );
}
