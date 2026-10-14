import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatView } from "@/components/views/ChatView";
import { DocumentsView } from "@/components/views/DocumentsView";
import { OverviewView, type HealthData } from "@/components/views/OverviewView";
import { SettingsView } from "@/components/views/SettingsView";
import { ThemeProvider } from "@/lib/theme";
import { ToastProvider } from "@/components/ui/toast";

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <WorkspaceShell />
      </ToastProvider>
    </ThemeProvider>
  );
}

function WorkspaceShell() {
  const [activeView, setActiveView] = useState<string>("overview");
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Live health state
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [documentCount, setDocumentCount] = useState<number | null>(null);

  // Dynamic API URL resolution with resilient auto-discovery
  const configuredApiBaseUrl =
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
  const initialBaseUrl = configuredApiBaseUrl.replace(/\/api\/?$/, "");

  const [activeBaseUrl, setActiveBaseUrl] = useState<string>(initialBaseUrl);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();

    // Candidates to probe: current activeBaseUrl, 127.0.0.1:8000, and localhost:8000
    const candidateUrls = Array.from(
      new Set([
        activeBaseUrl,
        "http://127.0.0.1:8000",
        "http://localhost:8000",
      ])
    );

    let lastError: Error | null = null;
    let successfulData: HealthData | null = null;
    let connectedBaseUrl = activeBaseUrl;

    for (const candidate of candidateUrls) {
      try {
        let res = await fetch(`${candidate}/health`, {
          headers: { Accept: "application/json" },
        });
        if (!res.ok) {
          res = await fetch(`${candidate}/api/health`, {
            headers: { Accept: "application/json" },
          });
        }
        if (res.ok) {
          successfulData = await res.json();
          connectedBaseUrl = candidate;
          break;
        }
      } catch (err: unknown) {
        lastError = err instanceof Error ? err : new Error(String(err));
      }
    }

    if (successfulData) {
      setLatency(Math.round(performance.now() - start));
      setHealth(successfulData);
      setActiveBaseUrl(connectedBaseUrl);

      // Proactively fetch live document count for sidebar badge
      try {
        const docRes = await fetch(`${connectedBaseUrl}/api/v1/documents?limit=1`);
        if (docRes.ok) {
          const docJson = await docRes.json();
          if (docJson.success && docJson.data && typeof docJson.data.total === "number") {
            setDocumentCount(docJson.data.total);
          }
        }
      } catch {
        // Non-critical, ignore
      }
    } else {
      const message = lastError?.message || "Failed to connect to backend";
      setError(message);
      setHealth(null);
      setLatency(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="relative flex min-h-screen bg-slate-50 dark:bg-[#070b14] text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Background ambient lighting gradients */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="absolute -left-[15%] -top-[10%] h-[550px] w-[550px] rounded-full bg-violet-600/10 dark:bg-violet-600/15 blur-[140px]" />
        <div className="absolute right-[5%] top-[10%] h-[450px] w-[450px] rounded-full bg-blue-600/10 dark:bg-blue-600/15 blur-[140px]" />
        <div className="absolute bottom-[5%] left-[25%] h-[400px] w-[400px] rounded-full bg-indigo-600/5 dark:bg-indigo-600/10 blur-[130px]" />
      </div>

      {/* Persistent Desktop Sidebar & Mobile Drawer */}
      <Sidebar
        activeView={activeView}
        onSelectView={setActiveView}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        groqConfigured={Boolean(health?.groq_configured)}
        documentCount={documentCount}
      />

      {/* Main Content Column */}
      <div className="relative flex flex-1 flex-col min-w-0 z-10">
        {/* Top Header */}
        <Header
          activeView={activeView}
          onMobileMenuToggle={() => setMobileMenuOpen((prev) => !prev)}
          backendOnline={Boolean(health)}
          backendLoading={loading}
          latency={latency}
          onRefreshHealth={fetchHealth}
        />

        {/* View Content Canvas */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          <div className="mx-auto max-w-7xl">
            {activeView === "overview" && (
              <OverviewView
                rawBaseUrl={activeBaseUrl}
                backendError={error}
                onNavigateToDocuments={() => setActiveView("documents")}
                onNavigateToChat={() => setActiveView("chat")}
              />
            )}

            {activeView === "documents" && (
              <DocumentsView
                rawBaseUrl={activeBaseUrl}
                onDocumentCountChange={setDocumentCount}
              />
            )}

            {activeView === "chat" && (
              <ChatView
                rawBaseUrl={activeBaseUrl}
                onNavigateToDocuments={() => setActiveView("documents")}
              />
            )}

            {activeView === "settings" && (
              <SettingsView
                health={health}
                loading={loading}
                latency={latency}
                rawBaseUrl={activeBaseUrl}
                onRefreshHealth={fetchHealth}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
