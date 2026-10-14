import {
  Menu,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { Tooltip } from "@/components/ui/tooltip";

interface HeaderProps {
  activeView: string;
  onMobileMenuToggle: () => void;
  backendOnline: boolean | null;
  backendLoading: boolean;
  latency: number | null;
  onRefreshHealth: () => void;
}

const VIEW_TITLES: Record<string, { title: string; subtitle: string }> = {
  overview: {
    title: "System Overview",
    subtitle: "Real-time engine diagnostics, metrics, and activity",
  },
  documents: {
    title: "Document Library",
    subtitle: "Manage, inspect, and pre-validate source documents",
  },
  chat: {
    title: "AI Workspace",
    subtitle: "Grounded conversational intelligence with source citations",
  },
  settings: {
    title: "Settings & Configuration",
    subtitle: "LLM inference, vector chunking, and system parameters",
  },
};

export function Header({
  activeView,
  onMobileMenuToggle,
  backendOnline,
  backendLoading,
  latency,
  onRefreshHealth,
}: HeaderProps) {
  const info = VIEW_TITLES[activeView] || {
    title: "DocuMind AI",
    subtitle: "Document Intelligence",
  };

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-slate-200/80 dark:border-white/10 bg-white/80 dark:bg-[#070b14]/80 px-4 sm:px-6 lg:px-8 backdrop-blur-xl transition-colors">
      {/* Left side: Mobile Toggle + Breadcrumb Title */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMobileMenuToggle}
          className="lg:hidden h-9 w-9 text-slate-600 dark:text-slate-300"
          aria-label="Toggle navigation drawer"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white tracking-tight">
              {info.title}
            </h1>
          </div>
          <p className="hidden md:block text-xs text-slate-500 dark:text-slate-400">
            {info.subtitle}
          </p>
        </div>
      </div>

      {/* Right side: Connection Status & Theme Toggle */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Live Backend Connection Indicator */}
        <Tooltip
          content={
            backendLoading
              ? "Connecting to FastAPI backend on port 8000..."
              : backendOnline
              ? `FastAPI Backend Online (${latency ?? 0}ms)`
              : "FastAPI Backend Offline (port 8000)"
          }
          side="bottom"
        >
          <div
            onClick={onRefreshHealth}
            className="flex items-center gap-2 rounded-full border border-slate-200 dark:border-white/10 bg-slate-100/70 dark:bg-white/[0.03] px-2.5 sm:px-3 py-1 cursor-pointer hover:bg-slate-200/60 dark:hover:bg-white/[0.06] transition-colors"
          >
            <span className="relative flex h-2 w-2">
              {backendLoading ? (
                <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping" />
              ) : backendOnline ? (
                <>
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </>
              ) : (
                <span className="h-2 w-2 rounded-full bg-rose-500" />
              )}
            </span>
            <span className="text-[11px] sm:text-xs font-medium text-slate-700 dark:text-slate-300">
              {backendLoading
                ? "Connecting..."
                : backendOnline
                ? "API Connected"
                : "Offline"}
            </span>
            {latency !== null && (
              <span className="hidden sm:inline text-[10px] text-slate-400">
                {latency}ms
              </span>
            )}
            <RefreshCw
              className={`h-3 w-3 text-slate-400 ${backendLoading ? "animate-spin" : ""}`}
            />
          </div>
        </Tooltip>

        {/* Theme Toggle */}
        <ThemeToggle />
      </div>
    </header>
  );
}
