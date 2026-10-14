import {
  Brain,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Settings,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  activeView: string;
  onSelectView: (view: string) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  groqConfigured: boolean;
  documentCount?: number | null;
}

export function Sidebar({
  activeView,
  onSelectView,
  mobileOpen,
  onCloseMobile,
  groqConfigured,
  documentCount,
}: SidebarProps) {
  const navItems = [
    {
      id: "overview",
      label: "Overview",
      icon: LayoutDashboard,
    },
    {
      id: "documents",
      label: "Documents",
      icon: FileText,
      badge:
        documentCount !== null && documentCount !== undefined && documentCount > 0
          ? String(documentCount)
          : undefined,
    },
    {
      id: "chat",
      label: "AI Workspace",
      icon: MessageSquare,
    },
    {
      id: "settings",
      label: "Settings",
      icon: Settings,
    },
  ];

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between p-4 sm:p-5">
      {/* Top: Brand Logo and Navigation */}
      <div className="space-y-6">
        {/* Brand Logo Treatment */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-200/60 dark:border-white/[0.08]">
          <div className="flex items-center gap-3">
            {/* Logo Icon */}
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-blue-500 text-white shadow-md shadow-violet-500/20">
              <Brain className="h-5 w-5" />
            </div>

            {/* Typography */}
            <div>
              <div className="flex items-center gap-1">
                <span className="text-base font-extrabold tracking-tight text-slate-900 dark:text-white">
                  DocuMind
                </span>
                <span className="font-extrabold text-violet-600 dark:text-violet-400">
                  .AI
                </span>
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 tracking-wide font-medium">
                AI Document Assistant
              </p>
            </div>
          </div>

          {/* Close button for mobile */}
          <button
            onClick={onCloseMobile}
            className="lg:hidden rounded-lg p-1 text-slate-400 hover:text-slate-600 dark:hover:text-white"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="space-y-1.5" aria-label="Main Navigation">
          <div className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
            Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectView(item.id);
                  onCloseMobile();
                }}
                className={cn(
                  "group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all duration-200",
                  isActive
                    ? "bg-gradient-to-r from-violet-600/15 via-indigo-600/10 to-transparent text-violet-700 dark:text-white border-l-2 border-violet-600 shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-white/[0.04] hover:text-slate-900 dark:hover:text-slate-200"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      "h-4 w-4 transition-transform group-hover:scale-110",
                      isActive
                        ? "text-violet-600 dark:text-violet-400"
                        : "text-slate-400 dark:text-slate-500"
                    )}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={cn(
                      "rounded-md px-1.5 py-0.5 text-[10px] font-bold",
                      isActive
                        ? "bg-violet-600/20 text-violet-700 dark:text-violet-300"
                        : "bg-slate-200/70 dark:bg-white/10 text-slate-600 dark:text-slate-400"
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom: Project Info & RAG Engine Status */}
      <div className="space-y-3 pt-4 border-t border-slate-200/60 dark:border-white/[0.08]">
        <div className="rounded-xl border border-slate-200/80 dark:border-white/[0.06] bg-slate-50/70 dark:bg-white/[0.02] p-3 text-xs space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-700 dark:text-slate-300 text-[11px]">System Status</span>
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {groqConfigured ? "Groq RAG Ready" : "Local Mode"}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">
            FastAPI • FAISS • Sentence Transformers
          </p>
        </div>

        {/* Portfolio Credit */}
        <div className="flex items-center justify-between px-1 text-[11px] text-slate-400 dark:text-slate-500">
          <span>AI Portfolio Project</span>
          <span>v1.0</span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:flex h-screen w-64 flex-col border-r border-slate-200/80 dark:border-white/10 bg-white dark:bg-[#070b14] z-30 transition-colors">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity animate-in fade-in"
            onClick={onCloseMobile}
            aria-hidden="true"
          />

          {/* Drawer Window */}
          <div className="fixed inset-y-0 left-0 w-72 max-w-[85vw] bg-white dark:bg-[#070b14] shadow-2xl border-r border-slate-200 dark:border-white/10 transition-transform animate-in slide-in-from-left duration-200 z-10">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
