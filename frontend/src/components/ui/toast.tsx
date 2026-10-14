import * as React from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastType = "success" | "error" | "info";

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, "id">) => void;
  removeToast: (id: string) => void;
  toast: {
    success: (title: string, description?: string) => void;
    error: (title: string, description?: string) => void;
    info: (title: string, description?: string) => void;
  };
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = React.useCallback(
    (item: Omit<ToastItem, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastItem = { ...item, id };
      setToasts((prev) => [...prev.slice(-4), newToast]);

      const duration = item.duration ?? 4000;
      window.setTimeout(() => {
        removeToast(id);
      }, duration);
    },
    [removeToast]
  );

  const toast = React.useMemo(
    () => ({
      success: (title: string, description?: string) =>
        addToast({ type: "success", title, description }),
      error: (title: string, description?: string) =>
        addToast({ type: "error", title, description }),
      info: (title: string, description?: string) =>
        addToast({ type: "info", title, description }),
    }),
    [addToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, toast }}>
      {children}
      {/* Toast viewport container */}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex max-w-md w-full flex-col gap-2 pointer-events-none px-4 sm:px-0"
      >
        {toasts.map((item) => (
          <div
            key={item.id}
            className={cn(
              "pointer-events-auto flex items-start gap-3 rounded-xl border p-4 shadow-xl backdrop-blur-xl transition-all duration-300 animate-in slide-in-from-bottom-5",
              item.type === "success" &&
                "border-emerald-500/30 bg-[#061e16]/90 text-emerald-100 dark:bg-[#061e16]/90",
              item.type === "error" &&
                "border-rose-500/30 bg-[#250d14]/90 text-rose-100 dark:bg-[#250d14]/90",
              item.type === "info" &&
                "border-indigo-500/30 bg-[#0d152b]/90 text-indigo-100 dark:bg-[#0d152b]/90"
            )}
          >
            <div className="flex-shrink-0 mt-0.5">
              {item.type === "success" && (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              )}
              {item.type === "error" && (
                <AlertCircle className="h-5 w-5 text-rose-400" />
              )}
              {item.type === "info" && <Info className="h-5 w-5 text-indigo-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold">{item.title}</p>
              {item.description && (
                <p className="mt-0.5 text-xs opacity-85 leading-relaxed">
                  {item.description}
                </p>
              )}
            </div>
            <button
              onClick={() => removeToast(item.id)}
              className="flex-shrink-0 rounded-lg p-1 opacity-70 hover:opacity-100 hover:bg-white/10 transition-opacity"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
