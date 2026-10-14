import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <Tooltip content={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} side="bottom">
      <Button
        variant="outline"
        size="icon"
        onClick={toggleTheme}
        className="h-9 w-9 rounded-xl border-slate-200 dark:border-white/10 bg-white/50 dark:bg-white/[0.04] text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white"
        aria-label="Toggle theme"
      >
        {theme === "dark" ? (
          <Sun className="h-4 w-4 text-amber-400 transition-transform rotate-0 hover:rotate-45 duration-300" />
        ) : (
          <Moon className="h-4 w-4 text-indigo-600 transition-transform -rotate-12 hover:rotate-0 duration-300" />
        )}
      </Button>
    </Tooltip>
  );
}
